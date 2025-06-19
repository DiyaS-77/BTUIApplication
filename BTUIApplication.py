import dbus
import os
import sys
import time

from bt_ui_components import hci_commands as hci
from bt_ui_components import style_sheet as ss
from reportlab.lib.colors import palegreen
from test_framework.logger import Logger
from bt_ui_components.bluez_utils_25 import BluezLogger
from test_automation.UI_Application.controller_lib import Controller
from bt_ui_components.bt_ui_dummy import TestApplication
# from BT_UI.agent_runner import AgentRunner
from PyQt6.QtCore import QTimer, QDateTime
from PyQt6.QtCore import QFileSystemWatcher
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QIcon
from PyQt6.QtGui import QPalette
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QScrollArea
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QToolButton
from PyQt6.QtWidgets import QTreeWidget
from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QMessageBox


class CustomDialog(QDialog):
    """ Class for custom warning dialog box. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning!")
        layout = QVBoxLayout()
        message = QLabel("Select the controller!!")
        layout.addWidget(message)
        self.setLayout(layout)

    def showEvent(self, event):
        """ Sets the geometry for the dialog box and displays it. """
        parent_geometry = self.parent().geometry()
        dialog_geometry = self.geometry()
        x = (parent_geometry.x() + (parent_geometry.width() - dialog_geometry.width()) // 2)
        y = (parent_geometry.y() + (parent_geometry.height() - dialog_geometry.height()) // 2)
        self.move(x, y)
        super().showEvent(event)


class BluetoothUIApp(QMainWindow):
    """ Class for creating the bluetooth application for controller testing."""
    def __init__(self):
        super().__init__()
        self.log_path = '/root/Desktop/BT_Automation/BT_UI'
        #self.log_manager = LogManager(interface="hci0", log_path=self.log_path)
        #self.log_manager.start_all_logs()
        self.bluez_logger = BluezLogger(self.log_path)
        #self.bluez_logger = BluezLogger(self.log.log_path)
        #self.log = Logger("UI")
        #self.logger_init()
        #self.bluez_logger = BluezLogger(self.log.log_path)
        self.bluez_logger.start_dbus_service()
        self.bluez_logger.start_bluetoothd_logs()
        self.bluez_logger.start_pulseaudio_logs()
        # self.agent_runner = AgentRunner(capability="DisplayYesNo")
        # self.agent_runner.confirmation_requested.connect(self.show_confirmation_dialog)
        # self.agent_runner.start()

        self.scroll = None
        self.content_layout = None
        self.content_widget = None
        #self.window = QMainWindow()
        self.log = Logger("UI")
        self.logger_init()
        #self.bluez_logger = BluezLogger(self.log.log_path)
        #self.controller = Controller(self.log, self.log.log_path)
        self.controller = Controller(self.log)
        self.handle = None
        self.ocf = None
        self.ogf = None
        self.file_watcher = None
        self.dump_log_output = None
        self.empty_list = None
        self.command_input_layout = None
        self.commands_list_tree_widget = None
        self.controllers_list_widget = None
        self.test_application = None
        self.test_controller = None
        self.devices_button = None
        self.previous_row_selected = None
        self.previous_cmd_list = []
        self.controllers_list_layout = None
        self.test_application_widget = None
        self.list_controllers()

    # def show_confirmation_dialog(self, device, passkey):
    #     from PyQt6.QtWidgets import QMessageBox
    #     response = QMessageBox.question(
    #         self,
    #         "Bluetooth Pairing Request",
    #         f"Allow device {device} to pair?\nPasskey: {passkey:06d}",
    #         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    #     )
    #     confirmed = response == QMessageBox.StandardButton.Yes
    #     self.agent_runner.respond_to_confirmation(confirmed)

    def closeEvent(self, a0):
        self.log.debug(f"closing {a0}")
        if self.controller.hci_dump_started:
            self.controller.stop_dump_logs()

    def logger_init(self):
        """ Creates log folder and sets up the logger file. """
        log_time = time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime(time.time()))
        path = os.path.join(os.path.curdir, f"{log_time}_logs")
        if not os.path.exists(path):
            os.mkdir(path)
        self.log.setup_logger_file(path)
    '''
    def main_window(self):
        """ Creates main window with option to select list of devices. """
        self.setWindowTitle("Bluetooth UI Application")
        palette = QPalette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(QPixmap('/root/Desktop/BT_Automation/images/main_window_background.jpg')))
        self.setPalette(palette)
        main_layout = QVBoxLayout()
        main_layout.addStretch(1)
        application_label_layout = QHBoxLayout()
        application_label = QLabel("BLUETOOTH TEST APPLICATION")
        font = QFont("Aptos Black", 28, QFont.Weight.Bold)
        application_label.setFont(font)
        application_label.setStyleSheet("color: black;")
        application_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        application_label_layout.addStretch(1)
        application_label_layout.addWidget(application_label)
        application_label_layout.addStretch(1)
        main_layout.addLayout(application_label_layout)
        main_layout.addStretch(1)

        self.controllers_list_layout = QHBoxLayout()
        self.devices_button = QToolButton()
        self.devices_button.setIcon(QIcon("images/devices_icon.jpg"))
        self.devices_button.setIconSize(QSize(200, 100))
        self.devices_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.devices_button.setText("Devices")
        self.devices_button.setMinimumHeight(50)
        self.devices_button.setStyleSheet(ss.device_button_style_sheet)
        self.devices_button.clicked.connect(self.list_controllers)
        #self.list_controllers()
        self.controllers_list_layout.addStretch(1)
        self.controllers_list_layout.addWidget(self.devices_button)
        self.controllers_list_layout.addStretch(1)
        main_layout.addLayout(self.controllers_list_layout)
        main_layout.addStretch(1)

        buttons_layout = QGridLayout()
        button_layout = QHBoxLayout()
        self.test_controller = QToolButton()
        self.test_controller.setText("Test Controller")
        self.test_controller.setGeometry(100, 100, 200, 100)
        self.test_controller.clicked.connect(self.check_controller_selected)
        self.test_controller.setStyleSheet(ss.select_button_style_sheet)
        self.test_controller.hide()

        button_layout.addWidget(self.test_controller)
        buttons_layout.addLayout(button_layout, 0, 0)
        button_layout1 = QHBoxLayout()
        self.test_application = QToolButton()
        self.test_application.setText("Test Application")
        self.test_application.clicked.connect(self.check_application_selected)
        # self.test_application.clicked.connect(self.test_application_clicked)
        self.test_application.setGeometry(100, 100, 200, 100)
        self.test_application.setStyleSheet(ss.select_button_style_sheet)
        self.test_application.hide()
        button_layout1.addWidget(self.test_application)
        buttons_layout.addLayout(button_layout1, 0, 1)

        main_layout.addLayout(buttons_layout)
        main_layout.addStretch(1)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
    
    
    def list_controllers(self):
        """ Lists the controllers connected on the host. """
        self.devices_button.close()
        self.controllers_list_layout.removeWidget(self.devices_button)
        self.controllers_list_widget = QListWidget()
        self.controllers_list_widget.setMinimumSize(800, 400)
        self.controllers_list_widget.itemAlignment()
        self.add_items(self.controllers_list_widget, list(self.controller.get_controllers_connected().keys()),
                       Qt.AlignmentFlag.AlignHCenter)
        self.controllers_list_widget.setStyleSheet(ss.list_widget_style_sheet)
        self.controllers_list_widget.currentTextChanged.connect(self.controller_selected)
        self.controllers_list_layout.addStretch(1)
        self.controllers_list_layout.addWidget(self.controllers_list_widget)
        self.controllers_list_layout.addStretch(3)
        self.test_controller.show()
        self.test_application.show()
    

    def list_controllers(self):
        self.setWindowTitle("Bluetooth UI Application")
        palette = QPalette()
        palette.setBrush(QPalette.ColorRole.Window,QBrush(QPixmap('/root/Desktop/BT_Automation/images/main_window_background.jpg')))
        self.setPalette(palette)

        main_layout = QVBoxLayout()
        main_layout.addStretch(1)
        application_label_layout = QHBoxLayout()
        application_label=QLabel("BLUETOOTH TEST APPLICATION")
        font=QFont("Aptos Black", 28, QFont.Weight.Bold)
        application_label.setFont(font)
        application_label.setStyleSheet("color: black;")
        application_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        application_label_layout.addStretch(1)
        application_label_layout.addWidget(application_label)
        application_label_layout.addStretch(1)
        main_layout.addLayout(application_label_layout)
        main_layout.addSpacing(30)
        #main_layout.addStretch(1)

        self.controllers_list_layout = QHBoxLayout()
        self.controllers_list_widget=QListWidget()
        self.controllers_list_widget.setMinimumSize(800, 400)
        self.controllers_list_widget.itemAlignment()
        self.add_items(self.controllers_list_widget, list(self.controller.get_controllers_connected().keys()),Qt.AlignmentFlag.AlignHCenter)
        self.controllers_list_widget.setStyleSheet(ss.list_widget_style_sheet)
        self.controllers_list_widget.currentTextChanged.connect(self.controller_selected)
        self.controllers_list_layout.addStretch(1)
        #main_layout.addSpacing(20)
        main_layout.addWidget(self.controllers_list_widget)
        self.controllers_list_layout.addStretch(3)
        main_layout.addStretch(1)
        main_layout.addLayout(self.controllers_list_layout)
        main_layout.addStretch(3)

        #main_layout.addSpacing(60)
        buttons_layout = QGridLayout()
        button_layout = QHBoxLayout()
        self.test_controller=QToolButton()
        self.test_controller.setText("Test Controller")
        #self.test_controller.setMinimumSize(200,100)
        self.test_controller.setGeometry(100, 100, 200, 100)
        self.test_controller.clicked.connect(self.check_controller_selected)
        self.test_controller.setStyleSheet(ss.select_button_style_sheet)
        self.test_controller.hide()

        button_layout.addSpacing(20)
        button_layout.addWidget(self.test_controller)
        buttons_layout.addLayout(button_layout, 0, 0)
        button_layout1 = QHBoxLayout()
        self.test_application=QToolButton()
        self.test_application.setText("Test Application")
        self.test_application.clicked.connect(self.test_application_clicked)
        self.test_application.setGeometry(100, 100, 200, 100)
        self.test_application.setStyleSheet(ss.select_button_style_sheet)
        self.test_application.hide()
        button_layout.addWidget(self.test_application)
        buttons_layout.addLayout(button_layout1, 0, 1)
        
        
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch(1)
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.test_controller.show()
        self.test_application.show()
        
        buttons_layout=QHBoxLayout()
        self.test_controller=QToolButton()
        self.test_controller.setText("Test Controller")
        self.test_controller.setMinimumSize(200,100)
        self.test_controller.clicked.connect(self.check_controller_selected)
        self.test_controller.setStyleSheet(ss.select_button_style_sheet)

        self.test_application = QToolButton()
        self.test_controller.setText("Test Application")
        self.test_application.setMinimumSize(200, 100)
        self.test_application.clicked.connect(self.test_application_clicked)
        self.test_application.setStyleSheet(ss.select_button_style_sheet)

        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.test_controller)
        #buttons_layout.addSpacing(40)
        buttons_layout.addWidget(self.test_application)
        buttons_layout.addStretch(1)
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch(1)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.test_controller.show()
        self.test_application.show()
        '''

    def list_controllers(self):
        self.setWindowTitle("Bluetooth UI Application")

        # Set background
        palette = QPalette()
        palette.setBrush(QPalette.ColorRole.Window,
                         QBrush(QPixmap('/root/Desktop/BT_Automation/images/main_window_background.jpg')))
        self.setPalette(palette)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addStretch(1)

        # Title
        application_label_layout = QHBoxLayout()
        application_label = QLabel("BLUETOOTH TEST APPLICATION")
        font = QFont("Aptos Black", 28, QFont.Weight.Bold)
        application_label.setFont(font)
        application_label.setStyleSheet("color: black;")
        application_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        application_label_layout.addStretch(1)
        application_label_layout.addWidget(application_label)
        application_label_layout.addStretch(1)
        main_layout.addLayout(application_label_layout)
        main_layout.addStretch(1)

        # Controller list
        self.controllers_list_layout = QHBoxLayout()
        self.controllers_list_widget = QListWidget()
        self.controllers_list_widget.setMinimumSize(800, 400)
        self.add_items(
            self.controllers_list_widget,
            list(self.controller.get_controllers_connected().keys()),
            Qt.AlignmentFlag.AlignHCenter
        )
        self.controllers_list_widget.setStyleSheet(ss.list_widget_style_sheet)
        self.controllers_list_widget.currentTextChanged.connect(self.controller_selected)
        self.controllers_list_layout.addStretch(1)
        self.controllers_list_layout.addWidget(self.controllers_list_widget)
        self.controllers_list_layout.addStretch(1)
        main_layout.addLayout(self.controllers_list_layout)

        # Info label (interface, bus, etc.) will be dynamically added in controller_selected()

        main_layout.addStretch(1)

        # Buttons
        buttons_layout = QGridLayout()

        # Test Controller
        button_layout = QHBoxLayout()
        self.test_controller = QToolButton()
        self.test_controller.setText("Test Controller")
        self.test_controller.setGeometry(100, 100, 200, 100)
        self.test_controller.clicked.connect(self.check_controller_selected)
        self.test_controller.setStyleSheet(ss.select_button_style_sheet)
        self.test_controller.hide()
        button_layout.addWidget(self.test_controller)
        buttons_layout.addLayout(button_layout, 0, 0)

        # Test Application
        button_layout1 = QHBoxLayout()
        self.test_application = QToolButton()
        self.test_application.setText("Test Application")
        self.test_application.clicked.connect(self.test_application_clicked)
        self.test_application.setGeometry(100, 100, 200, 100)
        self.test_application.setStyleSheet(ss.select_button_style_sheet)
        self.test_application.hide()
        button_layout1.addWidget(self.test_application)
        buttons_layout.addLayout(button_layout1, 0, 1)

        # Add buttons layout to main layout
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch(1)

        # Final setup
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

        # Show buttons after layout is complete
        self.test_controller.show()
        self.test_application.show()

    def add_items(self, widget, items, align):
        """Adds the items to the list widget.

        Args:
            widget: list widget object
            items: items list to be added
            align: alignment of the item in the list

        """
        for test_item in items:
            item = QListWidgetItem(test_item)
            item.setTextAlignment(align)
            widget.addItem(item)

    def controller_selected(self, controller):
        """ Updates the controller list with details of the selected controller.

        Args:
            controller: selected controller address.
        """
        self.log.info(f"Controller Selected: {controller}")
        self.controller.bd_address = controller
        if self.previous_row_selected:
            self.controllers_list_widget.takeItem(self.previous_row_selected)
        row = self.controllers_list_widget.currentRow()
        item = QListWidgetItem(self.controller.get_controller_interface_details())
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.controllers_list_widget.insertItem(row + 1, item)
        self.previous_row_selected = row + 1

    def check_controller_selected(self):
        """ Checks and raises a dialog box if test controller button clicked without controller selection."""
        if self.controller.bd_address:
            self.controller_window()
        else:
            dlg = CustomDialog(self)
            if not dlg.exec():
                self.main_window()

    def check_application_selected(self):
        """Checks and raises a dialog box if Test Application button is clicked without controller selection."""
        if self.controller.bd_address:
            self.test_application_clicked()  # Only proceed if controller is selected
        else:
            dlg = CustomDialog(self)
            if not dlg.exec():
                self.main_window()


    def controller_window(self):
        """ Creates page for displaying controller details, executing hci commands and displaying dump logs"""
        main_layout = QGridLayout()
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)
        main_layout.setColumnStretch(2, 1)

        vertical_layout = QGridLayout()

        # label.setStyleSheet("border: 2px solid black; color: black; font: 12pt Arial bold;")
        # label.setAlignment(Qt.AlignmentFlag.AlignTop)
        # vertical_layout.addWidget(label, 1, 0)

        self.commands_list_tree_widget = QTreeWidget()
        self.commands_list_tree_widget.setHeaderLabels(["HCI Commands"])
        self.commands_list_tree_widget.setStyleSheet(ss.cmd_list_widget_style_sheet)
        items = []
        for item in list(hci.hci_commands.keys()):
            _item = QTreeWidgetItem([item])
            for value in list(
                    getattr(hci, item.lower().replace(' ', '_')).keys()):
                child = QTreeWidgetItem([value])
                _item.addChild(child)
            items.append(_item)

        self.commands_list_tree_widget.insertTopLevelItems(0, items)
        self.commands_list_tree_widget.clicked.connect(self.run_hci_cmd)

        vertical_layout.addWidget(self.commands_list_tree_widget, 0, 0)
        vertical_layout.setRowStretch(0, 1)
        vertical_layout.setRowStretch(1, 1)
        main_layout.addLayout(vertical_layout, 0, 0)

        self.command_input_layout = QVBoxLayout()

        self.empty_list = QListWidget()
        self.empty_list.setStyleSheet("background: transparent; border: 2px solid black;")
        self.command_input_layout.addWidget(self.empty_list)

        logs_layout = QVBoxLayout()
        logs_label = QLabel("DUMP LOGS")
        logs_label.setStyleSheet("border: 2px solid black; "
                                 "color: black; "
                                 "font-size:18px; "
                                 "font-weight: bold;")
        logs_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        logs_layout.addWidget(logs_label)
        self.bluez_logger.start_dump_logs()
        #self.controller.start_dump_logs()

        self.dump_log_output = QTextEdit()
        self.dump_log_output.setMaximumWidth(700)
        self.dump_log_output.setReadOnly(True)
        #content = self.controller.logfile_fd.read()
        content = self.bluez_logger.logfile_fd.read()
        #self.controller.file_position = self.controller.logfile_fd.tell()
        self.bluez_logger.file_position = self.bluez_logger.logfile_fd.tell()
        self.dump_log_output.append(content)
        logs_layout.addWidget(self.dump_log_output)

        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.addPath(self.controller.hcidump_log_name)
        self.file_watcher.addPath(self.bluez_logger.hcidump_log_name)
        self.file_watcher.addPath(self.bluez_logger.hcidump_log_name)
        self.file_watcher.fileChanged.connect(self.update_log)
        self.dump_log_output.setStyleSheet("border: 2px solid black;")

        main_layout.addLayout(self.command_input_layout, 0, 1)
        main_layout.addLayout(logs_layout, 0, 2)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def execute_hci_cmd(self):
        """ Updates the parameters for selected ocf and ogf and executes the command using controller library. """
        parameters = []
        for parameter in getattr(hci, self.ocf.lower().replace(' ', '_'))[self.ogf][1]:
            _param = list(parameter.keys())[0]
            if isinstance(getattr(self, _param), QComboBox):
                parameters.append(self.controller.handles[self.handle])
                self.handle = None
                continue
            if getattr(self, _param).toPlainText() == 'None':
                break
            parameters.append(getattr(self, _param).toPlainText())
        setattr(self, f"{self.ogf}_values", parameters)
        self.log.debug(f"{self.ocf=} {self.ogf=} {parameters=}")
        self.controller.run_hci_cmd(self.ocf, self.ogf, parameters)

    def reset_default_params(self):
        """ Resets the parameters with default values."""
        parameters = getattr(hci, self.ocf.lower().replace(' ', '_'))[self.ogf][1]
        for parameter in parameters:
            key = list(parameter.keys())[0]
            default_val = list(parameter.values())[0]
            getattr(self, key).setText(default_val)

    def run_hci_cmd(self, text_selected):
        """ Updates the ocf and ogf selected from hci commands list. """
        if text_selected.parent().data():
            self.ocf = text_selected.parent().data()
            self.ogf = text_selected.data()
        else:
            self.ocf = text_selected.data()
            return
        if not self.scroll:
            self.scroll = QScrollArea()
            self.scroll.setWidgetResizable(True)
        if self.content_layout:
            if self.content_layout.count() > 0:
                while self.content_layout.count():
                    item = self.content_layout.itemAt(0).widget()
                    self.content_layout.removeWidget(item)
                    if item is not None:
                        item.deleteLater()
                self.content_widget.hide()
        self.empty_list.hide()

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        parameters = getattr(hci, self.ocf.lower().replace(' ', '_'))[self.ogf][1]
        index = 0
        for parameter in parameters:
            key = list(parameter.keys())[0]
            default_val = list(parameter.values())[0]
            label = QLabel(key)
            label.setStyleSheet("color: black; font-size:12px;")
            label.setMaximumHeight(30)
            label.setText(key)
            if 'Connection_Handle' in key:
                setattr(self, key, QComboBox())
                combo_box_widget = getattr(self, key)
                combo_box_widget.setPlaceholderText("Connection Handles")
                combo_box_widget.addItems(list(self.controller.get_connection_handles().keys()))
                combo_box_widget.currentTextChanged.connect(self.current_text_changed)
                combo_box_widget.setMaximumHeight(30)
            else:
                setattr(self, key, QTextEdit(default_val))
                getattr(self, key).setMaximumHeight(30)
                if hasattr(self, f"{self.ogf}_values"):
                    if getattr(self, f"{self.ogf}_values"):
                        getattr(self, key).setText(getattr(self, f"{self.ogf}_values")[index])
                        index += 1
            self.content_layout.addWidget(label)
            self.content_layout.addWidget(getattr(self, key))
            self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        if len(parameters) < 1:
            text_edit_widget = QTextEdit("No parameters")
            text_edit_widget.setMaximumHeight(30)
            text_edit_widget.setReadOnly(True)
            self.content_layout.addWidget(text_edit_widget)
            self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        execute_btn = QPushButton("Execute")
        execute_btn.setStyleSheet(
            "font-size: 18px; "
            "color: white; "
            "background: transparent; "
            "padding: 10px;")
        execute_btn.clicked.connect(self.execute_hci_cmd)
        self.content_layout.addWidget(execute_btn)
        if len(parameters) >= 1:
            reset_btn = QPushButton("Reset to default")
            reset_btn.setStyleSheet(
                "font-size: 18px; "
                "color: white; "
                "background: transparent; "
                "padding: 10px;")
            reset_btn.clicked.connect(self.reset_default_params)
            self.content_layout.addWidget(reset_btn)
        self.scroll.setWidget(self.content_widget)
        self.command_input_layout.addWidget(self.scroll)

    def update_log(self):
        """ Updates the dump logs on the logs layout from log file"""
        #self.controller.logfile_fd.seek(self.controller.file_position)
        self.bluez_logger.logfile_fd.seek(self.bluez_logger.file_position)
        #content = self.controller.logfile_fd.read()
        content = self.bluez_logger.logfile_fd.read()
        #self.controller.file_position = self.controller.logfile_fd.tell()
        self.bluez_logger.file_position = self.bluez_logger.logfile_fd.tell()
        self.dump_log_output.append(content)


    def current_text_changed(self, text):
        """ Stores the handle selected for executing the hci command. """
        self.handle = text

    def test_application_clicked(self):
        """ Displays the Test Application window inside the main GUI. """
        if self.centralWidget():
            self.centralWidget().deleteLater()
        #self.controller.start_dump_logs()
        self.test_application_widget = TestApplication()
        self.setCentralWidget(self.test_application_widget)
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_window = BluetoothUIApp()
    app_window.setWindowIcon(QIcon('/root/Desktop/BT_Automation/images/app_icon.png'))
    #app_window.main_window()
    app_window.showMaximized()


    def stop_logs():
        app_window.bluez_logger.stop_pulseaudio_logs()
        app_window.bluez_logger.stop_bluetoothd_logs()
        app_window.bluez_logger.stop_dump_logs()

    app.aboutToQuit.connect(stop_logs)
    sys.exit(app.exec())








