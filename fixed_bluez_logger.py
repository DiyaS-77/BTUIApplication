import os
import re
import subprocess
import time
import logging
from PyQt6.QtCore import QDateTime, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QTextEdit
from test_framework.utils import check_command_running, kill_process, run
from test_framework.logger import Logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class LogWatcher(FileSystemEventHandler):
    def __init__(self, log_file, text_browser):
        self.log_file = log_file
        self.text_browser = text_browser
        self.last_position = 0

    def on_modified(self, event):
        """Constantly modifying the logs using the LogWatcher class"""
        if event.src_path == self.log_file:
            with open(self.log_file, 'r') as f:
                f.seek(self.last_position)
                content = f.read()
                if content:
                    self.text_browser.append(content)
                    self.last_position = f.tell()


class HcidumpLogReader(QThread):
    log_updated = pyqtSignal(str)

    def __init__(self, logfile_path, parent=None):
        super().__init__(parent)
        self.logfile_path = logfile_path
        self._running = True
        self.last_position = 0

    def run(self):
        while self._running:
            try:
                if os.path.exists(self.logfile_path):
                    with open(self.logfile_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_logs = f.read()
                        if new_logs:
                            self.log_updated.emit(new_logs)
                        self.last_position = f.tell()
                time.sleep(0.5)  # Reduced sleep time for more responsive updates
            except Exception as e:
                logging.error(f"Error reading hcidump log: {e}")
                time.sleep(1)

    def stop(self):
        self._running = False
        self.wait(timeout=5000)  # Wait up to 5 seconds for thread to finish


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def run_command(log_path, command, log_file=None):
    """Function for the run command"""
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    logging.info(f"Command: {command}\nOutput: {output.stdout}")
    return output


class BluezLogger:
    def __init__(self, log_path):
        super().__init__()
        # Pulseaudio attributes
        self.pulseaudio_log_name = None
        self.pulseaudio_file_position = None
        self.pulseaudio_logfile_fd = None
        self.pulseaudio_process = None
        
        # Bluetoothd attributes
        self.bluetoothd_file_position = None
        self.bluetoothd_logfile_fd = None
        self.bluetoothd_log_name = None
        self.bluetoothd_process = None
        
        # HCI dump attributes
        self.hcidump_process = None
        self.hci_log_reader = None
        self.logfile_fd = None
        self.file_position = None
        self.hcidump_log_name = None
        self.hci_dump_started = False
        
        # General attributes
        self.bd_address = None
        self.controllers_list = {}
        self.handles = None
        self.log = Logger("BluezLogger")
        self.log_path = log_path
        self.interface = None
        self.dbus_process = None
        
        # UI scroll management
        self.bluetoothd_scrollbar_dragged_down = False
        self.pulseaudio_scrollbar_dragged_down = False
        self.hcidump_scrollbar_dragged_down = False

    def start_dbus_service(self):
        """Starts the D-Bus service."""
        print("Starting D-Bus service...")
        try:
            # Check if D-Bus is already running
            result = subprocess.run(['pgrep', '-f', 'dbus-daemon.*--system'], 
                                  capture_output=True, text=True)
            if result.stdout.strip():
                print("D-Bus service already running.")
                return True
                
            dbus_command = "/usr/local/bluez/dbus-1.12.20/bin/dbus-daemon --system --nopidfile"
            self.dbus_process = subprocess.Popen(dbus_command, shell=True)
            time.sleep(2)
            print("D-Bus service started successfully.")
            return True
        except Exception as e:
            print(f"Error starting D-Bus service: {e}")
            return False

    def start_bluetoothd_logs(self, log_text_browser=None):
        """Starts the bluetoothd logs and redirects to the file."""
        try:
            print(f"Starting bluetoothd logs in: {self.log_path}")
            
            # Stop any existing bluetoothd process
            self.stop_bluetoothd_logs()
            
            bluetoothd_command = '/usr/local/bluez/bluez-tools/libexec/bluetooth/bluetoothd -nd --compat'
            self.bluetoothd_log_name = os.path.join(self.log_path, 'bluetoothd.log')
            
            # Start bluetoothd process with log redirection
            with open(self.bluetoothd_log_name, 'w') as log_file:
                self.bluetoothd_process = subprocess.Popen(
                    bluetoothd_command.split(),
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
            
            time.sleep(2)
            print(f"bluetoothd process started: {self.bluetoothd_log_name}")
            
            self.bluetoothd_logfile_fd = open(self.bluetoothd_log_name, 'r')
            self.bluetoothd_file_position = self.bluetoothd_logfile_fd.tell()
            
            if log_text_browser is not None:
                print("Creating LogWatcher for bluetoothd logs")
                self.bluetoothd_log_watcher = LogWatcher(self.bluetoothd_log_name, log_text_browser)
                self.observer = Observer()
                self.observer.schedule(self.bluetoothd_log_watcher, 
                                     path=os.path.dirname(self.bluetoothd_log_name), 
                                     recursive=False)
                self.observer.start()
                
                self.update_log_timer = QTimer()
                self.update_log_timer.timeout.connect(self.update_bluetoothd_log)
                self.update_log_timer.start(1000)
            
            return True
        except Exception as e:
            print(f"Error starting bluetoothd logs: {e}")
            return False

    def start_pulseaudio_logs(self, log_text_browser=None):
        """Starts the pulseaudio logs and redirects to the file."""
        try:
            print(f"Starting pulseaudio logs in: {self.log_path}")
            
            # Stop any existing pulseaudio process
            self.stop_pulseaudio_logs()
            
            pulseaudio_command = '/usr/local/bluez/pulseaudio-13.0_for_bluez-5.65/bin/pulseaudio -vvv'
            self.pulseaudio_log_name = os.path.join(self.log_path, 'pulseaudio.log')
            
            # Start pulseaudio process with log redirection
            with open(self.pulseaudio_log_name, 'w') as log_file:
                self.pulseaudio_process = subprocess.Popen(
                    pulseaudio_command.split(),
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
            
            time.sleep(2)
            print(f"pulseaudio process started: {self.pulseaudio_log_name}")
            
            self.pulseaudio_logfile_fd = open(self.pulseaudio_log_name, 'r')
            self.pulseaudio_file_position = self.pulseaudio_logfile_fd.tell()
            
            if log_text_browser is not None:
                print("Creating LogWatcher for pulseaudio logs")
                self.pulseaudio_log_watcher = LogWatcher(self.pulseaudio_log_name, log_text_browser)
                if not hasattr(self, 'observer') or not self.observer:
                    self.observer = Observer()
                self.observer.schedule(self.pulseaudio_log_watcher, 
                                     path=os.path.dirname(self.pulseaudio_log_name), 
                                     recursive=False)
                if not self.observer.is_alive():
                    self.observer.start()
                
                self.update_pulseaudio_log_timer = QTimer()
                self.update_pulseaudio_log_timer.timeout.connect(self.update_pulseaudio_log)
                self.update_pulseaudio_log_timer.start(1000)
            
            return True
        except Exception as e:
            print(f"Error starting pulseaudio logs: {e}")
            return False

    def start_dump_logs(self, interface=None, log_text_browser=None):
        """Starts the hcidump logs for the specified interface."""
        try:
            # Use provided interface or fall back to stored interface
            if interface:
                self.interface = interface
            elif not self.interface:
                print("Error: No interface specified for hcidump")
                return False
            
            print(f"Starting hcidump logs for interface: {self.interface}")
            
            # Stop any existing hcidump process
            self.stop_dump_logs()
            
            # Ensure the interface is up
            bring_up_cmd = f"hciconfig {self.interface} up"
            subprocess.run(bring_up_cmd.split(), capture_output=True)
            time.sleep(1)
            
            # Verify interface is available and up
            check_cmd = f"hciconfig {self.interface}"
            result = subprocess.run(check_cmd.split(), capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error: Interface {self.interface} not available")
                return False
            
            if "UP RUNNING" not in result.stdout:
                print(f"Warning: Interface {self.interface} may not be properly UP")
            
            # Create hcidump log file
            self.hcidump_log_name = os.path.join(self.log_path, f'{self.interface}_hcidump.log')
            
            # Start hcidump process
            hcidump_command = f'/usr/local/bluez/bluez-tools/bin/hcidump -i {self.interface} -Xt'
            print(f"Executing: {hcidump_command}")
            
            with open(self.hcidump_log_name, 'w') as log_file:
                self.hcidump_process = subprocess.Popen(
                    hcidump_command.split(),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    bufsize=1,  # Line buffered
                    universal_newlines=True
                )
            
            # Wait a moment for the process to start
            time.sleep(2)
            
            # Check if process is still running
            if self.hcidump_process.poll() is not None:
                print(f"Error: hcidump process exited immediately with code {self.hcidump_process.returncode}")
                return False
            
            print(f"hcidump process started successfully: {self.hcidump_log_name}")
            
            # Open file for reading
            self.logfile_fd = open(self.hcidump_log_name, 'r')
            self.file_position = self.logfile_fd.tell()
            self.hci_dump_started = True
            
            # Set up UI monitoring if text browser provided
            if log_text_browser is not None:
                print("Setting up HCI dump log reader for UI")
                self.hci_log_reader = HcidumpLogReader(self.hcidump_log_name)
                self.hci_log_reader.log_updated.connect(log_text_browser.append)
                self.hci_log_reader.start()
                print("HCI dump log reader started")
            
            return True
            
        except Exception as e:
            print(f"Error starting hcidump logs: {e}")
            self.hci_dump_started = False
            return False

    def stop_dump_logs(self):
        """Stops the hcidump logs."""
        try:
            print("Stopping HCI dump logs")
            
            # Stop the log reader thread
            if hasattr(self, 'hci_log_reader') and self.hci_log_reader:
                self.hci_log_reader.stop()
                self.hci_log_reader = None
            
            # Close file descriptor
            if self.logfile_fd:
                self.logfile_fd.close()
                self.logfile_fd = None
            
            # Terminate the hcidump process
            if hasattr(self, 'hcidump_process') and self.hcidump_process:
                try:
                    self.hcidump_process.terminate()
                    self.hcidump_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.hcidump_process.kill()
                    self.hcidump_process.wait()
                self.hcidump_process = None
            
            # Kill any remaining hcidump processes for this interface
            if self.interface:
                try:
                    result = subprocess.run(['pgrep', '-f', f'hcidump.*{self.interface}'], 
                                          capture_output=True, text=True)
                    if result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            subprocess.run(['kill', '-TERM', pid])
                        time.sleep(1)
                        # Force kill if still running
                        for pid in pids:
                            subprocess.run(['kill', '-KILL', pid])
                except Exception as e:
                    print(f"Error killing hcidump processes: {e}")
            
            self.hci_dump_started = False
            print("HCI dump logs stopped successfully")
            
        except Exception as e:
            print(f"Error stopping hcidump logs: {e}")

    def stop_bluetoothd_logs(self):
        """Stops the bluetoothd logs."""
        try:
            print("Stopping bluetoothd logs")
            
            if self.bluetoothd_logfile_fd:
                self.bluetoothd_logfile_fd.close()
                self.bluetoothd_logfile_fd = None
            
            if hasattr(self, 'bluetoothd_process') and self.bluetoothd_process:
                self.bluetoothd_process.terminate()
                self.bluetoothd_process.wait(timeout=5)
                self.bluetoothd_process = None
            
            # Kill any remaining bluetoothd processes
            subprocess.run(['pkill', '-f', 'bluetoothd'])
            
        except Exception as e:
            print(f"Error stopping bluetoothd logs: {e}")

    def stop_pulseaudio_logs(self):
        """Stops the pulseaudio logs."""
        try:
            print("Stopping pulseaudio logs")
            
            if self.pulseaudio_logfile_fd:
                self.pulseaudio_logfile_fd.close()
                self.pulseaudio_logfile_fd = None
            
            if hasattr(self, 'pulseaudio_process') and self.pulseaudio_process:
                self.pulseaudio_process.terminate()
                self.pulseaudio_process.wait(timeout=5)
                self.pulseaudio_process = None
            
            # Kill any remaining pulseaudio processes
            subprocess.run(['pkill', '-f', 'pulseaudio'])
            
        except Exception as e:
            print(f"Error stopping pulseaudio logs: {e}")

    def update_bluetoothd_log(self):
        """Constantly updating the bluetoothd logs"""
        if hasattr(self, 'bluetoothd_log_watcher'):
            scrollbar = self.bluetoothd_log_watcher.text_browser.verticalScrollBar()
            at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
            try:
                with open(self.bluetoothd_log_name, 'r') as f:
                    f.seek(self.bluetoothd_log_watcher.last_position)
                    new_logs = f.read()
                    if new_logs:
                        self.bluetoothd_log_watcher.text_browser.append(new_logs)
                        if at_bottom:
                            scrollbar.setValue(scrollbar.maximum())
                    self.bluetoothd_log_watcher.last_position = f.tell()
            except Exception as e:
                logging.error(f"Error updating bluetoothd log: {e}")

    def update_pulseaudio_log(self):
        """Constantly updating the pulseaudio logs"""
        if hasattr(self, 'pulseaudio_log_watcher'):
            scrollbar = self.pulseaudio_log_watcher.text_browser.verticalScrollBar()
            at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
            try:
                with open(self.pulseaudio_log_name, 'r') as f:
                    f.seek(self.pulseaudio_log_watcher.last_position)
                    new_logs = f.read()
                    if new_logs:
                        self.pulseaudio_log_watcher.text_browser.append(new_logs)
                        if at_bottom:
                            scrollbar.setValue(scrollbar.maximum())
                    self.pulseaudio_log_watcher.last_position = f.tell()
            except Exception as e:
                logging.error(f"Error updating pulseaudio log: {e}")

    def get_controller_details(self):
        """Fetching all the relevant controller details"""
        details = {}
        try:
            if not self.interface:
                return details
                
            run_command(self.log_path, f'hciconfig -a {self.interface} up')
            result = run_command(self.log_path, f'hciconfig -a {self.interface}')
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if match := re.match('BD Address: (.*) ACL(.*)', line):
                    details['BD_ADDR'] = match[1]
                elif match := re.match('Link policy: (.*)', line):
                    details['Link policy'] = match[1]
                elif match := re.match('Link mode: (.*)', line):
                    details['Link mode'] = match[1]
                elif match := re.match('Name: (.*)', line):
                    details['Name'] = match[1]
                elif match := re.match('Class: (.*)', line):
                    details['Class'] = match[1]
                elif match := re.match('HCI Version: (.*) .+', line):
                    details['HCI Version'] = match[1]
                elif match := re.match('LMP Version: (.*) .+', line):
                    details['LMP Version'] = match[1]
                elif match := re.match('Manufacturer: (.*)', line):
                    details['Manufacturer'] = match[1]
            
            self.name = details.get('Name')
            self.bd_address = details.get('BD_ADDR')
            self.link_policy = details.get('Link policy')
            self.lmp_version = details.get('LMP Version')
            self.link_mode = details.get('Link mode')
            self.hci_version = details.get('HCI Version')
            self.manufacturer = details.get('Manufacturer')
            
        except Exception as e:
            print(f"Error getting controller details: {e}")
            
        return details

    def cleanup(self):
        """Clean up all resources and processes"""
        print("Cleaning up BluezLogger resources...")
        self.stop_dump_logs()
        self.stop_bluetoothd_logs()
        self.stop_pulseaudio_logs()
        
        if hasattr(self, 'observer') and self.observer:
            self.observer.stop()
            self.observer.join()
        
        if hasattr(self, 'dbus_process') and self.dbus_process:
            self.dbus_process.terminate()
            self.dbus_process.wait()
