# -*- coding: utf-8 -*-
"""
Batch Fitting Module - Standalone Batch Processing
Extract batch fitting functionality from Auto Fitting Module
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QFrame, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from auto_fitting_module_v2 import AutoFittingModule


class BatchFittingModule(QWidget):
    """Standalone Batch Fitting Module - wrapper for Auto Fitting batch functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #FAF0FF;")
        
        # Initialize the main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Create header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #E6D5F5;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("📊 Batch Peak Fitting")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #7B1FA2; background-color: transparent;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Automated batch processing for multiple XRD data files\n"
            "Auto-detect peaks, fit parameters, and export results"
        )
        desc_label.setFont(QFont('Arial', 11))
        desc_label.setStyleSheet("color: #4A148C; background-color: transparent;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        header_layout.addWidget(desc_label)
        
        main_layout.addWidget(header_frame)
        
        # Create info frame
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #F3E5F5;
                border: 2px solid #BA68C8;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        info_title = QLabel("ℹ️ How to Use:")
        info_title.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        info_title.setStyleSheet("color: #7B1FA2; background-color: transparent;")
        info_layout.addWidget(info_title)
        
        steps = [
            "1. Click 'Launch Batch Fitting' to open the full interface",
            "2. Load XRD data files (.xy, .dat, .txt)",
            "3. Configure batch settings (verification, auto-save, etc.)",
            "4. Click 'Batch Auto Fit' to start processing",
            "5. Results will be auto-saved and merged into batch_summary.csv"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setFont(QFont('Arial', 10))
            step_label.setStyleSheet("color: #4A148C; background-color: transparent; padding: 3px;")
            info_layout.addWidget(step_label)
        
        main_layout.addWidget(info_frame)
        
        # Create features frame
        features_frame = QFrame()
        features_frame.setStyleSheet("""
            QFrame {
                background-color: #E1BEE7;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        features_layout = QVBoxLayout(features_frame)
        
        features_title = QLabel("✨ Features:")
        features_title.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        features_title.setStyleSheet("color: #6A1B9A; background-color: transparent;")
        features_layout.addWidget(features_title)
        
        features = [
            "• Auto peak detection and fitting",
            "• Interactive verification for each file",
            "• Background subtraction",
            "• Peak retention across files (manual adjustments preserved)",
            "• Auto-save results with CSV summary",
            "• Support for Voigt and Pseudo-Voigt functions"
        ]
        
        for feature in features:
            feature_label = QLabel(feature)
            feature_label.setFont(QFont('Arial', 10))
            feature_label.setStyleSheet("color: #4A148C; background-color: transparent; padding: 2px;")
            features_layout.addWidget(feature_label)
        
        main_layout.addWidget(features_frame)
        
        # Create launch button
        launch_btn = QPushButton("🚀 Launch Batch Fitting")
        launch_btn.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        launch_btn.setFixedHeight(60)
        launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #6A1B9A;
            }
        """)
        launch_btn.clicked.connect(self.launch_batch_fitting)
        main_layout.addWidget(launch_btn)
        
        # Add stretch to push everything up
        main_layout.addStretch()
        
        # Store reference to the full module (will be created on demand)
        self.auto_fitting_window = None
    
    def launch_batch_fitting(self):
        """Launch the full Auto Fitting module for batch processing"""
        if self.auto_fitting_window is None:
            # Create a new window with the AutoFittingModule
            from PyQt6.QtWidgets import QDialog, QVBoxLayout
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Batch Peak Fitting - Full Interface")
            dialog.resize(1400, 900)
            
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Create AutoFittingModule
            self.auto_fitting_module = AutoFittingModule()
            layout.addWidget(self.auto_fitting_module)
            
            self.auto_fitting_window = dialog
        
        # Show the window
        self.auto_fitting_window.show()
        self.auto_fitting_window.raise_()
        self.auto_fitting_window.activateWindow()
