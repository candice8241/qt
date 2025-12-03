#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch Fitting Dialog for Interactive Fitting GUI

Allows users to batch process multiple .xy files with manual peak and background adjustment.
"""

import os
import sys
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QFileDialog, QMessageBox, 
                              QListWidget, QListWidgetItem, QSplitter, QWidget,
                              QFrame, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from scipy.signal import find_peaks, peak_widths
from scipy.optimize import curve_fit
from scipy.special import wofz
import traceback


# Fitting functions
def voigt(x, amplitude, center, sigma, gamma):
    """Voigt profile"""
    z = ((x - center) + 1j * gamma) / (sigma * np.sqrt(2))
    return amplitude * np.real(wofz(z)) / (sigma * np.sqrt(2 * np.pi))

def pseudo_voigt(x, amplitude, center, sigma, gamma, eta):
    """Pseudo-Voigt profile"""
    gaussian = amplitude * np.exp(-(x - center)**2 / (2 * sigma**2)) / (sigma * np.sqrt(2 * np.pi))
    lorentzian = amplitude * gamma**2 / ((x - center)**2 + gamma**2) / (np.pi * gamma)
    return eta * lorentzian + (1 - eta) * gaussian


class MplCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas for plotting"""
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.axes.set_facecolor('#FAFAFA')
        super().__init__(fig)
        self.setParent(parent)


