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
                              QFrame, QComboBox, QLineEdit, QSizePolicy)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont, QPainter, QPen, QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
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


class BatchFittingDialog(QWidget):
    """Interactive batch fitting widget (can be used as dialog or embedded widget)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Don't set window title when used as embedded widget
        # self.setWindowTitle("Batch Peak Fitting (Interactive)")
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
        
        # Peak grouping and fitting parameters (matching auto_fitting_module.py)
        self.overlap_threshold = 1.5  # Overlap FWHM multiplier for grouping peaks (default mode)
        self.overlap_threshold_normal = 1.5  # Normal mode threshold
        self.overlap_threshold_overlap = 5.0  # Overlap mode threshold (like auto_fitting_module)
        self.fitting_window_multiplier = 3.0  # Fit window multiplier for peak fitting
        self.overlap_mode = False  # Overlap mode switch (like auto_fitting_module.py)
        
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
        else:
            super().keyPressEvent(event)
        
    def paintEvent(self, event):
        """Custom paint event to draw border with explicit right and bottom lines"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        border_width = 3
        
        # Draw main border with enough inset - using larger inset for visibility
        pen = QPen(QColor("#7E57C2"), border_width)
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        # Draw rounded rectangle with proper insets (inset more from right/bottom for visibility)
        inset = border_width + 2  # Inset by border width + extra padding
        painter.drawRoundedRect(
            rect.adjusted(inset, inset, -inset - 10, -inset - 10),  # Extra inset on right and bottom
            8, 8
        )
        
        # Draw EXPLICIT right border line (guaranteed visible) - further from edge
        pen_thick = QPen(QColor("#7E57C2"), 4)
        pen_thick.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_thick)
        
        # Right vertical line - further inset from edge for visibility
        right_x = rect.width() - 15  # 15px from right edge (was 6, now much more visible)
        painter.drawLine(right_x, 10, right_x, rect.height() - 15)
        
        # Bottom horizontal line - also further inset
        bottom_y = rect.height() - 15  # 15px from bottom edge (was 6)
        painter.drawLine(rect.width() - 120, bottom_y, right_x, bottom_y)
        
        painter.end()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Set background with padding for border
        self.setStyleSheet("""
            BatchFittingDialog {
                background-color: #E8E8E8;
                min-width: 1400px;
                min-height: 800px;
            }
        """)
        
        # Main layout with margins for manual border
        # Extra margins on right and bottom for border visibility
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 25, 20)  # Right:25px Bottom:20px for border visibility
        main_layout.setSpacing(0)
        
        # Create content container
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #FAFAFA;
                border-radius: 5px;
            }
        """)
        
        # Force container to not expand beyond available space
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        main_layout.addWidget(container)
        
        # Inner layout for actual content
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 20, 8)  # Increased right margin for border visibility
        layout.setSpacing(5)
        
        # Title and controls (no border)
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #F3E5F5;
                border: none;
                border-radius: 5px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 5, 30, 5)  # Increased right margin for border visibility
        
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
        """Create left panel with file list (no border)"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.NoFrame)
        panel.setStyleSheet("background-color: #F5F5F5; border: none; border-radius: 5px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Title (smaller, no emphasis)
        title = QLabel("File List")
        title.setFont(QFont('Arial', 9))
        title.setStyleSheet("color: #666666; border: none;")
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
        
        # Progress label (no border)
        self.progress_label = QLabel("No files loaded")
        self.progress_label.setFont(QFont('Arial', 8))
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #666666;
                border: none;
                background: transparent;
                padding: 2px;
            }
        """)
        layout.addWidget(self.progress_label)
        
        return panel
        
    def create_right_panel(self):
        """Create right panel with plot and controls"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 25, 5)  # Increased right margin for border visibility
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
        bar.setStyleSheet("""
            QWidget {
                background-color: #E3F2FF;
                border: 2px solid #90CAF9;
                border-radius: 6px;
            }
        """)
        main_layout = QVBoxLayout(bar)
        main_layout.setContentsMargins(10, 5, 30, 5)  # Increased right margin for border visibility
        main_layout.setSpacing(5)
        
        # First row: mode and method
        row1 = QHBoxLayout()
        
        # Add mode selector
        mode_label = QLabel("Mode:")
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
        
        row1.addSpacing(20)
        
        # Overlap FWHM parameter
        overlap_label = QLabel("Overlap FWHM×:")
        overlap_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        overlap_label.setToolTip("Peaks within this multiplier of FWHM will be grouped together")
        row1.addWidget(overlap_label)
        
        self.overlap_entry = QLineEdit(str(self.overlap_threshold))
        self.overlap_entry.setFixedWidth(50)
        self.overlap_entry.setFont(QFont('Arial', 9))
        self.overlap_entry.setStyleSheet("padding: 3px;")
        self.overlap_entry.textChanged.connect(self.on_overlap_changed)
        row1.addWidget(self.overlap_entry)
        
        row1.addSpacing(20)
        
        # Fit window parameter
        fit_window_label = QLabel("Fit Window×:")
        fit_window_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        fit_window_label.setToolTip("Fitting window size as multiplier of peak FWHM")
        row1.addWidget(fit_window_label)
        
        self.fit_window_entry = QLineEdit(str(self.fitting_window_multiplier))
        self.fit_window_entry.setFixedWidth(50)
        self.fit_window_entry.setFont(QFont('Arial', 9))
        self.fit_window_entry.setStyleSheet("padding: 3px;")
        self.fit_window_entry.textChanged.connect(self.on_fit_window_changed)
        row1.addWidget(self.fit_window_entry)
        
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
        
        # Auto fit (Enter key)
        auto_fit_btn = QPushButton("⚡ Auto Fit (Enter)")
        auto_fit_btn.setFixedWidth(140)
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
        
        # Overlap mode button (like auto_fitting_module.py)
        self.overlap_btn = QPushButton("Overlap Mode")
        self.overlap_btn.setFixedWidth(120)
        self.overlap_btn.setFont(QFont('Arial', 9))
        self.overlap_btn.setCheckable(True)
        self.overlap_btn.setStyleSheet("""
            QPushButton {
                background-color: #E9D9E9;
                border: 2px solid #BA68C8;
                border-radius: 4px;
                padding: 5px;
                color: black;
            }
            QPushButton:checked {
                background-color: #B8F5B8;
                color: black;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #CE93D8; }
        """)
        self.overlap_btn.setToolTip("Enable overlap mode: use larger threshold for peak grouping")
        self.overlap_btn.clicked.connect(self.toggle_overlap_mode)
        row2.addWidget(self.overlap_btn)
        
        row2.addStretch()
        
        # Instructions
        info_label = QLabel("💡 Left: Add | Right: Delete | Scroll: Zoom | Enter: Auto-fit")
        info_label.setFont(QFont('Arial', 8))
        info_label.setStyleSheet("color: #666666;")
        row2.addWidget(info_label)
        
        # Add spacing to prevent components from extending to right edge
        row2.addSpacing(5)
        
        main_layout.addLayout(row2)
        
        return bar
        
    def create_navigation_bar(self):
        """Create navigation bar with prev/next/save buttons"""
        bar = QWidget()
        bar.setFixedHeight(55)
        bar.setStyleSheet("""
            QWidget {
                background-color: #FFF9C4;
                border: 2px solid #FFD54F;
                border-radius: 6px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 30, 5)  # Increased right margin for border visibility
        
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
        
        # Add spacing after save button to prevent it from extending to right edge
        layout.addSpacing(5)
        
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
            self.current_fit_curves = []  # Clear fit curves for new file
            
            # Reset zoom limits for new file
            self.xlim_original = None
            self.ylim_original = None
            
            # Update display
            filename = os.path.basename(filepath)
            self.current_file_label.setText(f"[{self.current_index + 1}/{len(self.file_list)}] {filename}")
            
            # Auto detect peaks (this will call plot_data with preserve_zoom=False implicitly)
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
        
        # Don't preserve zoom when auto-detecting peaks on new file
        self.plot_data(preserve_zoom=False)
        
    def clear_peaks(self):
        """Clear all peaks"""
        self.peaks = []
        self.plot_data(preserve_zoom=True)
        
    def clear_background(self):
        """Clear all background points"""
        self.bg_points = []
        self.plot_data(preserve_zoom=True)
        
    def clear_all(self):
        """Clear all peaks, background points, and fitted curves"""
        self.peaks = []
        self.bg_points = []
        self.current_fit_curves = []
        
        # Also clear fit results for current file
        if self.file_list and self.current_index >= 0 and self.current_index < len(self.file_list):
            current_filename = os.path.basename(self.file_list[self.current_index])
            # Remove results for current file
            self.results = [r for r in self.results if r['file'] != current_filename]
        
        self.plot_data(preserve_zoom=True)
        
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
            
        # Preserve zoom when adding/removing peaks
        self.plot_data(preserve_zoom=True)
        
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
        
    def plot_data(self, preserve_zoom=True):
        """Plot current data with peaks and background"""
        if self.current_data is None:
            return
        
        # Save current zoom state before clearing
        current_xlim = None
        current_ylim = None
        if preserve_zoom:
            try:
                current_xlim = self.canvas.axes.get_xlim()
                current_ylim = self.canvas.axes.get_ylim()
            except:
                pass
            
        self.canvas.axes.clear()
        x, y = self.current_data[:, 0], self.current_data[:, 1]
        
        # Store original limits for reset
        if self.xlim_original is None:
            self.xlim_original = (x.min(), x.max())
            y_range = y.max() - y.min()
            self.ylim_original = (y.min() - y_range * 0.05, y.max() + y_range * 0.1)
        
        # Plot current data
        self.canvas.axes.plot(x, y, 'k-', linewidth=1.5, label='Data', zorder=2)
        
        # Plot fitted curves for current file (matching auto_fitting_module.py style)
        current_filename = os.path.basename(self.file_list[self.current_index]) if self.file_list and self.current_index >= 0 else None
        
        if current_filename:
            # Find fit results from results list
            for result in self.results:
                if result['file'] == current_filename and 'fit_curves' in result:
                    fit_curves = result['fit_curves']
                    
                    # Plot background line if available (darker blue for visibility)
                    if self.bg_points and len(self.bg_points) >= 2:
                        bg_x = [p[0] for p in self.bg_points]
                        bg_y = [p[1] for p in self.bg_points]
                        self.canvas.axes.plot(bg_x, bg_y, 's', color='#1E3A8A',
                                            markersize=4, alpha=0.9, label='BG Points', zorder=3)
                        # Interpolate background line (darker blue, more opaque)
                        bg_line_y = np.interp(x, bg_x, bg_y)
                        self.canvas.axes.plot(x, bg_line_y, '-', color='#1E3A8A',
                                            linewidth=2.0, alpha=0.6, label='Background', zorder=3)
                    
                    # Plot individual peak components (dashed lines, different colors)
                    colors = plt.cm.tab10(np.linspace(0, 1, len(fit_curves)))
                    
                    for idx, (fit_x, fit_y) in enumerate(fit_curves):
                        label = f'Peak {idx+1}' if idx < 3 else None  # Only label first 3
                        self.canvas.axes.plot(fit_x, fit_y, '--', linewidth=1.5, 
                                            color=colors[idx], alpha=0.7, 
                                            label=label, zorder=4)
                    
                    # Calculate and plot total fit (red solid line)
                    if len(fit_curves) > 0:
                        # Find common x range
                        x_min = min(fit_x.min() for fit_x, _ in fit_curves)
                        x_max = max(fit_x.max() for fit_x, _ in fit_curves)
                        x_total = np.linspace(x_min, x_max, 500)
                        
                        # Add background
                        if self.bg_points and len(self.bg_points) >= 2:
                            bg_x = [p[0] for p in self.bg_points]
                            bg_y = [p[1] for p in self.bg_points]
                            y_total = np.interp(x_total, bg_x, bg_y)
                        else:
                            y_total = np.zeros_like(x_total)
                        
                        # Sum all peak components (without background, as they already include it)
                        for fit_x, fit_y in fit_curves:
                            # Subtract background first, then add to total
                            if self.bg_points and len(self.bg_points) >= 2:
                                bg_x = [p[0] for p in self.bg_points]
                                bg_y = [p[1] for p in self.bg_points]
                                bg_interp = np.interp(fit_x, bg_x, bg_y)
                                peak_only = fit_y - bg_interp
                            else:
                                peak_only = fit_y
                            # Interpolate to common x grid and add
                            peak_interp = np.interp(x_total, fit_x, peak_only, left=0, right=0)
                            y_total += peak_interp
                        
                        # Plot total fit
                        self.canvas.axes.plot(x_total, y_total, '-', linewidth=2.0, 
                                            color='#FF0000', alpha=0.6, 
                                            label='Total Fit', zorder=5)
                    
                    break
        
        # Plot peaks as vertical lines
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
        
        # Update legend based on number of fit curves
        num_fit_curves = len(fit_curves_to_plot) if 'fit_curves_to_plot' in locals() else 0
        self.canvas.axes.legend(loc='upper right', fontsize=8, framealpha=0.85, 
                               ncol=2 if num_fit_curves > 3 else 1)
        self.canvas.axes.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
        self.canvas.axes.set_facecolor('#FAFAFA')
        
        # Restore zoom state if it was saved and preserve_zoom is True
        if preserve_zoom and current_xlim is not None and current_ylim is not None:
            # Check if the saved limits are valid and reasonable
            try:
                if (current_xlim[0] < current_xlim[1] and 
                    current_ylim[0] < current_ylim[1] and
                    current_xlim[0] < x.max() and current_xlim[1] > x.min()):
                    self.canvas.axes.set_xlim(current_xlim)
                    self.canvas.axes.set_ylim(current_ylim)
            except:
                pass  # If restoration fails, use default view
        
        self.canvas.draw()
        
    def _estimate_peak_fwhm(self, x, y, peak_idx):
        """Estimate FWHM for a peak using half-maximum method"""
        try:
            results_half = peak_widths(y, [peak_idx], rel_height=0.5)
            width_pts = results_half[0][0] if len(results_half[0]) > 0 else 40
            # Convert from points to x-axis units
            if width_pts > 0 and peak_idx > 0 and peak_idx < len(x) - 1:
                dx = np.mean(np.diff(x))
                fwhm = width_pts * dx
            else:
                fwhm = 0.5  # Default fallback
            return fwhm
        except:
            return 0.5  # Default fallback
    
    def _group_overlapping_peaks(self, peak_positions, x, y):
        """
        Group overlapping peaks based on their positions and FWHM.
        Uses configurable overlap_threshold for grouping decision.
        
        Parameters:
        -----------
        peak_positions : list
            List of peak center positions
        x : array
            X-axis data
        y : array
            Y-axis data
            
        Returns:
        --------
        groups : list of lists
            Each group contains tuples of (position, index) for peaks that should be fitted together
        """
        if len(peak_positions) == 0:
            return []
        
        # Estimate FWHM for each peak
        peak_indices = [np.argmin(np.abs(x - pos)) for pos in peak_positions]
        peak_fwhms = [self._estimate_peak_fwhm(x, y, idx) for idx in peak_indices]
        
        # Use configurable overlap threshold
        overlap_mult = self.overlap_threshold
        
        # Convert to sorted list with positions
        peak_data = [(pos, idx, fwhm) for pos, idx, fwhm in zip(peak_positions, peak_indices, peak_fwhms)]
        peak_data.sort(key=lambda x: x[0])  # Sort by position
        
        groups = []
        current_group = [(peak_data[0][0], peak_data[0][1])]  # (position, index)
        current_end = peak_data[0][0] + overlap_mult * peak_data[0][2]  # Position + overlap_mult*FWHM
        
        for i in range(1, len(peak_data)):
            pos, idx, fwhm = peak_data[i]
            peak_start = pos - overlap_mult * fwhm
            
            # Check if this peak overlaps with current group
            if peak_start <= current_end:
                # Overlapping - add to current group
                current_group.append((pos, idx))
                # Extend the end boundary
                current_end = max(current_end, pos + overlap_mult * fwhm)
            else:
                # Not overlapping - start new group
                groups.append(current_group)
                current_group = [(pos, idx)]
                current_end = pos + overlap_mult * fwhm
        
        # Add last group
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _fit_single_peak(self, x, y, peak_idx, peak_pos):
        """
        Fit a single peak independently using improved background subtraction.
        Uses configurable fitting_window_multiplier and overlap_mode adjustments.
        Matches auto_fitting_module.py behavior.
        
        Parameters:
        -----------
        x : array
            X-axis data
        y : array
            Y-axis data
        peak_idx : int
            Index of peak in data array
        peak_pos : float
            Position of peak center
            
        Returns:
        --------
        result : dict or None
            Dictionary containing fit results or None if fitting failed
        """
        try:
            # Get peak width for window estimation
            results_half = peak_widths(y, [peak_idx], rel_height=0.5)
            width_pts = results_half[0][0] if len(results_half[0]) > 0 else 40
            
            # Calculate FWHM estimate
            dx = np.mean(np.diff(x)) if len(x) > 1 else 1.0
            fwhm_est = width_pts * dx
            
            # Use configurable fit window multiplier
            # If overlap mode is on, use larger window (like auto_fitting_module)
            fit_window_mult = self.fitting_window_multiplier
            if self.overlap_mode:
                fit_window_mult += 1.0  # Increase window for overlap mode
            
            window = int(width_pts * fit_window_mult)
            window = max(20, min(window, 200))
            
            # Extract local region
            left = max(0, peak_idx - window)
            right = min(len(x), peak_idx + window)
            x_local = x[left:right]
            y_local = y[left:right]
            
            if len(x_local) < 5:
                return None
            
            # Improved background subtraction using lowest points at edges
            if len(self.bg_points) >= 2:
                bg_x = np.array([p[0] for p in self.bg_points])
                bg_y = np.array([p[1] for p in self.bg_points])
                background = np.interp(x_local, bg_x, bg_y)
            else:
                # Use edge-based background estimation
                split_index = max(1, int(len(y_local) * 0.05))
                
                left_y = y_local[:split_index]
                left_x = x_local[:split_index]
                N_left = max(1, int(len(left_y) * 0.1))
                low_left_idx = np.argsort(left_y)[:N_left]
                bg_left_y = np.mean(left_y[low_left_idx])
                bg_left_x = np.mean(left_x[low_left_idx])
                
                right_y = y_local[-split_index:]
                right_x = x_local[-split_index:]
                N_right = max(1, int(len(right_y) * 0.1))
                low_right_idx = np.argsort(right_y)[:N_right]
                bg_right_y = np.mean(right_y[low_right_idx])
                bg_right_x = np.mean(right_x[low_right_idx])
                
                slope = (bg_right_y - bg_left_y) / (bg_right_x - bg_left_x + 1e-10)
                background = bg_left_y + slope * (x_local - bg_left_x)
            
            y_fit_input = y_local - background
            y_fit_input = np.maximum(y_fit_input, 0)  # Ensure non-negative
            
            # Initial guess (matching auto_fitting_module.py)
            peak_height = np.max(y_fit_input)
            center_guess = x_local[np.argmax(y_fit_input)]
            
            # FWHM-based sigma and gamma estimates
            sigma_guess = fwhm_est / 2.355
            gamma_guess = fwhm_est / 2
            amplitude_guess = peak_height * sigma_guess * np.sqrt(2 * np.pi)
            
            # Center tolerance (larger if overlap mode is on)
            center_tolerance = fwhm_est * 0.8 if self.overlap_mode else fwhm_est * 0.5
            
            # Bounds (matching auto_fitting_module.py)
            y_range = np.max(y_fit_input) - np.min(y_fit_input)
            amp_lower = 0
            amp_upper = y_range * sigma_guess * np.sqrt(2 * np.pi) * 10
            sig_lower = dx * 0.5
            sig_upper = fwhm_est * 3
            gam_lower = dx * 0.5
            gam_upper = fwhm_est * 3
            
            # Max iterations and tolerances (higher for overlap mode)
            max_iter = 30000 if self.overlap_mode else 10000
            ftol = 1e-9 if self.overlap_mode else 1e-8
            xtol = 1e-9 if self.overlap_mode else 1e-8
            
            # Fit peak
            if self.fit_method == "voigt":
                p0 = [amplitude_guess, center_guess, sigma_guess, gamma_guess]
                bounds = ([amp_lower, center_guess - center_tolerance, sig_lower, gam_lower],
                         [amp_upper, center_guess + center_tolerance, sig_upper, gam_upper])
                popt, _ = curve_fit(voigt, x_local, y_fit_input, p0=p0, bounds=bounds, 
                                   maxfev=max_iter, ftol=ftol, xtol=xtol)
                sigma = popt[2]
                gamma = popt[3]
                eta = None
            else:  # pseudo-voigt
                p0 = [amplitude_guess, center_guess, sigma_guess, gamma_guess, 0.5]
                bounds = ([amp_lower, center_guess - center_tolerance, sig_lower, gam_lower, 0],
                         [amp_upper, center_guess + center_tolerance, sig_upper, gam_upper, 1.0])
                popt, _ = curve_fit(pseudo_voigt, x_local, y_fit_input, p0=p0, bounds=bounds,
                                   maxfev=max_iter, ftol=ftol, xtol=xtol)
                sigma = popt[2]
                gamma = popt[3]
                eta = popt[4]
            
            # Generate fine x points for smooth curve
            x_fine = np.linspace(x_local.min(), x_local.max(), 500)
            
            # Calculate fitted curve
            if self.fit_method == "voigt":
                y_fit = voigt(x_local, *popt)
                y_fit_fine = voigt(x_fine, *popt)
            else:
                y_fit = pseudo_voigt(x_local, *popt)
                y_fit_fine = pseudo_voigt(x_fine, *popt)
            
            # Add background back for display
            if len(self.bg_points) >= 2:
                bg_x = np.array([p[0] for p in self.bg_points])
                bg_y = np.array([p[1] for p in self.bg_points])
                bg_fine = np.interp(x_fine, bg_x, bg_y)
            else:
                bg_fine = np.interp(x_fine, x_local, background)
            
            y_fit_display = y_fit_fine + bg_fine
            
            # Calculate metrics
            fwhm = 2 * np.sqrt(2 * np.log(2)) * sigma  # Gaussian approximation
            dx = x_fine[1] - x_fine[0]
            area = np.trapz(y_fit_fine, dx=dx)
            intensity = popt[0]
            
            # Calculate R-squared
            ss_res = np.sum((y_fit_input - y_fit)**2)
            ss_tot = np.sum((y_fit_input - np.mean(y_fit_input))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            return {
                'x_fine': x_fine,
                'y_fit_display': y_fit_display,
                'center': popt[1],
                'fwhm': fwhm,
                'area': area,
                'intensity': intensity,
                'r_squared': r_squared
            }
            
        except Exception as e:
            print(f"Failed to fit peak at position {peak_pos}: {e}")
            return None
    
    def _fit_multi_peaks_group(self, x, y, group):
        """
        Fit multiple overlapping peaks together.
        Uses configurable fitting_window_multiplier.
        
        Parameters:
        -----------
        x : array
            X-axis data
        y : array
            Y-axis data
        group : list of tuples
            List of (position, index) tuples for peaks in the group
            
        Returns:
        --------
        results : list of dicts or list of None
            List of fit results for each peak, or None values if fitting failed
        """
        try:
            peak_positions = [pos for pos, idx in group]
            peak_indices = [idx for pos, idx in group]
            
            # Define fitting region for entire group
            min_peak_idx = min(peak_indices)
            max_peak_idx = max(peak_indices)
            
            # Get average width for window estimation
            avg_width = 40
            try:
                results_half = peak_widths(y, peak_indices, rel_height=0.5)
                if len(results_half[0]) > 0:
                    avg_width = np.mean(results_half[0])
            except:
                pass
            
            # Use configurable fit window multiplier
            # If overlap mode is on, use larger window (like auto_fitting_module)
            fit_window_mult = self.fitting_window_multiplier
            if self.overlap_mode:
                fit_window_mult += 1.0
            
            window = int(avg_width * fit_window_mult * 0.8)  # Slightly smaller for multi-peak
            window = max(40, min(window, 250))
            
            # Calculate FWHM estimate for tolerance calculations
            dx = np.mean(np.diff(x)) if len(x) > 1 else 1.0
            avg_fwhm = avg_width * dx
            
            # Extract local region covering all peaks in group
            left = max(0, min_peak_idx - window)
            right = min(len(x), max_peak_idx + window)
            x_local = x[left:right]
            y_local = y[left:right]
            
            if len(x_local) < 10:
                return [None] * len(group)
            
            # Background subtraction
            if len(self.bg_points) >= 2:
                bg_x = np.array([p[0] for p in self.bg_points])
                bg_y = np.array([p[1] for p in self.bg_points])
                background = np.interp(x_local, bg_x, bg_y)
            else:
                split_index = max(1, int(len(y_local) * 0.05))
                
                left_y = y_local[:split_index]
                left_x = x_local[:split_index]
                N_left = max(1, int(len(left_y) * 0.1))
                low_left_idx = np.argsort(left_y)[:N_left]
                bg_left_y = np.mean(left_y[low_left_idx])
                bg_left_x = np.mean(left_x[low_left_idx])
                
                right_y = y_local[-split_index:]
                right_x = x_local[-split_index:]
                N_right = max(1, int(len(right_y) * 0.1))
                low_right_idx = np.argsort(right_y)[:N_right]
                bg_right_y = np.mean(right_y[low_right_idx])
                bg_right_x = np.mean(right_x[low_right_idx])
                
                slope = (bg_right_y - bg_left_y) / (bg_right_x - bg_left_x + 1e-10)
                background = bg_left_y + slope * (x_local - bg_left_x)
            
            y_fit_input = y_local - background
            y_fit_input = np.maximum(y_fit_input, 0)
            
            # Multi-peak fitting function
            def multi_peak_func(x_vals, *params):
                """Sum of multiple peaks"""
                n_peaks = len(group)
                result = np.zeros_like(x_vals)
                
                if self.fit_method == "voigt":
                    # 4 parameters per peak
                    for i in range(n_peaks):
                        amplitude = params[i*4]
                        center = params[i*4 + 1]
                        sigma = params[i*4 + 2]
                        gamma = params[i*4 + 3]
                        result += voigt(x_vals, amplitude, center, sigma, gamma)
                else:  # pseudo-voigt
                    # 5 parameters per peak
                    for i in range(n_peaks):
                        amplitude = params[i*5]
                        center = params[i*5 + 1]
                        sigma = params[i*5 + 2]
                        gamma = params[i*5 + 3]
                        eta = params[i*5 + 4]
                        result += pseudo_voigt(x_vals, amplitude, center, sigma, gamma, eta)
                
                return result
            
            # Initial guess for all peaks in group (matching auto_fitting_module.py)
            p0 = []
            bounds_lower = []
            bounds_upper = []
            
            y_range = np.max(y_fit_input) - np.min(y_fit_input)
            
            for pos, peak_idx in group:
                # Find local peak position in extracted region
                local_peak_idx = peak_idx - left
                if local_peak_idx < 0 or local_peak_idx >= len(y_fit_input):
                    local_peak_idx = np.argmax(y_fit_input)
                
                # Estimate FWHM for this peak
                fwhm_est = avg_fwhm
                try:
                    widths = peak_widths(y, [peak_idx], rel_height=0.5)
                    if len(widths[0]) > 0:
                        fwhm_est = widths[0][0] * dx
                except:
                    pass
                
                # Initial guesses (matching auto_fitting_module.py)
                peak_height = y_fit_input[local_peak_idx] if (0 <= local_peak_idx < len(y_fit_input)) else np.max(y_fit_input)
                if peak_height <= 0:
                    peak_height = np.max(y_fit_input) * 0.5
                
                center_guess = x_local[local_peak_idx]
                sigma_guess = fwhm_est / 2.355
                gamma_guess = fwhm_est / 2
                amplitude_guess = peak_height * sigma_guess * np.sqrt(2 * np.pi)
                
                # Center tolerance (larger if overlap mode is on)
                center_tolerance = fwhm_est * 0.8 if self.overlap_mode else fwhm_est * 0.5
                
                # Bounds
                amp_lower = 0
                amp_upper = y_range * sigma_guess * np.sqrt(2 * np.pi) * 10
                sig_lower = dx * 0.5
                sig_upper = fwhm_est * 3
                gam_lower = dx * 0.5
                gam_upper = fwhm_est * 3
                
                if self.fit_method == "voigt":
                    p0.extend([amplitude_guess, center_guess, sigma_guess, gamma_guess])
                    bounds_lower.extend([amp_lower, center_guess - center_tolerance, sig_lower, gam_lower])
                    bounds_upper.extend([amp_upper, center_guess + center_tolerance, sig_upper, gam_upper])
                else:  # pseudo-voigt
                    p0.extend([amplitude_guess, center_guess, sigma_guess, gamma_guess, 0.5])
                    bounds_lower.extend([amp_lower, center_guess - center_tolerance, sig_lower, gam_lower, 0])
                    bounds_upper.extend([amp_upper, center_guess + center_tolerance, sig_upper, gam_upper, 1.0])
            
            # Max iterations and tolerances (higher for multi-peak or overlap mode)
            max_iter = 30000 if self.overlap_mode else 20000
            ftol = 1e-9 if self.overlap_mode else 1e-8
            xtol = 1e-9 if self.overlap_mode else 1e-8
            
            # Fit all peaks together
            popt, _ = curve_fit(multi_peak_func, x_local, y_fit_input, 
                               p0=p0, bounds=(bounds_lower, bounds_upper), 
                               maxfev=max_iter, ftol=ftol, xtol=xtol)
            
            # Calculate fitted curve
            y_fit = multi_peak_func(x_local, *popt)
            
            # Generate results for each peak
            results = []
            n_peaks = len(group)
            
            for i in range(n_peaks):
                if self.fit_method == "voigt":
                    amplitude = popt[i*4]
                    center = popt[i*4 + 1]
                    sigma = popt[i*4 + 2]
                    gamma = popt[i*4 + 3]
                    eta = None
                else:  # pseudo-voigt
                    amplitude = popt[i*5]
                    center = popt[i*5 + 1]
                    sigma = popt[i*5 + 2]
                    gamma = popt[i*5 + 3]
                    eta = popt[i*5 + 4]
                
                # Generate fine x points for this peak
                x_fine = np.linspace(x_local.min(), x_local.max(), 500)
                
                # Calculate individual peak contribution
                if self.fit_method == "voigt":
                    y_peak_fine = voigt(x_fine, amplitude, center, sigma, gamma)
                else:
                    y_peak_fine = pseudo_voigt(x_fine, amplitude, center, sigma, gamma, eta)
                
                # Add background back for display
                if len(self.bg_points) >= 2:
                    bg_x = np.array([p[0] for p in self.bg_points])
                    bg_y = np.array([p[1] for p in self.bg_points])
                    bg_fine = np.interp(x_fine, bg_x, bg_y)
                else:
                    bg_fine = np.interp(x_fine, x_local, background)
                
                y_fit_display = y_peak_fine + bg_fine
                
                # Calculate metrics
                fwhm = 2 * np.sqrt(2 * np.log(2)) * sigma
                dx = x_fine[1] - x_fine[0]
                area = np.trapz(y_peak_fine, dx=dx)
                intensity = amplitude
                
                # Calculate R-squared for the entire multi-peak fit (same for all peaks in group)
                ss_res = np.sum((y_fit_input - y_fit)**2)
                ss_tot = np.sum((y_fit_input - np.mean(y_fit_input))**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                results.append({
                    'x_fine': x_fine,
                    'y_fit_display': y_fit_display,
                    'center': center,
                    'fwhm': fwhm,
                    'area': area,
                    'intensity': intensity,
                    'r_squared': r_squared
                })
            
            return results
            
        except Exception as e:
            print(f"Failed to fit multi-peak group: {e}")
            return [None] * len(group)
    
    def fit_current(self):
        """Fit current file with selected peaks using improved curve fitting from curvefit module"""
        if self.current_data is None or not self.peaks:
            QMessageBox.warning(self, "No Data", "Please load a file and add peaks first.")
            return
            
        filename = os.path.basename(self.file_list[self.current_index])
        
        try:
            # Perform actual fitting
            x, y = self.current_data[:, 0], self.current_data[:, 1]
            
            # Clear previous fit curves
            self.current_fit_curves = []
            
            # Group overlapping peaks
            peak_groups = self._group_overlapping_peaks(self.peaks, x, y)
            
            # Fit each group (single peak or multi-peak)
            peak_results = []
            fit_quality = []
            fit_curves = []
            
            for group in peak_groups:
                if len(group) == 1:
                    # Single peak - fit independently
                    pos, idx = group[0]
                    result = self._fit_single_peak(x, y, idx, pos)
                    
                    if result is not None:
                        fit_curves.append((result['x_fine'].copy(), result['y_fit_display'].copy()))
                        peak_results.append({
                            'center': result['center'],
                            'fwhm': result['fwhm'],
                            'area': result['area'],
                            'intensity': result['intensity'],
                            'r_squared': result['r_squared']
                        })
                        fit_quality.append(result['r_squared'])
                    else:
                        peak_results.append({
                            'center': pos,
                            'fwhm': 0,
                            'area': 0,
                            'intensity': 0,
                            'r_squared': 0
                        })
                        fit_quality.append(0)
                else:
                    # Multiple overlapping peaks - fit together
                    results = self._fit_multi_peaks_group(x, y, group)
                    
                    for i, result in enumerate(results):
                        if result is not None:
                            fit_curves.append((result['x_fine'].copy(), result['y_fit_display'].copy()))
                            peak_results.append({
                                'center': result['center'],
                                'fwhm': result['fwhm'],
                                'area': result['area'],
                                'intensity': result['intensity'],
                                'r_squared': result['r_squared']
                            })
                            fit_quality.append(result['r_squared'])
                        else:
                            pos, idx = group[i]
                            peak_results.append({
                                'center': pos,
                                'fwhm': 0,
                                'area': 0,
                                'intensity': 0,
                                'r_squared': 0
                            })
                            fit_quality.append(0)
            
            # Store fit curves
            self.current_fit_curves = fit_curves
            
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
                'fit_method': self.fit_method,
                'fit_curves': fit_curves  # Store fit curves for this file
            }
            self.results.append(result)
            
            # Redraw plot with fit curves
            self.plot_data()
            
            # Show result only if not in auto-fitting mode
            if not self.auto_fitting:
                multi_groups = len([g for g in peak_groups if len(g) > 1])
                status_msg = f"✓ Fitted {len(self.peaks)} peaks for {filename}\n\n"
                if multi_groups > 0:
                    status_msg += f"({multi_groups} multi-peak groups)\n"
                status_msg += f"Average R² = {avg_r_squared:.3f}"
                
                if avg_r_squared < self.fit_tolerance:
                    QMessageBox.warning(
                        self, 
                        "Poor Fit Quality", 
                        status_msg + f"\n\n⚠️ R² < {self.fit_tolerance:.2f}\n"
                        f"Consider adjusting peaks or background points."
                    )
                else:
                    QMessageBox.information(
                        self, 
                        "Fit Successful", 
                        status_msg
                    )
            
            return avg_r_squared
            
        except Exception as e:
            if not self.auto_fitting:
                QMessageBox.warning(self, "Fit Error", f"Fitting failed:\n{str(e)}\n{traceback.format_exc()}")
            return 0
            
    def start_auto_fitting(self):
        """Start automatic fitting for all remaining files"""
        if not self.file_list:
            QMessageBox.warning(self, "No Files", "Please load a folder first.")
            return
            
        if not self.peaks:
            QMessageBox.warning(self, "No Peaks", "Please add peaks to the current file first.")
            return
        
        # Start auto-fitting from current file onwards
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
    
    def on_overlap_changed(self):
        """Handle overlap FWHM multiplier change"""
        try:
            value = float(self.overlap_entry.text())
            if value > 0:
                self.overlap_threshold = value
        except ValueError:
            pass
    
    def on_fit_window_changed(self):
        """Handle fit window multiplier change"""
        try:
            value = float(self.fit_window_entry.text())
            if value > 0:
                self.fitting_window_multiplier = value
        except ValueError:
            pass
            
    def toggle_overlap_mode(self):
        """
        Toggle overlap mode (matching auto_fitting_module.py behavior).
        When enabled, uses larger threshold for peak grouping and adjusted fitting parameters.
        """
        self.overlap_mode = self.overlap_btn.isChecked()
        
        if self.overlap_mode:
            # Enable overlap mode - use larger threshold for peak grouping
            self.overlap_btn.setText("Overlap ON")
            # Use larger threshold value from the entry field, or default to 5.0
            try:
                self.overlap_threshold = float(self.overlap_entry.text())
                if self.overlap_threshold < self.overlap_threshold_normal:
                    self.overlap_threshold = self.overlap_threshold_overlap  # Use default overlap value
            except:
                self.overlap_threshold = self.overlap_threshold_overlap
            
            # Update the entry field to show current threshold
            self.overlap_entry.setText(str(self.overlap_threshold))
            
            # Show info message
            QMessageBox.information(
                self, 
                "Overlap Mode ON", 
                f"Overlap mode enabled.\n\n"
                f"Peaks within {self.overlap_threshold}×FWHM will be grouped together.\n"
                f"This allows better fitting of closely overlapping peaks."
            )
        else:
            # Disable overlap mode - revert to normal threshold
            self.overlap_btn.setText("Overlap Mode")
            self.overlap_threshold = self.overlap_threshold_normal
            self.overlap_entry.setText(str(self.overlap_threshold))
        
            
    def save_all_results(self):
        """Save all results to CSV"""
        if not self.results:
            QMessageBox.warning(self, "No Results", "No fitting results to save.")
            return
            
        if not self.output_folder:
            QMessageBox.warning(self, "No Output", "Please load a folder first.")
            return
            
        # Prepare data for CSV output
        # Format: each peak in each file gets its own row, blank rows between files
        rows = []
        
        for file_idx, result in enumerate(self.results):
            filename = result['file']
            # Remove .xy extension
            filename_clean = filename.replace('.xy', '').replace('.dat', '')
            
            peak_results = result.get('peak_results', [])
            
            for peak_idx, peak_data in enumerate(peak_results, 1):
                rows.append({
                    'File': filename_clean,
                    'Peak': f'Peak {peak_idx}',
                    'Center': peak_data.get('center', 0),
                    'FWHM': peak_data.get('fwhm', 0),
                    'Area': peak_data.get('area', 0),
                    'Intensity': peak_data.get('intensity', 0),
                    'R_squared': peak_data.get('r_squared', 0)
                })
            
            # Add blank row between different files (except after last file)
            if file_idx < len(self.results) - 1:
                rows.append({
                    'File': '',
                    'Peak': '',
                    'Center': '',
                    'FWHM': '',
                    'Area': '',
                    'Intensity': '',
                    'R_squared': ''
                })
        
        if not rows:
            QMessageBox.warning(self, "No Data", "No peak fitting data to save.")
            return
            
        # Create dataframe
        df = pd.DataFrame(rows)
        
        # Save to CSV
        output_file = os.path.join(self.output_folder, "batch_fitting_results.csv")
        df.to_csv(output_file, index=False, float_format='%.6f')
        
        # Count total files and peaks
        total_files = len(self.results)
        total_peaks = sum(len(r.get('peak_results', [])) for r in self.results)
        
        QMessageBox.information(
            self,
            "Saved",
            f"Results saved to:\n{output_file}\n\n"
            f"Processed {total_files} files\n"
            f"Total peaks fitted: {total_peaks}"
        )


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow
    app = QApplication(sys.argv)
    
    # Create a main window to hold the batch widget
    main_window = QMainWindow()
    main_window.setWindowTitle("Batch Peak Fitting")
    main_window.setMinimumWidth(1600)
    main_window.setMinimumHeight(900)
    
    # Create batch widget
    batch_widget = BatchFittingDialog()
    main_window.setCentralWidget(batch_widget)
    
    main_window.show()
    sys.exit(app.exec())