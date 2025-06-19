
device_button_style_sheet = """ QToolButton {
                                    font: 12pt "Arial";
                                    color: white;
                                    background: transparent;
                                    padding: 10px;
                                }
                                QToolButton:hover {
                                    background-color: black;
                                }"""

list_widget_style_sheet = """ QListWidget {
                                font: 14pt "Arial";
                                color: black;
                                background: transparent;
                                padding: 5px;
                            }
                            QListWidget::item {
                                padding : 5px;
                                border: 2px solid black;
                            }
                            QListWidget::item:selected {
                                background-color: white;
                                color: black;
                            }"""

cmd_list_widget_style_sheet = """ QTreeWidget {
                                    font: 12pt "Arial";
                                    color: black;
                                    background: transparent;
                                    padding: 2px;
                                    border: 2px solid black;
                                }
                                QListWidget::item {
                                    padding : 2px;
                                    border: 2px solid black;
                                }
                                QListWidget::item:selected {
                                    background-color: white;
                                    color: black;
                                }"""

select_button_style_sheet = """ QToolButton {
                                    font-size: 20px;
                                    color: white;
                                    background: transparent;
                                    padding: 20px;
                                }
                                QToolButton:hover {
                                    background-color: transparent;
                                }"""
