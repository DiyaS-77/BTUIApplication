from PyQt6.QtCore import QDateTime, QTimer
from PyQt6.QtGui import QTextCursor
from test_framework.utils import check_command_running
from test_framework.utils import kill_process
from test_framework.utils import run
from test_framework.logger import Logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from test_automation.UI_Application.controller_lib import Controller
from PyQt6.QtCore import QThread
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QTextEdit

import logging
import os
import re
import subprocess
import time


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
            with open(self.logfile_path, 'r') as f:
            #with open(self.logfile_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self.last_position)
                new_logs = f.read()
                if new_logs:
                    self.log_updated.emit(new_logs)
                self.last_position = f.tell()
            time.sleep(1)

    def stop(self):
        self._running = False
        self.wait()


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
def run_command(log_path, command, log_file=None):
    """Function for the run command"""
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    logging.info(f"Command: {command}\nOutput: {output.stdout}")
    return output

class BluezLogger:
    def __init__(self, log_path):
        super().__init__()
        self.pulseaudio_log_name = None
        self.pulseaudio_file_position = None
        self.pulseaudio_logfile_fd = None
        self.bluetoothd_file_position = None
        self.bluetoothd_logfile_fd = None
        self.bluetoothd_log_name = None
        self.bd_address = None
        self.controllers_list = {}
        self.handles = None
        self.log = Logger("UI")
        controller=Controller(self.log)
        self.log_path = log_path
        self.interface = None
        self.logfile_path = '/root/Desktop/BT_Automation/BT_UI'
        self.logfile_fd = None
        self.file_position = None
        self.hcidump_log_name = None
        self.bluetoothd_scrollbar_dragged_down = False
        self.pulseaudio_scrollbar_dragged_down = False
        self.hcidump_scrollbar_dragged_down = False



    def start_dbus_service(self):
        """Starts the D-Bus service."""
        print("Starting D-Bus service...")
        dbus_command = "/usr/local/bluez/dbus-1.12.20/bin/dbus-daemon --system --nopidfile"
        self.dbus_process = subprocess.Popen(dbus_command, shell=True)
        time.sleep(1)
        print("D-Bus service started successfully.")

    def start_bluetoothd_logs(self,log_text_browser=None):
        """ Starts the hcidump logs and redirects to the file. """
        print(self.log_path)
        bluetoothd_command = '/usr/local/bluez/bluez-tools/libexec/bluetooth/bluetoothd -nd --compat'
        self.bluetoothd_log_name = '/'.join([self.log_path, 'bluetoothd.log'])
        run(self.log_path, bluetoothd_command, self.bluetoothd_log_name)
        time.sleep(1)
        print(f"bluetoothd process has started {self.bluetoothd_log_name}")
        self.bluetoothd_logfile_fd = open(self.bluetoothd_log_name, 'r')
        self.bluetoothd_file_position = self.bluetoothd_logfile_fd.tell()
        if log_text_browser is not None:
            print(f"Creating LogWatcher instance for bluetoothd logs")
            self.bluetoothd_log_watcher = LogWatcher(self.bluetoothd_log_name, log_text_browser)
            self.observer = Observer()
            self.observer.schedule(self.bluetoothd_log_watcher, path='.', recursive=False)
            self.observer.start()
            print(f"LogWatcher instance started for bluetoothd logs")
            self.update_log_timer = QTimer()
            self.update_log_timer.timeout.connect(self.update_bluetoothd_log)
            self.update_log_timer.start(1000)
        return True

    def start_pulseaudio_logs(self, log_text_browser=None):
        """ Starts the pulseaudio logs and redirects to the file. """
        print(self.log_path)
        pulseaudio_command = '/usr/local/bluez/pulseaudio-13.0_for_bluez-5.65/bin/pulseaudio -vvv'
        self.pulseaudio_log_name = '/'.join([self.log_path, 'pulseaudio.log'])
        run(self.log_path, pulseaudio_command, self.pulseaudio_log_name)
        time.sleep(1)
        print(f"pulseaudio process has started {self.pulseaudio_log_name}")
        self.pulseaudio_logfile_fd = open(self.pulseaudio_log_name, 'r')
        self.pulseaudio_file_position = self.pulseaudio_logfile_fd.tell()
        if log_text_browser is not None:
            print(f"Creating LogWatcher instance for pulseaudio logs")
            self.pulseaudio_log_watcher = LogWatcher(self.pulseaudio_log_name, log_text_browser)
            self.observer = Observer()
            self.observer.schedule(self.pulseaudio_log_watcher, path='.', recursive=False)
            self.observer.start()
            print(f"LogWatcher instance started for pulseaudio logs")
            self.update_pulseaudio_log_timer = QTimer()
            self.update_pulseaudio_log_timer.timeout.connect(self.update_pulseaudio_log)
            self.update_pulseaudio_log_timer.start(1000)
        return True

    def update_bluetoothd_log(self):
        "Constantly updating the bluetoothd logs "
        scrollbar = self.bluetoothd_log_watcher.text_browser.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
        with open(self.bluetoothd_log_name, 'r') as f:
            f.seek(self.bluetoothd_log_watcher.last_position)
            new_logs = f.read()
            self.bluetoothd_log_watcher.last_position = f.tell()
        if new_logs:
            self.bluetoothd_log_watcher.text_browser.append(new_logs)
            if at_bottom:
                scrollbar.setValue(scrollbar.maximum())

    def update_pulseaudio_log(self):
        scrollbar = self.pulseaudio_log_watcher.text_browser.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
        with open(self.pulseaudio_log_name, 'r') as f:
            f.seek(self.pulseaudio_log_watcher.last_position)
            new_logs = f.read()
            self.pulseaudio_log_watcher.last_position = f.tell()
        if new_logs:
            self.pulseaudio_log_watcher.text_browser.append(new_logs)
            if at_bottom:
                scrollbar.setValue(scrollbar.maximum())

    def get_controller_details(self):
        """ Fetching all the relevant controller details """
        details = {}
        run_command(self.log_path,'hciconfig -a hci0 up')
        result = run_command(self.log_path, 'hciconfig -a hci0')
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
        return details

    def stop_pulseaudio_logs(self):
        """Stops the pulseaudio logs."""
        print("Pulse audio logs has been stopped")
        if self.pulseaudio_logfile_fd:
            self.pulseaudio_logfile_fd.close()
            self.pulseaudio_logfile_fd = None
        pulseaudio_process = subprocess.Popen(['pgrep', 'pulseaudio'], stdout=subprocess.PIPE)
        pulseaudio_pid = pulseaudio_process.communicate()[0].decode('utf-8').strip()
        if pulseaudio_pid:
            subprocess.run(['kill', pulseaudio_pid])

    def stop_bluetoothd_logs(self):
        """Stops the bluetoothd logs."""
        print("Bluetoothd logs has been stopped")
        if self.bluetoothd_logfile_fd:
            self.bluetoothd_logfile_fd.close()
            self.bluetoothd_logfile_fd = None
        bluetoothd_process = subprocess.Popen(['pgrep', 'bluetoothd'], stdout=subprocess.PIPE)
        bluetoothd_pid = bluetoothd_process.communicate()[0].decode('utf-8').strip()
        if bluetoothd_pid:
            subprocess.run(['kill', bluetoothd_pid])

    def start_dump_logs(self, log_text_browser=None):
        print(self.log_path)
        hcidump_command = f'/usr/local/bluez/bluez-tools/bin/hcidump -i USB -Xt'
        #hcidump_command = '/usr/local/bluez/bluez-tools/bin/hcidump -i {} -Xt'.format(self.controller.controllers_list.interface)
        self.hcidump_log_name = os.path.join(self.log_path, 'hcidump.log')
        # Start hcidump via subprocess
        self.hcidump_process = subprocess.Popen(hcidump_command.split(),stdout=open(self.hcidump_log_name, 'w'),stderr=subprocess.STDOUT)
        self.logfile_fd = open(self.hcidump_log_name, 'r')
        self.file_position = self.logfile_fd.tell()
        time.sleep(1)
        print(f"hcidump process has started: {self.hcidump_log_name}")
        if log_text_browser is not None:
            self.hci_log_reader = HcidumpLogReader(self.hcidump_log_name)
            self.hci_log_reader.log_updated.connect(log_text_browser.append)
            self.hci_log_reader.start()

    def stop_dump_logs(self):
        """Stops the hcidump logs."""
        print("HCI dump logs has been stopped")
        if self.logfile_fd:
            self.logfile_fd.close()
            self.logfile_fd = None
        subprocess.run(['pgrep', 'hcidump'], stdout=subprocess.PIPE).stdout.decode('utf-8').strip().split('\n')
        hcidump_process = subprocess.run(['pgrep', 'hcidump'], stdout=subprocess.PIPE).stdout.decode('utf-8').strip().split('\n')
        if hcidump_process:
            subprocess.run(['kill'] + hcidump_process)




    # def stop_dump_logs(self):
    #     print("Stopping HCI dump logs")
    #     if hasattr(self, 'hci_log_reader') and self.hci_log_reader:
    #         self.hci_log_reader.stop()
    #     if hasattr(self, 'hcidump_process') and self.hcidump_process:
    #         self.hcidump_process.terminate()
    #         self.hcidump_process.wait()
    #         self.hcidump_process = None


    # def start_dump_logs(self, log_text_browser=None):
    #     """Starts the hcidump logs and redirects to the file."""
    #     print(self.log_path)
    #     hcidump_command = f'/usr/local/bluez/bluez-tools/bin/hcidump -i USB -Xt'
    #     self.hcidump_log_name = os.path.join(self.log_path, 'hcidump.log')
    #     run(self.log_path, hcidump_command, self.hcidump_log_name)
    #     time.sleep(1)
    #     print(f"hcidump process has started: {self.hcidump_log_name}")
    #     self.logfile_fd = open(self.hcidump_log_name, 'r')
    #     self.file_position = self.logfile_fd.tell()
    #     if log_text_browser is not None:
    #         print("Creating LogWatcher instance for hcidump logs")
    #         self.hcidump_log_watcher = LogWatcher(self.hcidump_log_name, log_text_browser)
    #         self.observer = Observer()
    #         hcidump_log_dir = os.path.dirname(self.hcidump_log_name)
    #         self.observer.schedule(self.hcidump_log_watcher, path=hcidump_log_dir, recursive=False)
    #         self.observer.start()
    #         print("LogWatcher instance started for hcidump logs")
    #         self.update_hcidump_log_timer = QTimer()
    #         self.update_hcidump_log_timer.timeout.connect(self.update_hcidump_log)
    #         self.update_hcidump_log_timer.start(1000)
    #     return True

    # def update_hcidump_log(self):
    #     """Constantly appends new HCI dump log content to the text browser."""
    #     scrollbar = self.hcidump_log_watcher.text_browser.verticalScrollBar()
    #     at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
    #     with open(self.hcidump_log_name, 'r') as f:
    #         f.seek(self.hcidump_log_watcher.last_position)
    #         new_logs = f.read()
    #         self.hcidump_log_watcher.last_position = f.tell()
    #     if new_logs:
    #         self.hcidump_log_watcher.text_browser.append(new_logs)
    #         if at_bottom:
    #             scrollbar.setValue(scrollbar.maximum())









