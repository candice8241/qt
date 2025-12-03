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
        
        # Mode: 'peak' or 'background'
        self.add_mode = 'peak'
        
        # Auto-fitting state
        self.auto_fitting = False
        self.fit_tolerance = 0.92  # R-squared tolerance for auto-fitting (0.92 means 92%)
        
        # Zoom state
        self.xlim_original = None
        self.ylim_original = None
        
        # Fitting results for plotting
        self.current_fit_curves = []  # List of (x, y) tuples for fitted curves
        
        # Overlap mode
        self.overlap_mode = False
        self.overlapped_data = []  # List of (filename, x, y, peaks, bg_points) for overlay
        
        self.setup_ui()
        
    def keyPressEvent(self, event):
        """Handle keyboard events"""
        from PyQt6.QtCore import Qt
        
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Enter key - start auto-fitting
            if not self.auto_fitting:
                self.start_auto_fitting()
        elif event.key() == Qt.Key.Key_Left:
            # Left arrow - previous file
            self.go_previous()
        elif event.key() == Qt.Key.Key_Right:
            # Right arrow - next file
            self.go_next()
        elif event.key() == Qt.Key.Key_Space:
            # Space - fit current
            self.fit_current()
        elif event.key() == Qt.Key.Key_A:
            # A - auto detect peaks
            self.auto_detect_peaks()
        elif event.key() == Qt.Key.Key_C:
            # C - clear all
            self.clear_all()
        elif event.key() == Qt.Key.Key_P:
            # P - switch to peak mode
            self.set_mode('peak')
        elif event.key() == Qt.Key.Key_B:
            # B - switch to background mode
            self.set_mode('background')
        elif event.key() == Qt.Key.Key_R:
            # R - reset zoom
            self.reset_zoom()
        elif event.key() == Qt.Key.Key_O:
            # O - toggle overlap mode
            self.overlap_btn.setChecked(not self.overlap_btn.isChecked())
            self.toggle_overlap_mode()
        else:
            super().keyPressEvent(event)
        
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
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        layout.addWidget(self.canvas)
        
        # Navigation bar
        nav_bar = self.create_navigation_bar()
        layout.addWidget(nav_bar)
        
        return panel
        
    def create_control_bar(self):
        """Create control bar with buttons and settings"""
        bar = QWidget()
        bar.setFixedHeight(90)
        bar.setStyleSheet("background-color: #E3F2FF; border-radius: 5px;")
        main_layout = QVBoxLayout(bar)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)
        
        # First row: mode and method
        row1 = QHBoxLayout()
        
        # Add mode selector
        mode_label = QLabel("Add Mode:")
        mode_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        row1.addWidget(mode_label)
        
        self.mode_peak_btn = QPushButton("🔴 Peak")
        self.mode_peak_btn.setFixedWidth(80)
        self.mode_peak_btn.setFont(QFont('Arial', 9))
        self.mode_peak_btn.setCheckable(True)
        self.mode_peak_btn.setChecked(True)
        self.mode_peak_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFCDD2;
                border: 2px solid #E57373;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:checked {
                background-color: #E57373;
                color: white;
                font-weight: bold;
            }
        """)
        self.mode_peak_btn.clicked.connect(lambda: self.set_mode('peak'))
        row1.addWidget(self.mode_peak_btn)
        
        self.mode_bg_btn = QPushButton("🔵 Background")
        self.mode_bg_btn.setFixedWidth(110)
        self.mode_bg_btn.setFont(QFont('Arial', 9))
        self.mode_bg_btn.setCheckable(True)
        self.mode_bg_btn.setStyleSheet("""
            QPushButton {
                background-color: #BBDEFB;
                border: 2px solid #90CAF9;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:checked {
                background-color: #42A5F5;
                color: white;
                font-weight: bold;
            }
        """)
        self.mode_bg_btn.clicked.connect(lambda: self.set_mode('background'))
        row1.addWidget(self.mode_bg_btn)
        
        row1.addSpacing(20)
        
        # Fit method selector
        method_label = QLabel("Fit Method:")
        method_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        row1.addWidget(method_label)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Pseudo-Voigt", "Voigt"])
        self.method_combo.setCurrentIndex(0)
        self.method_combo.setFixedWidth(120)
        self.method_combo.setFont(QFont('Arial', 9))
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        row1.addWidget(self.method_combo)
        
        row1.addStretch()
        
        main_layout.addLayout(row1)
        
        # Second row: actions
        row2 = QHBoxLayout()
        
        # Auto detect peaks
        auto_btn = QPushButton("🔍 Auto Detect")
        auto_btn.setFixedWidth(110)
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
        row2.addWidget(auto_btn)
        
        # Clear all
        clear_all_btn = QPushButton("🗑️ Clear All")
        clear_all_btn.setFixedWidth(90)
        clear_all_btn.setFont(QFont('Arial', 9))
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFCDD2;
                border: 2px solid #E57373;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #EF9A9A; }
        """)
        clear_all_btn.clicked.connect(self.clear_all)
        row2.addWidget(clear_all_btn)
        
        # Reset zoom
        reset_zoom_btn = QPushButton("🔍 Reset Zoom")
        reset_zoom_btn.setFixedWidth(110)
        reset_zoom_btn.setFont(QFont('Arial', 9))
        reset_zoom_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFE082;
                border: 2px solid #FFD54F;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #FFD54F; }
        """)
        reset_zoom_btn.clicked.connect(self.reset_zoom)
        row2.addWidget(reset_zoom_btn)
        
        row2.addSpacing(20)
        
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
        row2.addWidget(fit_btn)
        
        # Auto fit all (Enter key)
        auto_fit_btn = QPushButton("⚡ Auto Fit All (Enter)")
        auto_fit_btn.setFixedWidth(150)
        auto_fit_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        auto_fit_btn.setStyleSheet("""
            QPushButton {
                background-color: #7E57C2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #673AB7; }
        """)
        auto_fit_btn.clicked.connect(self.start_auto_fitting)
        row2.addWidget(auto_fit_btn)
        
        row2.addSpacing(10)
        
        # Overlap button
        self.overlap_btn = QPushButton("📊 Overlap (O)")
        self.overlap_btn.setFixedWidth(120)
        self.overlap_btn.setFont(QFont('Arial', 9))
        self.overlap_btn.setCheckable(True)
        self.overlap_btn.setStyleSheet("""
            QPushButton {
                background-color: #B9F2FF;
                border: 2px solid #81D4FA;
                border-radius: 4px;
                padding: 5px;
                color: black;
            }
            QPushButton:checked {
                background-color: #00BCD4;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #81D4FA; }
        """)
        self.overlap_btn.clicked.connect(self.toggle_overlap_mode)
        row2.addWidget(self.overlap_btn)
        
        # Clear overlay button
        clear_overlay_btn = QPushButton("Clear Overlay")
        clear_overlay_btn.setFixedWidth(100)
        clear_overlay_btn.setFont(QFont('Arial', 8))
        clear_overlay_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFEBEE;
                border: 1px solid #EF5350;
                border-radius: 4px;
                padding: 5px;
                color: #C62828;
            }
            QPushButton:hover { background-color: #FFCDD2; }
        """)
        clear_overlay_btn.clicked.connect(self.clear_overlap)
        row2.addWidget(clear_overlay_btn)
        
        row2.addStretch()
        
        # Instructions
        info_label = QLabel("💡 Left: Add | Right: Delete | Scroll: Zoom | Enter: Auto-fit | O: Overlap")
        info_label.setFont(QFont('Arial', 8))
        info_label.setStyleSheet("color: #666666;")
        row2.addWidget(info_label)
        
        main_layout.addLayout(row2)
        
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
            
            # Reset zoom limits for new file
            self.xlim_original = None
            self.ylim_original = None
            
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
        
        # Auto add background points at start and end if none exist
        if not self.bg_points:
            # Add points at 5% and 95% of x range
            x_range = x.max() - x.min()
            left_idx = int(len(x) * 0.05)
            right_idx = int(len(x) * 0.95)
            
            # Use minimum y values in edge regions for background
            left_region = y[:left_idx + 20]
            right_region = y[right_idx - 20:]
            
            left_y = np.percentile(left_region, 10)
            right_y = np.percentile(right_region, 10)
            
            self.bg_points = [
                (x[left_idx], left_y),
                (x[right_idx], right_y)
            ]
        
        self.plot_data()
        
    def clear_peaks(self):
        """Clear all peaks"""
        self.peaks = []
        self.plot_data()
        
    def clear_background(self):
        """Clear all background points"""
        self.bg_points = []
        self.plot_data()
        
    def clear_all(self):
        """Clear all peaks and background points"""
        self.peaks = []
        self.bg_points = []
        self.plot_data()
        
    def set_mode(self, mode):
        """Set add mode (peak or background)"""
        self.add_mode = mode
        if mode == 'peak':
            self.mode_peak_btn.setChecked(True)
            self.mode_bg_btn.setChecked(False)
        else:
            self.mode_peak_btn.setChecked(False)
            self.mode_bg_btn.setChecked(True)
            
    def snap_to_nearest_peak(self, x_click):
        """Snap to nearest peak position"""
        if self.current_data is None:
            return x_click
            
        x, y = self.current_data[:, 0], self.current_data[:, 1]
        
        # Find data points within search window
        search_window = (x.max() - x.min()) * 0.02  # 2% of x range
        mask = np.abs(x - x_click) < search_window
        
        if not np.any(mask):
            return x_click
            
        # Find maximum y value in window
        y_window = y[mask]
        x_window = x[mask]
        max_idx = np.argmax(y_window)
        
        return x_window[max_idx]
        
    def snap_to_nearest_point(self, x_click, y_click):
        """Snap to nearest data point for background"""
        if self.current_data is None:
            return x_click, y_click
            
        x, y = self.current_data[:, 0], self.current_data[:, 1]
        
        # Find nearest point
        distances = np.sqrt((x - x_click)**2 + ((y - y_click) / np.max(y) * (x.max() - x.min()))**2)
        min_idx = np.argmin(distances)
        
        return x[min_idx], y[min_idx]
        
    def find_nearest_peak(self, x_click, threshold=None):
        """Find nearest peak to click position"""
        if not self.peaks:
            return None
            
        if threshold is None:
            x_range = self.canvas.axes.get_xlim()
            threshold = (x_range[1] - x_range[0]) * 0.02
            
        distances = [abs(p - x_click) for p in self.peaks]
        min_dist = min(distances)
        
        if min_dist < threshold:
            return self.peaks[distances.index(min_dist)]
        return None
        
    def find_nearest_bg_point(self, x_click, y_click, threshold=None):
        """Find nearest background point to click position"""
        if not self.bg_points:
            return None
            
        if threshold is None:
            x_range = self.canvas.axes.get_xlim()
            y_range = self.canvas.axes.get_ylim()
            threshold_x = (x_range[1] - x_range[0]) * 0.02
            threshold_y = (y_range[1] - y_range[0]) * 0.05
        else:
            threshold_x = threshold
            threshold_y = threshold
            
        for i, (bx, by) in enumerate(self.bg_points):
            if abs(bx - x_click) < threshold_x and abs(by - y_click) < threshold_y:
                return i
        return None
        
    def on_plot_click(self, event):
        """Handle click on plot"""
        if event.inaxes != self.canvas.axes or self.current_data is None:
            return
            
        x_click = event.xdata
        y_click = event.ydata
        
        if event.button == 1:  # Left click - add
            if self.add_mode == 'peak':
                # Snap to nearest peak
                x_snap = self.snap_to_nearest_peak(x_click)
                self.peaks.append(x_snap)
                self.peaks.sort()
            else:  # background
                # Snap to nearest point
                x_snap, y_snap = self.snap_to_nearest_point(x_click, y_click)
                self.bg_points.append((x_snap, y_snap))
                self.bg_points.sort(key=lambda p: p[0])
                
        elif event.button == 3:  # Right click - delete
            if self.add_mode == 'peak':
                # Find and remove nearest peak
                peak = self.find_nearest_peak(x_click)
                if peak is not None:
                    self.peaks.remove(peak)
            else:  # background
                # Find and remove nearest bg point
                idx = self.find_nearest_bg_point(x_click, y_click)
                if idx is not None:
                    del self.bg_points[idx]
            
        self.plot_data()
        
    def on_scroll(self, event):
        """Handle mouse scroll for zooming"""
        if event.inaxes != self.canvas.axes:
            return
            
        # Get current axis limits
        cur_xlim = self.canvas.axes.get_xlim()
        cur_ylim = self.canvas.axes.get_ylim()
        
        # Get event location
        xdata = event.xdata
        ydata = event.ydata
        
        # Zoom factor
        if event.button == 'up':
            scale_factor = 0.9  # Zoom in
        elif event.button == 'down':
            scale_factor = 1.1  # Zoom out
        else:
            return
            
        # Calculate new limits
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        
        self.canvas.axes.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.canvas.axes.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        
        self.canvas.draw()
        
    def reset_zoom(self):
        """Reset zoom to show all data"""
        if self.xlim_original is not None:
            self.canvas.axes.set_xlim(self.xlim_original)
            self.canvas.axes.set_ylim(self.ylim_original)
            self.canvas.draw()
        
    def plot_data(self):
        """Plot current data with peaks and background"""
        if self.current_data is None:
            return
            
        self.canvas.axes.clear()
        x, y = self.current_data[:, 0], self.current_data[:, 1]
        
        # Store original limits for reset
        if self.xlim_original is None:
            self.xlim_original = (x.min(), x.max())
            y_range = y.max() - y.min()
            self.ylim_original = (y.min() - y_range * 0.05, y.max() + y_range * 0.1)
        
        # Plot overlapped data if overlap mode is on
        if self.overlap_mode and self.overlapped_data:
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
            for idx, (fname, ox, oy, opeaks, obg) in enumerate(self.overlapped_data):
                color = colors[idx % len(colors)]
                alpha = 0.5
                self.canvas.axes.plot(ox, oy, '-', linewidth=1, alpha=alpha, 
                                    color=color, label=fname, zorder=1)
        
        # Plot current data
        self.canvas.axes.plot(x, y, 'k-', linewidth=1.5, label='Current', zorder=2)
        
        # Plot fitted curves
        if self.current_fit_curves:
            colors_fit = ['#BA68C8', '#9C27B0', '#7B1FA2', '#6A1B9A', '#4A148C']
            for idx, (fit_x, fit_y) in enumerate(self.current_fit_curves):
                color = colors_fit[idx % len(colors_fit)]
                self.canvas.axes.plot(fit_x, fit_y, '--', linewidth=2, 
                                     color=color, alpha=0.8, 
                                     label=f'Fit Peak {idx+1}', zorder=4)
        
        # Plot peaks as red vertical lines
        for peak_x in self.peaks:
            self.canvas.axes.axvline(peak_x, color='#E57373', linestyle='--', 
                                     alpha=0.8, linewidth=2, zorder=3)
            
        # Plot background points as smaller light blue squares
        if self.bg_points:
            bg_x = [p[0] for p in self.bg_points]
            bg_y = [p[1] for p in self.bg_points]
            
            # Use smaller light blue squares (reduced from 6 to 4)
            self.canvas.axes.plot(bg_x, bg_y, marker='s', color='#90CAF9', 
                                 markerfacecolor='#E3F2FD', markersize=4, 
                                 linestyle='', markeredgewidth=1, 
                                 label='BG', zorder=5)
            
            # Draw background line if >= 2 points
            if len(self.bg_points) >= 2:
                self.canvas.axes.plot(bg_x, bg_y, color='#64B5F6', 
                                     linestyle='--', alpha=0.4, linewidth=1, zorder=2)
            
        self.canvas.axes.set_xlabel('2θ (deg)', fontsize=10, fontweight='bold')
        self.canvas.axes.set_ylabel('Intensity', fontsize=10, fontweight='bold')
        self.canvas.axes.legend(loc='upper right', fontsize=8, framealpha=0.85, 
                               ncol=2 if len(self.current_fit_curves) > 3 else 1)
        self.canvas.axes.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
        self.canvas.axes.set_facecolor('#FAFAFA')
        
        self.canvas.draw()
        
    def fit_current(self):
        """Fit current file with selected peaks"""
        if self.current_data is None or not self.peaks:
            QMessageBox.warning(self, "No Data", "Please load a file and add peaks first.")
            return
            
        filename = os.path.basename(self.file_list[self.current_index])
        
        try:
            # Perform actual fitting
            x, y = self.current_data[:, 0], self.current_data[:, 1]
            
            # Calculate background
            if len(self.bg_points) >= 2:
                bg_x = np.array([p[0] for p in self.bg_points])
                bg_y = np.array([p[1] for p in self.bg_points])
                # Linear interpolation for background
                background = np.interp(x, bg_x, bg_y)
            else:
                # Use simple baseline
                background = np.percentile(y, 5)
                
            # Subtract background
            y_corrected = y - background
            y_corrected = np.maximum(y_corrected, 0)  # Ensure non-negative
            
            # Clear previous fit curves
            self.current_fit_curves = []
            
            # Fit each peak
            peak_results = []
            fit_quality = []
            
            for peak_pos in self.peaks:
                # Define window around peak
                window = 50  # points
                peak_idx = np.argmin(np.abs(x - peak_pos))
                left = max(0, peak_idx - window)
                right = min(len(x), peak_idx + window)
                
                x_local = x[left:right]
                y_local = y_corrected[left:right]
                
                if len(x_local) < 5:
                    continue
                    
                try:
                    # Generate fine x points for smooth curve
                    x_fine = np.linspace(x_local.min(), x_local.max(), 500)
                    
                    # Fit peak
                    if self.fit_method == "voigt":
                        p0 = [np.max(y_local), peak_pos, 0.1, 0.1]
                        bounds = ([0, x_local.min(), 0, 0], 
                                 [np.inf, x_local.max(), np.inf, np.inf])
                        popt, _ = curve_fit(voigt, x_local, y_local, p0=p0, 
                                          bounds=bounds, maxfev=10000)
                        y_fit = voigt(x_local, *popt)
                        y_fit_fine = voigt(x_fine, *popt)
                    else:  # pseudo-voigt
                        p0 = [np.max(y_local), peak_pos, 0.1, 0.1, 0.5]
                        bounds = ([0, x_local.min(), 0, 0, 0], 
                                 [np.inf, x_local.max(), np.inf, np.inf, 1.0])
                        popt, _ = curve_fit(pseudo_voigt, x_local, y_local, p0=p0, 
                                          bounds=bounds, maxfev=10000)
                        y_fit = pseudo_voigt(x_local, *popt)
                        y_fit_fine = pseudo_voigt(x_fine, *popt)
                    
                    # Add background back for display
                    bg_fine = np.interp(x_fine, bg_x, bg_y) if len(self.bg_points) >= 2 else background
                    y_fit_display = y_fit_fine + bg_fine
                    
                    # Store fit curve for plotting
                    self.current_fit_curves.append((x_fine, y_fit_display))
                        
                    # Calculate R-squared
                    ss_res = np.sum((y_local - y_fit)**2)
                    ss_tot = np.sum((y_local - np.mean(y_local))**2)
                    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                    
                    fit_quality.append(r_squared)
                    peak_results.append({
                        'position': popt[1],
                        'amplitude': popt[0],
                        'r_squared': r_squared
                    })
                    
                except Exception as e:
                    fit_quality.append(0)
                    peak_results.append({
                        'position': peak_pos,
                        'amplitude': 0,
                        'r_squared': 0
                    })
            
            # Calculate average fit quality
            avg_r_squared = np.mean(fit_quality) if fit_quality else 0
            
            # Store results
            result = {
                'file': filename,
                'num_peaks': len(self.peaks),
                'peaks': self.peaks.copy(),
                'bg_points': self.bg_points.copy(),
                'peak_results': peak_results,
                'r_squared': avg_r_squared,
                'fit_method': self.fit_method
            }
            self.results.append(result)
            
            # Redraw plot with fit curves
            self.plot_data()
            
            # Show result only if not in auto-fitting mode
            if not self.auto_fitting:
                if avg_r_squared < self.fit_tolerance:
                    QMessageBox.warning(
                        self, 
                        "Poor Fit Quality", 
                        f"Fitted {len(self.peaks)} peaks for {filename}\n\n"
                        f"⚠️ Average R² = {avg_r_squared:.3f} (< {self.fit_tolerance:.2f})\n"
                        f"Consider adjusting peaks or background points."
                    )
                else:
                    QMessageBox.information(
                        self, 
                        "Fit Successful", 
                        f"✓ Fitted {len(self.peaks)} peaks for {filename}\n\n"
                        f"Average R² = {avg_r_squared:.3f}"
                    )
            
            return avg_r_squared
            
        except Exception as e:
            if not self.auto_fitting:
                QMessageBox.warning(self, "Fit Error", f"Fitting failed:\n{str(e)}")
            return 0
            
    def start_auto_fitting(self):
        """Start automatic fitting for all remaining files"""
        if not self.file_list:
            QMessageBox.warning(self, "No Files", "Please load a folder first.")
            return
            
        if not self.peaks:
            QMessageBox.warning(self, "No Peaks", "Please add peaks to the current file first.")
            return
            
        # Start auto-fitting directly without confirmation
        self.auto_fitting = True
        self.continue_auto_fitting()
        
    def continue_auto_fitting(self):
        """Continue auto-fitting to next file"""
        if not self.auto_fitting:
            return
            
        # Fit current file
        r_squared = self.fit_current()
        
        # Check quality
        if r_squared < self.fit_tolerance:
            self.auto_fitting = False
            QMessageBox.warning(
                self,
                "Auto-Fitting Paused",
                f"Auto-fitting paused due to poor fit quality (R² = {r_squared:.3f})\n\n"
                f"Please manually adjust peaks/background and:\n"
                f"- Click 'Fit Current' to fit this file\n"
                f"- Click 'Auto Fit All' again to continue"
            )
            return
            
        # Go to next file
        if self.current_index < len(self.file_list) - 1:
            self.go_next()
            # Continue after a short delay (allow UI to update)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.continue_auto_fitting)
        else:
            self.auto_fitting = False
            QMessageBox.information(
                self,
                "Auto-Fitting Complete",
                f"✓ Auto-fitting completed!\n\n"
                f"Processed {len(self.results)} files.\n"
                f"Click 'Save All Results' to save."
            )
            
    def go_previous(self):
        """Go to previous file"""
        if self.current_index > 0:
            # Add current to overlay if overlap mode is on
            if self.overlap_mode:
                self.add_to_overlay()
                
            self.current_index -= 1
            self.load_current_file()
            self.file_list_widget.setCurrentRow(self.current_index)
            
    def go_next(self):
        """Go to next file"""
        if self.current_index < len(self.file_list) - 1:
            # Add current to overlay if overlap mode is on
            if self.overlap_mode:
                self.add_to_overlay()
                
            self.current_index += 1
            self.load_current_file()
            self.file_list_widget.setCurrentRow(self.current_index)
            
    def on_method_changed(self, text):
        """Handle fit method change"""
        if "Voigt" in text and "Pseudo" not in text:
            self.fit_method = "voigt"
        else:
            self.fit_method = "pseudo"
            
    def toggle_overlap_mode(self):
        """Toggle overlap mode"""
        self.overlap_mode = self.overlap_btn.isChecked()
        
        if self.overlap_mode:
            # Entering overlap mode - add current file to overlapped data
            if self.current_data is not None:
                filename = os.path.basename(self.file_list[self.current_index])
                x, y = self.current_data[:, 0], self.current_data[:, 1]
                self.overlapped_data.append((
                    filename, 
                    x.copy(), 
                    y.copy(), 
                    self.peaks.copy(),
                    self.bg_points.copy()
                ))
                
            # Update button text
            self.overlap_btn.setText(f"📊 Overlap ({len(self.overlapped_data)})")
            
            # Update status label
            self.current_file_label.setText(
                f"[{self.current_index + 1}/{len(self.file_list)}] "
                f"{os.path.basename(self.file_list[self.current_index])} "
                f"[Overlap: {len(self.overlapped_data)} files]"
            )
        else:
            # Exiting overlap mode - keep the data but update display
            self.overlap_btn.setText("📊 Overlap (O)")
            
            # Restore normal status label
            if self.file_list and self.current_index >= 0:
                filename = os.path.basename(self.file_list[self.current_index])
                self.current_file_label.setText(f"[{self.current_index + 1}/{len(self.file_list)}] {filename}")
            
        self.plot_data()
        
    def clear_overlap(self):
        """Clear all overlapped data"""
        self.overlapped_data = []
        self.overlap_mode = False
        self.overlap_btn.setChecked(False)
        self.overlap_btn.setText("📊 Overlap (O)")
        
        # Restore normal status label
        if self.file_list and self.current_index >= 0:
            filename = os.path.basename(self.file_list[self.current_index])
            self.current_file_label.setText(f"[{self.current_index + 1}/{len(self.file_list)}] {filename}")
            
        self.plot_data()
        
    def add_to_overlay(self):
        """Add current file to overlay"""
        if self.current_data is not None and self.overlap_mode:
            filename = os.path.basename(self.file_list[self.current_index])
            
            # Check if already in overlay
            existing_names = [name for name, _, _, _, _ in self.overlapped_data]
            if filename in existing_names:
                return
                
            x, y = self.current_data[:, 0], self.current_data[:, 1]
            self.overlapped_data.append((
                filename,
                x.copy(),
                y.copy(),
                self.peaks.copy(),
                self.bg_points.copy()
            ))
            self.overlap_btn.setText(f"📊 Overlap ({len(self.overlapped_data)})")
            self.plot_data()
            
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