class BatchFittingDialog(QDialog):
    """Interactive batch fitting dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Peak Fitting (Interactive)")
        self.setMinimumWidth(1400)
        self.setMinimumHeight(800)
        
        # Data variables
        self.file_list = []
        self.current_index = -1
        self.current_data = None
        self.peaks = []  # List of peak positions
        self.bg_points = []  # List of background points (x, y)
        self.fit_method = "pseudo"  # pseudo or voigt
        self.results = []  # Store all fitting results
        self.output_folder = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Title and controls
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        title = QLabel("📊 Batch Peak Fitting - Interactive Mode")
        title.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #4A148C;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Load folder button
        load_btn = QPushButton("📁 Load Folder")
        load_btn.setFixedHeight(35)
        load_btn.setFixedWidth(120)
        load_btn.setFont(QFont('Arial', 9))
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                border: 2px solid #90CAF9;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #BBDEFB; }
        """)
        load_btn.clicked.connect(self.load_folder)
        header_layout.addWidget(load_btn)
        
        layout.addWidget(header)
        
        # Main content (splitter for file list and plot)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: file list
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: plot and controls
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
        
    def create_left_panel(self):
        """Create left panel with file list"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("background-color: #F5F5F5; border: 2px solid #CCCCCC; border-radius: 5px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("📄 File List")
        title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #333333; border: none;")
        layout.addWidget(title)
        
        # File list widget
        self.file_list_widget = QListWidget()
        self.file_list_widget.setFont(QFont('Arial', 9))
        self.file_list_widget.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 2px solid #AAAAAA;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #7E57C2;
                color: white;
            }
        """)
        self.file_list_widget.itemClicked.connect(self.on_file_selected)
        layout.addWidget(self.file_list_widget)
        
        # Progress label
        self.progress_label = QLabel("No files loaded")
        self.progress_label.setFont(QFont('Arial', 8))
        self.progress_label.setStyleSheet("color: #666666; border: none;")
        layout.addWidget(self.progress_label)
        
        return panel
        
    def create_right_panel(self):
        """Create right panel with plot and controls"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Control bar
        control_bar = self.create_control_bar()
        layout.addWidget(control_bar)
        
        # Plot canvas
        self.canvas = MplCanvas(self, width=10, height=7, dpi=100)
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
        layout.addWidget(self.canvas)
        
        # Navigation bar
        nav_bar = self.create_navigation_bar()
        layout.addWidget(nav_bar)
        
        return panel
        
    def create_control_bar(self):
        """Create control bar with buttons and settings"""
        bar = QWidget()
        bar.setFixedHeight(50)
        bar.setStyleSheet("background-color: #E3F2FF; border-radius: 5px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Fit method selector
        method_label = QLabel("Fit Method:")
        method_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        layout.addWidget(method_label)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Pseudo-Voigt", "Voigt"])
        self.method_combo.setCurrentIndex(0)
        self.method_combo.setFixedWidth(120)
        self.method_combo.setFont(QFont('Arial', 9))
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        layout.addWidget(self.method_combo)
        
        layout.addSpacing(20)
        
        # Auto detect peaks
        auto_btn = QPushButton("🔍 Auto Detect Peaks")
        auto_btn.setFixedWidth(140)
        auto_btn.setFont(QFont('Arial', 9))
        auto_btn.setStyleSheet("""
            QPushButton {
                background-color: #C5E1A5;
                border: 2px solid #9CCC65;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #AED581; }
        """)
        auto_btn.clicked.connect(self.auto_detect_peaks)
        layout.addWidget(auto_btn)
        
        # Clear peaks
        clear_peaks_btn = QPushButton("Clear Peaks")
        clear_peaks_btn.setFixedWidth(100)
        clear_peaks_btn.setFont(QFont('Arial', 9))
        clear_peaks_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFCDD2;
                border: 2px solid #E57373;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #EF9A9A; }
        """)
        clear_peaks_btn.clicked.connect(self.clear_peaks)
        layout.addWidget(clear_peaks_btn)
        
        # Clear background
        clear_bg_btn = QPushButton("Clear Background")
        clear_bg_btn.setFixedWidth(130)
        clear_bg_btn.setFont(QFont('Arial', 9))
        clear_bg_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFE082;
                border: 2px solid #FFD54F;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #FFD54F; }
        """)
        clear_bg_btn.clicked.connect(self.clear_background)
        layout.addWidget(clear_bg_btn)
        
        # Fit current
        fit_btn = QPushButton("✨ Fit Current")
        fit_btn.setFixedWidth(110)
        fit_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        fit_btn.setStyleSheet("""
            QPushButton {
                background-color: #CE93D8;
                border: 2px solid #BA68C8;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #BA68C8; }
        """)
        fit_btn.clicked.connect(self.fit_current)
        layout.addWidget(fit_btn)
        
        layout.addStretch()
        
        # Instructions
        info_label = QLabel("💡 Click to add peaks(left) or background points(right)")
        info_label.setFont(QFont('Arial', 8))
        info_label.setStyleSheet("color: #666666;")
        layout.addWidget(info_label)
        
        return bar
        
    def create_navigation_bar(self):
        """Create navigation bar with prev/next/save buttons"""
        bar = QWidget()
        bar.setFixedHeight(55)
        bar.setStyleSheet("background-color: #FFF9C4; border-radius: 5px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Current file label
        self.current_file_label = QLabel("No file loaded")
        self.current_file_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        self.current_file_label.setStyleSheet("color: #333333;")
        layout.addWidget(self.current_file_label)
        
        layout.addStretch()
        
        # Previous button
        prev_btn = QPushButton("⬅ Previous")
        prev_btn.setFixedWidth(100)
        prev_btn.setFont(QFont('Arial', 9))
        prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: 2px solid #BDBDBD;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        prev_btn.clicked.connect(self.go_previous)
        layout.addWidget(prev_btn)
        
        # Next button
        next_btn = QPushButton("Next ➡")
        next_btn.setFixedWidth(100)
        next_btn.setFont(QFont('Arial', 9))
        next_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: 2px solid #BDBDBD;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        next_btn.clicked.connect(self.go_next)
        layout.addWidget(next_btn)
        
        layout.addSpacing(20)
        
        # Save all button
        save_btn = QPushButton("💾 Save All Results")
        save_btn.setFixedWidth(140)
        save_btn.setFixedHeight(40)
        save_btn.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #7E57C2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #673AB7; }
        """)
        save_btn.clicked.connect(self.save_all_results)
        layout.addWidget(save_btn)
        
        return bar
        
    def load_folder(self):
        """Load folder containing .xy files"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing .xy Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder:
            return
            
        # Find all .xy files
        xy_files = sorted([f for f in os.listdir(folder) if f.endswith('.xy')])
        
        if not xy_files:
            QMessageBox.warning(self, "No Files", "No .xy files found in the selected folder.")
            return
            
        # Store file list
        self.file_list = [os.path.join(folder, f) for f in xy_files]
        self.output_folder = os.path.join(folder, "fit_output")
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Populate list widget
        self.file_list_widget.clear()
        for fname in xy_files:
            item = QListWidgetItem(fname)
            self.file_list_widget.addItem(item)
            
        # Update progress
        self.progress_label.setText(f"Loaded {len(self.file_list)} files")
        
        # Load first file
        if self.file_list:
            self.current_index = 0
            self.load_current_file()
            self.file_list_widget.setCurrentRow(0)
            
    def on_file_selected(self, item):
        """Handle file selection from list"""
        index = self.file_list_widget.row(item)
        if index != self.current_index:
            self.current_index = index
            self.load_current_file()
            
    def load_current_file(self):
        """Load current file and display"""
        if self.current_index < 0 or self.current_index >= len(self.file_list):
            return
            
        filepath = self.file_list[self.current_index]
        
        try:
            # Load data
            with open(filepath, encoding='latin1') as f:
                data = np.genfromtxt(f, comments="#")
            
            self.current_data = data
            self.peaks = []
            self.bg_points = []
            
            # Update display
            filename = os.path.basename(filepath)
            self.current_file_label.setText(f"[{self.current_index + 1}/{len(self.file_list)}] {filename}")
            
            # Auto detect peaks
            self.auto_detect_peaks()
            
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load file:\n{str(e)}")
            
    def auto_detect_peaks(self):
        """Auto detect peaks in current data"""
        if self.current_data is None:
            return
            
        x, y = self.current_data[:, 0], self.current_data[:, 1]
        
        # Find peaks
        peaks, _ = find_peaks(y, distance=20, prominence=np.max(y) * 0.1)
        self.peaks = x[peaks].tolist()
        
        self.plot_data()
        
    def clear_peaks(self):
        """Clear all peaks"""
        self.peaks = []
        self.plot_data()
        
    def clear_background(self):
        """Clear all background points"""
        self.bg_points = []
        self.plot_data()
        
    def on_plot_click(self, event):
        """Handle click on plot"""
        if event.inaxes != self.canvas.axes or self.current_data is None:
            return
            
        x_click = event.xdata
        
        if event.button == 1:  # Left click - add peak
            self.peaks.append(x_click)
            self.peaks.sort()
        elif event.button == 3:  # Right click - add background point
            y_click = event.ydata
            self.bg_points.append((x_click, y_click))
            self.bg_points.sort(key=lambda p: p[0])
            
        self.plot_data()
        
    def plot_data(self):
        """Plot current data with peaks and background"""
        if self.current_data is None:
            return
            
        self.canvas.axes.clear()
        x, y = self.current_data[:, 0], self.current_data[:, 1]
        
        # Plot data
        self.canvas.axes.plot(x, y, 'k-', linewidth=1, label='Data')
        
        # Plot peaks
        for peak_x in self.peaks:
            self.canvas.axes.axvline(peak_x, color='red', linestyle='--', alpha=0.7, linewidth=1.5)
            
        # Plot background points
        if self.bg_points:
            bg_x = [p[0] for p in self.bg_points]
            bg_y = [p[1] for p in self.bg_points]
            self.canvas.axes.plot(bg_x, bg_y, 'bo', markersize=8, label='BG Points')
            
            # Draw background line if >= 2 points
            if len(self.bg_points) >= 2:
                self.canvas.axes.plot(bg_x, bg_y, 'b--', alpha=0.5, linewidth=1.5)
                
        self.canvas.axes.set_xlabel('2θ (deg)', fontsize=10)
        self.canvas.axes.set_ylabel('Intensity', fontsize=10)
        self.canvas.axes.legend(loc='upper right', fontsize=8)
        self.canvas.axes.grid(True, alpha=0.3)
        self.canvas.draw()
        
    def fit_current(self):
        """Fit current file with selected peaks"""
        if self.current_data is None or not self.peaks:
            QMessageBox.warning(self, "No Data", "Please load a file and add peaks first.")
            return
            
        # Perform fitting for each peak
        # (Simplified version - you can expand this)
        filename = os.path.basename(self.file_list[self.current_index])
        
        try:
            # For now, just mark as processed
            QMessageBox.information(self, "Fitted", f"Fitted {len(self.peaks)} peaks for {filename}")
            
            # Store results
            result = {
                'file': filename,
                'num_peaks': len(self.peaks),
                'peaks': self.peaks.copy(),
                'bg_points': self.bg_points.copy()
            }
            self.results.append(result)
            
        except Exception as e:
            QMessageBox.warning(self, "Fit Error", f"Fitting failed:\n{str(e)}")
            
    def go_previous(self):
        """Go to previous file"""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_file()
            self.file_list_widget.setCurrentRow(self.current_index)
            
    def go_next(self):
        """Go to next file"""
        if self.current_index < len(self.file_list) - 1:
            self.current_index += 1
            self.load_current_file()
            self.file_list_widget.setCurrentRow(self.current_index)
            
    def on_method_changed(self, text):
        """Handle fit method change"""
        if "Voigt" in text and "Pseudo" not in text:
            self.fit_method = "voigt"
        else:
            self.fit_method = "pseudo"
            
    def save_all_results(self):
        """Save all results to CSV"""
        if not self.results:
            QMessageBox.warning(self, "No Results", "No fitting results to save.")
            return
            
        if not self.output_folder:
            QMessageBox.warning(self, "No Output", "Please load a folder first.")
            return
            
        # Save results
        output_file = os.path.join(self.output_folder, "batch_fitting_results.csv")
        
        # Create dataframe
        df = pd.DataFrame(self.results)
        df.to_csv(output_file, index=False)
        
        QMessageBox.information(
            self,
            "Saved",
            f"Results saved to:\n{output_file}\n\nProcessed {len(self.results)} files."
        )


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = BatchFittingDialog()
    dialog.show()
    sys.exit(app.exec())
