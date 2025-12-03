#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch Fitting Dialog for Interactive Fitting GUI

Allows users to batch process multiple .xy files for peak fitting.
"""

import os
import sys
# Set matplotlib backend before importing pyplot
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend to avoid conflicts with PyQt6

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QLineEdit, QComboBox, QTextEdit,
                              QFileDialog, QMessageBox, QGroupBox, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from peak_fitting import BatchFitter
import pandas as pd
import traceback


class BatchFittingWorker(QThread):
    """Worker thread for batch fitting to avoid freezing the UI"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # current, total
    
    def __init__(self, folder, fit_method):
        super().__init__()
        self.folder = folder
        self.fit_method = fit_method
        
    def run(self):
        """Run batch fitting in separate thread"""
        try:
            self.log_signal.emit("Initializing batch fitter...")
            
            # Create BatchFitter instance
            fitter = BatchFitter(folder=self.folder, fit_method=self.fit_method)
            
            # Get list of files
            files = sorted(f for f in os.listdir(self.folder) if f.endswith(".xy"))
            total_files = len(files)
            
            self.log_signal.emit(f"Found {total_files} .xy files to process\n")
            
            # Process each file manually to show progress
            all_dfs = []
            for idx, fname in enumerate(files, 1):
                self.log_signal.emit(f"[{idx}/{total_files}] Processing: {fname}")
                fpath = os.path.join(self.folder, fname)
                
                try:
                    df = fitter.process_file(fpath)
                    if df is not None:
                        all_dfs.append(df)
                        all_dfs.append(pd.DataFrame([[""] * len(df.columns)], columns=df.columns))
                        self.log_signal.emit(f"  ✓ Success: {fname}")
                    else:
                        self.log_signal.emit(f"  ⚠ No peaks found: {fname}")
                except Exception as e:
                    self.log_signal.emit(f"  ✗ Error: {fname} - {str(e)}")
                
                self.progress.emit(idx, total_files)
            
            # Save combined results
            if all_dfs:
                import pandas as pd
                combined_df = pd.concat(all_dfs, ignore_index=True)
                combined_csv_path = os.path.join(fitter.save_dir, "all_results.csv")
                combined_df.to_csv(combined_csv_path, index=False)
                self.log_signal.emit(f"\n📦 Combined results saved to: {combined_csv_path}")
            
            self.finished.emit()
            
        except Exception as e:
            error_msg = f"Error during batch fitting:\n{str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class BatchFittingDialog(QDialog):
    """Dialog for batch fitting configuration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Peak Fitting")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.worker = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📊 Batch Peak Fitting")
        title.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #4A148C; padding: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Automatically fit peaks for multiple .xy files in a folder.\n"
            "Results will be saved in a 'fit_output' subfolder."
        )
        desc.setFont(QFont('Arial', 9))
        desc.setStyleSheet("color: #666666; padding: 5px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Input folder section
        input_group = QGroupBox("Input Settings")
        input_group.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        input_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #CCCCCC;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(10)
        
        # Input folder
        folder_row = QHBoxLayout()
        folder_label = QLabel("Input Folder:")
        folder_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        folder_label.setFixedWidth(100)
        folder_row.addWidget(folder_label)
        
        self.folder_entry = QLineEdit()
        self.folder_entry.setPlaceholderText("Select folder containing .xy files...")
        self.folder_entry.setFont(QFont('Arial', 9))
        self.folder_entry.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 2px solid #AAAAAA;
                border-radius: 4px;
            }
        """)
        folder_row.addWidget(self.folder_entry)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setFont(QFont('Arial', 9))
        browse_btn.setFixedWidth(80)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: black;
                border: 2px solid #90CAF9;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        browse_btn.clicked.connect(self.browse_folder)
        folder_row.addWidget(browse_btn)
        
        input_layout.addLayout(folder_row)
        
        # Fit method
        method_row = QHBoxLayout()
        method_label = QLabel("Fit Method:")
        method_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        method_label.setFixedWidth(100)
        method_row.addWidget(method_label)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Pseudo-Voigt", "Voigt"])
        self.method_combo.setCurrentIndex(0)
        self.method_combo.setFont(QFont('Arial', 9))
        self.method_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 2px solid #AAAAAA;
                border-radius: 4px;
            }
        """)
        method_row.addWidget(self.method_combo)
        method_row.addStretch()
        
        input_layout.addLayout(method_row)
        
        layout.addWidget(input_group)
        
        # Output/Log section
        log_group = QGroupBox("Processing Log")
        log_group.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        log_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #CCCCCC;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Courier New', 8))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.log_text.setPlaceholderText("Logs will appear here during processing...")
        log_layout.addWidget(self.log_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #CCCCCC;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #7E57C2;
            }
        """)
        log_layout.addWidget(self.progress_bar)
        
        layout.addWidget(log_group)
        
        # Button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.run_btn = QPushButton("🚀 Run Batch Fitting")
        self.run_btn.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        self.run_btn.setFixedHeight(40)
        self.run_btn.setFixedWidth(180)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #7E57C2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #673AB7;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.run_btn.clicked.connect(self.run_batch_fitting)
        btn_row.addWidget(self.run_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setFont(QFont('Arial', 10))
        close_btn.setFixedHeight(40)
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: black;
                border: 2px solid #CCCCCC;
                border-radius: 6px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
    def browse_folder(self):
        """Browse for input folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing .xy Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.folder_entry.setText(folder)
            self.log(f"Selected folder: {folder}")
            
            # Count .xy files
            xy_files = [f for f in os.listdir(folder) if f.endswith('.xy')]
            self.log(f"Found {len(xy_files)} .xy files")
            
    def log(self, message):
        """Add message to log"""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def update_progress(self, current, total):
        """Update progress bar"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{current}/{total} files ({percentage}%)")
        
    def run_batch_fitting(self):
        """Run batch fitting process"""
        folder = self.folder_entry.text().strip()
        
        # Validation
        if not folder:
            QMessageBox.warning(self, "Input Required", "Please select an input folder.")
            return
            
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid Folder", "The selected folder does not exist.")
            return
            
        # Check for .xy files
        xy_files = [f for f in os.listdir(folder) if f.endswith('.xy')]
        if not xy_files:
            QMessageBox.warning(
                self,
                "No Files Found",
                "No .xy files found in the selected folder."
            )
            return
            
        # Get fit method
        fit_method = self.method_combo.currentText().lower().replace("-", "")
        if fit_method == "pseudovoigt":
            fit_method = "pseudo"
            
        # Confirm before running
        reply = QMessageBox.question(
            self,
            "Confirm Batch Fitting",
            f"Start batch fitting for {len(xy_files)} files using {self.method_combo.currentText()} method?\n\n"
            f"Results will be saved in:\n{os.path.join(folder, 'fit_output')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
            
        # Disable button during processing
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Processing...")
        self.log_text.clear()
        self.log("=" * 60)
        self.log("Starting batch fitting process...")
        self.log(f"Input folder: {folder}")
        self.log(f"Fit method: {self.method_combo.currentText()}")
        self.log(f"Number of files: {len(xy_files)}")
        self.log("=" * 60)
        self.log("")
        
        # Create and start worker thread
        self.worker = BatchFittingWorker(folder, fit_method)
        self.worker.finished.connect(self.on_fitting_finished)
        self.worker.error.connect(self.on_fitting_error)
        self.worker.log_signal.connect(self.log)
        self.worker.progress.connect(self.update_progress)
        
        # Show and reset progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker.start()
        
    def on_fitting_finished(self):
        """Called when batch fitting finishes successfully"""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🚀 Run Batch Fitting")
        self.progress_bar.setVisible(False)
        self.log("")
        self.log("=" * 60)
        self.log("✓ Batch fitting completed successfully!")
        self.log("=" * 60)
        
        QMessageBox.information(
            self,
            "Success",
            "Batch fitting completed successfully!\n\n"
            f"Results saved in:\n{os.path.join(self.folder_entry.text(), 'fit_output')}"
        )
        
    def on_fitting_error(self, error_msg):
        """Called when batch fitting encounters an error"""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🚀 Run Batch Fitting")
        self.progress_bar.setVisible(False)
        self.log("")
        self.log("=" * 60)
        self.log("✗ Error occurred during batch fitting")
        self.log("=" * 60)
        self.log(error_msg)
        
        QMessageBox.critical(
            self,
            "Error",
            "An error occurred during batch fitting.\n\n"
            "Please check the log for details."
        )


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = BatchFittingDialog()
    dialog.show()
    sys.exit(app.exec())
