# -*- coding: utf-8 -*-
"""
Auto Fitting Module - Qt6 Wrapper
This module wraps the original auto_fitting.py functionality for integration with Qt6 main application.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QFont
import subprocess
import sys
import os

class AutoFittingModule(QWidget):
    """
    Qt6 wrapper module for Auto Fitting functionality.
    Launches the original tkinter-based auto fitting application.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto Peak Fitting Module")
        self.process = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the module UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Interactive XRD Peak Fitting")
        title.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #9370DB; padding: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "This module provides automated peak fitting functionality for XRD data.\n\n"
            "Features:\n"
            "• Automatic peak detection and fitting\n"
            "• Manual peak selection\n"
            "• Background subtraction\n"
            "• Batch processing\n"
            "• Multiple fitting profiles (Pseudo-Voigt, Voigt)\n"
            "• Results export"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("background-color: #F5F5F5; padding: 15px; border-radius: 5px;")
        layout.addWidget(desc)
        
        # Launch button
        self.launch_btn = QPushButton("Launch Auto Fitting Tool")
        self.launch_btn.setMinimumHeight(50)
        self.launch_btn.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #9370DB;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #7B68EE;
            }
            QPushButton:pressed {
                background-color: #6A5ACD;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_auto_fitting)
        layout.addWidget(self.launch_btn)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
    def launch_auto_fitting(self):
        """Launch the auto fitting application"""
        try:
            # Get the path to the original auto_fitting.py
            script_dir = os.path.dirname(os.path.abspath(__file__))
            auto_fitting_path = os.path.join(script_dir, 'auto_fitting.py')
            
            if not os.path.exists(auto_fitting_path):
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"Could not find auto_fitting.py at:\n{auto_fitting_path}"
                )
                return
                
            # Launch the application in a new process
            self.status_label.setText("Launching Auto Fitting Tool...")
            
            if sys.platform == 'win32':
                # Windows
                subprocess.Popen([sys.executable, auto_fitting_path], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                # Linux/Mac
                subprocess.Popen([sys.executable, auto_fitting_path])
                
            self.status_label.setText("Auto Fitting Tool launched successfully")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Launch Error",
                f"Failed to launch Auto Fitting Tool:\n{str(e)}"
            )
            self.status_label.setText("Failed to launch")


# For standalone testing
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = AutoFittingModule()
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec())
