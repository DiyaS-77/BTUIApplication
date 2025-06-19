# Key changes to make in your BTUIApplication.py

class BluetoothUIApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.log_path = '/root/Desktop/BT_Automation/BT_UI'
        self.bluez_logger = BluezLogger(self.log_path)
        
        # Start basic services (but NOT hcidump yet)
        self.bluez_logger.start_dbus_service()
        self.bluez_logger.start_bluetoothd_logs()
        self.bluez_logger.start_pulseaudio_logs()
        
        # ... rest of your initialization ...
        self.log = Logger("UI")
        self.logger_init()
        self.controller = Controller(self.log)
        
        # ... other initialization code ...
        self.list_controllers()

    def controller_selected(self, item):
        """Updates the controller list with details of the selected controller."""
        controller = item.text()
        self.log.info(f"Controller Selected: {controller}")
        self.controller.bd_address = controller
        
        if controller in self.controller.controllers_list:
            self.controller.interface = self.controller.controllers_list[controller]
            
            # IMPORTANT: Set the interface in bluez_logger as well
            self.bluez_logger.interface = self.controller.interface
            
            # Bring up the interface
            run(self.log, f"hciconfig -a {self.controller.interface} up")
            
            # Wait a moment for interface to come up
            time.sleep(1)
            
            # NOW start hcidump for this specific interface
            print(f"Starting hcidump for selected interface: {self.controller.interface}")
            success = self.bluez_logger.start_dump_logs(interface=self.controller.interface)
            if not success:
                self.log.error(f"Failed to start hcidump for {self.controller.interface}")
            
        # ... rest of your controller selection logic ...
        
        if self.previous_row_selected:
            self.controllers_list_widget.takeItem(self.previous_row_selected)

        row = self.controllers_list_widget.currentRow()
        item = QListWidgetItem(self.controller.get_controller_interface_details())
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.controllers_list_widget.insertItem(row + 1, item)
        self.previous_row_selected = row + 1

    def controller_window(self):
        """Creates page for displaying controller details, executing hci commands and displaying dump logs"""
        # ... your existing layout code ...
        
        logs_layout = QVBoxLayout()
        logs_label = QLabel("DUMP LOGS")
        logs_label.setStyleSheet("border: 2px solid black; "
                                 "color: black; "
                                 "font-size:18px; "
                                 "font-weight: bold;")
        logs_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        logs_layout.addWidget(logs_label)

        self.dump_log_output = QTextEdit()
        self.dump_log_output.setMaximumWidth(700)
        self.dump_log_output.setReadOnly(True)
        
        # CRITICAL: Start hcidump with the text browser for UI updates
        if self.controller.interface and not self.bluez_logger.hci_dump_started:
            print(f"Starting hcidump for controller window: {self.controller.interface}")
            success = self.bluez_logger.start_dump_logs(
                interface=self.controller.interface, 
                log_text_browser=self.dump_log_output
            )
            if not success:
                self.dump_log_output.append("Error: Failed to start HCI dump logging")
        elif self.bluez_logger.hci_dump_started:
            # If already started, just connect to existing log reader
            if hasattr(self.bluez_logger, 'hci_log_reader') and self.bluez_logger.hci_log_reader:
                self.bluez_logger.hci_log_reader.log_updated.connect(self.dump_log_output.append)
        
        # Read any existing content
        if self.bluez_logger.logfile_fd:
            try:
                content = self.bluez_logger.logfile_fd.read()
                if content:
                    self.dump_log_output.append(content)
            except Exception as e:
                self.log.error(f"Error reading existing dump logs: {e}")
        
        logs_layout.addWidget(self.dump_log_output)

        # Set up file watcher as backup (optional, since we have the thread reader)
        self.file_watcher = QFileSystemWatcher()
        if self.bluez_logger.hcidump_log_name and os.path.exists(self.bluez_logger.hcidump_log_name):
            self.file_watcher.addPath(self.bluez_logger.hcidump_log_name)
            self.file_watcher.fileChanged.connect(self.update_log)
        
        self.dump_log_output.setStyleSheet("border: 2px solid black;")

        # ... rest of your layout code ...

    def test_application_clicked(self):
        """Displays the Test Application window inside the main GUI."""
        if self.centralWidget():
            self.centralWidget().deleteLater()
        
        # Ensure hcidump is running for the test application
        if self.controller.interface and not self.bluez_logger.hci_dump_started:
            print(f"Starting hcidump for test application: {self.controller.interface}")
            self.bluez_logger.start_dump_logs(interface=self.controller.interface)
        
        self.test_application_widget = TestApplication()
        self.setCentralWidget(self.test_application_widget)
        
        # Don't close the main window, just switch the central widget
        # self.close()  # Remove this line

    def update_log(self):
        """Updates the dump logs on the logs layout from log file"""
        if self.bluez_logger.logfile_fd:
            try:
                self.bluez_logger.logfile_fd.seek(self.bluez_logger.file_position)
                content = self.bluez_logger.logfile_fd.read()
                if content:
                    self.bluez_logger.file_position = self.bluez_logger.logfile_fd.tell()
                    self.dump_log_output.append(content)
            except Exception as e:
                self.log.error(f"Error updating log: {e}")

    def closeEvent(self, a0):
        """Handle application close event"""
        self.log.debug(f"closing {a0}")
        
        # Clean up all logging processes
        self.bluez_logger.cleanup()
        
        if self.controller.hci_dump_started:
            self.controller.stop_dump_logs()

# In your main section, also update the cleanup:
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_window = BluetoothUIApp()
    app_window.setWindowIcon(QIcon('/root/Desktop/BT_Automation/images/app_icon.png'))
    app_window.showMaximized()

    def stop_logs():
        """Clean up all processes on application exit"""
        app_window.bluez_logger.cleanup()

    app.aboutToQuit.connect(stop_logs)
    sys.exit(app.exec())