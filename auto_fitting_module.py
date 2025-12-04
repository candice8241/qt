# -*- coding: utf-8 -*-
"""
Auto Fitting Module - Complete 1:1 Qt6 Conversion
完整一比一转换版本
Converted from auto_fitting.py (tkinter) to Qt6
"""

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')  # Set backend BEFORE importing pyplot
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, 
    QPushButton, QMessageBox, QFileDialog, QTextEdit, 
    QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox, 
    QScrollArea, QRadioButton, QButtonGroup, QDialog, 
    QLineEdit, QGridLayout, QSizePolicy, QApplication,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QDoubleValidator, QIntValidator

from scipy.optimize import curve_fit
from scipy.special import wofz
from scipy.signal import savgol_filter, find_peaks
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import UnivariateSpline
from sklearn.cluster import DBSCAN

import os
import pandas as pd
import warnings
import sys

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# Import data processing classes from original file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from auto_fitting import (DataProcessor, PeakClusterer, BackgroundFitter, 
                              PeakProfile, PeakDetector)
except ImportError:
    # Minimal fallback if import fails
    print("Warning: Could not import from auto_fitting.py, using minimal fallbacks")
    
    class DataProcessor:
        @staticmethod
        def gaussian_smoothing(y, sigma=2):
            return gaussian_filter1d(y, sigma=sigma)
        
        @staticmethod
        def savgol_smoothing(y, window_length=11, polyorder=3):
            window_length = min(window_length, len(y))
            if window_length % 2 == 0:
                window_length -= 1
            if window_length < polyorder + 2:
                window_length = polyorder + 2
                if window_length % 2 == 0:
                    window_length += 1
            return savgol_filter(y, window_length, polyorder)
        
        @classmethod
        def apply_smoothing(cls, y, method='gaussian', **kwargs):
            if method == 'gaussian':
                sigma = kwargs.get('sigma', 2)
                return cls.gaussian_smoothing(y, sigma=sigma)
            elif method == 'savgol':
                window_length = kwargs.get('window_length', 11)
                polyorder = kwargs.get('polyorder', 3)
                return cls.savgol_smoothing(y, window_length=window_length, polyorder=polyorder)
            return y
    
    class PeakDetector:
        @staticmethod
        def auto_find_peaks(x, y):
            if len(y) > 15:
                window_length = min(15, len(y) // 2 * 2 + 1)
                y_smooth = savgol_filter(y, window_length, 3)
            else:
                y_smooth = y
            y_range = np.max(y) - np.min(y)
            dx = np.mean(np.diff(x))
            height_threshold = np.min(y) + y_range * 0.05
            prominence_threshold = y_range * 0.02
            min_distance = max(5, int(0.1 / dx)) if dx > 0 else 5
            peaks, _ = find_peaks(y_smooth, height=height_threshold, 
                                 prominence=prominence_threshold, distance=min_distance)
            return peaks
    
    class PeakProfile:
        @staticmethod
        def pseudo_voigt(x, amplitude, center, sigma, gamma, eta):
            gaussian = amplitude * np.exp(-(x - center)**2 / (2 * sigma**2)) / (sigma * np.sqrt(2 * np.pi))
            lorentzian = amplitude * gamma**2 / ((x - center)**2 + gamma**2) / (np.pi * gamma)
            return eta * lorentzian + (1 - eta) * gaussian
        
        @staticmethod
        def voigt(x, amplitude, center, sigma, gamma):
            z = ((x - center) + 1j * gamma) / (sigma * np.sqrt(2))
            return amplitude * np.real(wofz(z)) / (sigma * np.sqrt(2 * np.pi))
        
        @staticmethod
        def calculate_fwhm(sigma, gamma, eta):
            fwhm_g = 2.355 * sigma
            fwhm_l = 2 * gamma
            return eta * fwhm_l + (1 - eta) * fwhm_g
    
    class BackgroundFitter:
        @staticmethod
        def fit_global_background(x, y, peak_indices, method='spline', **kwargs):
            if len(peak_indices) == 0:
                return np.full_like(y, np.median(y)), []
            # Simplified version
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
        
        @staticmethod
        def find_auto_background_points(x, y, n_points=10, window_size=50):
            if len(x) < 2:
                return []
            x_min, x_max = x.min(), x.max()
            segment_boundaries = np.linspace(x_min, x_max, n_points + 1)
            bg_points = []
            for i in range(n_points):
                seg_start = segment_boundaries[i]
                seg_end = segment_boundaries[i + 1]
                mask = (x >= seg_start) & (x <= seg_end)
                indices = np.where(mask)[0]
                if len(indices) == 0:
                    continue
                seg_y = y[indices]
                min_local_idx = np.argmin(seg_y)
                global_idx = indices[min_local_idx]
                bg_points.append((x[global_idx], y[global_idx]))
            return bg_points
    
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


# ==================== Main GUI Application ====================
class AutoFittingModule(QWidget):
    """
    Complete 1:1 Qt6 conversion of PeakFittingGUI
    完整一比一转换版本
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Window title (for standalone mode)
        self.setWindowTitle("Interactive XRD Peak Fitting Tool - Enhanced")
        
        # Data storage (lines 576-587 of original)
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
        
        # File navigation (lines 589-591)
        self.file_list = []
        self.current_file_index = -1
        
        # Background fitting storage (lines 593-598)
        self.bg_points = []
        self.bg_markers = []
        self.bg_line = None
        self.bg_connect_line = None
        self.selecting_bg = False
        
        # Batch background reuse (lines 600-602)
        self.batch_bg_template = []
        self.batch_bg_initialized = False
        
        # Dialog geometry persistence (lines 604-605)
        self.verification_dialog_geometry = None
        
        # Store previous peaks/bg points for retention between files
        self._previous_peaks = None
        self._previous_bg_points = None
        
        # Store complete state for each file (for navigation preservation)
        self._file_states = {}  # filepath -> state dict
        
        # Undo stack (lines 607-608)
        self.undo_stack = []
        
        # Fitting settings (lines 610-615)
        # In Qt6, we don't use StringVar, just direct values
        self.fit_method = "pseudo_voigt"
        self.overlap_mode = False
        self.group_distance_threshold = 2.5
        self.overlap_threshold = 5.0  # Direct value, not Var
        self.fitting_window_multiplier = 3.0  # Direct value, not Var
        
        # Smoothing settings (lines 617-622)
        self.smoothing_enabled = False  # Direct bool, not BooleanVar
        self.smoothing_method = "gaussian"  # Direct string, not StringVar
        self.smoothing_sigma = 2.0  # Direct float, not DoubleVar
        self.smoothing_window = 11  # Direct int, not IntVar
        self.y_smoothed = None
        
        # Batch auto-fitting settings (lines 624-631)
        self.batch_running = False
        self.batch_paused = False
        self.batch_skip_current = False
        self.batch_stopped_by_user = False
        self.batch_delay = 0.01  # Direct float, not DoubleVar
        self.batch_on_failure = "skip"  # Direct string, not StringVar
        self.batch_auto_save = True  # Direct bool, not BooleanVar
        self.batch_verify_each = False  # Added for batch verification
        self.batch_csv_paths = []  # Track saved CSV files
        
        # Initialize GUI components (line 633-634)
        self.create_widgets()
    
    def create_widgets(self):
        """Create all GUI components (line 665-683)"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(2)
        
        # Top control panel (line 668)
        self._create_control_panel(main_layout)
        
        # Background fitting panel (line 671)
        self._create_background_panel(main_layout)
        
        # Smoothing panel (line 674)
        self._create_smoothing_panel(main_layout)
        
        # Results display panel (line 677)
        self._create_results_panel(main_layout)
        
        # Main plot area (line 680)
        self._create_plot_area(main_layout)
        
        # Info panel removed as per user request
        
        # Initialize hidden info text for logging
        self._init_hidden_info_text()
    
    def _create_control_panel(self, parent_layout):
        """Create top control panel (lines 685-773)"""
        # Create frame
        control_frame = QFrame()
        control_frame.setStyleSheet("QFrame { background-color: #E6D5F5; border-radius: 5px; }")
        control_frame.setFixedHeight(30)  # Half of original 60px
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(3, 2, 3, 2)
        control_layout.setSpacing(3)
        
        # Button style
        btn_style = """
            QPushButton {
                background-color: #D4C5E8;
                color: black;
                border: none;
                border-radius: 3px;
                padding: 3px;
                font-weight: bold;
                font-size: 8.5pt;
                min-width: 85px;
                min-height: 17px;
            }
            QPushButton:hover { background-color: #B19CD9; }
            QPushButton:disabled { background-color: #F4F6FB; color: #999999; border: 1px solid #E0E0E0; }
        """
        
        # Load File button (lines 699-702)
        self.btn_load = QPushButton("Load File")
        self.btn_load.setStyleSheet(btn_style)
        self.btn_load.clicked.connect(self.load_file)
        control_layout.addWidget(self.btn_load)
        
        # File navigation buttons (lines 704-717)
        nav_btn_style = btn_style.replace('min-width: 85px', 'min-width: 28px')
        
        self.btn_prev_file = QPushButton("◀")
        self.btn_prev_file.setStyleSheet(nav_btn_style)
        self.btn_prev_file.clicked.connect(self.prev_file)
        self.btn_prev_file.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_prev_file)
        
        self.btn_next_file = QPushButton("▶")
        self.btn_next_file.setStyleSheet(nav_btn_style)
        self.btn_next_file.clicked.connect(self.next_file)
        self.btn_next_file.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_next_file)
        
        # Fit Peaks button (lines 719-722)
        self.btn_fit = QPushButton("Fit Peaks")
        self.btn_fit.setStyleSheet(btn_style.replace('#D4C5E8', '#E1D5F0'))
        self.btn_fit.clicked.connect(self.fit_peaks)
        self.btn_fit.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_fit)
        
        # Reset button (lines 724-727)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setStyleSheet(btn_style.replace('#D4C5E8', '#FFD4DC'))
        self.btn_reset.clicked.connect(self.reset_peaks)
        self.btn_reset.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_reset)
        
        # Save Results button (lines 729-732)
        self.btn_save = QPushButton("Save Results")
        self.btn_save.setStyleSheet(btn_style.replace('#D4C5E8', '#C5FDC5'))
        self.btn_save.clicked.connect(self.save_results)
        self.btn_save.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_save)
        
        # Clear Fit button (lines 734-737)
        self.btn_clear_fit = QPushButton("Clear Fit")
        self.btn_clear_fit.setStyleSheet(btn_style.replace('#D4C5E8', '#FFC4A8'))
        self.btn_clear_fit.clicked.connect(self.clear_fit)
        self.btn_clear_fit.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_clear_fit)
        
        # Undo button (lines 739-742)
        self.btn_undo = QPushButton("Undo")
        self.btn_undo.setStyleSheet(btn_style.replace('#D4C5E8', '#ECC5EC'))
        self.btn_undo.clicked.connect(self.undo_action)
        self.btn_undo.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_undo)
        
        # Auto Find button (lines 744-747)
        self.btn_auto_find = QPushButton("Auto Find")
        self.btn_auto_find.setStyleSheet(btn_style)
        self.btn_auto_find.clicked.connect(self.auto_find_peaks)
        self.btn_auto_find.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_auto_find)
        
        # Overlap button (lines 749-753)
        self.btn_overlap_mode = QPushButton("Overlap")
        self.btn_overlap_mode.setStyleSheet(btn_style.replace('#D4C5E8', '#E9D9E9'))
        self.btn_overlap_mode.clicked.connect(self.toggle_overlap_mode)
        self.btn_overlap_mode.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_overlap_mode)
        
        # Batch Auto Fit button (lines 755-758)
        # User says: "batch auto fit应该在最初就可以点"
        self.btn_batch_auto = QPushButton("Batch Auto Fit")
        self.btn_batch_auto.setStyleSheet(btn_style.replace('#D4C5E8', '#D1ECFA'))
        self.btn_batch_auto.clicked.connect(self.batch_auto_fit)
        self.btn_batch_auto.setEnabled(True)  # User wants this ENABLED initially!
        control_layout.addWidget(self.btn_batch_auto)
        
        # Batch Settings button (lines 760-766)
        self.btn_batch_settings = QPushButton("⚙")
        self.btn_batch_settings.setStyleSheet(nav_btn_style.replace('#D4C5E8', '#D4E1EE'))
        self.btn_batch_settings.clicked.connect(self.show_batch_settings)
        self.btn_batch_settings.setEnabled(True)  # state=tk.NORMAL
        control_layout.addWidget(self.btn_batch_settings)
        
        # Status label (lines 768-772)
        self.status_label = QLabel("Please load a file to start")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #9370DB;
                font-weight: bold;
                font-size: 9.5pt;
                background-color: #E6D5F5;
                padding: 2px;
            }
        """)
        self.status_label.setMinimumWidth(300)
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        parent_layout.addWidget(control_frame)
    
    def _create_background_panel(self, parent_layout):
        """Create background fitting control panel"""
        # Create frame
        bg_frame = QFrame()
        bg_frame.setStyleSheet("QFrame { background-color: #F5E6FA; border-radius: 5px; }")
        bg_frame.setFixedHeight(50)
        bg_layout = QHBoxLayout(bg_frame)
        bg_layout.setContentsMargins(10, 8, 10, 8)
        bg_layout.setSpacing(5)
        
        # Background label
        bg_label = QLabel("Background:")
        bg_label.setStyleSheet("color: #9370DB; font-weight: bold; font-size: 8.5pt;")
        bg_layout.addWidget(bg_label)
        
        # Button style
        btn_bg_style = """
            QPushButton {
                background-color: #D4C5E8;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 7.5pt;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #B19CD9; }
            QPushButton:disabled { background-color: #F4F6FB; color: #999999; }
        """
        
        # Select BG Points button (lines 793-797)
        self.btn_select_bg = QPushButton("Select BG Points")
        self.btn_select_bg.setStyleSheet(btn_bg_style)
        self.btn_select_bg.clicked.connect(self.toggle_bg_selection)
        self.btn_select_bg.setEnabled(False)
        bg_layout.addWidget(self.btn_select_bg)
        
        # Subtract BG button (lines 799-803)
        self.btn_subtract_bg = QPushButton("Subtract BG")
        self.btn_subtract_bg.setStyleSheet(btn_bg_style.replace('#D4C5E8', '#C5FDC5'))
        self.btn_subtract_bg.clicked.connect(self.subtract_background)
        self.btn_subtract_bg.setEnabled(False)
        bg_layout.addWidget(self.btn_subtract_bg)
        
        # Clear BG button (lines 805-809)
        self.btn_clear_bg = QPushButton("Clear BG")
        self.btn_clear_bg.setStyleSheet(btn_bg_style.replace('#D4C5E8', '#F48982'))
        self.btn_clear_bg.clicked.connect(self.clear_background)
        self.btn_clear_bg.setEnabled(False)
        bg_layout.addWidget(self.btn_clear_bg)
        
        # Auto Select BG button (lines 811-815)
        self.btn_auto_bg = QPushButton("Auto Select BG")
        self.btn_auto_bg.setStyleSheet(btn_bg_style.replace('#D4C5E8', '#6CCFFA'))
        self.btn_auto_bg.clicked.connect(self.auto_select_background)
        self.btn_auto_bg.setEnabled(False)
        bg_layout.addWidget(self.btn_auto_bg)
        
        # Fit Method
        fit_method_label = QLabel("Fit Method:")
        fit_method_label.setStyleSheet("color: #9370DB; font-weight: bold; font-size: 7.5pt; margin-left: 20px;")
        bg_layout.addWidget(fit_method_label)
        
        self.fit_method_combo = QComboBox()
        self.fit_method_combo.addItems(["pseudo_voigt", "voigt"])
        self.fit_method_combo.setCurrentIndex(0)
        self.fit_method_combo.currentTextChanged.connect(self.on_fit_method_changed)
        self.fit_method_combo.setMaximumWidth(110)
        self.fit_method_combo.setStyleSheet("font-size: 7.5pt;")
        bg_layout.addWidget(self.fit_method_combo)
        
        # Overlap threshold
        overlap_label = QLabel("Overlap FWHM×:")
        overlap_label.setStyleSheet("color: #9370DB; font-weight: bold; font-size: 7.5pt; margin-left: 20px;")
        bg_layout.addWidget(overlap_label)
        
        self.overlap_threshold_entry = QLineEdit(str(self.overlap_threshold))
        self.overlap_threshold_entry.setMaximumWidth(45)
        self.overlap_threshold_entry.setStyleSheet("padding: 4px; font-weight: bold; font-size: 7.5pt;")
        bg_layout.addWidget(self.overlap_threshold_entry)
        
        # Fitting window
        window_label = QLabel("Fit Window×:")
        window_label.setStyleSheet("color: #9370DB; font-weight: bold; font-size: 7.5pt; margin-left: 20px;")
        bg_layout.addWidget(window_label)
        
        self.fitting_window_entry = QLineEdit(str(self.fitting_window_multiplier))
        self.fitting_window_entry.setMaximumWidth(45)
        self.fitting_window_entry.setStyleSheet("padding: 4px; font-weight: bold; font-size: 7.5pt;")
        bg_layout.addWidget(self.fitting_window_entry)
        
        # Coordinate label
        self.coord_label = QLabel("")
        self.coord_label.setStyleSheet("color: #9370DB; font-weight: bold; font-size: 7.5pt;")
        bg_layout.addWidget(self.coord_label)
        
        bg_layout.addStretch()
        parent_layout.addWidget(bg_frame)
    
    def _create_smoothing_panel(self, parent_layout):
        """Create smoothing control panel"""
        # Create frame
        smooth_frame = QFrame()
        smooth_frame.setStyleSheet("QFrame { background-color: #E6E6FA; border-radius: 5px; }")
        smooth_frame.setFixedHeight(50)
        smooth_layout = QHBoxLayout(smooth_frame)
        smooth_layout.setContentsMargins(10, 8, 10, 8)
        smooth_layout.setSpacing(5)
        
        # Smoothing label
        smooth_label = QLabel("Smoothing:")
        smooth_label.setStyleSheet("color: #0078D7; font-weight: bold; font-size: 8.5pt;")
        smooth_layout.addWidget(smooth_label)
        
        # Enable checkbox
        self.chk_smooth = QCheckBox("Enable")
        self.chk_smooth.setStyleSheet("color: #0078D7; font-weight: bold; font-size: 7.5pt;")
        self.chk_smooth.setChecked(self.smoothing_enabled)
        smooth_layout.addWidget(self.chk_smooth)
        
        # Method
        method_label = QLabel("Method:")
        method_label.setStyleSheet("color: #0078D7; font-weight: bold; font-size: 7.5pt; margin-left: 10px;")
        smooth_layout.addWidget(method_label)
        
        self.smooth_method_combo = QComboBox()
        self.smooth_method_combo.addItems(["gaussian", "savgol"])
        self.smooth_method_combo.setCurrentText(self.smoothing_method)
        self.smooth_method_combo.setMaximumWidth(90)
        self.smooth_method_combo.setStyleSheet("font-size: 7.5pt;")
        smooth_layout.addWidget(self.smooth_method_combo)
        
        # Sigma
        sigma_label = QLabel("Sigma:")
        sigma_label.setStyleSheet("color: #0078D7; font-weight: bold; font-size: 7.5pt; margin-left: 10px;")
        smooth_layout.addWidget(sigma_label)
        
        self.smooth_sigma_entry = QLineEdit(str(self.smoothing_sigma))
        self.smooth_sigma_entry.setMaximumWidth(45)
        self.smooth_sigma_entry.setStyleSheet("padding: 4px; font-weight: bold; font-size: 7.5pt;")
        smooth_layout.addWidget(self.smooth_sigma_entry)
        
        # Window
        window_label = QLabel("Window:")
        window_label.setStyleSheet("color: #0078D7; font-weight: bold; font-size: 7.5pt; margin-left: 10px;")
        smooth_layout.addWidget(window_label)
        
        self.smooth_window_entry = QLineEdit(str(self.smoothing_window))
        self.smooth_window_entry.setMaximumWidth(45)
        self.smooth_window_entry.setStyleSheet("padding: 4px; font-weight: bold; font-size: 7.5pt;")
        smooth_layout.addWidget(self.smooth_window_entry)
        
        # Buttons style
        btn_smooth_style = """
            QPushButton {
                background-color: #C5FDC5;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 7.5pt;
                min-width: 70px;
            }
            QPushButton:hover { background-color: #98FB98; }
            QPushButton:disabled { background-color: #F4F6FB; color: #999999; }
        """
        
        self.btn_apply_smooth = QPushButton("Apply")
        self.btn_apply_smooth.setStyleSheet(btn_smooth_style)
        self.btn_apply_smooth.clicked.connect(self.apply_smoothing_to_data)
        self.btn_apply_smooth.setEnabled(False)
        smooth_layout.addWidget(self.btn_apply_smooth)
        
        self.btn_reset_smooth = QPushButton("Reset Data")
        self.btn_reset_smooth.setStyleSheet(btn_smooth_style.replace('#C5FDC5', '#F48982'))
        self.btn_reset_smooth.clicked.connect(self.reset_to_original_data)
        self.btn_reset_smooth.setEnabled(False)
        smooth_layout.addWidget(self.btn_reset_smooth)
        
        smooth_layout.addStretch()
        parent_layout.addWidget(smooth_frame)
    
    def _create_results_panel(self, parent_layout):
        """Create results display panel"""
        # Create frame
        results_frame = QGroupBox("Fitting Results:")
        results_frame.setStyleSheet("""
            QGroupBox {
                background-color: #FFF0F5;
                border: 1px solid #FF6B9D;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                font-size: 8.5pt;
                color: #FF6B9D;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        results_frame.setFixedHeight(120)
        results_layout = QVBoxLayout(results_frame)
        results_layout.setContentsMargins(10, 15, 10, 5)
        
        # Create table (lines 919-926)
        columns = ['Peak', '2theta', 'FWHM', 'Area', 'Amplitude', 'Sigma', 'Gamma', 'Eta']
        self.results_tree = QTableWidget()
        self.results_tree.setColumnCount(len(columns))
        self.results_tree.setHorizontalHeaderLabels(columns)
        
        # Set column widths (lines 922-926) - Fixed widths to prevent layout shift
        col_widths = {'Peak': 50, '2theta': 100, 'FWHM': 100, 'Area': 100,
                      'Amplitude': 100, 'Sigma': 80, 'Gamma': 80, 'Eta': 80}
        for i, col in enumerate(columns):
            self.results_tree.setColumnWidth(i, col_widths.get(col, 80))
        
        # Disable column resize on content change to prevent flickering
        header = self.results_tree.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        
        # Style
        self.results_tree.setStyleSheet("""
            QTableWidget {
                background-color: #FFFBF0;
                gridline-color: #E0E0E0;
                font-weight: bold;
                font-size: 7.5pt;
            }
            QHeaderView::section {
                background-color: #FFE4E1;
                padding: 4px;
                border: 1px solid #E0E0E0;
                font-weight: bold;
                font-size: 7.5pt;
            }
        """)
        
        # Set alternating row colors
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.horizontalHeader().setStretchLastSection(True)
        self.results_tree.verticalHeader().setVisible(False)
        
        results_layout.addWidget(self.results_tree)
        parent_layout.addWidget(results_frame)
    
    def _create_plot_area(self, parent_layout):
        """Create main plot area"""
        # Create frame
        plot_frame = QFrame()
        plot_frame.setStyleSheet("QFrame { background-color: white; }")
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create matplotlib figure with new styling
        self.fig = Figure(figsize=(12, 6), facecolor='white')
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.15)
        self.ax.set_facecolor('#F4F6FB')  # New background color
        self.ax.grid(True, alpha=0.3, linestyle='--', color='#D4A5D4')
        
        # Set labels with Arial font and black color
        self.ax.set_xlabel('2theta (degree)', fontsize=13, color='black', fontname='Arial')
        self.ax.set_ylabel('Intensity', fontsize=13, color='black', fontname='Arial')
        self.ax.set_title('Click on peaks to select | Use toolbar or scroll to zoom/pan',
                         fontsize=11, color='black', fontname='Arial')
        
        # Set tick labels to Arial and black
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_fontname('Arial')
            label.set_color('black')
            label.set_fontsize(11)
        
        # Embed canvas
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        plot_layout.addWidget(self.canvas)
        
        # Add bottom border line
        bottom_line = QFrame()
        bottom_line.setFrameShape(QFrame.Shape.HLine)
        bottom_line.setFrameShadow(QFrame.Shadow.Sunken)
        bottom_line.setStyleSheet("QFrame { color: #CCCCCC; }")
        plot_layout.addWidget(bottom_line)
        
        # Connect events (lines 966-969)
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        parent_layout.addWidget(plot_frame, stretch=1)
    
    def _create_info_panel(self, parent_layout):
        """Info panel removed, create hidden text widget for logging"""
        pass
    
    def _init_hidden_info_text(self):
        """Initialize hidden info text widget for logging"""
        self.info_text = QTextEdit()
        self.info_text.setVisible(False)
    
    # ==================== Event Handlers (lines 986-1152) ====================
    
    def on_scroll(self, event):
        """Handle mouse scroll for zooming (lines 988-1011)"""
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
    
    def on_mouse_move(self, event):
        """Display mouse coordinates (lines 1013-1018)"""
        if event.inaxes == self.ax and event.xdata is not None:
            self.coord_label.setText(f"2theta: {event.xdata:.4f}  Intensity: {event.ydata:.2f}")
        else:
            self.coord_label.setText("")
    
    def on_click(self, event):
        """Handle mouse clicks (lines 1020-1036)"""
        if event.inaxes != self.ax or self.x is None:
            return
        
        # Toolbar removed, no mode check needed
        
        x_click = event.xdata
        idx = np.argmin(np.abs(self.x - x_click))
        point_x = self.x[idx]
        point_y = self.y[idx]
        
        if self.selecting_bg:
            self._handle_bg_click(event, idx, point_x, point_y, x_click)
        elif not self.fitted:
            self._handle_peak_click(event, idx, point_x, point_y, x_click)
    
    def _handle_bg_click(self, event, idx, point_x, point_y, x_click):
        """Handle clicks in background selection mode (lines 1038-1084)"""
        if event.button == 1:  # Left click - add point
            marker, = self.ax.plot(point_x, point_y, 's', color='#4169E1',
                                  markersize=5, markeredgecolor='#FFD700',
                                  markeredgewidth=1.5, zorder=10)
            text = self.ax.text(point_x, point_y * 0.97, f'BG{len(self.bg_points)+1}',
                               ha='center', fontsize=5, color='#4169E1',
                               fontweight='bold', zorder=11)
            self.bg_points.append((point_x, point_y))
            self.bg_markers.append((marker, text))
            self.update_bg_connect_line()
            self.canvas.draw()
            
            self.undo_stack.append(('bg_point', len(self.bg_points) - 1))
            self.btn_undo.setEnabled(True)
            self.update_info(f"BG point {len(self.bg_points)} added at 2theta = {point_x:.4f}\n")
            
            if len(self.bg_points) >= 2:
                self.btn_subtract_bg.setEnabled(True)
        
        elif event.button == 3:  # Right click - remove point
            if len(self.bg_points) > 0:
                distances = [abs(x_click - p[0]) for p in self.bg_points]
                delete_idx = np.argmin(distances)
                
                removed_point = self.bg_points.pop(delete_idx)
                marker_tuple = self.bg_markers.pop(delete_idx)
                
                try:
                    marker_tuple[0].remove()
                    marker_tuple[1].remove()
                except:
                    pass
                
                # Update labels
                for i, (marker, text) in enumerate(self.bg_markers):
                    text.set_text(f'BG{i+1}')
                
                self.update_bg_connect_line()
                self.canvas.draw()
                
                self.update_info(f"BG point removed at 2theta = {removed_point[0]:.4f}\n")
                
                if len(self.bg_points) < 2:
                    self.btn_subtract_bg.setEnabled(False)
    
    def _handle_peak_click(self, event, idx, point_x, point_y, x_click):
        """Handle clicks in peak selection mode (lines 1086-1151)"""
        if event.button == 1:  # Left click - add peak
            search_window = max(5, min(10, len(self.y) // 20))
            left_idx = max(0, idx - search_window)
            right_idx = min(len(self.y), idx + search_window + 1)
            
            local_y = self.y[left_idx:right_idx]
            local_max_idx = np.argmax(local_y)
            peak_idx = left_idx + local_max_idx
            
            dx = np.mean(np.diff(self.x))
            distance_to_click = abs(self.x[peak_idx] - x_click)
            max_allowed_distance = dx * search_window * 0.7
            
            if distance_to_click > max_allowed_distance:
                peak_idx = idx
                peak_x = point_x
                peak_y = point_y
                adjustment_note = "(using click position)"
            else:
                peak_x = self.x[peak_idx]
                peak_y = self.y[peak_idx]
                adjustment_note = "(auto-adjusted to local max)" if peak_idx != idx else ""
            
            # Use red dashed vertical line for peak marker (no star)
            vline = self.ax.axvline(x=peak_x, color='red', linestyle='--', linewidth=1.5, 
                                   alpha=0.7, zorder=11)
            
            self.selected_peaks.append(peak_idx)
            self.peak_markers.append(vline)  # Store vline in markers for compatibility
            self.peak_texts.append(vline)  # Also store in texts for removal
            self.canvas.draw()
            
            self.undo_stack.append(('peak', len(self.selected_peaks) - 1))
            self.btn_undo.setEnabled(True)
            self.update_info(f"Peak {len(self.selected_peaks)} at 2theta = {peak_x:.4f} {adjustment_note}\n")
            self.status_label.setText(f"{len(self.selected_peaks)} peak(s) selected")
        
        elif event.button == 3:  # Right click - remove peak
            if len(self.selected_peaks) > 0:
                peak_positions = [self.x[peak_idx] for peak_idx in self.selected_peaks]
                distances = [abs(x_click - pos) for pos in peak_positions]
                nearest_idx = np.argmin(distances)
                
                removed_peak_idx = self.selected_peaks.pop(nearest_idx)
                removed_peak_x = self.x[removed_peak_idx]
                
                marker = self.peak_markers.pop(nearest_idx)
                text = self.peak_texts.pop(nearest_idx)
                try:
                    marker.remove()
                    text.remove()
                except:
                    pass
                
                # No need to renumber since we're using vertical lines instead of text
                self.canvas.draw()
                
                self.update_info(f"Peak removed at 2theta = {removed_peak_x:.4f}\n")
                self.status_label.setText(f"{len(self.selected_peaks)} peak(s) selected")
    
    # ==================== File Operations (lines 1153-1266) ====================
    
    def load_file(self):
        """Load XRD data file via file dialog (lines 1155-1168)"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select XRD Data File",
            "",
            "XY files (*.xy);;DAT files (*.dat);;Text files (*.txt);;All files (*.*)"
        )
        
        if not filepath:
            return
        
        self._scan_folder(filepath)
        self.load_file_by_path(filepath)
    
    def _scan_folder(self, filepath):
        """Scan folder and build file list for navigation (lines 1170-1186)"""
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
    
    def load_file_by_path(self, filepath, skip_state_save=False):
        """Load XRD data file from specific path (lines 1188-1247)"""
        try:
            # Save current file state before loading new file (unless skipped)
            if not skip_state_save and self.filepath is not None:
                self._save_file_state()
            
            # Try to restore state if this file was loaded before
            if filepath in self._file_states:
                if self._restore_file_state(filepath):
                    # Enable buttons
                    self.btn_fit.setEnabled(True)
                    self.btn_reset.setEnabled(True)
                    self.btn_select_bg.setEnabled(True)
                    self.btn_clear_bg.setEnabled(True)
                    self.btn_auto_bg.setEnabled(True)
                    self.btn_auto_find.setEnabled(True)
                    self.btn_overlap_mode.setEnabled(True)
                    self.btn_apply_smooth.setEnabled(True)
                    self.btn_reset_smooth.setEnabled(True)
                    
                    if len(self.file_list) > 1:
                        self.btn_prev_file.setEnabled(True)
                        self.btn_next_file.setEnabled(True)
                        self.btn_batch_auto.setEnabled(True)
                    
                    self.update_info(f"File restored from cache: {self.filename}\nData points: {len(self.x)}\n")
                    return
            
            # Load fresh data if no cached state
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
            self.clear_background()
            self.fitted = False
            self.undo_stack = []
            self.btn_undo.setEnabled(False)
            
            self.ax.clear()
            self.ax.plot(self.x, self.y, '-', color='#9370DB', linewidth=0.8, label='Data')
            self.ax.set_facecolor('#F4F6FB')
            self.ax.grid(True, alpha=0.3, linestyle='--', color='#D4A5D4')
            self.ax.set_xlabel('2theta (degree)', fontsize=13, color='black', fontname='Arial')
            self.ax.set_ylabel('Intensity', fontsize=13, color='black', fontname='Arial')
            self.ax.set_title(f'{self.filename} | Click on peaks to select',
                            fontsize=11, color='black', fontname='Arial')
            # Set tick labels to Arial and black
            for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
                label.set_fontname('Arial')
                label.set_color('black')
                label.set_fontsize(9)
            # Expand x-axis range
            x_range = self.x.max() - self.x.min()
            self.ax.set_xlim(self.x.min() - x_range * 0.05, self.x.max() + x_range * 0.05)
            self.fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.15)
            self.canvas.draw()
            
            # Enable buttons
            self.btn_fit.setEnabled(True)
            self.btn_reset.setEnabled(True)
            self.btn_select_bg.setEnabled(True)
            self.btn_clear_bg.setEnabled(True)
            self.btn_auto_bg.setEnabled(True)
            self.btn_auto_find.setEnabled(True)
            self.btn_overlap_mode.setEnabled(True)
            self.btn_apply_smooth.setEnabled(True)
            self.btn_reset_smooth.setEnabled(True)
            
            if len(self.file_list) > 1:
                self.btn_prev_file.setEnabled(True)
                self.btn_next_file.setEnabled(True)
                self.btn_batch_auto.setEnabled(True)
            
            file_info = f"File {self.current_file_index + 1}/{len(self.file_list)}: {self.filename}"
            self.status_label.setText(file_info)
            self.update_info(f"File loaded: {self.filename}\nData points: {len(self.x)}\n")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
    
    def prev_file(self):
        """Load previous file (lines 1249-1256)"""
        if len(self.file_list) == 0:
            return
        self.current_file_index = (self.current_file_index - 1) % len(self.file_list)
        filepath = self.file_list[self.current_file_index]
        self.load_file_by_path(filepath)
    
    def next_file(self):
        """Load next file (lines 1258-1265)"""
        if len(self.file_list) == 0:
            return
        self.current_file_index = (self.current_file_index + 1) % len(self.file_list)
        filepath = self.file_list[self.current_file_index]
        self.load_file_by_path(filepath)
    
    # ==================== Background Operations (lines 1267-1443) ====================
    
    def toggle_bg_selection(self):
        """Toggle background selection mode (lines 1269-1277)"""
        self.selecting_bg = not self.selecting_bg
        if self.selecting_bg:
            # Update button style for active state
            self.btn_select_bg.setStyleSheet(self.btn_select_bg.styleSheet().replace('#D4C5E8', '#FFC4A8'))
            self.btn_select_bg.setText("Stop Selection")
            self.status_label.setText("Selecting background points...")
        else:
            # Restore normal state
            self.btn_select_bg.setStyleSheet(self.btn_select_bg.styleSheet().replace('#FFC4A8', '#D4C5E8'))
            self.btn_select_bg.setText("Select BG Points")
            self.status_label.setText(f"{len(self.bg_points)} BG points selected")
    
    def update_bg_connect_line(self):
        """Update background connecting line (lines 1279-1293)"""
        if self.bg_connect_line is not None:
            try:
                self.bg_connect_line.remove()
            except:
                pass
            self.bg_connect_line = None
        
        if len(self.bg_points) >= 2:
            sorted_points = sorted(self.bg_points, key=lambda p: p[0])
            bg_x = [p[0] for p in sorted_points]
            bg_y = [p[1] for p in sorted_points]
            self.bg_connect_line, = self.ax.plot(bg_x, bg_y, '-', color='#4169E1',
                                                 linewidth=1.5, alpha=0.7, zorder=8)
    
    def auto_select_background(self):
        """Automatically select background points (lines 1295-1331)"""
        if self.x is None or self.y is None:
            QMessageBox.warning(self, "No Data", "Please load a file first!")
            return
        
        try:
            self.clear_background()
            
            bg_points = BackgroundFitter.find_auto_background_points(self.x, self.y, n_points=10)
            
            if len(bg_points) == 0:
                QMessageBox.warning(self, "Auto Selection Failed",
                                  "Could not automatically find background points.")
                return
            
            for point_x, point_y in bg_points:
                marker, = self.ax.plot(point_x, point_y, 's', color='#4169E1',
                                      markersize=5, markeredgecolor='#FFD700',
                                      markeredgewidth=1.5, zorder=10)
                text = self.ax.text(point_x, point_y * 0.97, f'BG{len(self.bg_points)+1}',
                                   ha='center', fontsize=5, color='#4169E1',
                                   fontweight='bold', zorder=11)
                self.bg_points.append((point_x, point_y))
                self.bg_markers.append((marker, text))
            
            self.update_bg_connect_line()
            self.canvas.draw()
            
            if len(self.bg_points) >= 2:
                self.btn_subtract_bg.setEnabled(True)
            
            self.update_info(f"Auto-selected {len(bg_points)} background points\n")
            self.status_label.setText(f"{len(bg_points)} BG points auto-selected")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Auto background selection failed:\n{str(e)}")
    
    def subtract_background(self):
        """Subtract background (lines 1333-1380)"""
        if len(self.bg_points) < 2:
            QMessageBox.warning(self, "Insufficient Points", "Please select at least 2 background points!")
            return
        
        try:
            sorted_points = sorted(self.bg_points, key=lambda p: p[0])
            bg_x = np.array([p[0] for p in sorted_points])
            bg_y = np.array([p[1] for p in sorted_points])
            
            bg_interp = np.interp(self.x, bg_x, bg_y)
            self.y = self.y_original - bg_interp
            
            self.ax.clear()
            self.ax.plot(self.x, self.y, '-', color='#9370DB', linewidth=0.8,
                        label='Data (BG subtracted)')
            self.ax.set_facecolor('#FAF0FF')
            self.ax.grid(True, alpha=0.3, linestyle='--', color='#9370DB')
            self.ax.set_xlabel('2theta (degree)', fontsize=13, color='#9370DB')
            self.ax.set_ylabel('Intensity', fontsize=13, color='#9370DB')
            self.ax.set_title(f'{self.filename} (BG Subtracted)',
                            fontsize=11, color='black', fontname='Arial')
            
            # Re-add peak markers (red dashed vertical lines only, no stars)
            for i, idx in enumerate(self.selected_peaks):
                vline = self.ax.axvline(x=self.x[idx], color='red', linestyle='--', linewidth=1.5, 
                                       alpha=0.7, zorder=11)
                self.peak_markers[i] = vline
                self.peak_texts[i] = vline
            
            self.canvas.draw()
            
            self.bg_points = []
            self.bg_markers = []
            self.bg_line = None
            self.bg_connect_line = None
            self.btn_subtract_bg.setEnabled(False)
            
            self.update_info("Background subtracted\n")
            self.status_label.setText("Background subtracted")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to subtract background:\n{str(e)}")
    
    def clear_background(self):
        """Clear background selection (lines 1382-1417)"""
        for marker_tuple in self.bg_markers:
            try:
                marker_tuple[0].remove()
                marker_tuple[1].remove()
            except:
                pass
        
        if self.bg_line is not None:
            try:
                self.bg_line.remove()
            except:
                pass
        
        if self.bg_connect_line is not None:
            try:
                self.bg_connect_line.remove()
            except:
                pass
        
        self.bg_points = []
        self.bg_markers = []
        self.bg_line = None
        self.bg_connect_line = None
        self.selecting_bg = False
        
        self.undo_stack = [item for item in self.undo_stack if item[0] != 'bg_point']
        if not self.undo_stack:
            self.btn_undo.setEnabled(False)
        
        # Reset button appearance
        self.btn_select_bg.setText("Select BG Points")
        self.btn_subtract_bg.setEnabled(False)
        
        if self.x is not None:
            self.canvas.draw()
            
            # Update verification dialog if active
            if hasattr(self, '_update_verification_msg') and self._update_verification_msg:
                self._update_verification_msg()
    
    # ==================== Smoothing Operations (lines 1444-1514) ====================
    
    def apply_smoothing_to_data(self):
        """Apply smoothing to data (lines 1446-1479)"""
        if self.x is None or self.y is None:
            QMessageBox.warning(self, "No Data", "Please load a file first!")
            return
        
        if not self.chk_smooth.isChecked():
            QMessageBox.warning(self, "Smoothing Disabled", "Please enable smoothing first!")
            return
        
        try:
            method = self.smooth_method_combo.currentText()
            
            if method == 'gaussian':
                sigma = float(self.smooth_sigma_entry.text())
                self.y = DataProcessor.gaussian_smoothing(self.y, sigma=sigma)
                self.y_smoothed = self.y.copy()
            elif method == 'savgol':
                window = int(self.smooth_window_entry.text())
                polyorder = 3
                self.y = DataProcessor.savgol_smoothing(self.y, window_length=window, polyorder=polyorder)
                self.y_smoothed = self.y.copy()
            
            self.plot_data()
            self.btn_reset_smooth.setEnabled(True)
            self.update_info(f"Applied {method} smoothing\n")
            self.status_label.setText(f"Smoothing applied ({method})")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply smoothing:\n{str(e)}")
    
    def reset_to_original_data(self):
        """Reset to original data (lines 1481-1512)"""
        if self.y_original is None:
            return
        
        self.y = self.y_original.copy()
        self.y_smoothed = None
        self.plot_data()
        self.btn_reset_smooth.setEnabled(False)
        self.update_info("Reset to original data\n")
        self.status_label.setText("Data reset to original")
    
    # ==================== Peak Operations (lines 1515-2119) ====================
    
    def auto_find_peaks(self):
        """Automatically find peaks (lines 1515-1572)"""
        if self.x is None or self.y is None:
            QMessageBox.warning(self, "No Data", "Please load a file first!")
            return
        
        try:
            peaks = PeakDetector.auto_find_peaks(self.x, self.y)
            
            if len(peaks) == 0:
                QMessageBox.information(self, "No Peaks", "No peaks detected automatically.")
                return
            
            # Clear existing peaks
            for marker in self.peak_markers:
                try:
                    marker.remove()
                except:
                    pass
            for text in self.peak_texts:
                try:
                    text.remove()
                except:
                    pass
            
            self.selected_peaks = []
            self.peak_markers = []
            self.peak_texts = []
            
            # Add detected peaks (red dashed vertical lines only, no stars)
            for peak_idx in peaks:
                peak_x = self.x[peak_idx]
                
                vline = self.ax.axvline(x=peak_x, color='red', linestyle='--', linewidth=1.5, 
                                       alpha=0.7, zorder=11)
                
                self.selected_peaks.append(peak_idx)
                self.peak_markers.append(vline)
                self.peak_texts.append(vline)
            
            self.canvas.draw()
            self.btn_fit.setEnabled(True)
            self.btn_reset.setEnabled(True)
            
            self.update_info(f"Auto-detected {len(peaks)} peaks\n")
            self.status_label.setText(f"{len(peaks)} peaks auto-detected")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Auto peak detection failed:\n{str(e)}")
    
    def toggle_overlap_mode(self):
        """Toggle overlap mode (lines 1574-1584)"""
        self.overlap_mode = not self.overlap_mode
        if self.overlap_mode:
            self.btn_overlap_mode.setStyleSheet(self.btn_overlap_mode.styleSheet().replace('#E9D9E9', '#B8F5B8'))
            self.btn_overlap_mode.setText("Overlap ON")
            try:
                self.overlap_threshold = float(self.overlap_threshold_entry.text())
            except:
                self.overlap_threshold = 5.0
            self.group_distance_threshold = self.overlap_threshold
            self.update_info(f"Overlap mode ON: Peaks within {self.group_distance_threshold}×FWHM will be grouped together\n")
        else:
            self.btn_overlap_mode.setStyleSheet(self.btn_overlap_mode.styleSheet().replace('#B8F5B8', '#E9D9E9'))
            self.btn_overlap_mode.setText("Overlap")
            self.group_distance_threshold = 2.5
            self.update_info("Overlap mode OFF: Standard grouping (2.5×FWHM)\n")
    
    def undo_action(self):
        """Undo last action (lines 1586-1622)"""
        if not self.undo_stack:
            return
        
        action_type, index = self.undo_stack.pop()
        
        if action_type == 'peak':
            if self.selected_peaks and index == len(self.selected_peaks) - 1:
                self.selected_peaks.pop()
                marker = self.peak_markers.pop()
                text = self.peak_texts.pop()
                try:
                    marker.remove()
                    text.remove()
                except:
                    pass
                self.canvas.draw()
                self.status_label.setText(f"{len(self.selected_peaks)} peak(s) selected")
        
        elif action_type == 'bg_point':
            if self.bg_points and index == len(self.bg_points) - 1:
                self.bg_points.pop()
                marker_tuple = self.bg_markers.pop()
                try:
                    marker_tuple[0].remove()
                    marker_tuple[1].remove()
                except:
                    pass
                self.update_bg_connect_line()
                self.canvas.draw()
                
                if len(self.bg_points) < 2:
                    self.btn_subtract_bg.setEnabled(False)
        
        if not self.undo_stack:
            self.btn_undo.setEnabled(False)
    
    def reset_peaks(self):
        """Clear all peaks and fits (lines 1624-1664)"""
        for marker in self.peak_markers:
            try:
                marker.remove()
            except:
                pass
        for text in self.peak_texts:
            try:
                text.remove()
            except:
                pass
        for line in self.fit_lines:
            try:
                line.remove()
            except:
                pass
        
        self.selected_peaks = []
        self.peak_markers = []
        self.peak_texts = []
        self.fit_lines = []
        self.fitted = False
        self.fit_results = None
        
        # Clear results table
        self.results_tree.setRowCount(0)
        
        self.undo_stack = [item for item in self.undo_stack if item[0] != 'peak']
        if not self.undo_stack:
            self.btn_undo.setEnabled(False)
        
        if self.x is not None:
            self.ax.set_title(f'{self.filename} | Click on peaks to select',
                            fontsize=11, color='black', fontname='Arial')
            self.canvas.draw()
            self.update_info("All peaks and fits cleared\n")
            self.status_label.setText("Ready to select peaks")
        
        self.btn_save.setEnabled(False)
        self.btn_clear_fit.setEnabled(False)
    
    def fit_peaks(self):
        """Fit selected peaks using appropriate profile function (lines 1668-1799)"""
        if len(self.selected_peaks) == 0:
            QMessageBox.warning(self, "No Peaks", "Please select at least one peak first!")
            return
        
        fit_method = self.fit_method
        self.update_info(f"Fitting {len(self.selected_peaks)} peaks using {fit_method}...\n")
        self.status_label.setText("Fitting in progress...")
        QApplication.processEvents()
        
        try:
            # Sort peaks by position
            sorted_indices = sorted(range(len(self.selected_peaks)),
                                   key=lambda i: self.x[self.selected_peaks[i]])
            sorted_peaks = [self.selected_peaks[i] for i in sorted_indices]
            
            # Fit global background
            self.update_info("Fitting global background...\n")
            
            if len(self.bg_points) >= 2:
                sorted_bg_points = sorted(self.bg_points, key=lambda p: p[0])
                bg_x = np.array([p[0] for p in sorted_bg_points])
                bg_y = np.array([p[1] for p in sorted_bg_points])
                global_bg = np.interp(self.x, bg_x, bg_y)
                global_bg_points = sorted_bg_points
                self.update_info(f"Using {len(global_bg_points)} manually selected background points\n")
            else:
                global_bg, global_bg_points = BackgroundFitter.fit_global_background(
                    self.x, self.y, sorted_peaks, method='piecewise')
                self.update_info(f"Piecewise linear background fitted "
                               f"with {len(global_bg_points)} anchor points\n")
            
            # Subtract global background
            y_nobg = self.y - global_bg
            
            # Estimate FWHM for each peak
            fwhm_estimates = []
            for idx in sorted_peaks:
                window_size = 50
                left = max(0, idx - window_size)
                right = min(len(self.x), idx + window_size)
                x_local = self.x[left:right]
                y_local = y_nobg[left:right]
                local_peak_idx = idx - left
                fwhm, _ = PeakProfile.estimate_fwhm(x_local, y_local, local_peak_idx)
                fwhm_estimates.append(fwhm)
            
            # Group peaks using DBSCAN clustering
            peak_positions = np.array([self.x[idx] for idx in sorted_peaks])
            avg_fwhm = np.mean(fwhm_estimates)
            eps = avg_fwhm * self.group_distance_threshold
            
            cluster_labels, n_clusters = PeakClusterer.cluster_peaks(peak_positions, eps=eps)
            
            peak_groups = []
            for cluster_id in range(max(cluster_labels) + 1):
                group = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
                if group:
                    peak_groups.append(group)
            
            peak_groups.sort(key=lambda g: self.x[sorted_peaks[g[0]]])
            
            self.update_info(f"DBSCAN clustering: {n_clusters} groups (eps={eps:.4f})\n")
            
            # Fit each group
            use_voigt = (fit_method == "voigt")
            all_popt = {}
            group_windows = []
            
            for g_idx, group in enumerate(peak_groups):
                self.status_label.setText(f"Fitting group {g_idx+1}/{len(peak_groups)}...")
                QApplication.processEvents()
                
                group_peak_indices = [sorted_peaks[i] for i in group]
                group_fwhms = [fwhm_estimates[i] for i in group]
                is_overlapping = len(group) > 1
                
                # Create fitting window
                try:
                    base_multiplier = float(self.fitting_window_entry.text())
                except:
                    base_multiplier = self.fitting_window_multiplier
                    
                window_multiplier = base_multiplier + 1 if (is_overlapping and self.overlap_mode) else base_multiplier
                left_center = self.x[min(group_peak_indices)]
                right_center = self.x[max(group_peak_indices)]
                left_fwhm = group_fwhms[0]
                right_fwhm = group_fwhms[-1]
                
                window_left = left_center - left_fwhm * window_multiplier
                window_right = right_center + right_fwhm * window_multiplier
                
                left_idx = max(0, np.searchsorted(self.x, window_left))
                right_idx = min(len(self.x), np.searchsorted(self.x, window_right))
                group_windows.append((left_idx, right_idx))
                
                x_fit = self.x[left_idx:right_idx]
                y_fit_nobg = y_nobg[left_idx:right_idx]
                
                if len(x_fit) < 5:
                    continue
                
                # Build fit parameters
                p0, bounds_lower, bounds_upper = self._build_fit_parameters(
                    group, sorted_peaks, left_idx, fwhm_estimates, y_fit_nobg, use_voigt)
                
                # Perform fitting
                popt = self._perform_group_fit(x_fit, y_fit_nobg, p0, bounds_lower, bounds_upper,
                                              len(group), use_voigt, is_overlapping)
                
                if popt is not None:
                    # Store results
                    n_params = 4 if use_voigt else 5
                    for j, i in enumerate(group):
                        offset = j * n_params
                        all_popt[i] = {
                            'params': popt[offset:offset+n_params],
                            'group_idx': g_idx,
                            'window': (left_idx, right_idx)
                        }
            
            # Plot results
            self._plot_fit_results(all_popt, sorted_indices, sorted_peaks, peak_groups,
                                  group_windows, global_bg, global_bg_points, use_voigt)
            
            # Extract and display results
            self._extract_and_display_results(all_popt, sorted_indices, use_voigt, fit_method)
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error", f"Fitting failed:\n{str(e)}\n\n{traceback.format_exc()}")
            self.update_info(f"Fitting failed: {traceback.format_exc()}\n")
            self.status_label.setText("Fitting failed")
    
    def _build_fit_parameters(self, group, sorted_peaks, left_idx, fwhm_estimates,
                             y_fit_nobg, use_voigt):
        """Build initial parameters and bounds for curve fitting (lines 1800-1844)"""
        p0 = []
        bounds_lower = []
        bounds_upper = []
        
        dx = np.mean(np.diff(self.x))
        y_range = np.max(y_fit_nobg) - np.min(y_fit_nobg)
        
        for i in group:
            idx = sorted_peaks[i]
            local_idx = idx - left_idx
            cen_guess = self.x[idx]
            fwhm_est = fwhm_estimates[i]
            
            sig_guess = fwhm_est / 2.355
            gam_guess = fwhm_est / 2
            
            peak_height = y_fit_nobg[local_idx] if (0 <= local_idx < len(y_fit_nobg)) else np.max(y_fit_nobg)
            if peak_height <= 0:
                peak_height = np.max(y_fit_nobg) * 0.5
            
            amp_guess = peak_height * sig_guess * np.sqrt(2 * np.pi)
            
            amp_lower = 0
            amp_upper = y_range * sig_guess * np.sqrt(2 * np.pi) * 10
            
            center_tolerance = fwhm_est * 0.8 if self.overlap_mode else fwhm_est * 0.5
            
            sig_lower = dx * 0.5
            sig_upper = fwhm_est * 3
            gam_lower = dx * 0.5
            gam_upper = fwhm_est * 3
            
            if use_voigt:
                p0.extend([amp_guess, cen_guess, sig_guess, gam_guess])
                bounds_lower.extend([amp_lower, cen_guess - center_tolerance, sig_lower, gam_lower])
                bounds_upper.extend([amp_upper, cen_guess + center_tolerance, sig_upper, gam_upper])
            else:
                p0.extend([amp_guess, cen_guess, sig_guess, gam_guess, 0.5])
                bounds_lower.extend([amp_lower, cen_guess - center_tolerance, sig_lower, gam_lower, 0])
                bounds_upper.extend([amp_upper, cen_guess + center_tolerance, sig_upper, gam_upper, 1.0])
        
        return p0, bounds_lower, bounds_upper
    
    def _perform_group_fit(self, x_fit, y_fit_nobg, p0, bounds_lower, bounds_upper,
                          n_peaks, use_voigt, is_overlapping):
        """Perform curve fitting for a group of peaks (lines 1846-1885)"""
        # Define fitting function
        if use_voigt:
            def multi_peak_func(x, *params):
                y = np.zeros_like(x)
                for i in range(n_peaks):
                    offset = i * 4
                    amp, cen, sig, gam = params[offset:offset+4]
                    y += PeakProfile.voigt(x, amp, cen, sig, gam)
                return y
        else:
            def multi_peak_func(x, *params):
                y = np.zeros_like(x)
                for i in range(n_peaks):
                    offset = i * 5
                    amp, cen, sig, gam, eta = params[offset:offset+5]
                    y += PeakProfile.pseudo_voigt(x, amp, cen, sig, gam, eta)
                return y
        
        max_iter = 30000 if (is_overlapping or self.overlap_mode) else 10000
        ftol = 1e-9 if (is_overlapping or self.overlap_mode) else 1e-8
        xtol = 1e-9 if (is_overlapping or self.overlap_mode) else 1e-8
        
        try:
            popt, _ = curve_fit(multi_peak_func, x_fit, y_fit_nobg,
                               p0=p0, bounds=(bounds_lower, bounds_upper),
                               method='trf', maxfev=max_iter,
                               ftol=ftol, xtol=xtol)
            return popt
        except Exception:
            try:
                popt, _ = curve_fit(multi_peak_func, x_fit, y_fit_nobg,
                                   p0=p0, bounds=(bounds_lower, bounds_upper),
                                   method='dogbox', maxfev=50000)
                return popt
            except Exception as e:
                self.update_info(f"Group fit failed: {str(e)}\n")
                return None
    
    def _plot_fit_results(self, all_popt, sorted_indices, sorted_peaks, peak_groups,
                         group_windows, global_bg, global_bg_points, use_voigt):
        """Plot fitting results (lines 1887-1963)"""
        colors = plt.cm.tab10(np.linspace(0, 1, len(sorted_peaks)))
        
        # Clear manual background connecting line
        if self.bg_connect_line is not None:
            try:
                self.bg_connect_line.remove()
            except:
                pass
            self.bg_connect_line = None
        
        # Plot global background
        if len(global_bg_points) >= 2:
            # Plot background points
            bg_x = [p[0] for p in global_bg_points]
            bg_y = [p[1] for p in global_bg_points]
            bg_markers, = self.ax.plot(bg_x, bg_y, 's', color='#4169E1',
                                      markersize=3, alpha=0.8, zorder=3)
            self.fit_lines.append(bg_markers)
            
            # Plot background line
            bg_label = 'Manual Background' if len(self.bg_points) >= 2 else 'Auto Background'
            bg_line, = self.ax.plot(self.x, global_bg, '-', color='#4169E1',
                                   linewidth=1.5, alpha=0.4,
                                   label=bg_label, zorder=3)
            self.fit_lines.append(bg_line)
        
        # Plot total fit for each group
        for g_idx, (left, right) in enumerate(group_windows):
            x_region = self.x[left:right]
            x_smooth = np.linspace(x_region.min(), x_region.max(), 400)
            bg_smooth = np.interp(x_smooth, self.x, global_bg)
            
            y_total = bg_smooth.copy()
            group = peak_groups[g_idx]
            
            for i in group:
                if i not in all_popt:
                    continue
                params = all_popt[i]['params']
                if use_voigt:
                    y_total += PeakProfile.voigt(x_smooth, *params)
                else:
                    y_total += PeakProfile.pseudo_voigt(x_smooth, *params)
            
            label = 'Total Fit' if g_idx == 0 else None
            line1, = self.ax.plot(x_smooth, y_total, color='#FF0000', linewidth=1.5,
                                label=label, zorder=5, alpha=0.6)
            self.fit_lines.append(line1)
        
        # Plot individual peak components with background baseline
        for i in range(len(sorted_peaks)):
            if i not in all_popt:
                continue
            
            params = all_popt[i]['params']
            left, right = all_popt[i]['window']
            
            x_smooth = np.linspace(self.x[left], self.x[right], 400)
            
            if use_voigt:
                y_component = PeakProfile.voigt(x_smooth, *params)
            else:
                y_component = PeakProfile.pseudo_voigt(x_smooth, *params)
            
            # Get background baseline
            bg_smooth = np.interp(x_smooth, self.x, global_bg)
            y_peak_with_bg = y_component + bg_smooth
            
            original_idx = sorted_indices[i]
            line_comp, = self.ax.plot(x_smooth, y_peak_with_bg, '--',
                                     color=colors[i], linewidth=1.2, alpha=0.7, zorder=4,
                                     label=f'Peak {original_idx+1}')
            self.fit_lines.append(line_comp)
    
    def _extract_and_display_results(self, all_popt, sorted_indices, use_voigt, fit_method):
        """Extract fitting results and display in table (lines 1965-2031)"""
        results = []
        info_msg = f"Fitting Results ({fit_method}):\n" + "="*50 + "\n"
        
        for i in range(len(sorted_indices)):
            original_idx = sorted_indices[i]
            
            if i not in all_popt:
                continue
            
            params = all_popt[i]['params']
            
            if use_voigt:
                amp, cen, sig, gam = params
                fwhm = 2.355 * sig
                area = amp
                eta = "N/A"
            else:
                amp, cen, sig, gam, eta = params
                fwhm = PeakProfile.calculate_fwhm(sig, gam, eta)
                area = PeakProfile.calculate_area(amp, sig, gam, eta)
            
            results.append({
                'Peak': original_idx + 1,
                'center': cen,
                'fwhm': fwhm,
                'area': area,
                'amplitude': amp,
                'sigma': sig,
                'gamma': gam,
                'eta': eta
            })
            
            info_msg += f"Peak {original_idx+1}: 2theta={cen:.4f}, FWHM={fwhm:.5f}, Area={area:.1f}\n"
        
        results.sort(key=lambda r: r['Peak'])
        
        self.fit_results = results
        self.fitted = True
        
        # Update results table
        self.results_tree.setRowCount(len(results))
        for row_idx, r in enumerate(results):
            eta_str = f"{r['eta']:.3f}" if isinstance(r['eta'], float) else r['eta']
            self.results_tree.setItem(row_idx, 0, QTableWidgetItem(str(r['Peak'])))
            self.results_tree.setItem(row_idx, 1, QTableWidgetItem(f"{r['center']:.4f}"))
            self.results_tree.setItem(row_idx, 2, QTableWidgetItem(f"{r['fwhm']:.5f}"))
            self.results_tree.setItem(row_idx, 3, QTableWidgetItem(f"{r['area']:.2f}"))
            self.results_tree.setItem(row_idx, 4, QTableWidgetItem(f"{r['amplitude']:.2f}"))
            self.results_tree.setItem(row_idx, 5, QTableWidgetItem(f"{r['sigma']:.5f}"))
            self.results_tree.setItem(row_idx, 6, QTableWidgetItem(f"{r['gamma']:.5f}"))
            self.results_tree.setItem(row_idx, 7, QTableWidgetItem(eta_str))
        
        self.ax.set_title(f'{self.filename} - Fit Complete ({fit_method})',
                        fontsize=11, fontweight='bold', color='black', fontname='Arial')
        self.canvas.draw()
        
        self.update_info(info_msg)
        self.status_label.setText("Fitting successful!")
        
        self.btn_save.setEnabled(True)
        self.btn_clear_fit.setEnabled(True)
    
    def clear_fit(self):
        """Clear fitting results (lines 2033-2055)"""
        for line in self.fit_lines:
            try:
                line.remove()
            except:
                pass
        
        self.fit_lines = []
        self.fit_results = None
        self.fitted = False
        
        self.results_tree.setRowCount(0)
        
        if self.x is not None:
            self.canvas.draw()
            self.update_info("Fit results cleared\n")
            self.status_label.setText(f"{len(self.selected_peaks)} peak(s) selected")
        
        self.btn_save.setEnabled(False)
        self.btn_clear_fit.setEnabled(False)
    
    def save_results(self):
        """Save fitting results to user-selected directory (lines 2059-2077)"""
        if self.fit_results is None:
            QMessageBox.warning(self, "No Results", "Please fit peaks before saving!")
            return
        
        save_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if not save_dir:
            return
        
        try:
            csv_path, fig_path = self._save_results_to_dir(save_dir)
            QMessageBox.information(self, "Success",
                              f"Results saved to:\n{save_dir}\n\nCSV: {os.path.basename(csv_path)}\nPNG: {os.path.basename(fig_path)}")
            self.update_info(f"Results saved to: {save_dir}\n")
            self.status_label.setText("Results saved!")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{str(e)}")
    
    def _save_results_to_dir(self, save_dir):
        """Internal method to save results to a specific directory (lines 2099-2109)"""
        # Convert fit_results to DataFrame format for saving
        import pandas as pd
        df = pd.DataFrame(self.fit_results)
        
        # Rename 'center' to 'Center' for consistency
        if 'center' in df.columns:
            df.rename(columns={'center': 'Center'}, inplace=True)
        
        df['File'] = self.filename
        
        csv_path = os.path.join(save_dir, f"{self.filename}_fit_results.csv")
        df.to_csv(csv_path, index=False)
        
        fig_path = os.path.join(save_dir, f"{self.filename}_fit_plot.png")
        self.fig.savefig(fig_path, dpi=300, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
        
        return csv_path, fig_path
    
    def on_fit_method_changed(self, method):
        """Handle fit method change"""
        self.fit_method = method
    
    def plot_data(self):
        """Plot current data"""
        if self.x is None or self.y is None:
            return
        
        self.ax.clear()
        self.ax.plot(self.x, self.y, '-', color='#9370DB', linewidth=0.8, label='Data')
        self.ax.set_facecolor('#F4F6FB')
        self.ax.grid(True, alpha=0.3, linestyle='--', color='#D4A5D4')
        self.ax.set_xlabel('2theta (degree)', fontsize=13, color='black', fontname='Arial')
        self.ax.set_ylabel('Intensity', fontsize=13, color='black', fontname='Arial')
        self.ax.set_title(f'{self.filename} | Click on peaks to select',
                        fontsize=11, color='black', fontname='Arial')
        # Set tick labels
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_fontname('Arial')
            label.set_color('black')
            label.set_fontsize(9)
        self.canvas.draw()
    
    def update_info(self, message):
        """Update info panel"""
        self.info_text.append(message)
        scrollbar = self.info_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def display_results(self):
        """Display fitting results in table"""
        if self.fit_results is None:
            return
        
        self.results_tree.setRowCount(len(self.fit_results))
        for i, result in enumerate(self.fit_results):
            self.results_tree.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.results_tree.setItem(i, 1, QTableWidgetItem(f"{result['center']:.4f}"))
            self.results_tree.setItem(i, 2, QTableWidgetItem(f"{result.get('fwhm', 0):.4f}"))
            self.results_tree.setItem(i, 3, QTableWidgetItem(f"{result.get('area', 0):.2f}"))
            self.results_tree.setItem(i, 4, QTableWidgetItem(f"{result.get('amplitude', 0):.2f}"))
            self.results_tree.setItem(i, 5, QTableWidgetItem(f"{result.get('sigma', 0):.4f}"))
            self.results_tree.setItem(i, 6, QTableWidgetItem(f"{result.get('gamma', 0):.4f}"))
            self.results_tree.setItem(i, 7, QTableWidgetItem(f"{result.get('eta', 0):.3f}"))
    
    # ==================== Batch Processing (lines 2120-2952) ====================
    
    def show_batch_settings(self):
        """Show batch auto-fitting settings dialog (lines 2122-2196)"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Batch Auto-Fit Settings")
        dialog.setMinimumSize(400, 420)
        dialog.setStyleSheet("QDialog { background-color: #F0E6FA; }")
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Delay setting
        delay_frame = QFrame()
        delay_layout = QHBoxLayout(delay_frame)
        delay_label = QLabel("Display delay per file (seconds):")
        delay_label.setStyleSheet("color: #4B0082; font-weight: bold; font-size: 7.5pt;")
        delay_layout.addWidget(delay_label)
        
        delay_spinbox = QDoubleSpinBox()
        delay_spinbox.setRange(0.01, 10.0)
        delay_spinbox.setSingleStep(0.01)
        delay_spinbox.setValue(self.batch_delay)
        delay_spinbox.setStyleSheet("font-weight: bold; font-size: 7.5pt;")
        delay_layout.addWidget(delay_spinbox)
        layout.addWidget(delay_frame)
        
        # Auto-save setting
        autosave_check = QCheckBox("Auto-save results for each file")
        autosave_check.setChecked(self.batch_auto_save)
        autosave_check.setStyleSheet("color: #4B0082; font-weight: bold; font-size: 7.5pt;")
        layout.addWidget(autosave_check)
        
        # Failure handling
        failure_group = QGroupBox("When auto-fitting fails:")
        failure_group.setStyleSheet("QGroupBox { color: #4B0082; font-weight: bold; font-size: 7.5pt; }")
        failure_layout = QVBoxLayout(failure_group)
        
        failure_buttons = QButtonGroup(dialog)
        
        pause_radio = QRadioButton("Pause and allow manual adjustment")
        pause_radio.setStyleSheet("color: #4B0082; font-weight: bold; font-size: 6.5pt;")
        failure_layout.addWidget(pause_radio)
        failure_buttons.addButton(pause_radio, 0)
        
        skip_radio = QRadioButton("Skip to next file")
        skip_radio.setStyleSheet("color: #4B0082; font-weight: bold; font-size: 6.5pt;")
        failure_layout.addWidget(skip_radio)
        failure_buttons.addButton(skip_radio, 1)
        
        stop_radio = QRadioButton("Stop batch processing")
        stop_radio.setStyleSheet("color: #4B0082; font-weight: bold; font-size: 6.5pt;")
        failure_layout.addWidget(stop_radio)
        failure_buttons.addButton(stop_radio, 2)
        
        if self.batch_on_failure == "pause":
            pause_radio.setChecked(True)
        elif self.batch_on_failure == "skip":
            skip_radio.setChecked(True)
        else:
            stop_radio.setChecked(True)
        
        layout.addWidget(failure_group)
        
        # Info text
        info_text = QLabel(
            "Batch Auto-Fit will:\n"
            "1. Auto-find peaks\n"
            "2. Auto-select background\n"
            "3. Subtract background\n"
            "4. Fit peaks\n"
            "5. Save results (if enabled)"
        )
        info_text.setStyleSheet("""
            QLabel {
                background-color: #FAF0FF;
                color: #4B0082;
                font-weight: bold;
                font-size: 6.5pt;
                border: 2px inset;
                padding: 10px;
            }
        """)
        layout.addWidget(info_text)
        
        # Confirm button
        confirm_btn = QPushButton("Confirm")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #B19CD9;
                color: black;
                font-weight: bold;
                font-size: 8.5pt;
                padding: 10px;
                min-width: 140px;
            }
            QPushButton:hover { background-color: #9370DB; }
        """)
        
        def on_confirm():
            self.batch_delay = delay_spinbox.value()
            self.batch_auto_save = autosave_check.isChecked()
            
            if pause_radio.isChecked():
                self.batch_on_failure = "pause"
            elif skip_radio.isChecked():
                self.batch_on_failure = "skip"
            else:
                self.batch_on_failure = "stop"
            
            dialog.accept()
        
        confirm_btn.clicked.connect(on_confirm)
        layout.addWidget(confirm_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        dialog.exec()
    
    def batch_auto_fit(self):
        """Start batch auto-fitting for all files in folder (lines 2198-2285)"""
        if len(self.file_list) <= 1:
            QMessageBox.warning(self, "Insufficient Files",
                              "Need at least 2 files for batch processing!")
            return
        
        # Confirm start
        reply = QMessageBox.question(
            self,
            "Start Batch Processing",
            f"Start batch auto-fitting for {len(self.file_list)} files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Initialize batch processing
        self.batch_running = True
        self.batch_paused = False
        self.batch_skip_current = False
        self.batch_stopped_by_user = False
        self.batch_csv_paths = []
        
        # Disable other buttons during batch processing
        self.btn_load.setEnabled(False)
        self.btn_fit.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.btn_batch_settings.setEnabled(False)
        
        start_index = self.current_file_index
        
        try:
            for i in range(len(self.file_list)):
                if not self.batch_running:
                    break
                
                file_idx = (start_index + i) % len(self.file_list)
                self.current_file_index = file_idx
                filepath = self.file_list[file_idx]
                
                self.update_info(f"\n{'='*50}\n")
                self.update_info(f"Batch processing file {i+1}/{len(self.file_list)}: "
                               f"{os.path.basename(filepath)}\n")
                self.status_label.setText(f"Batch: {i+1}/{len(self.file_list)}")
                
                # Process this file
                success = self._process_single_file_auto(filepath)
                
                if not success:
                    # Check if user deliberately skipped in verification dialog
                    if self.batch_skip_current:
                        self.update_info("Skipping to next file...\n")
                        self.batch_skip_current = False
                        continue
                    
                    # Handle actual failure according to settings
                    if self.batch_on_failure == "stop":
                        self.update_info("Batch processing stopped due to failure.\n")
                        break
                    elif self.batch_on_failure == "pause":
                        self.update_info("Auto-fitting failed. Pausing for manual adjustment...\n")
                        self.batch_paused = True
                        self._show_manual_adjustment_dialog()
                        
                        # Wait for user to continue or skip
                        while self.batch_paused and self.batch_running:
                            QApplication.processEvents()
                            import time
                            time.sleep(0.1)
                        
                        if self.batch_skip_current:
                            self.update_info("Skipping current file...\n")
                            self.batch_skip_current = False
                            continue
                    elif self.batch_on_failure == "skip":
                        self.update_info("Auto-fitting failed. Skipping to next file...\n")
                        continue
                
                # Display delay
                QApplication.processEvents()
                import time
                time.sleep(self.batch_delay)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Batch processing error:\n{str(e)}")
        
        finally:
            self.batch_running = False
            
            # Re-enable buttons
            self.btn_load.setEnabled(True)
            self.btn_fit.setEnabled(True)
            self.btn_reset.setEnabled(True)
            self.btn_batch_settings.setEnabled(True)
            
            self.update_info("\n" + "="*50 + "\n")
            self.update_info("Batch processing complete!\n")
            
            # Merge all CSV files into one summary file
            if self.batch_auto_save and len(self.batch_csv_paths) > 0:
                try:
                    self._merge_batch_csv_files()
                except Exception as e:
                    QMessageBox.warning(self, "CSV Merge Warning", 
                                      f"Batch completed but CSV merge failed:\n{str(e)}")
            
            self.status_label.setText("Batch complete")
            
            if self.batch_auto_save and len(self.batch_csv_paths) > 0:
                QMessageBox.information(self, "Batch Complete",
                                      f"Processed {len(self.batch_csv_paths)} files successfully!")
    
    def _process_single_file_auto(self, filepath):
        """Process a single file automatically with verification dialog (lines 2290-2397)"""
        try:
            # Step 1: Load file (skip state save during batch processing)
            self.update_info("  Step 1: Loading file...\n")
            self.load_file_by_path(filepath, skip_state_save=True)
            QApplication.processEvents()
            self.update_info("  ✓ File loaded successfully\n")
            
            # Restore previous background points only (not peaks - always auto-detect peaks)
            # This ensures modifications from previous verification are retained
            previous_bg_points = []
            if hasattr(self, '_previous_bg_points') and self._previous_bg_points is not None:
                previous_bg_points = self._previous_bg_points.copy()
                self._previous_bg_points = None
            
            # Clear any previous peaks (don't retain them)
            self._previous_peaks = None
            
            # Step 2: Auto-find peaks (always perform fresh auto peak finding)
            self.update_info("  Step 2: Auto-detecting peaks...\n")
            peaks = PeakDetector.auto_find_peaks(self.x, self.y)
            
            # Add all peaks (red dashed vertical lines only, no stars)
            for peak_idx in peaks:
                peak_x = self.x[peak_idx]
                
                vline = self.ax.axvline(x=peak_x, color='red', linestyle='--', linewidth=1.5, 
                                       alpha=0.7, zorder=11)
                
                self.selected_peaks.append(peak_idx)
                self.peak_markers.append(vline)
                self.peak_texts.append(vline)
            
            self.canvas.draw()
            
            if len(self.selected_peaks) == 0:
                self.update_info("  ❌ No peaks detected!\n")
                return False
            
            self.update_info(f"  ✓ Total {len(self.selected_peaks)} peaks ready\n")
            
            # Restore or auto-select background
            if len(previous_bg_points) > 0:
                self.bg_points = previous_bg_points.copy()
                # Redraw background points (square markers)
                for bg_x, bg_y in self.bg_points:
                    idx = np.argmin(np.abs(self.x - bg_x))
                    marker, = self.ax.plot(bg_x, bg_y, 's', color='#4169E1',
                                          markersize=6, markeredgecolor='white',
                                          markeredgewidth=1, zorder=5)
                    text_obj = self.ax.text(bg_x, bg_y * 0.95, '',
                                           ha='center', fontsize=6, color='#4169E1',
                                           fontweight='bold', zorder=6)
                    self.bg_markers.append((marker, text_obj))
                self.update_bg_connect_line()
                self.canvas.draw()
                self.update_info(f"  Using previous {len(self.bg_points)} background point(s)\n")
            else:
                # Auto-select background
                self.update_info("  Auto-selecting background...\n")
                self.auto_select_background()
                QApplication.processEvents()
                self.update_info(f"  ✓ Selected {len(self.bg_points)} background points\n")
            
            # Manual verification step - allow user to review and adjust
            self.update_info("  Waiting for manual verification...\n")
            
            # Save current state before showing verification dialog
            peaks_before = self.selected_peaks.copy()
            bg_before = self.bg_points.copy()
            
            user_action = self._show_verification_dialog()
            
            if user_action == "skip":
                self.update_info("  User chose to skip this file\n")
                self.batch_skip_current = True
                # Save current state for next file (only background points, not peaks)
                self._previous_peaks = None  # Don't retain peaks
                self._previous_bg_points = self.bg_points.copy()
                return False
            elif user_action == "stop":
                self.update_info("  User chose to stop batch processing\n")
                self.batch_running = False
                self.batch_stopped_by_user = True
                return False
            
            # Check if user made modifications
            if len(self.selected_peaks) != len(peaks_before) or len(self.bg_points) != len(bg_before):
                self.update_info(f"  User adjusted: {len(self.selected_peaks)} peaks, {len(self.bg_points)} BG points\n")
            
            self.update_info("  ✓ Manual verification completed\n")
            
            # Step 3: Fit peaks
            self.update_info("  Step 3: Fitting peaks...\n")
            self.fit_peaks()
            QApplication.processEvents()
            
            if not self.fitted or self.fit_results is None:
                self.update_info("  ❌ Peak fitting failed!\n")
                # Save current state for next file even if fitting failed (only bg points)
                self._previous_peaks = None  # Don't retain peaks
                self._previous_bg_points = self.bg_points.copy()
                return False
            
            self.update_info(f"  ✓ Successfully fitted {len(self.fit_results)} peaks\n")
            
            # Step 4: Save results (if enabled)
            if self.batch_auto_save and self.filepath:
                self.update_info("  Step 4: Saving results...\n")
                save_dir = os.path.dirname(self.filepath)
                csv_path, _ = self._save_results_to_dir(save_dir)
                self.batch_csv_paths.append(csv_path)
                self.update_info(f"  ✓ Results saved to {save_dir}\n")
            
            # Save current state for next file (only bg_points, not peaks)
            self._previous_peaks = None  # Don't retain peaks - auto-detect each time
            self._previous_bg_points = self.bg_points.copy()
            
            # Also save the complete file state for navigation preservation
            self._save_file_state()
            
            self.update_info("  ✅ File processed successfully!\n")
            return True
            
        except Exception as e:
            import traceback
            self.update_info(f"  ❌ Error: {str(e)}\n")
            self.update_info(f"  {traceback.format_exc()}\n")
            return False
    
    def _show_verification_dialog(self):
        """Show verification dialog for manual review before fitting (non-modal for interaction)"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Manual Verification - Review Peaks and Background")
        dialog.setMinimumSize(420, 320)
        dialog.setMaximumSize(450, 400)  # Fix size to prevent flickering
        dialog.setStyleSheet("QDialog { background-color: #E6F3FF; }")
        
        # Set non-modal to allow interaction with plot area
        dialog.setModal(False)
        # Remove WindowStaysOnTopHint to reduce flickering
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(8)
        
        # Message label with dynamic update capability
        self._verification_msg_label = QLabel()
        self._verification_msg_label.setStyleSheet("""
            QLabel {
                background-color: #E6F3FF;
                color: #2C5282;
                font-weight: bold;
                font-size: 8.5pt;
                padding: 5px;
            }
        """)
        self._verification_msg_label.setWordWrap(True)
        layout.addWidget(self._verification_msg_label)
        
        # Function to update message dynamically
        def update_message():
            msg_text = (
                f"File: {self.filename}\n\n"
                f"Current state:\n"
                f"  • {len(self.selected_peaks)} peak(s)\n"
                f"  • {len(self.bg_points)} background point(s)\n\n"
                "You can interact with the plot:\n"
                "  • Click on plot to add/remove peaks\n"
                "  • Use 'Select BG Points' to add background points\n"
                "  • Use 'Clear BG' to reset background\n"
                "  • Use 'Undo' to revert last action\n\n"
                "Shortcuts: Enter=Continue | Space=Skip | Esc=Stop"
            )
            self._verification_msg_label.setText(msg_text)
        
        # Set initial message
        update_message()
        
        # Store update function for external calls
        self._update_verification_msg = update_message
        
        # User action storage
        user_action = {"action": "continue"}
        
        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("QFrame { background-color: #E6F3FF; }")
        btn_layout = QVBoxLayout(btn_frame)
        btn_layout.setSpacing(5)
        
        def continue_fitting():
            user_action["action"] = "continue"
            dialog.accept()
        
        def skip_file():
            user_action["action"] = "skip"
            dialog.accept()
        
        def stop_batch():
            user_action["action"] = "stop"
            dialog.accept()
        
        btn_continue = QPushButton("✓ Continue to Fit")
        btn_continue.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                font-weight: bold;
                font-size: 8.5pt;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_continue.clicked.connect(continue_fitting)
        btn_layout.addWidget(btn_continue)
        
        btn_skip = QPushButton("⏭ Skip This File")
        btn_skip.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B;
                color: white;
                font-weight: bold;
                font-size: 8.5pt;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #D97706; }
        """)
        btn_skip.clicked.connect(skip_file)
        btn_layout.addWidget(btn_skip)
        
        btn_stop = QPushButton("⏹ Stop Batch")
        btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                font-weight: bold;
                font-size: 8.5pt;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        btn_stop.clicked.connect(stop_batch)
        btn_layout.addWidget(btn_stop)
        
        layout.addWidget(btn_frame)
        
        # Keyboard shortcuts
        btn_continue.setShortcut(Qt.Key.Key_Return)
        btn_skip.setShortcut(Qt.Key.Key_Space)
        btn_stop.setShortcut(Qt.Key.Key_Escape)
        
        # Store dialog reference for potential updates
        self._verification_dialog = dialog
        
        # Show non-modal dialog to allow plot interaction
        dialog.show()
        
        # Wait for user action using event loop
        from PyQt6.QtCore import QEventLoop
        loop = QEventLoop()
        dialog.finished.connect(loop.quit)
        loop.exec()
        
        # Clean up
        self._verification_dialog = None
        
        return user_action["action"]
    
    def _merge_batch_csv_files(self):
        """Merge all batch CSV files into a single summary file with blank lines between files"""
        if not self.batch_csv_paths:
            return
        
        import pandas as pd
        
        # Get output directory from first CSV file
        output_dir = os.path.dirname(self.batch_csv_paths[0])
        summary_filename = "batch_summary.csv"
        summary_path = os.path.join(output_dir, summary_filename)
        
        # Read and merge CSV files with blank lines between different files
        total_peaks = 0
        with open(summary_path, 'w', newline='', encoding='utf-8') as outfile:
            import csv
            writer = None
            
            for idx, csv_path in enumerate(self.batch_csv_paths):
                try:
                    df = pd.read_csv(csv_path)
                    # Add source filename column
                    source_name = os.path.basename(csv_path).replace('_fit_results.csv', '').replace('_peaks.csv', '')
                    df.insert(0, 'Source_File', source_name)
                    
                    # Write header only for first file
                    if writer is None:
                        writer = csv.writer(outfile)
                        writer.writerow(df.columns.tolist())
                    
                    # Write data rows
                    for _, row in df.iterrows():
                        writer.writerow(row.tolist())
                        total_peaks += 1
                    
                    # Add blank line between different files (except after last file)
                    if idx < len(self.batch_csv_paths) - 1:
                        writer.writerow([])
                    
                except Exception as e:
                    print(f"Warning: Failed to read {csv_path}: {e}")
                    continue
        
        self.update_info(f"All CSV files merged into: {summary_filename}\n")
        QMessageBox.information(self, "CSV Merged", 
                              f"All batch results merged into:\n{summary_filename}\n\n"
                              f"Location: {output_dir}\n"
                              f"Total peaks: {total_peaks}")
    
    def _show_manual_adjustment_dialog(self):
        """Show dialog for manual adjustment during batch processing (lines 2399-2466)"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Manual Adjustment Needed")
        dialog.setMinimumSize(400, 250)
        dialog.setStyleSheet("QDialog { background-color: #FFF8DC; }")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Message
        msg = QLabel(
            "Auto-fitting failed for current file.\n\n"
            "You can now manually:\n"
            "• Click on peak positions\n"
            "• Adjust background points\n"
            "• Click 'Fit Peaks' button\n\n"
            "When ready, choose an action below:"
        )
        msg.setStyleSheet("""
            QLabel {
                background-color: #FFF8DC;
                color: #8B4513;
                font-weight: bold;
                font-size: 7.5pt;
            }
        """)
        layout.addWidget(msg)
        
        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("QFrame { background-color: #FFF8DC; }")
        btn_layout = QVBoxLayout(btn_frame)
        btn_layout.setSpacing(5)
        
        def continue_batch():
            self.batch_paused = False
            dialog.accept()
        
        def skip_current():
            self.batch_skip_current = True
            self.batch_paused = False
            dialog.accept()
        
        def stop_batch():
            self.batch_running = False
            self.batch_paused = False
            self.batch_stopped_by_user = True
            dialog.accept()
        
        btn_continue = QPushButton("Continue After Manual Fix")
        btn_continue.setStyleSheet("""
            QPushButton {
                background-color: #90EE90;
                color: #006400;
                font-weight: bold;
                font-size: 7.5pt;
                padding: 8px;
            }
            QPushButton:hover { background-color: #7FD77F; }
        """)
        btn_continue.clicked.connect(continue_batch)
        btn_layout.addWidget(btn_continue)
        
        btn_skip = QPushButton("Skip This File")
        btn_skip.setStyleSheet("""
            QPushButton {
                background-color: #FFD700;
                color: #8B4513;
                font-weight: bold;
                font-size: 7.5pt;
                padding: 8px;
            }
            QPushButton:hover { background-color: #FFC700; }
        """)
        btn_skip.clicked.connect(skip_current)
        btn_layout.addWidget(btn_skip)
        
        btn_stop = QPushButton("Stop Batch Processing")
        btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #FF6347;
                color: black;
                font-weight: bold;
                font-size: 7.5pt;
                padding: 8px;
            }
            QPushButton:hover { background-color: #FF4500; }
        """)
        btn_stop.clicked.connect(stop_batch)
        btn_layout.addWidget(btn_stop)
        
        layout.addWidget(btn_frame)
        
        dialog.exec()
    
    def _save_file_state(self):
        """Save current file state for navigation preservation"""
        if self.filepath is None:
            return
        
        # Create a deep copy of the current state
        state = {
            'x': self.x.copy() if self.x is not None else None,
            'y': self.y.copy() if self.y is not None else None,
            'y_original': self.y_original.copy() if self.y_original is not None else None,
            'filename': self.filename,
            'selected_peaks': self.selected_peaks.copy(),
            'bg_points': self.bg_points.copy(),
            'fitted': self.fitted,
            'fit_results': self.fit_results.copy() if self.fit_results else None,
            'fit_method': self.fit_method,
        }
        
        self._file_states[self.filepath] = state
    
    def _restore_file_state(self, filepath):
        """Restore file state if it exists"""
        if filepath not in self._file_states:
            return False
        
        state = self._file_states[filepath]
        
        # Restore data
        self.x = state['x'].copy() if state['x'] is not None else None
        self.y = state['y'].copy() if state['y'] is not None else None
        self.y_original = state['y_original'].copy() if state['y_original'] is not None else None
        self.filename = state['filename']
        self.filepath = filepath
        
        # Clear existing visual elements
        self.reset_peaks()
        self.clear_background()
        
        # Restore state variables
        self.selected_peaks = state['selected_peaks'].copy()
        self.bg_points = state['bg_points'].copy()
        self.fitted = state['fitted']
        self.fit_results = state['fit_results'].copy() if state['fit_results'] else None
        self.fit_method = state['fit_method']
        
        # Redraw the plot with all restored elements
        self.ax.clear()
        self.ax.plot(self.x, self.y, '-', color='#9370DB', linewidth=0.8, label='Data')
        self.ax.set_facecolor('#F4F6FB')
        self.ax.grid(True, alpha=0.3, linestyle='--', color='#D4A5D4')
        self.ax.set_xlabel('2theta (degree)', fontsize=13, color='black', fontname='Arial')
        self.ax.set_ylabel('Intensity', fontsize=13, color='black', fontname='Arial')
        
        # Restore peak markers (red dashed vertical lines only, no stars)
        for peak_idx in self.selected_peaks:
            if peak_idx < len(self.x):
                peak_x = self.x[peak_idx]
                vline = self.ax.axvline(x=peak_x, color='red', linestyle='--', linewidth=1.5, 
                                       alpha=0.7, zorder=11)
                self.peak_markers.append(vline)
                self.peak_texts.append(vline)
        
        # Restore background points (square markers)
        for bg_x, bg_y in self.bg_points:
            marker, = self.ax.plot(bg_x, bg_y, 's', color='#4169E1',
                                  markersize=6, markeredgecolor='white',
                                  markeredgewidth=1, zorder=5)
            text_obj = self.ax.text(bg_x, bg_y * 0.95, '',
                                   ha='center', fontsize=6, color='#4169E1',
                                   fontweight='bold', zorder=6)
            self.bg_markers.append((marker, text_obj))
        
        if len(self.bg_points) >= 2:
            self.update_bg_connect_line()
        
        # Restore fitted results if they exist
        if self.fitted and self.fit_results:
            # Re-fit to restore the visual fit lines
            # This is a simplified approach - we just call fit_peaks again
            # since we have the peaks and bg_points restored
            try:
                self.fit_peaks()
            except:
                # If re-fitting fails, just display peaks without fit
                pass
        
        # Set title
        if self.fitted:
            self.ax.set_title(f'{self.filename} - Fit Complete ({self.fit_method})',
                            fontsize=11, fontweight='bold', color='black', fontname='Arial')
        else:
            self.ax.set_title(f'{self.filename} | Click on peaks to select',
                            fontsize=11, color='black', fontname='Arial')
        
        # Set tick labels
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_fontname('Arial')
            label.set_color('black')
            label.set_fontsize(9)
        
        # Expand x-axis range
        x_range = self.x.max() - self.x.min()
        self.ax.set_xlim(self.x.min() - x_range * 0.05, self.x.max() + x_range * 0.05)
        self.fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.15)
        self.canvas.draw()
        
        # Update info
        file_info = f"File {self.current_file_index + 1}/{len(self.file_list)}: {self.filename}"
        self.status_label.setText(file_info)
        
        return True


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoFittingModule()
    window.setMinimumSize(1400, 850)
    window.show()
    sys.exit(app.exec())