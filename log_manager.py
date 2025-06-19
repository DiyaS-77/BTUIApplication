import os
import time
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal


class LogReaderThread(QThread):
    log_updated = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self._running = True

    def run(self):
        with open(self.file_path, 'r') as file:
            file.seek(0, os.SEEK_END)
            while self._running:
                line = file.readline()
                if line:
                    self.log_updated.emit(line.strip())
                else:
                    self.msleep(200)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()


class LogManager:
    """
    Base class to manage bluetoothd, pulseaudio, and hcidump log processes.
    Can be used by both Controller and Application components.
    """

    def __init__(self, interface="hci0", log_path="/tmp/logs"):
        self.interface = interface
        self.log_path = log_path
        os.makedirs(self.log_path, exist_ok=True)

        self.bluetoothd_log = os.path.join(self.log_path, "bluetoothd.log")
        self.pulseaudio_log = os.path.join(self.log_path, "pulseaudio.log")
        self.hcidump_log = os.path.join(self.log_path, f"{self.interface}_hcidump.log")

        self.bluetoothd_process = None
        self.pulseaudio_process = None
        self.hcidump_process = None

        self.bluetoothd_reader = None
        self.pulseaudio_reader = None
        self.hcidump_reader = None

    def start_all_logs(self):
        """Starts all logging processes."""
        self.start_bluetoothd_log()
        self.start_pulseaudio_log()
        self.start_hcidump_log()

    def stop_all_logs(self):
        """Stops all logging processes."""
        self.stop_process(self.bluetoothd_process, "bluetoothd")
        self.stop_process(self.pulseaudio_process, "pulseaudio")
        self.stop_process(self.hcidump_process, "hcidump")

        for reader in [self.bluetoothd_reader, self.pulseaudio_reader, self.hcidump_reader]:
            if reader:
                reader.stop()

    def start_bluetoothd_log(self, log_text_browser=None):
        if not self._is_process_running(self.bluetoothd_process):
            cmd = "/usr/local/bluez/bluez-tools/libexec/bluetooth/bluetoothd -nd --compat"
            self.bluetoothd_process = subprocess.Popen(
                cmd.split(), stdout=open(self.bluetoothd_log, 'w'), stderr=subprocess.STDOUT
            )
            time.sleep(1)
            print(f"[INFO] bluetoothd started: {self.bluetoothd_log}")
        if log_text_browser:
            self.bluetoothd_reader = LogReaderThread(self.bluetoothd_log)
            self.bluetoothd_reader.log_updated.connect(log_text_browser.append)
            self.bluetoothd_reader.start()

    def start_pulseaudio_log(self, log_text_browser=None):
        if not self._is_process_running(self.pulseaudio_process):
            cmd = "/usr/local/bluez/pulseaudio-13.0_for_bluez-5.65/bin/pulseaudio -vvv"
            self.pulseaudio_process = subprocess.Popen(
                cmd.split(), stdout=open(self.pulseaudio_log, 'w'), stderr=subprocess.STDOUT
            )
            time.sleep(1)
            print(f"[INFO] pulseaudio started: {self.pulseaudio_log}")
        if log_text_browser:
            self.pulseaudio_reader = LogReaderThread(self.pulseaudio_log)
            self.pulseaudio_reader.log_updated.connect(log_text_browser.append)
            self.pulseaudio_reader.start()

    def start_hcidump_log(self, log_text_browser=None):
        if not self._is_process_running(self.hcidump_process):
            cmd = f"hcidump -i {self.interface} -Xt"
            self.hcidump_process = subprocess.Popen(
                cmd.split(), stdout=open(self.hcidump_log, 'w'), stderr=subprocess.STDOUT
            )
            time.sleep(1)
            print(f"[INFO] hcidump started: {self.hcidump_log}")
        if log_text_browser:
            self.hcidump_reader = LogReaderThread(self.hcidump_log)
            self.hcidump_reader.log_updated.connect(log_text_browser.append)
            self.hcidump_reader.start()

    def stop_process(self, process, name):
        if process is None:
            print(f"[INFO] No {name} process to stop (not started by LogManager)")
            return

        if process.poll() is None:
            print(f"[INFO] Stopping {name} process...")
            process.terminate()
            process.wait()
            print(f"[INFO] {name} stopped")
        else:
            print(f"[INFO] {name} already stopped")

    def _is_process_running(self, process):
        return process and process.poll() is None
