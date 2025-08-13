import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QRadioButton, QLabel, QTextEdit, QHBoxLayout, QFrame, QFormLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from function_project import update_attachments_by_type
from function_item import update_item_attachments

class AttachmentUpdater(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Attachment Name Updater") # Title of app in header bar
        
        # Open app in the center of the screen & set size
        screen = QApplication.primaryScreen() # Scrape the correct screen to open on
        screen_geometry = screen.geometry() # Determine the primary screen's geometry
        window_width = 800 # Width of the app
        window_height = 600 # Height of the app
        x = (screen_geometry.width() - window_width) // 2 # Calculate the halfway width
        y = (screen_geometry.height() - window_height) // 2 # Calculate the halfway height
        self.setGeometry(x, y, window_width, window_height) # Set the app's opening location and size

        # Set the icon
        script_dir = os.path.dirname(os.path.abspath(__file__)) # Get the file path for this code
        icon_path = os.path.join(script_dir, 'jama_logo_icon.png') # Add the icon's file name to the path
        self.setWindowIcon(QIcon(icon_path)) # Add the icon to the app's header bar

        # Initialize the main layout for the entire window
        self.main_app_layout = QVBoxLayout()
        self.setLayout(self.main_app_layout)

        # --- Permanent Top Section ---
        self.permanent_header()

        # --- Dynamic Content Area ---
        # This is the layout that will be cleared and repopulated
        self.dynamic_content_layout = QVBoxLayout()
        self.main_app_layout.addLayout(self.dynamic_content_layout) # Add it to the main layout

        # Add a stretch to push content to the top
        self.main_app_layout.addStretch()

        self.SelectLoginMethod()

    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def permanent_header(self):
        # Create a horizontal layout for the header
        header_layout = QHBoxLayout()

        # Example permanent widget: a title label
        self.title_label = QLabel("<h1>Attachment Name Updater</h1>")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(self.title_label)

        self.logo = QLabel(self)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignRight)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, 'jama_logo.png')
        pixmap = QPixmap(logo_path)
        scaled_pixmap = pixmap.scaled(
                150,
                35,
                Qt.AspectRatioMode.KeepAspectRatio,  # Maintain aspect ratio
                Qt.TransformationMode.SmoothTransformation # For better quality
            )
        self.logo.setPixmap(scaled_pixmap)
        header_layout.addWidget(self.logo)
        
        # Add a separator line for visual clarity
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)

        # Add the header layout and separator to the main app layout
        self.main_app_layout.addLayout(header_layout)
        self.main_app_layout.addWidget(separator)

    def SelectLoginMethod(self):
        # A set of radio buttons to allow the user to select Basic or oAuth login for Jama Connect
        form_layout = QFormLayout()

        self.basic = QRadioButton("Basic")
        self.oAuth = QRadioButton("oAuth")
        self.basic.setChecked(True)
        
        radio_button_layout = QHBoxLayout()
        radio_button_layout.addWidget(self.basic)
        radio_button_layout.addWidget(self.oAuth)
        radio_button_layout.addStretch()

        form_layout.addRow("Select Jama Connect Login Method:", radio_button_layout)
        
        self.submit_button = self.NextButton("Submit",True)
        
        self.dynamic_content_layout.addLayout(form_layout)
        self.dynamic_content_layout.addWidget(self.submit_button)
        self.dynamic_content_layout.addStretch() # Push content to the top within its own section

        self.submit_button.clicked.connect(self.CheckLoginMethod)

    def CheckLoginMethod(self):
        self.clearLayout(self.dynamic_content_layout) # Clear only the dynamic content layout
        
        if self.basic.isChecked():
            self.LoginForm("Username","Password")
        elif self.oAuth.isChecked():
            self.LoginForm("Client ID","Client Secret")

    def LoginForm(self,UN,PW):
        form_layout = QFormLayout()

        self.Jama_label = QLabel("Jama Connect API Login Information")
        self.URL_label = QLabel("Jama Connect URL: ")
        self.URL_input = QLineEdit()
        self.URL_input.setPlaceholderText("Enter your Jama Connect instance's URL")
        form_layout.addRow(self.URL_label,self.URL_input)

        self.username_label = QLabel(UN + ": ")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your " + UN)
        form_layout.addRow(self.username_label, self.username_input)

        self.password_label = QLabel(PW + ": ")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your " + PW)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(self.password_label, self.password_input)

        self.project_api_id_label = QLabel("Project API ID: ")
        self.project_api_id_input = QLineEdit()
        self.project_api_id_input.setPlaceholderText("Enter the API ID of the specific project for updates")
        form_layout.addRow(self.project_api_id_label,self.project_api_id_input)

        self.attachement_api_id_label = QLabel("Attachment API ID: ")
        self.attachement_api_id_input = QLineEdit()
        self.attachement_api_id_input.setPlaceholderText("Enter the API ID of the Attachment item type (typically 22)")
        form_layout.addRow(self.attachement_api_id_label,self.attachement_api_id_input)

        self.custom_prefix_label = QLabel("Custom Prefix: ")
        self.custom_prefix_input = QLineEdit()
        self.custom_prefix_input.setPlaceholderText("Enter the custom prefix for each new attachment's name")
        form_layout.addRow(self.custom_prefix_label,self.custom_prefix_input)

        self.delete_downloads_label = QLabel("Delete Downloaded Attachments? ")
        self.delete_downloads_input = QRadioButton("Delete")
        self.delete_downloads_input.setChecked(False)
        form_layout.addRow(self.delete_downloads_label,self.delete_downloads_input)

        self.login_button = self.NextButton("Run",True)
        
        # Add to the dynamic content layout
        self.dynamic_content_layout.addLayout(form_layout)
        self.dynamic_content_layout.addWidget(self.login_button)
        self.dynamic_content_layout.addStretch() # Push content to the top within its own section

    def NextButton(self,label,Enable):
        self.next_button = QPushButton(label)
        self.next_button.setEnabled(Enable)
        if Enable == False:
            self.next_button.setStyleSheet("background-color: #53575A; color: white;")
        else:
            self.next_button.setStyleSheet("background-color: #0052CC; color: white;")
        return self.next_button

if __name__ == "__main__":
    # Run the app when running this file
    app = QApplication(sys.argv)
    window = AttachmentUpdater()
    window.show()
    sys.exit(app.exec())