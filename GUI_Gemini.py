import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QRadioButton, QLabel, QTextEdit, QHBoxLayout, QFrame, QFormLayout)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
# Assuming these modules are in the same directory and contain the correct functions
from function_project import update_attachments_by_type
from function_item import update_item_attachments

# Custom stream class to redirect stdout (print statements) to the QTextEdit widget
class Stream(QObject):
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(str(text))
    
    def flush(self):
        pass

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

        # Redirect sys.stdout to our custom Stream class
        sys.stdout = Stream()
        sys.stdout.text_written.connect(self.log_to_readout)

    def log_to_readout(self, text):
        """Append text to the readout log."""
        self.readout_log.append(text)
        self.readout_log.verticalScrollBar().setValue(self.readout_log.verticalScrollBar().maximum())


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

    def LoginForm(self, UN, PW):
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
        
        # Add the readout log area
        self.readout_label = QLabel("Readout Log:")
        self.readout_log = QTextEdit()
        self.readout_log.setReadOnly(True)

        # Add to the dynamic content layout
        self.dynamic_content_layout.addLayout(form_layout)
        self.dynamic_content_layout.addWidget(self.login_button)
        self.dynamic_content_layout.addWidget(self.readout_label)
        self.dynamic_content_layout.addWidget(self.readout_log)
        self.dynamic_content_layout.addStretch() # Push content to the top within its own section

        # Connect the login button to the new sequence function
        self.login_button.clicked.connect(self.run_update_sequence)

    def NextButton(self,label,Enable):
        self.next_button = QPushButton(label)
        self.next_button.setEnabled(Enable)
        if not Enable:
            self.next_button.setStyleSheet("background-color: #53575A; color: white;")
        else:
            self.next_button.setStyleSheet("background-color: #0052CC; color: white;")
        return self.next_button

    def run_update_sequence(self):
        """
        Executes the two update functions in sequence.
        
        1. Gathers all input from the GUI.
        2. Calls update_item_attachments, which returns an index.
        3. Calls update_project_attachments with the returned index.
        4. All print statements from the functions are redirected to the readout log.
        """
        # Clear the log for a new run
        self.readout_log.clear()

        print("Starting attachment update sequence...")

        # Get all the input values from the GUI
        jama_username = self.username_input.text()
        jama_password = self.password_input.text()
        project_api_id = self.project_api_id_input.text()
        custom_prefix = self.custom_prefix_input.text()
        url = self.URL_input.text()
        attachment_item_type_id = self.attachement_api_id_input.text()
        delete_downloads = self.delete_downloads_input.isChecked()

        # Construct the V2 URL
        if not url.endswith("/"):
            jama_base_url_v2 = url + "/rest/v2/"
        else:
            jama_base_url_v2 = url + "rest/v2/"

        try:
            # Step 1: Execute the first function
            print("Executing update_item_attachments...")
            index = update_item_attachments(
                jama_username=jama_username,
                jama_password=jama_password,
                project_api_id=project_api_id,
                custom_prefix=custom_prefix,
                jama_base_url_v2=jama_base_url_v2,
                t_f=delete_downloads
            )
            print(f"update_item_attachments completed. Returned index: {index}")

            # Step 2: Execute the second function with the returned index
            print("Executing update_project_attachments...")
            update_attachments_by_type(
                jama_username=jama_username,
                jama_password=jama_password,
                project_api_id=project_api_id,
                custom_prefix=custom_prefix,
                jama_base_url_v2=jama_base_url_v2,
                attachment_item_type_id=attachment_item_type_id,
                t_f=delete_downloads,
                index=index
            )
            print("update_project_attachments completed.")
            print("Attachment update sequence finished successfully!")
        except Exception as e:
            print(f"An error occurred during the update sequence: {e}")


if __name__ == "__main__":
    # Run the app when running this file
    app = QApplication(sys.argv)
    window = AttachmentUpdater()
    window.show()
    sys.exit(app.exec())
