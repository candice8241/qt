# -*- coding: utf-8 -*-
"""
Dioptas Integration Module
Provides standalone interface for Dioptas calibration software
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QFrame, QTextEdit, QGroupBox, QMessageBox, QFileDialog,
                              QLineEdit, QComboBox)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal
from PyQt6.QtGui import QFont
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from gui_base import GUIBase
from theme_module import ModernButton


class DioptasModule(GUIBase):
    """Standalone Dioptas integration module"""
    
    # Signals
    calibration_loaded = pyqtSignal(dict)  # Emit when calibration is imported
    
    def __init__(self, parent, root):
        """
        Initialize Dioptas module
        
        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        GUIBase.__init__(self)
        self.parent = parent
        self.root = root
        
        self.dioptas_process = None
        self.temp_dir = None
    
    def setup_ui(self):
        """Setup the Dioptas module user interface"""
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)
        
        # Title
        title_label = QLabel("🔬 Dioptas Integration")
        title_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 10px;")
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Launch Dioptas for advanced detector calibration and diffraction analysis.\n"
            #"Dioptas is a professional tool for X-ray diffraction image processing."
        )
        desc_label.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 5px; font-size: 11pt;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Status section
        self.setup_status_section(layout)
        
        # Launch section
        self.setup_launch_section(layout)
        
        # Process control section
        self.setup_process_info_section(layout)
        
        # Log output
        log_label = QLabel("Activity Log:")
        log_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        log_label.setStyleSheet(f"color: {self.colors['text_dark']}; padding-top: 10px;")
        layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)
        self.log_output.setFont(QFont('Courier', 9))
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.log_output)
        
        layout.addStretch()
        
        # Check Dioptas status on startup
        self.check_dioptas_status()
    
    def setup_status_section(self, parent_layout):
        """Setup Dioptas status check section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        
        title = QLabel("📊 Dioptas Status")
        title.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']};")
        card_layout.addWidget(title)
        
        # Status display
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 5, 0, 5)
        
        self.status_label = QLabel("Checking...")
        self.status_label.setFont(QFont('Arial', 10))
        status_layout.addWidget(self.status_label)
        
        card_layout.addWidget(status_frame)
        
        # Check button - centered
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 10, 0, 10)
        
        btn_layout.addStretch()
        
        check_btn = ModernButton("Check Status",
                                self.check_dioptas_status,
                               
                                bg_color='#DBE3F9',
                                hover_color='#C5D3F0',
                                width=250, height=40,
                                font_size=11,
                                parent=btn_container)
        btn_layout.addWidget(check_btn)
        
        btn_layout.addStretch()
        
        card_layout.addWidget(btn_container)
        parent_layout.addWidget(card)
    
    def setup_launch_section(self, parent_layout):
        """Setup Dioptas launch section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        
        title = QLabel("🚀 Launch Application")
        title.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']};")
        card_layout.addWidget(title)
        
        # Description
        desc_label = QLabel(
            "Start Dioptas in a separate window. You can manually load images and "
            "perform calibration within Dioptas interface."
        )
        desc_label.setStyleSheet(f"color: {self.colors['text_dark']}; font-size: 10pt; padding: 5px;")
        desc_label.setWordWrap(True)
        card_layout.addWidget(desc_label)
        
        # Launch button - centered
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 10, 0, 10)
        
        btn_layout.addStretch()
        
        launch_btn = ModernButton("Launch Dioptas",
                                lambda: self.launch_dioptas(),
                                
                                bg_color='#DBE3F9',
                                hover_color='#C5D3F0',
                                width=250, height=40,
                                font_size=11,
                                parent=btn_container)
        btn_layout.addWidget(launch_btn)
        
        btn_layout.addStretch()
        
        card_layout.addWidget(btn_container)
        parent_layout.addWidget(card)
    
    
    def setup_process_info_section(self, parent_layout):
        """Setup process control section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        
        title = QLabel("⚙️ Process Control")
        title.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']};")
        card_layout.addWidget(title)
        
        # Description
        desc_label = QLabel(
            "Monitor and control the Dioptas process. Force terminate if the application becomes unresponsive."
        )
        desc_label.setStyleSheet(f"color: {self.colors['text_dark']}; font-size: 10pt; padding: 5px;")
        desc_label.setWordWrap(True)
        card_layout.addWidget(desc_label)
        
        # Process status
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 5, 0, 5)
        
        status_label = QLabel("Process Status:")
        status_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        status_layout.addWidget(status_label)
        
        self.process_status_label = QLabel("Not Running")
        self.process_status_label.setFont(QFont('Arial', 10))
        self.process_status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self.process_status_label)
        
        card_layout.addWidget(status_frame)
        
        # Terminate button - centered
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 10, 0, 10)
        
        btn_layout.addStretch()
        
        self.terminate_btn = ModernButton("Terminate Dioptas",
                                         self.terminate_dioptas,
                                         
                                         bg_color='#DBE3F9',
                                         hover_color='#C5D3F0',
                                         width=250, height=40,
                                         font_size=11,
                                         parent=btn_container)
        self.terminate_btn.setEnabled(False)
        btn_layout.addWidget(self.terminate_btn)
        
        btn_layout.addStretch()
        
        card_layout.addWidget(btn_container)
        parent_layout.addWidget(card)
    
    def check_dioptas_status(self):
        """Check if Dioptas is installed and available"""
        self.log("Checking Dioptas installation...")
        
        # Try importing dioptas module
        try:
            import dioptas
            version = getattr(dioptas, '__version__', 'unknown')
            self.status_label.setText(f"✅ Dioptas available (v{version})")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.log(f"Dioptas module found: {dioptas.__file__}")
            self.log(f"Version: {version}")
            return True
        except ImportError:
            pass
        
        # Try dioptas command line
        try:
            result = subprocess.run(['dioptas', '--version'], 
                                   capture_output=True, 
                                   timeout=5,
                                   text=True)
            if result.returncode == 0:
                self.status_label.setText("✅ Dioptas command available")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.log("Dioptas command found in system PATH")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Not found
        self.status_label.setText("❌ Dioptas not installed")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.log("Dioptas not found. Install via: pip install dioptas")
        return False
    
    def launch_dioptas(self):
        """Launch Dioptas application in detached mode"""
        self.log("Launching Dioptas...")
        
        try:
            # Terminate existing process if any
            if self.dioptas_process is not None:
                try:
                    self.dioptas_process.terminate()
                    self.dioptas_process.waitForFinished(500)
                except:
                    pass
            
            # Update UI immediately
            self.process_status_label.setText("Launching...")
            self.process_status_label.setStyleSheet("color: orange; font-weight: bold;")
            
            # Use startDetached for faster, independent launch without screen flash
            success = QProcess.startDetached('dioptas', [])
            
            if success:
                self.log("✅ Dioptas launched successfully (detached mode)")
                # Simulate running status since we can't track detached process
                self.process_status_label.setText("Running (External)")
                self.process_status_label.setStyleSheet("color: green; font-weight: bold;")
                self.terminate_btn.setEnabled(False)  # Can't control detached process
            else:
                raise Exception("Failed to start Dioptas")
            
        except Exception as e:
            self.process_status_label.setText("Not Running")
            self.process_status_label.setStyleSheet("color: gray;")
            QMessageBox.critical(
                self.parent,
                "Launch Error",
                f"Failed to launch Dioptas:\n{str(e)}\n\n"
                "Please ensure Dioptas is installed:\n"
                "  pip install dioptas"
            )
            self.log(f"ERROR: {str(e)}")
    
    def terminate_dioptas(self):
        """Terminate the running Dioptas process"""
        if self.dioptas_process and self.dioptas_process.state() == QProcess.ProcessState.Running:
            reply = QMessageBox.question(
                self.parent,
                "Confirm Termination",
                "Are you sure you want to terminate the Dioptas process?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.dioptas_process.terminate()
                if not self.dioptas_process.waitForFinished(3000):
                    self.dioptas_process.kill()
                self.log("Dioptas process terminated")
    
    def on_dioptas_started(self):
        """Handle Dioptas process start event"""
        self.log("✅ Dioptas started successfully")
        self.process_status_label.setText("Running")
        self.process_status_label.setStyleSheet("color: green; font-weight: bold;")
        self.terminate_btn.setEnabled(True)
    
    def on_dioptas_finished(self, exit_code, exit_status):
        """Handle Dioptas process termination event"""
        if exit_status == QProcess.ExitStatus.NormalExit:
            self.log(f"Dioptas exited normally (exit code: {exit_code})")
        else:
            self.log(f"Dioptas crashed (exit code: {exit_code})")
        self.process_status_label.setText("Not Running")
        self.process_status_label.setStyleSheet("color: gray;")
        self.terminate_btn.setEnabled(False)
    
    def on_dioptas_error(self, error):
        """Handle Dioptas process error events"""
        error_messages = {
            QProcess.ProcessError.FailedToStart: "Failed to start process",
            QProcess.ProcessError.Crashed: "Process crashed unexpectedly",
            QProcess.ProcessError.Timedout: "Process timed out",
            QProcess.ProcessError.WriteError: "Write error occurred",
            QProcess.ProcessError.ReadError: "Read error occurred",
            QProcess.ProcessError.UnknownError: "Unknown error occurred"
        }
        
        error_msg = error_messages.get(error, "Unknown error")
        self.log(f"❌ Dioptas error: {error_msg}")
        self.process_status_label.setText(f"Error: {error_msg}")
        self.process_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.terminate_btn.setEnabled(False)
    
    def log(self, message):
        """Append message to activity log with timestamp"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
    
    def cleanup(self):
        """Clean up resources on module close"""
        # Terminate Dioptas process if running
        if self.dioptas_process and self.dioptas_process.state() == QProcess.ProcessState.Running:
            self.dioptas_process.terminate()
            self.dioptas_process.waitForFinished(3000)
        
        # Remove temporary directory if exists
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass