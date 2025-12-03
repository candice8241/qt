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
        
        # Info panel (line 683)
        self._create_info_panel(main_layout)
    
    def _create_control_panel(self, parent_layout):
        """Create top control panel (lines 685-773)"""
        # Create frame (line 687)
        control_frame = QFrame()
        control_frame.setStyleSheet("QFrame { background-color: #E6D5F5; border-radius: 5px; }")
        control_frame.setFixedHeight(60)  # height=60 in original
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(5, 8, 5, 8)
        control_layout.setSpacing(5)
        
        # Button style (lines 691-697)
        btn_style = """
            QPushButton {
                background-color: #B19CD9;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                font-size: 10pt;
                min-width: 100px;
                min-height: 40px;
            }
            QPushButton:hover { background-color: #9370DB; }
            QPushButton:disabled { background-color: #CCCCCC; color: #666666; }
        """
        
        # Load File button (lines 699-702)
        self.btn_load = QPushButton("Load File")
        self.btn_load.setStyleSheet(btn_style)
        self.btn_load.clicked.connect(self.load_file)
        control_layout.addWidget(self.btn_load)
        
        # File navigation buttons (lines 704-717)
        nav_btn_style = btn_style.replace('min-width: 100px', 'min-width: 30px')
        
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
        self.btn_fit.setStyleSheet(btn_style.replace('#B19CD9', '#CE93D8'))
        self.btn_fit.clicked.connect(self.fit_peaks)
        self.btn_fit.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_fit)
        
        # Reset button (lines 724-727)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setStyleSheet(btn_style.replace('#B19CD9', '#FFB6C1'))
        self.btn_reset.clicked.connect(self.reset_peaks)
        self.btn_reset.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_reset)
        
        # Save Results button (lines 729-732)
        self.btn_save = QPushButton("Save Results")
        self.btn_save.setStyleSheet(btn_style.replace('#B19CD9', '#98FB98'))
        self.btn_save.clicked.connect(self.save_results)
        self.btn_save.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_save)
        
        # Clear Fit button (lines 734-737)
        self.btn_clear_fit = QPushButton("Clear Fit")
        self.btn_clear_fit.setStyleSheet(btn_style.replace('#B19CD9', '#FFA07A'))
        self.btn_clear_fit.clicked.connect(self.clear_fit)
        self.btn_clear_fit.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_clear_fit)
        
        # Undo button (lines 739-742)
        self.btn_undo = QPushButton("Undo")
        self.btn_undo.setStyleSheet(btn_style.replace('#B19CD9', '#DDA0DD'))
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
        self.btn_overlap_mode.setStyleSheet(btn_style.replace('#B19CD9', '#D8BFD8'))
        self.btn_overlap_mode.clicked.connect(self.toggle_overlap_mode)
        self.btn_overlap_mode.setEnabled(False)  # state=tk.DISABLED
        control_layout.addWidget(self.btn_overlap_mode)
        
        # Batch Auto Fit button (lines 755-758)
        # User says: "batch auto fit应该在最初就可以点"
        self.btn_batch_auto = QPushButton("Batch Auto Fit")
        self.btn_batch_auto.setStyleSheet(btn_style.replace('#B19CD9', '#ADD8E6'))
        self.btn_batch_auto.clicked.connect(self.batch_auto_fit)
        self.btn_batch_auto.setEnabled(True)  # User wants this ENABLED initially!
        control_layout.addWidget(self.btn_batch_auto)
        
        # Batch Settings button (lines 760-766)
        self.btn_batch_settings = QPushButton("⚙")
        self.btn_batch_settings.setStyleSheet(btn_style.replace('min-width: 100px', 'min-width: 30px').replace('#B19CD9', '#B0C4DE'))
        self.btn_batch_settings.clicked.connect(self.show_batch_settings)
        self.btn_batch_settings.setEnabled(True)  # state=tk.NORMAL
        control_layout.addWidget(self.btn_batch_settings)
        
        # Status label (lines 768-772)
        self.status_label = QLabel("Please load a file to start")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #9370DB;
                font-weight: bold;
                font-size: 11pt;
                background-color: #E6D5F5;
                padding: 5px;
            }
        """)
        self.status_label.setMinimumWidth(350)
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        parent_layout.addWidget(control_frame)
    
    # Placeholder for other methods - will continue in next part
    def _create_background_panel(self, parent_layout):
        """Create background fitting control panel"""
        pass  # TODO: Implement line by line from original
    
    def _create_smoothing_panel(self, parent_layout):
        """Create smoothing control panel"""
        pass  # TODO: Implement
    
    def _create_results_panel(self, parent_layout):
        """Create results display panel"""
        pass  # TODO: Implement
    
    def _create_plot_area(self, parent_layout):
        """Create main plot area"""
        pass  # TODO: Implement
    
    def _create_info_panel(self, parent_layout):
        """Create info panel"""
        pass  # TODO: Implement
    
    # Event handlers and other methods
    def load_file(self):
        pass  # TODO: Implement
    
    def prev_file(self):
        pass  # TODO: Implement
    
    def next_file(self):
        pass  # TODO: Implement
    
    def fit_peaks(self):
        pass  # TODO: Implement
    
    def reset_peaks(self):
        pass  # TODO: Implement
    
    def save_results(self):
        pass  # TODO: Implement
    
    def clear_fit(self):
        pass  # TODO: Implement
    
    def undo_action(self):
        pass  # TODO: Implement
    
    def auto_find_peaks(self):
        pass  # TODO: Implement
    
    def toggle_overlap_mode(self):
        pass  # TODO: Implement
    
    def batch_auto_fit(self):
        pass  # TODO: Implement
    
    def show_batch_settings(self):
        pass  # TODO: Implement


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoFittingModule()
    window.setMinimumSize(1400, 850)
    window.show()
    sys.exit(app.exec())
