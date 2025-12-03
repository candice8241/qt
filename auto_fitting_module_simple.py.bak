# -*- coding: utf-8 -*-
"""
Auto Fitting Module - Embedded Qt6 Version
Interactive Peak Fitting with embedded matplotlib canvas
"""

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, 
                              QPushButton, QMessageBox, QFileDialog, QTextEdit, 
                              QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox, 
                              QScrollArea, QRadioButton, QButtonGroup, QDialog, 
                              QLineEdit, QGridLayout, QSizePolicy, QApplication,
                              QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from scipy.optimize import curve_fit
from scipy.special import wofz
from scipy.signal import savgol_filter, find_peaks
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import UnivariateSpline
from sklearn.cluster import DBSCAN
import os
import pandas as pd
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')


# ==================== Import Data Processing Classes ====================
# Import the helper classes from auto_fitting.py
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from auto_fitting import (DataProcessor, PeakClusterer, BackgroundFitter, 
                              PeakProfile, PeakDetector)
except ImportError:
    # If import fails, define minimal versions
    class DataProcessor:
        @staticmethod
        def gaussian_smoothing(y, sigma=2):
            return gaussian_filter1d(y, sigma=sigma)
    
    class PeakDetector:
        @staticmethod
        def auto_find_peaks(x, y):
            if len(y) > 15:
                window_length = min(15, len(y) // 2 * 2 + 1)
                y_smooth = savgol_filter(y, window_length, 3)
            else:
                y_smooth = y
            y_range = np.max(y) - np.min(y)
            height_threshold = np.min(y) + y_range * 0.05
            prominence_threshold = y_range * 0.02
            peaks, _ = find_peaks(y_smooth, height=height_threshold, 
                                 prominence=prominence_threshold, distance=5)
            return peaks
    
    class PeakProfile:
        @staticmethod
        def pseudo_voigt(x, amplitude, center, sigma, gamma, eta):
            gaussian = amplitude * np.exp(-(x - center)**2 / (2 * sigma**2)) / (sigma * np.sqrt(2 * np.pi))
            lorentzian = amplitude * gamma**2 / ((x - center)**2 + gamma**2) / (np.pi * gamma)
            return eta * lorentzian + (1 - eta) * gaussian
        
        @staticmethod
        def calculate_fwhm(sigma, gamma, eta):
            fwhm_g = 2.355 * sigma
            fwhm_l = 2 * gamma
            return eta * fwhm_l + (1 - eta) * fwhm_g
    
    class BackgroundFitter:
        @staticmethod
        def fit_global_background(x, y, peak_indices, method='spline'):
            if len(peak_indices) == 0:
                return np.full_like(y, np.median(y)), []
            sorted_peaks = sorted(peak_indices)
            bg_x, bg_y = [x[0]], [y[0]]
            for i in range(len(sorted_peaks) - 1):
                idx1, idx2 = sorted_peaks[i], sorted_peaks[i + 1]
                if idx2 > idx1 + 1:
                    min_idx = idx1 + np.argmin(y[idx1:idx2+1])
                    bg_x.append(x[min_idx])
                    bg_y.append(y[min_idx])
            bg_x.append(x[-1])
            bg_y.append(y[-1])
            background = np.interp(x, bg_x, bg_y)
            return background, list(zip(bg_x, bg_y))
    
    class PeakClusterer:
        @staticmethod
        def cluster_peaks(peak_positions, eps=None, min_samples=1):
            if len(peak_positions) == 0:
                return np.array([]), 0
            if len(peak_positions) == 1:
                return np.array([0]), 1
            X = np.array(peak_positions).reshape(-1, 1)
            if eps is None:
                sorted_pos = np.sort(peak_positions)
                distances = np.diff(sorted_pos) if len(sorted_pos) > 1 else [1.0]
                eps = np.median(distances) * 1.5 if len(distances) > 0 else 1.0
            clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
            labels = clustering.labels_
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            return labels, n_clusters


# ==================== Main Embedded Module ====================
class AutoFittingModule(QWidget):
    """
    Embedded Qt6 version of Auto Fitting module
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage
        self.x = None
        self.y = None
        self.y_original = None
        self.filename = None
        self.filepath = None
        self.selected_peaks = []
        self.peak_markers = []
        self.peak_texts = []
        self.fitted = False
        self.fit_results = None
        self.fit_lines = []
        
        # File navigation
        self.file_list = []
        self.current_file_index = -1
        
        # Background fitting
        self.bg_points = []
        self.bg_markers = []
        self.bg_line = None
        self.selecting_bg = False
        
        # Settings
        self.fit_method = "pseudo_voigt"
        self.overlap_mode = False
        self.overlap_threshold = 5.0
        self.fitting_window_multiplier = 3.0
        
        # Undo stack
        self.undo_stack = []
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the embedded UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Top control panel
        self.create_control_panel(main_layout)
        
        # Main plot area with matplotlib
        self.create_plot_area(main_layout)
        
        # Results table
        self.create_results_panel(main_layout)
        
        # Info panel
        self.create_info_panel(main_layout)
    
    def create_control_panel(self, parent_layout):
        """Create control buttons panel"""
        control_frame = QFrame()
        control_frame.setStyleSheet("QFrame { background-color: #E6D5F5; border-radius: 5px; }")
        control_frame.setMaximumHeight(120)
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.setSpacing(5)
        
        # First row of buttons
        row1 = QHBoxLayout()
        
        btn_style = """
            QPushButton {
                background-color: #B19CD9;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #9370DB;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """
        
        self.btn_load = QPushButton("Load File")
        self.btn_load.setStyleSheet(btn_style)
        self.btn_load.clicked.connect(self.load_file)
        row1.addWidget(self.btn_load)
        
        # File navigation buttons
        nav_btn_style = btn_style.replace('min-width: 100px', 'min-width: 40px')
        
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setStyleSheet(nav_btn_style)
        self.btn_prev.clicked.connect(self.prev_file)
        self.btn_prev.setEnabled(False)
        row1.addWidget(self.btn_prev)
        
        self.btn_next = QPushButton("▶")
        self.btn_next.setStyleSheet(nav_btn_style)
        self.btn_next.clicked.connect(self.next_file)
        self.btn_next.setEnabled(False)
        row1.addWidget(self.btn_next)
        
        self.btn_auto_find = QPushButton("Auto Find")
        self.btn_auto_find.setStyleSheet(btn_style)
        self.btn_auto_find.clicked.connect(self.auto_find_peaks)
        self.btn_auto_find.setEnabled(False)
        row1.addWidget(self.btn_auto_find)
        
        self.btn_fit = QPushButton("Fit Peaks")
        self.btn_fit.setStyleSheet(btn_style.replace('#B19CD9', '#CE93D8'))
        self.btn_fit.clicked.connect(self.fit_peaks)
        self.btn_fit.setEnabled(False)
        row1.addWidget(self.btn_fit)
        
        self.btn_clear_fit = QPushButton("Clear Fit")
        self.btn_clear_fit.setStyleSheet(btn_style.replace('#B19CD9', '#FFA07A'))
        self.btn_clear_fit.clicked.connect(self.clear_fit)
        self.btn_clear_fit.setEnabled(False)
        row1.addWidget(self.btn_clear_fit)
        
        self.btn_undo = QPushButton("Undo")
        self.btn_undo.setStyleSheet(btn_style.replace('#B19CD9', '#DDA0DD'))
        self.btn_undo.clicked.connect(self.undo_action)
        self.btn_undo.setEnabled(False)
        row1.addWidget(self.btn_undo)
        
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setStyleSheet(btn_style.replace('#B19CD9', '#FFB6C1'))
        self.btn_reset.clicked.connect(self.reset_peaks)
        self.btn_reset.setEnabled(False)
        row1.addWidget(self.btn_reset)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.setStyleSheet(btn_style.replace('#B19CD9', '#98FB98'))
        self.btn_save.clicked.connect(self.save_results)
        self.btn_save.setEnabled(False)
        row1.addWidget(self.btn_save)
        
        row1.addStretch()
        control_layout.addLayout(row1)
        
        # Second row - settings
        row2 = QHBoxLayout()
        
        row2.addWidget(QLabel("Fit Method:"))
        self.combo_fit_method = QComboBox()
        self.combo_fit_method.addItems(["pseudo_voigt", "voigt"])
        self.combo_fit_method.currentTextChanged.connect(self.on_fit_method_changed)
        row2.addWidget(self.combo_fit_method)
        
        row2.addWidget(QLabel("   "))
        
        self.btn_bg_mode = QPushButton("BG Selection Mode: OFF")
        self.btn_bg_mode.setStyleSheet(btn_style.replace('#B19CD9', '#29B6F6'))
        self.btn_bg_mode.clicked.connect(self.toggle_bg_selection)
        self.btn_bg_mode.setEnabled(False)
        row2.addWidget(self.btn_bg_mode)
        
        self.status_label = QLabel("Load a file to begin")
        self.status_label.setStyleSheet("color: #9370DB; font-weight: bold; padding: 5px;")
        row2.addWidget(self.status_label)
        
        row2.addStretch()
        control_layout.addLayout(row2)
        
        parent_layout.addWidget(control_frame)
    
    def create_plot_area(self, parent_layout):
        """Create matplotlib plot area"""
        plot_frame = QFrame()
        plot_frame.setStyleSheet("QFrame { background-color: white; }")
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create matplotlib figure (don't use plt.subplots to avoid extra window)
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(12, 6), facecolor='white')
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.12)
        self.ax.set_facecolor('#FAF0FF')
        self.ax.grid(True, alpha=0.3, linestyle='--', color='#D4A5D4')
        self.ax.set_xlabel('2theta (degree)', fontsize=11, color='#9370DB')
        self.ax.set_ylabel('Intensity', fontsize=11, color='#9370DB')
        self.ax.set_title('Click on peaks to select | Right-click to remove', 
                         fontsize=10, color='#9370DB')
        
        # Embed in Qt
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        plot_layout.addWidget(self.canvas)
        
        # Add toolbar
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("QFrame { background-color: #F5E6FA; }")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar = NavigationToolbar(self.canvas, toolbar_frame)
        toolbar_layout.addWidget(self.toolbar)
        plot_layout.addWidget(toolbar_frame)
        
        # Connect events
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        
        parent_layout.addWidget(plot_frame, stretch=3)
    
    def create_results_panel(self, parent_layout):
        """Create results table"""
        results_frame = QGroupBox("Fitting Results")
        results_frame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E6D5F5;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #9370DB;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        results_frame.setMaximumHeight(150)
        results_layout = QVBoxLayout(results_frame)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels(
            ['Peak', '2theta', 'FWHM', 'Area', 'Amplitude', 'Sigma', 'Gamma', 'Eta']
        )
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFBF0;
                gridline-color: #E6D5F5;
            }
            QHeaderView::section {
                background-color: #E6D5F5;
                padding: 4px;
                font-weight: bold;
            }
        """)
        results_layout.addWidget(self.results_table)
        
        parent_layout.addWidget(results_frame, stretch=1)
    
    def create_info_panel(self, parent_layout):
        """Create info text panel"""
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background-color: #F0E6FA; border-radius: 5px; }")
        info_frame.setMaximumHeight(80)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(5, 5, 5, 5)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background-color: #FAF0FF;
                color: #4B0082;
                border: 1px solid #E6D5F5;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        self.info_text.setMaximumHeight(60)
        self.info_text.append("Welcome! Load your XRD data file to begin peak fitting.")
        info_layout.addWidget(self.info_text)
        
        parent_layout.addWidget(info_frame)
    
    # ==================== Event Handlers ====================
    
    def on_scroll(self, event):
        """Handle mouse scroll for zooming"""
        if event.inaxes != self.ax or self.x is None:
            return
        
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        
        scale_factor = 0.8 if event.button == 'up' else 1.25
        
        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor
        
        relx = (xdata - xlim[0]) / (xlim[1] - xlim[0])
        rely = (ydata - ylim[0]) / (ylim[1] - ylim[0])
        
        new_xlim = [xdata - new_width * relx, xdata + new_width * (1 - relx)]
        new_ylim = [ydata - new_height * rely, ydata + new_height * (1 - rely)]
        
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw()
    
    def on_click(self, event):
        """Handle mouse clicks"""
        if event.inaxes != self.ax or self.x is None:
            return
        
        if self.toolbar.mode != '':
            return
        
        x_click = event.xdata
        idx = np.argmin(np.abs(self.x - x_click))
        point_x = self.x[idx]
        point_y = self.y[idx]
        
        if self.selecting_bg:
            self.handle_bg_click(event, idx, point_x, point_y)
        elif not self.fitted:
            self.handle_peak_click(event, idx, point_x, point_y)
    
    def handle_bg_click(self, event, idx, point_x, point_y):
        """Handle background point selection"""
        if event.button == 1:  # Left click - add
            marker, = self.ax.plot(point_x, point_y, 's', color='#4169E1',
                                  markersize=8, markeredgecolor='#FFD700',
                                  markeredgewidth=2, zorder=10)
            self.bg_points.append((point_x, point_y))
            self.bg_markers.append(marker)
            self.canvas.draw()
            self.update_info(f"BG point {len(self.bg_points)} added at 2theta = {point_x:.4f}")
            
            # Add to undo stack
            self.undo_stack.append(('bg_point', len(self.bg_points) - 1))
            self.btn_undo.setEnabled(True)
        
        elif event.button == 3:  # Right click - remove
            if len(self.bg_points) > 0:
                distances = [abs(x_click - p[0]) for p in self.bg_points]
                delete_idx = np.argmin(distances)
                self.bg_markers[delete_idx].remove()
                del self.bg_points[delete_idx]
                del self.bg_markers[delete_idx]
                self.canvas.draw()
                self.update_info(f"Removed BG point at index {delete_idx + 1}")
    
    def handle_peak_click(self, event, idx, point_x, point_y):
        """Handle peak selection"""
        if event.button == 1:  # Left click - add peak
            if idx not in self.selected_peaks:
                self.selected_peaks.append(idx)
                marker, = self.ax.plot(point_x, point_y, 'r^', markersize=10,
                                      markeredgecolor='black', markeredgewidth=1,
                                      zorder=5)
                text = self.ax.text(point_x, point_y * 1.05, f'P{len(self.selected_peaks)}',
                                   ha='center', fontsize=9, color='red',
                                   fontweight='bold', zorder=6)
                self.peak_markers.append(marker)
                self.peak_texts.append(text)
                self.canvas.draw()
                self.update_info(f"Peak {len(self.selected_peaks)} added at 2theta = {point_x:.4f}")
                
                # Add to undo stack
                self.undo_stack.append(('peak', idx))
                self.btn_undo.setEnabled(True)
                
                if len(self.selected_peaks) >= 1:
                    self.btn_fit.setEnabled(True)
                    self.btn_reset.setEnabled(True)
        
        elif event.button == 3:  # Right click - remove peak
            if idx in self.selected_peaks:
                peak_idx = self.selected_peaks.index(idx)
                self.peak_markers[peak_idx].remove()
                self.peak_texts[peak_idx].remove()
                del self.selected_peaks[peak_idx]
                del self.peak_markers[peak_idx]
                del self.peak_texts[peak_idx]
                
                # Renumber remaining peaks
                for i, text in enumerate(self.peak_texts):
                    text.set_text(f'P{i+1}')
                
                self.canvas.draw()
                self.update_info(f"Removed peak at 2theta = {point_x:.4f}")
                
                if len(self.selected_peaks) == 0:
                    self.btn_fit.setEnabled(False)
                    self.btn_reset.setEnabled(False)
    
    # ==================== Main Functions ====================
    
    def load_file(self):
        """Load XRD data file"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select XRD Data File",
            "",
            "XY files (*.xy);;DAT files (*.dat);;Text files (*.txt);;All files (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, encoding='latin1') as f:
                data = np.genfromtxt(f, comments="#")
            
            if data.ndim != 2 or data.shape[1] < 2:
                raise ValueError("Data must have at least 2 columns")
            
            self.x = data[:, 0]
            self.y = data[:, 1]
            self.y_original = self.y.copy()
            self.filepath = filepath
            self.filename = os.path.splitext(os.path.basename(filepath))[0]
            
            self.reset_peaks()
            self._scan_folder(filepath)
            self.plot_data()
            
            self.btn_auto_find.setEnabled(True)
            self.btn_bg_mode.setEnabled(True)
            self.status_label.setText(f"Loaded: {self.filename}")
            self.update_info(f"Successfully loaded: {self.filename}\nData points: {len(self.x)}")
            
            # Enable file navigation if multiple files
            if len(self.file_list) > 1:
                self.btn_prev.setEnabled(True)
                self.btn_next.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load file:\n{str(e)}")
    
    def plot_data(self):
        """Plot XRD data"""
        self.ax.clear()
        self.ax.plot(self.x, self.y, 'b-', linewidth=1.5, label='Data')
        self.ax.set_xlabel('2theta (degree)', fontsize=11, color='#9370DB')
        self.ax.set_ylabel('Intensity', fontsize=11, color='#9370DB')
        self.ax.set_title(f'XRD Data: {self.filename}', fontsize=10, color='#9370DB')
        self.ax.grid(True, alpha=0.3, linestyle='--', color='#D4A5D4')
        self.ax.set_facecolor('#FAF0FF')
        self.ax.legend()
        self.canvas.draw()
    
    def auto_find_peaks(self):
        """Automatically find peaks"""
        if self.x is None:
            return
        
        try:
            peaks = PeakDetector.auto_find_peaks(self.x, self.y)
            
            if len(peaks) == 0:
                QMessageBox.information(self, "No Peaks", "No peaks were detected automatically.")
                return
            
            # Clear existing peaks
            self.reset_peaks()
            
            # Add detected peaks
            for idx in peaks:
                self.selected_peaks.append(idx)
                point_x = self.x[idx]
                point_y = self.y[idx]
                marker, = self.ax.plot(point_x, point_y, 'r^', markersize=10,
                                      markeredgecolor='black', markeredgewidth=1,
                                      zorder=5)
                text = self.ax.text(point_x, point_y * 1.05, f'P{len(self.selected_peaks)}',
                                   ha='center', fontsize=9, color='red',
                                   fontweight='bold', zorder=6)
                self.peak_markers.append(marker)
                self.peak_texts.append(text)
            
            self.canvas.draw()
            self.btn_fit.setEnabled(True)
            self.btn_reset.setEnabled(True)
            self.update_info(f"Auto-detected {len(peaks)} peaks")
            
        except Exception as e:
            QMessageBox.warning(self, "Detection Error", f"Failed to detect peaks:\n{str(e)}")
    
    def fit_peaks(self):
        """Fit selected peaks"""
        if len(self.selected_peaks) == 0:
            QMessageBox.warning(self, "No Peaks", "Please select at least one peak first!")
            return
        
        self.status_label.setText("Fitting peaks...")
        QApplication.processEvents()
        
        try:
            # Sort peaks
            sorted_indices = sorted(range(len(self.selected_peaks)),
                                   key=lambda i: self.x[self.selected_peaks[i]])
            sorted_peaks = [self.selected_peaks[i] for i in sorted_indices]
            
            # Fit background
            if len(self.bg_points) >= 2:
                sorted_bg = sorted(self.bg_points, key=lambda p: p[0])
                bg_x = np.array([p[0] for p in sorted_bg])
                bg_y = np.array([p[1] for p in sorted_bg])
                global_bg = np.interp(self.x, bg_x, bg_y)
            else:
                global_bg, _ = BackgroundFitter.fit_global_background(
                    self.x, self.y, sorted_peaks, method='piecewise')
            
            y_nobg = self.y - global_bg
            
            # Fit peaks (simplified version)
            self.fit_results = []
            
            for peak_idx in sorted_peaks:
                # Simple Gaussian fit for each peak
                center = self.x[peak_idx]
                amplitude = y_nobg[peak_idx]
                sigma = 0.1  # Initial guess
                
                # Define local fitting window
                window = 50
                left = max(0, peak_idx - window)
                right = min(len(self.x), peak_idx + window)
                x_fit = self.x[left:right]
                y_fit = y_nobg[left:right]
                
                try:
                    # Fit pseudo-Voigt profile
                    def fit_func(x, amp, cen, sig, gam, eta):
                        return PeakProfile.pseudo_voigt(x, amp, cen, sig, gam, eta)
                    
                    p0 = [amplitude, center, sigma, sigma, 0.5]
                    bounds_lower = [0, center - 1, 0.01, 0.01, 0]
                    bounds_upper = [amplitude * 3, center + 1, 1, 1, 1]
                    
                    popt, _ = curve_fit(fit_func, x_fit, y_fit, p0=p0,
                                       bounds=(bounds_lower, bounds_upper),
                                       maxfev=5000)
                    
                    amp, cen, sig, gam, eta = popt
                    fwhm = PeakProfile.calculate_fwhm(sig, gam, eta)
                    area = amp * fwhm * np.pi / 2  # Approximate
                    
                    self.fit_results.append({
                        'center': cen,
                        'fwhm': fwhm,
                        'area': area,
                        'amplitude': amp,
                        'sigma': sig,
                        'gamma': gam,
                        'eta': eta
                    })
                    
                    # Plot fit
                    x_plot = np.linspace(x_fit[0], x_fit[-1], 200)
                    y_plot = fit_func(x_plot, *popt)
                    line, = self.ax.plot(x_plot, y_plot, 'g-', linewidth=2, alpha=0.8)
                    self.fit_lines.append(line)
                    
                except Exception as e:
                    self.update_info(f"Warning: Failed to fit peak at {center:.2f}: {str(e)}")
            
            # Plot background
            self.ax.plot(self.x, global_bg, 'orange', linewidth=2, 
                        linestyle='--', label='Background', alpha=0.7)
            
            self.canvas.draw()
            self.fitted = True
            self.btn_save.setEnabled(True)
            self.btn_clear_fit.setEnabled(True)
            self.display_results()
            self.status_label.setText(f"Fitted {len(self.fit_results)} peaks successfully")
            self.update_info(f"Successfully fitted {len(self.fit_results)} peaks")
            
        except Exception as e:
            QMessageBox.critical(self, "Fit Error", f"Failed to fit peaks:\n{str(e)}")
            self.status_label.setText("Fit failed")
    
    def reset_peaks(self):
        """Reset all peaks and fits"""
        # Clear peak markers
        for marker in self.peak_markers:
            marker.remove()
        for text in self.peak_texts:
            text.remove()
        
        # Clear fit lines
        for line in self.fit_lines:
            line.remove()
        
        # Clear background
        for marker in self.bg_markers:
            marker.remove()
        
        self.selected_peaks = []
        self.peak_markers = []
        self.peak_texts = []
        self.fit_lines = []
        self.fit_results = None
        self.fitted = False
        self.bg_points = []
        self.bg_markers = []
        
        self.results_table.setRowCount(0)
        
        if self.x is not None:
            self.plot_data()
        
        self.btn_fit.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.update_info("Reset all selections")
    
    def save_results(self):
        """Save fitting results"""
        if self.fit_results is None:
            QMessageBox.warning(self, "No Results", "Please fit peaks before saving!")
            return
        
        save_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if not save_dir:
            return
        
        try:
            # Save to CSV
            df = pd.DataFrame(self.fit_results)
            csv_path = os.path.join(save_dir, f"{self.filename}_fit_results.csv")
            df.to_csv(csv_path, index=False)
            
            # Save plot
            fig_path = os.path.join(save_dir, f"{self.filename}_fit_plot.png")
            self.fig.savefig(fig_path, dpi=150, bbox_inches='tight')
            
            QMessageBox.information(self, "Success", 
                                   f"Results saved to:\n{save_dir}")
            self.update_info(f"Results saved to: {save_dir}")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{str(e)}")
    
    def display_results(self):
        """Display results in table"""
        if not self.fit_results:
            return
        
        self.results_table.setRowCount(len(self.fit_results))
        
        for i, result in enumerate(self.fit_results):
            self.results_table.setItem(i, 0, QTableWidgetItem(f"P{i+1}"))
            self.results_table.setItem(i, 1, QTableWidgetItem(f"{result['center']:.4f}"))
            self.results_table.setItem(i, 2, QTableWidgetItem(f"{result['fwhm']:.4f}"))
            self.results_table.setItem(i, 3, QTableWidgetItem(f"{result['area']:.2f}"))
            self.results_table.setItem(i, 4, QTableWidgetItem(f"{result['amplitude']:.2f}"))
            self.results_table.setItem(i, 5, QTableWidgetItem(f"{result['sigma']:.4f}"))
            self.results_table.setItem(i, 6, QTableWidgetItem(f"{result['gamma']:.4f}"))
            self.results_table.setItem(i, 7, QTableWidgetItem(f"{result['eta']:.4f}"))
    
    def toggle_bg_selection(self):
        """Toggle background selection mode"""
        self.selecting_bg = not self.selecting_bg
        if self.selecting_bg:
            self.btn_bg_mode.setText("BG Selection Mode: ON")
            self.btn_bg_mode.setStyleSheet(self.btn_bg_mode.styleSheet().replace('#29B6F6', '#FFA07A'))
            self.status_label.setText("Click to select background points")
        else:
            self.btn_bg_mode.setText("BG Selection Mode: OFF")
            self.btn_bg_mode.setStyleSheet(self.btn_bg_mode.styleSheet().replace('#FFA07A', '#29B6F6'))
            self.status_label.setText(f"{len(self.bg_points)} BG points selected")
    
    def on_fit_method_changed(self, method):
        """Handle fit method change"""
        self.fit_method = method
    
    def update_info(self, message):
        """Update info panel"""
        self.info_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.info_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _scan_folder(self, filepath):
        """Scan folder and build file list for navigation"""
        folder = os.path.dirname(filepath)
        all_files = []
        
        extensions = ['.xy', '.dat', '.txt']
        for file in sorted(os.listdir(folder)):
            if any(file.lower().endswith(ext) for ext in extensions):
                full_path = os.path.join(folder, file)
                if os.path.isfile(full_path):
                    all_files.append(full_path)
        
        self.file_list = all_files
        try:
            self.current_file_index = self.file_list.index(filepath)
        except ValueError:
            self.current_file_index = 0
    
    def prev_file(self):
        """Load previous file in folder"""
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self.load_file_by_path(self.file_list[self.current_file_index])
    
    def next_file(self):
        """Load next file in folder"""
        if self.current_file_index < len(self.file_list) - 1:
            self.current_file_index += 1
            self.load_file_by_path(self.file_list[self.current_file_index])
    
    def load_file_by_path(self, filepath):
        """Load file from specific path"""
        try:
            with open(filepath, encoding='latin1') as f:
                data = np.genfromtxt(f, comments="#")
            
            if data.ndim != 2 or data.shape[1] < 2:
                raise ValueError("Data must have at least 2 columns")
            
            self.x = data[:, 0]
            self.y = data[:, 1]
            self.y_original = self.y.copy()
            self.filepath = filepath
            self.filename = os.path.splitext(os.path.basename(filepath))[0]
            
            self.reset_peaks()
            self.plot_data()
            
            self.btn_auto_find.setEnabled(True)
            self.btn_bg_mode.setEnabled(True)
            self.status_label.setText(f"Loaded: {self.filename} ({self.current_file_index+1}/{len(self.file_list)})")
            self.update_info(f"Loaded: {self.filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load file:\n{str(e)}")
    
    def clear_fit(self):
        """Clear fit results but keep peak selections"""
        # Clear fit lines
        for line in self.fit_lines:
            line.remove()
        
        self.fit_lines = []
        self.fit_results = None
        self.fitted = False
        
        self.results_table.setRowCount(0)
        self.canvas.draw()
        
        self.btn_save.setEnabled(False)
        self.btn_clear_fit.setEnabled(False)
        self.update_info("Cleared fit results")
    
    def undo_action(self):
        """Undo last action"""
        if not self.undo_stack:
            return
        
        action_type, data = self.undo_stack.pop()
        
        if action_type == 'peak':
            # Undo peak addition
            if len(self.selected_peaks) > 0:
                idx = self.selected_peaks.pop()
                self.peak_markers[-1].remove()
                self.peak_texts[-1].remove()
                self.peak_markers.pop()
                self.peak_texts.pop()
                self.canvas.draw()
                self.update_info(f"Undid peak selection")
        
        elif action_type == 'bg_point':
            # Undo background point
            if len(self.bg_points) > 0:
                self.bg_points.pop()
                self.bg_markers[-1].remove()
                self.bg_markers.pop()
                self.canvas.draw()
                self.update_info(f"Undid background point")
        
        if not self.undo_stack:
            self.btn_undo.setEnabled(False)


# For standalone testing
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = AutoFittingModule()
    window.setMinimumSize(1200, 800)
    window.show()
    sys.exit(app.exec())
