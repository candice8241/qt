#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interactive Peak Fitting GUI - Qt Version

Allows users to:
- Load XRD data files
- Automatically detect peaks
- Manually add/remove peaks
- Adjust peak parameters interactively
- Fit peaks using Voigt or Pseudo-Voigt functions
- Export fitted results

@author: candicewang928@gmail.com
"""

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QLineEdit, QComboBox, QCheckBox, QTextEdit, QSlider,
                              QFileDialog, QMessageBox, QFrame, QGroupBox, QSplitter,
                              QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QDoubleValidator
from scipy.optimize import curve_fit
from scipy.signal import find_peaks, peak_widths, savgol_filter
from scipy.special import wofz
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import UnivariateSpline
from sklearn.cluster import DBSCAN
import os
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')


# ==================== Data Processing Module ====================
class DataProcessor:
    """Handles data smoothing and preprocessing operations"""

    @staticmethod
    def gaussian_smoothing(y, sigma=2):
        """
        Apply Gaussian smoothing to data.
        
        Parameters:
        -----------
        y : array
            Input data
        sigma : float
            Standard deviation for Gaussian kernel (higher = more smoothing)
        
        Returns:
        --------
        y_smooth : array
            Smoothed data
        """
        return gaussian_filter1d(y, sigma=sigma)

    @staticmethod
    def savgol_smoothing(y, window_length=11, polyorder=3):
        """
        Apply Savitzky-Golay smoothing to data.
        
        Parameters:
        -----------
        y : array
            Input data
        window_length : int
            Length of the filter window (must be odd)
        polyorder : int
            Order of the polynomial used to fit the samples
        
        Returns:
        --------
        y_smooth : array
            Smoothed data
        """
        # Ensure window_length is odd and not larger than data
        window_length = min(window_length, len(y))
        if window_length % 2 == 0:
            window_length -= 1
        if window_length < polyorder + 2:
            window_length = polyorder + 2
            if window_length % 2 == 0:
                window_length += 1
        
        return savgol_filter(y, window_length, polyorder)

    @staticmethod
    def moving_average_smoothing(y, window_size=5):
        """
        Apply moving average smoothing to data.
        
        Parameters:
        -----------
        y : array
            Input data
        window_size : int
            Size of moving window
        
        Returns:
        --------
        y_smooth : array
            Smoothed data
        """
        window_size = min(window_size, len(y))
        if window_size < 1:
            return y
        cumsum = np.cumsum(np.insert(y, 0, 0))
        return (cumsum[window_size:] - cumsum[:-window_size]) / float(window_size)

    @classmethod
    def apply_smoothing(cls, y, method='gaussian', **kwargs):
        """
        Apply smoothing to data using specified method.
        
        Parameters:
        -----------
        y : array
            Input data
        method : str
            'gaussian', 'savgol', or 'moving_average'
        **kwargs : dict
            Additional parameters for the smoothing method
        
        Returns:
        --------
        y_smooth : array
            Smoothed data
        """
        if method == 'gaussian':
            sigma = kwargs.get('sigma', 2)
            return cls.gaussian_smoothing(y, sigma=sigma)
        elif method == 'savgol':
            window_length = kwargs.get('window_length', 11)
            polyorder = kwargs.get('polyorder', 3)
            return cls.savgol_smoothing(y, window_length=window_length, polyorder=polyorder)
        elif method == 'moving_average':
            window_size = kwargs.get('window_size', 5)
            return cls.moving_average_smoothing(y, window_size=window_size)
        else:
            return y


# ==================== Peak Clustering Module ====================
class PeakClusterer:
    """Handles peak grouping using DBSCAN clustering"""

    @staticmethod
    def cluster_peaks(peak_positions, eps=None, min_samples=1):
        """
        Use DBSCAN density clustering to group nearby peaks.
        
        Parameters:
        -----------
        peak_positions : array
            1D array of peak positions (e.g., 2theta values)
        eps : float, optional
            Maximum distance between two peaks to be in the same group.
            If None, automatically estimated from data.
        min_samples : int
            Minimum number of peaks to form a cluster.
        
        Returns:
        --------
        labels : array
            Cluster labels for each peak (-1 means noise/outlier)
        n_clusters : int
            Number of clusters found
        """
        if len(peak_positions) == 0:
            return np.array([]), 0
        
        if len(peak_positions) == 1:
            return np.array([0]), 1
        
        # Reshape for sklearn
        X = np.array(peak_positions).reshape(-1, 1)
        
        # Auto-estimate eps if not provided
        if eps is None:
            sorted_pos = np.sort(peak_positions)
            if len(sorted_pos) > 1:
                distances = np.diff(sorted_pos)
                eps = np.median(distances) * 1.5
            else:
                eps = 1.0
        
        # Perform clustering
        clustering = DBSCAN(eps=eps, min_samples=min_samples)
        labels = clustering.fit_predict(X)
        
        # Count clusters (excluding noise label -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        return labels, n_clusters


# ==================== Background Fitting Module ====================
class BackgroundFitter:
    """Handles background fitting operations"""

    @staticmethod
    def fit_global_background(x, y, peak_indices, method='spline',
                             smoothing_factor=None, poly_order=3):
        """
        Fit a global smooth background to the data, excluding peak regions.
        
        Parameters:
        -----------
        x : array
            X data (2theta values)
        y : array
            Y data (intensity values)
        peak_indices : list
            Indices of detected peaks
        method : str
            'spline', 'piecewise', or 'polynomial'
        smoothing_factor : float, optional
            Smoothing factor for spline
        poly_order : int, optional
            Order of polynomial for 'polynomial' method
        
        Returns:
        --------
        background : array
            Background values at each x point
        bg_points : list of tuples
            (x, y) coordinates of background anchor points
        """
        if len(peak_indices) == 0:
            return np.full_like(y, np.median(y)), []
        
        sorted_peaks = sorted(peak_indices)
        bg_x, bg_y = [], []
        
        # Left edge
        first_peak = sorted_peaks[0]
        left_region_end = max(0, first_peak - 5)
        if left_region_end > 0:
            left_min_idx = np.argmin(y[:left_region_end+1])
            bg_x.append(x[left_min_idx])
            bg_y.append(y[left_min_idx])
        else:
            bg_x.append(x[0])
            bg_y.append(y[0])
        
        # Between peaks
        for i in range(len(sorted_peaks) - 1):
            idx1 = sorted_peaks[i]
            idx2 = sorted_peaks[i + 1]
            if idx2 > idx1 + 1:
                between_region = y[idx1:idx2+1]
                min_local = np.argmin(between_region)
                min_idx = idx1 + min_local
                bg_x.append(x[min_idx])
                bg_y.append(y[min_idx])
        
        # Right edge
        last_peak = sorted_peaks[-1]
        right_region_start = min(len(x) - 1, last_peak + 5)
        if right_region_start < len(x) - 1:
            right_min_idx = right_region_start + np.argmin(y[right_region_start:])
            bg_x.append(x[right_min_idx])
            bg_y.append(y[right_min_idx])
        else:
            bg_x.append(x[-1])
            bg_y.append(y[-1])
        
        bg_x = np.array(bg_x)
        bg_y = np.array(bg_y)
        
        # Sort and remove duplicates
        sort_idx = np.argsort(bg_x)
        bg_x = bg_x[sort_idx]
        bg_y = bg_y[sort_idx]
        
        unique_mask = np.concatenate([[True], np.diff(bg_x) > 0])
        bg_x = bg_x[unique_mask]
        bg_y = bg_y[unique_mask]
        
        bg_points = list(zip(bg_x, bg_y))
        
        if len(bg_x) < 2:
            return np.full_like(y, np.mean(bg_y) if len(bg_y) > 0 else np.median(y)), bg_points
        
        # Apply fitting method
        if method == 'polynomial':
            try:
                max_order = min(poly_order, len(bg_x) - 1, 5)
                coeffs = np.polyfit(bg_x, bg_y, max_order)
                poly = np.poly1d(coeffs)
                background = poly(x)
                background = np.clip(background, None, np.max(y))
            except Exception:
                background = np.interp(x, bg_x, bg_y)
        elif method == 'spline' and len(bg_x) >= 4:
            if smoothing_factor is None:
                smoothing_factor = len(bg_x) * 1.0
            try:
                spline = UnivariateSpline(bg_x, bg_y, s=smoothing_factor, k=3)
                background = spline(x)
                background = np.clip(background, None, np.max(y))
            except Exception:
                background = np.interp(x, bg_x, bg_y)
        else:
            background = np.interp(x, bg_x, bg_y)
        
        return background, bg_points

    @staticmethod
    def find_auto_background_points(x, y, n_points=10, window_size=50):
        """
        Automatically find background anchor points across the data range.
        
        Parameters:
        -----------
        x : array
            X data
        y : array
            Y data
        n_points : int
            Target number of background points to find
        window_size : int
            Size of local window for finding minima
        
        Returns:
        --------
        bg_points : list of tuples
            List of (x, y) coordinates for background points
        """
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
            seg_x = x[indices]
            
            # Find local minimum in segment
            min_idx_local = np.argmin(seg_y)
            min_idx_global = indices[min_idx_local]
            
            # Use windowed minimum for better stability
            window_start = max(0, min_idx_global - window_size // 2)
            window_end = min(len(y), min_idx_global + window_size // 2)
            
            window_y = y[window_start:window_end]
            window_x = x[window_start:window_end]
            
            if len(window_y) > 0:
                lowest_indices = np.argsort(window_y)[:max(1, len(window_y) // 10)]
                avg_x = np.mean(window_x[lowest_indices])
                avg_y = np.mean(window_y[lowest_indices])
                bg_points.append((avg_x, avg_y))
        
        return bg_points


# ==================== Peak Profile Module ====================
class PeakProfile:
    """Peak profile mathematical functions"""

    @staticmethod
    def pseudo_voigt(x, amplitude, center, sigma, gamma, eta):
        """Pseudo-Voigt: eta*Lorentzian + (1-eta)*Gaussian"""
        gaussian = amplitude * np.exp(-(x - center)**2 / (2 * sigma**2)) / (sigma * np.sqrt(2 * np.pi))
        lorentzian = amplitude * gamma**2 / ((x - center)**2 + gamma**2) / (np.pi * gamma)
        return eta * lorentzian + (1 - eta) * gaussian

    @staticmethod
    def voigt(x, amplitude, center, sigma, gamma):
        """Voigt profile using Faddeeva function"""
        z = ((x - center) + 1j * gamma) / (sigma * np.sqrt(2))
        return amplitude * np.real(wofz(z)) / (sigma * np.sqrt(2 * np.pi))

    @staticmethod
    def calculate_fwhm(sigma, gamma, eta):
        """Calculate FWHM from Pseudo-Voigt parameters"""
        fwhm_g = 2.355 * sigma
        fwhm_l = 2 * gamma
        return eta * fwhm_l + (1 - eta) * fwhm_g

    @staticmethod
    def calculate_area(amplitude, sigma, gamma, eta):
        """Calculate integrated area"""
        area_g = amplitude * sigma * np.sqrt(2 * np.pi)
        area_l = amplitude * np.pi * gamma
        return eta * area_l + (1 - eta) * area_g

    @staticmethod
    def estimate_fwhm(x, y, peak_idx, smooth=True):
        """
        Robust FWHM estimation using interpolation
        
        Parameters:
        -----------
        x : array
            X data
        y : array
            Y data
        peak_idx : int
            Index of peak position
        smooth : bool
            Whether to smooth data before estimation
        
        Returns:
        --------
        fwhm : float
            Full width at half maximum
        baseline : float
            Estimated baseline value
        """
        if smooth and len(y) > 11:
            try:
                y_smooth = savgol_filter(y, min(11, len(y)//2*2+1), 3)
            except:
                y_smooth = y
        else:
            y_smooth = y
        
        peak_height = y_smooth[peak_idx]
        
        # Estimate local baseline from edges
        n_edge = max(3, len(y) // 10)
        baseline = (np.mean(y_smooth[:n_edge]) + np.mean(y_smooth[-n_edge:])) / 2
        
        half_max = (peak_height + baseline) / 2
        
        # Find left half-max point with interpolation
        left_x = x[0]
        for j in range(peak_idx, 0, -1):
            if y_smooth[j] <= half_max:
                if y_smooth[j+1] != y_smooth[j]:
                    frac = (half_max - y_smooth[j]) / (y_smooth[j+1] - y_smooth[j])
                    left_x = x[j] + frac * (x[j+1] - x[j])
                else:
                    left_x = x[j]
                break
        
        # Find right half-max point with interpolation
        right_x = x[-1]
        for j in range(peak_idx, len(y_smooth)-1):
            if y_smooth[j] <= half_max:
                if y_smooth[j-1] != y_smooth[j]:
                    frac = (half_max - y_smooth[j]) / (y_smooth[j-1] - y_smooth[j])
                    right_x = x[j] - frac * (x[j] - x[j-1])
                else:
                    right_x = x[j]
                break
        
        fwhm = abs(right_x - left_x)
        
        # Sanity check
        dx = np.mean(np.diff(x))
        if fwhm < dx * 2:
            fwhm = dx * 8
        
        return fwhm, baseline


# ==================== Peak Detector Module ====================
class PeakDetector:
    """Automatic peak detection"""

    @staticmethod
    def auto_find_peaks(x, y):
        """
        Automatically find all peaks in the data using scipy.signal.find_peaks
        
        Parameters:
        -----------
        x : array
            X data
        y : array
            Y data
        
        Returns:
        --------
        peaks : array
            Indices of detected peaks
        """
        # Smooth data for better peak detection
        if len(y) > 15:
            window_length = min(15, len(y) // 2 * 2 + 1)
            y_smooth = savgol_filter(y, window_length, 3)
        else:
            y_smooth = y
        
        # Calculate data statistics
        y_range = np.max(y) - np.min(y)
        dx = np.mean(np.diff(x))
        
        # Adaptive parameters
        height_threshold = np.min(y) + y_range * 0.05
        prominence_threshold = y_range * 0.02
        min_distance = max(5, int(0.1 / dx)) if dx > 0 else 5
        
        # Find peaks
        peaks, properties = find_peaks(
            y_smooth,
            height=height_threshold,
            prominence=prominence_threshold,
            distance=min_distance,
            width=2
        )
        
        if len(peaks) == 0:
            # Try with less strict parameters
            peaks, properties = find_peaks(
                y_smooth,
                height=np.min(y) + y_range * 0.02,
                prominence=y_range * 0.01,
                distance=3
            )
        
        # Additional filtering
        filtered_peaks = []
        for idx in peaks:
            window = 40
            left = max(0, idx - window)
            right = min(len(y), idx + window)
            
            edge_n = max(3, (right - left) // 10)
            local_baseline = (np.mean(y[left:left+edge_n]) +
                             np.mean(y[right-edge_n:right])) / 2
            
            if y[idx] > local_baseline * 1.1:
                filtered_peaks.append(idx)
        
        return np.array(filtered_peaks)


class InteractiveFittingGUI(QWidget):
    """
    Interactive GUI for peak fitting with real-time visualization
    
    Features:
    - Load XRD data files (.xy, .dat, .chi)
    - Automatic peak detection with adjustable parameters
    - Manual peak selection by clicking
    - Interactive peak parameter adjustment
    - Voigt and Pseudo-Voigt fitting
    - Background subtraction options
    - Export fitted results to CSV
    """

    def __init__(self, parent=None):
        """Initialize the GUI"""
        super().__init__(parent)
        
        # Hide during construction to prevent flash
        self.setVisible(False)
        
        # Make this widget fill the available space in parent container
        # Remove standalone window flags to embed in main window
        # Do NOT use WA_DeleteOnClose to prevent deletion errors on re-opening
        
        # Set size constraints for proper display and prevent overflow
        self.setMinimumSize(1200, 700)
        self.setMaximumWidth(1600)  # Set right boundary to prevent UI overflow
        
        # Pre-allocate size to avoid flashing on first show
        self.resize(1200, 700)

        # Colorful vibrant palette (matching Image 1)
        self.palette = {
            'background': '#D4CCFF',  # Light purple background
            'panel_bg': '#E8E4FF',
            'primary': '#B794F6',      # Purple
            'success': '#7FD857',      # Bright green
            'warning': '#FFB84D',      # Orange
            'danger': '#FF8A80',       # Coral/pink
            'info': '#64D2FF',         # Cyan/bright blue
            'purple': '#C77DFF',       # Light purple
            'text_dark': '#4A148C',    # Dark purple
            'text_light': '#7B1FA2',   # Medium purple
            'text_cyan': '#00BCD4',    # Cyan
            'text_pink': '#FF4081',    # Pink
            'text_red': '#F44336',     # Red
            'text_yellow': '#FFEB3B',  # Yellow
            'border': '#B794F6',
        }

        # Set main window background to colorful gradient
        self.setStyleSheet("QWidget { background-color: #D4CCFF; }")

        # Data storage
        self.x_data = None
        self.y_data = None
        self.y_data_original = None  # Store original unsmoothed data
        self.y_smooth = None
        self.y_display = None  # Currently displayed data (may be smoothed)
        self.peaks = []  # List of peak indices
        self.peak_params = []  # List of fitted parameters for each peak
        self.fit_method = "pseudo-voigt"
        self.current_file = ""
        
        # Background fitting
        self.bg_points = []  # Background anchor points
        self.background = None  # Fitted background array
        self.bg_selection_mode = False
        
        # File navigation
        self.file_list = []
        self.current_file_index = -1
        
        # Undo history
        self.undo_stack = []
        self.max_undo_steps = 20
        
        # Fitting functions
        self.fitting_functions = {
            'voigt': self.voigt,
            'pseudo-voigt': self.pseudo_voigt
        }

        # Setup UI (while hidden)
        self.setup_ui()
        
        # Now ready to be shown
        # Note: parent will control visibility via show()

    def setup_ui(self):
        """Setup the user interface - compact layout"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(3, 3, 3, 3)  # More compact: 5 → 3
        main_layout.setSpacing(2)  # More compact: 3 → 2

        # 1. Top control panel - all main buttons
        self.setup_control_panel(main_layout)

        # 2. Background panel
        self.setup_background_panel(main_layout)

        # 3. Smoothing panel
        self.setup_smoothing_panel(main_layout)

        # 4. Results panel with header and table
        self.setup_results_panel(main_layout)

        # 5. Plot area (takes remaining space)
        self.setup_plot_area(main_layout)

        # Info panel removed - no longer needed

    def setup_control_panel(self, parent_layout):
        """Setup top control panel - compact and uniform"""
        control_widget = QWidget()
        control_widget.setFixedHeight(45)  # More compact: 50 → 45
        control_widget.setAutoFillBackground(True)
        # Changed color, removed bottom border
        control_widget.setStyleSheet("QWidget { background-color: #E8D5F0; }")
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(6, 3, 6, 3)  # More compact: 6,4 → 6,3
        control_layout.setSpacing(2)  # More compact: 3 → 2

        # Compact button style with smaller fonts and widths
        btn_style = """
            QPushButton {
                font-family: Arial;
                font-size: 8pt;
                font-weight: bold;
                border: 2px solid #9575CD;
                border-radius: 4px;
                padding: 4px 6px;
                min-width: 50px;
            }
            QPushButton:hover {
                opacity: 0.85;
            }
            QPushButton:pressed {
                padding: 5px 5px 3px 7px;
            }
        """

        # Load File button - compact
        load_btn = QPushButton("Load")
        load_btn.setFixedWidth(55)
        load_btn.setStyleSheet(btn_style + f"background-color: #C77DFF; color: black; font-weight: bold;")
        load_btn.clicked.connect(self.load_data_file)
        control_layout.addWidget(load_btn)

        # Navigation buttons - compact
        prev_btn = QPushButton("◀")
        prev_btn.setFixedWidth(30)
        prev_btn.setStyleSheet(btn_style + f"background-color: #A5D8FF; color: black; min-width: 20px;")
        prev_btn.clicked.connect(self.prev_file)
        control_layout.addWidget(prev_btn)

        next_btn = QPushButton("▶")
        next_btn.setFixedWidth(30)
        next_btn.setStyleSheet(btn_style + f"background-color: #A5D8FF; color: black; min-width: 20px;")
        next_btn.clicked.connect(self.next_file)
        control_layout.addWidget(next_btn)

        # Fit Peaks button - compact
        fit_btn = QPushButton("Fit")
        fit_btn.setFixedWidth(50)
        fit_btn.setStyleSheet(btn_style + f"background-color: #D0BFFF; color: black;")
        fit_btn.clicked.connect(self.fit_all_peaks)
        control_layout.addWidget(fit_btn)

        # Reset button - compact
        reset_btn = QPushButton("Reset")
        reset_btn.setFixedWidth(55)
        reset_btn.setStyleSheet(btn_style + f"background-color: #FFC9A8; color: black;")
        reset_btn.clicked.connect(self.clear_peaks)
        control_layout.addWidget(reset_btn)

        # Save Results button - compact
        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(50)
        save_btn.setStyleSheet(btn_style + f"background-color: #A8E6CF; color: black;")
        save_btn.clicked.connect(self.export_results)
        control_layout.addWidget(save_btn)

        # Clear Fit button - compact
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(50)
        clear_btn.setStyleSheet(btn_style + f"background-color: #FFB3BA; color: black;")
        clear_btn.clicked.connect(self.clear_peaks)
        control_layout.addWidget(clear_btn)

        # Undo button - compact
        undo_btn = QPushButton("Undo")
        undo_btn.setFixedWidth(50)
        undo_btn.setStyleSheet(btn_style + f"background-color: #E8D5F5; color: black;")
        undo_btn.clicked.connect(self.undo_action)
        control_layout.addWidget(undo_btn)

        # Auto Find button - compact
        auto_btn = QPushButton("Auto")
        auto_btn.setFixedWidth(50)
        auto_btn.setStyleSheet(btn_style + f"background-color: #B9DEFF; color: black;")
        auto_btn.clicked.connect(self.auto_detect_peaks)
        control_layout.addWidget(auto_btn)

        # Overlap button - compact with toggle state (default ON)
        self.overlap_btn = QPushButton("Overlap")
        self.overlap_btn.setFixedWidth(60)
        self.overlap_mode_enabled = True  # Default ON like peak_fitting.py
        # Set initial active state
        active_style = btn_style + f"background-color: #4FC3F7; color: black; font-weight: bold;"
        self.overlap_btn.setStyleSheet(active_style)
        self.overlap_btn.clicked.connect(self.toggle_overlap_mode)
        control_layout.addWidget(self.overlap_btn)

        # Batch Auto Fit button - compact
        batch_btn = QPushButton("Batch")
        batch_btn.setFixedWidth(50)
        batch_btn.setStyleSheet(btn_style + f"background-color: #D5D5FF; color: black;")
        batch_btn.clicked.connect(self.show_batch_info)
        control_layout.addWidget(batch_btn)

        # Settings button (gear icon) - compact
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedWidth(30)
        settings_btn.setStyleSheet(btn_style + f"background-color: #F5F5F5; color: black; min-width: 20px; font-size: 12pt;")
        settings_btn.clicked.connect(self.show_settings_info)
        control_layout.addWidget(settings_btn)

        control_layout.addStretch()

        # Status label - adjusted for better visibility
        self.status_label = QLabel("Please load a file to start")
        self.status_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))  # Smaller font
        self.status_label.setStyleSheet(f"color: #4A148C; background: transparent; padding: 3px;")
        self.status_label.setMinimumWidth(250)  # Reduced width
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        control_layout.addWidget(self.status_label)

        parent_layout.addWidget(control_widget)

    def setup_background_panel(self, parent_layout):
        """Setup background panel - compact and uniform"""
        bg_widget = QWidget()
        bg_widget.setFixedHeight(45)  # More compact: 50 → 45
        bg_widget.setAutoFillBackground(True)
        bg_widget.setStyleSheet("QWidget { background-color: #E3F2FF; }")  # Light blue tint
        bg_layout = QHBoxLayout(bg_widget)
        bg_layout.setContentsMargins(6, 3, 6, 3)  # More compact: 8,5 → 6,3
        bg_layout.setSpacing(3)  # More compact: 4 → 3

        # Background label - compact font like control panel
        bg_label = QLabel("Background:")
        bg_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        bg_label.setStyleSheet(f"color: #00BCD4; background: transparent;")  # Cyan
        bg_layout.addWidget(bg_label)

        # Compact button style - match load row
        bg_btn_style = """
            QPushButton {
                font-family: Arial;
                font-size: 8pt;
                font-weight: bold;
                border: 2px solid #7CB9E8;
                border-radius: 4px;
                padding: 3px 6px;
                min-width: 50px;
            }
            QPushButton:hover {
                opacity: 0.85;
            }
            QPushButton:pressed {
                background-color: #4FC3F7 !important;
                border: 2px solid #29B6F6;
            }
        """

        # Select BG Points with toggle state
        self.select_bg_btn = QPushButton("Select BG Points")
        self.select_bg_btn.setStyleSheet(bg_btn_style + f"background-color: #A5D8FF; color: black;")
        self.select_bg_btn.clicked.connect(self.toggle_bg_selection)
        bg_layout.addWidget(self.select_bg_btn)

        # Subtract BG
        subtract_bg_btn = QPushButton("Subtract BG")
        subtract_bg_btn.setStyleSheet(bg_btn_style + f"background-color: #A8E6CF; color: black;")
        subtract_bg_btn.clicked.connect(self.subtract_background)
        self.background_cb = QCheckBox()  # Hidden for compatibility
        self.background_cb.setChecked(True)
        self.background_cb.hide()
        bg_layout.addWidget(subtract_bg_btn)

        # Clear BG
        clear_bg_btn = QPushButton("Clear BG")
        clear_bg_btn.setStyleSheet(bg_btn_style + f"background-color: #FFB3BA; color: black;")
        clear_bg_btn.clicked.connect(self.clear_background)
        bg_layout.addWidget(clear_bg_btn)

        # Auto Select BG
        auto_bg_btn = QPushButton("Auto Select BG")
        auto_bg_btn.setStyleSheet(bg_btn_style + f"background-color: #B9E5FF; color: black;")
        auto_bg_btn.clicked.connect(self.auto_select_background)
        bg_layout.addWidget(auto_bg_btn)

        bg_layout.addSpacing(10)

        # Fit Method - black text, compact font
        fit_label = QLabel("Fit Method:")
        fit_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        fit_label.setStyleSheet(f"color: black; background: transparent;")  # Black text
        bg_layout.addWidget(fit_label)

        self.method_combo = QComboBox()
        self.method_combo.addItems(['pseudo_voigt', 'voigt'])
        self.method_combo.setFont(QFont('Arial', 8))  # Smaller font
        self.method_combo.setFixedWidth(110)
        self.method_combo.setStyleSheet(f"""
            QComboBox {{ 
                padding: 3px; 
                color: black;
                background-color: white;
                border: 2px solid #B794F6;
                border-radius: 3px;
            }}
            QComboBox QAbstractItemView {{
                color: black;
                background-color: white;
            }}
        """)
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        bg_layout.addWidget(self.method_combo)

        bg_layout.addSpacing(6)  # More compact: 10 → 6

        # Overlap FWHM× - compact font
        overlap_label = QLabel("FWHM×:")  # Shortened label
        overlap_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        overlap_label.setStyleSheet(f"color: #7B1FA2; background: transparent;")  # Purple
        bg_layout.addWidget(overlap_label)

        self.overlap_entry = QLineEdit("5.0")
        self.overlap_entry.setFixedWidth(45)  # Smaller: 50 → 45
        self.overlap_entry.setFont(QFont('Arial', 8))  # Smaller font
        self.overlap_entry.setStyleSheet(f"""
            QLineEdit {{ 
                padding: 2px; 
                color: black;
                background-color: white;
                border: 2px solid #B794F6;
                border-radius: 3px;
            }}
        """)
        bg_layout.addWidget(self.overlap_entry)

        bg_layout.addSpacing(6)  # More compact: 10 → 6

        # Fit Window× - black text, compact font
        window_label = QLabel("Window×:")  # Shortened label
        window_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        window_label.setStyleSheet(f"color: black; background: transparent;")  # Black text
        bg_layout.addWidget(window_label)

        self.fit_window_entry = QLineEdit("1.1")
        self.fit_window_entry.setFixedWidth(45)  # Smaller: 50 → 45
        self.fit_window_entry.setFont(QFont('Arial', 8))  # Smaller font
        self.fit_window_entry.setStyleSheet(f"""
            QLineEdit {{ 
                padding: 2px; 
                color: black;
                background-color: white;
                border: 2px solid #B794F6;
                border-radius: 3px;
            }}
        """)
        bg_layout.addWidget(self.fit_window_entry)

        bg_layout.addStretch()  # Use stretch instead of fixed spacing

        # Coordinate label (right side) - show real-time coordinates
        self.coord_label = QLabel("")
        self.coord_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))  # Larger font (8->10)
        self.coord_label.setStyleSheet(f"color: #00BCD4; background: transparent;")  # Cyan
        self.coord_label.setMinimumWidth(180)  # Increased for larger font
        self.coord_label.setMaximumWidth(280)  # Increased for larger font
        self.coord_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.coord_label.setWordWrap(False)  # Prevent wrapping
        self.coord_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.coord_label.setVisible(True)  # Show for real-time display
        bg_layout.addWidget(self.coord_label)

        parent_layout.addWidget(bg_widget)

    def setup_smoothing_panel(self, parent_layout):
        """Setup smoothing panel - compact and uniform"""
        smooth_widget = QWidget()
        smooth_widget.setFixedHeight(45)  # More compact: 50 → 45
        smooth_widget.setAutoFillBackground(True)
        smooth_widget.setStyleSheet("QWidget { background-color: #F3E5FF; }")  # Light purple tint
        smooth_layout = QHBoxLayout(smooth_widget)
        smooth_layout.setContentsMargins(6, 3, 6, 3)  # More compact: 8,5 → 6,3
        smooth_layout.setSpacing(3)  # More compact: 4 → 3

        # Smoothing label - black text, compact font
        smooth_label = QLabel("Smoothing:")
        smooth_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        smooth_label.setStyleSheet(f"color: black; background: transparent;")  # Black text
        smooth_layout.addWidget(smooth_label)

        # Enable checkbox
        self.smoothing_enable_cb = QCheckBox("Enable")
        self.smoothing_enable_cb.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Smaller font
        self.smoothing_enable_cb.setStyleSheet(f"color: #4A148C; background: transparent;")
        smooth_layout.addWidget(self.smoothing_enable_cb)

        smooth_layout.addSpacing(6)  # More compact: 10 → 6

        # Method - compact font
        method_label = QLabel("Method:")
        method_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        method_label.setStyleSheet(f"color: #7B1FA2; background: transparent;")  # Purple
        smooth_layout.addWidget(method_label)

        self.smooth_method_combo = QComboBox()
        self.smooth_method_combo.addItems(['gaussian', 'savgol'])
        self.smooth_method_combo.setFont(QFont('Arial', 8))  # Smaller font
        self.smooth_method_combo.setFixedWidth(90)  # More compact: 100 → 90
        self.smooth_method_combo.setStyleSheet(f"""
            QComboBox {{ 
                padding: 2px; 
                color: black;
                background-color: white;
                border: 2px solid #B794F6;
                border-radius: 3px;
            }}
            QComboBox QAbstractItemView {{
                color: black;
                background-color: white;
            }}
        """)
        smooth_layout.addWidget(self.smooth_method_combo)

        smooth_layout.addSpacing(6)  # More compact: 10 → 6

        # Sigma - compact font
        sigma_label = QLabel("Sigma:")
        sigma_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        sigma_label.setStyleSheet(f"color: #4A148C; background: transparent;")
        smooth_layout.addWidget(sigma_label)

        self.sigma_entry = QLineEdit("2.0")
        self.sigma_entry.setFixedWidth(45)  # More compact: 50 → 45
        self.sigma_entry.setFont(QFont('Arial', 8))  # Smaller font
        self.sigma_entry.setStyleSheet(f"""
            QLineEdit {{ 
                padding: 2px; 
                color: black;
                background-color: white;
                border: 2px solid #B794F6;
                border-radius: 3px;
            }}
        """)
        smooth_layout.addWidget(self.sigma_entry)

        smooth_layout.addSpacing(6)  # More compact: 10 → 6

        # Window - black text, compact font
        window_label = QLabel("Window:")
        window_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        window_label.setStyleSheet(f"color: black; background: transparent;")  # Black text
        smooth_layout.addWidget(window_label)

        self.smooth_window_entry = QLineEdit("11")
        self.smooth_window_entry.setFixedWidth(45)  # More compact: 50 → 45
        self.smooth_window_entry.setFont(QFont('Arial', 8))  # Smaller font
        self.smooth_window_entry.setStyleSheet(f"""
            QLineEdit {{ 
                padding: 2px; 
                color: black;
                background-color: white;
                border: 2px solid #B794F6;
                border-radius: 3px;
            }}
        """)
        smooth_layout.addWidget(self.smooth_window_entry)

        smooth_layout.addSpacing(6)  # More compact: 10 → 6

        # Apply button - match load row style
        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: Arial;
                font-size: 8pt;
                font-weight: bold;
                background-color: #A8E6CF;
                color: black;
                border: 2px solid #7CB9A8;
                border-radius: 4px;
                padding: 3px 8px;
                min-width: 50px;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        apply_btn.clicked.connect(self.apply_smoothing_to_data)
        smooth_layout.addWidget(apply_btn)

        # Reset Data button - match load row style
        reset_data_btn = QPushButton("Reset")
        reset_data_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: Arial;
                font-size: 8pt;
                font-weight: bold;
                background-color: #FFB3BA;
                color: black;
                border: 2px solid #FF8A80;
                border-radius: 4px;
                padding: 3px 8px;
                min-width: 50px;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        reset_data_btn.clicked.connect(self.reset_to_original_data)
        smooth_layout.addWidget(reset_data_btn)

        smooth_layout.addStretch()

        parent_layout.addWidget(smooth_widget)

    def setup_results_panel(self, parent_layout):
        """Setup results panel - compact and uniform"""
        results_widget = QWidget()
        results_widget.setFixedHeight(110)  # More compact: 120 → 110
        results_widget.setAutoFillBackground(True)
        results_widget.setStyleSheet("QWidget { background-color: #FFF9DB; }")  # Light yellow tint
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(6, 3, 6, 3)  # More compact: 8,4 → 6,3
        results_layout.setSpacing(2)  # More compact: 3 → 2

        # Results label - compact font like load row
        results_label = QLabel("Fitting Results:")
        results_label.setFont(QFont('Arial', 8, QFont.Weight.Bold))  # Match load row font
        results_label.setStyleSheet(f"color: #FF6B00; background: transparent;")  # Orange
        results_layout.addWidget(results_label)

        # Results table
        self.peak_table = QTableWidget()
        self.peak_table.setColumnCount(8)
        self.peak_table.setHorizontalHeaderLabels([
            "Peak", "2theta", "FWHM", "Area", "Amplitude", "Sigma", "Gamma", "Eta"
        ])
        
        # Set column widths
        col_widths = [45, 90, 90, 90, 90, 75, 75, 55]
        for i, width in enumerate(col_widths):
            self.peak_table.setColumnWidth(i, width)
        
        self.peak_table.setFont(QFont('Arial', 8))
        self.peak_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: white;
                gridline-color: #FFD88D;
                border: 2px solid #FFD88D;
                color: #000000;
            }}
            QHeaderView::section {{
                background-color: #FFF4CC;
                color: #4A148C;
                font-weight: bold;
                font-family: Arial;
                font-size: 8pt;
                border: 1px solid #FFD88D;
                padding: 3px;
            }}
            QTableWidget::item {{
                color: #000000;
                padding: 2px;
            }}
        """)
        results_layout.addWidget(self.peak_table)

        parent_layout.addWidget(results_widget)

    def setup_plot_area(self, parent_layout):
        """Setup plot area - white background"""
        plot_widget = QWidget()
        plot_widget.setAutoFillBackground(True)
        plot_widget.setStyleSheet("QWidget { background-color: #FFFFFF; }")  # Changed to white
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(5, 5, 5, 5)
        plot_layout.setSpacing(2)

        # Create matplotlib figure
        self.fig = Figure(figsize=(12, 6), facecolor='#FFFFFF')  # Changed to white
        # Adjust margins: left margin reduced for plot area to extend left
        self.fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.12)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#FFFFFF')  # White plot area
        self.ax.grid(True, alpha=0.3, linestyle='--', color='#9575CD')
        # Set initial axis ranges to avoid flashing when loading data
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 1000)
        # Initial labels - consistent with loaded data
        self.ax.set_xlabel('2θ (degree)', fontsize=10, color='#4A148C', fontweight='normal')
        # Use labelpad to keep ylabel visible and at good position
        self.ax.set_ylabel('Intensity', fontsize=10, color='#4A148C', fontweight='normal', labelpad=18)
        self.ax.set_title('Left click: add | Right click: remove | Scroll: zoom',
                         fontsize=9, color='#7B1FA2', fontweight='normal')
        # Set tick label colors and size
        self.ax.tick_params(colors='#4A148C', which='both', labelsize=6)

        # Canvas
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)  # Add scroll zoom
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)  # Enable real-time coordinate display
        plot_layout.addWidget(self.canvas)

        # Toolbar removed - no longer needed

        parent_layout.addWidget(plot_widget)


    def on_mouse_move(self, event):
        """Display mouse coordinates with larger spacing"""
        if event.inaxes == self.ax and event.xdata is not None:
            # Larger spacing between 2theta and I
            self.coord_label.setText(f"2θ:{event.xdata:.3f}    I:{event.ydata:.1f}")
        else:
            self.coord_label.setText("")

    def on_scroll(self, event):
        """Handle mouse scroll for zooming"""
        if event.inaxes != self.ax:
            return
        
        # Get current axis limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Calculate zoom factor
        zoom_factor = 0.9 if event.button == 'up' else 1.1
        
        # Get click position
        xdata = event.xdata
        ydata = event.ydata
        
        # Calculate new limits centered on cursor
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        
        new_x_range = x_range * zoom_factor
        new_y_range = y_range * zoom_factor
        
        # Keep cursor position fixed
        x_ratio = (xdata - xlim[0]) / x_range if x_range > 0 else 0.5
        y_ratio = (ydata - ylim[0]) / y_range if y_range > 0 else 0.5
        
        new_xlim = [xdata - new_x_range * x_ratio, xdata + new_x_range * (1 - x_ratio)]
        new_ylim = [ydata - new_y_range * y_ratio, ydata + new_y_range * (1 - y_ratio)]
        
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw()

    def find_nearest_peak(self, idx, search_window=20):
        """Find nearest peak position within search window"""
        if self.y_data is None:
            return idx
        
        # Define search window
        left = max(0, idx - search_window)
        right = min(len(self.y_data), idx + search_window)
        
        # Find local maximum
        local_y = self.y_data[left:right]
        if len(local_y) > 0:
            local_max_idx = np.argmax(local_y)
            return left + local_max_idx
        
        return idx

    def find_nearest_minimum(self, idx, search_window=15):
        """Find nearest minimum position within search window"""
        if self.y_data is None:
            return idx
        
        # Define search window
        left = max(0, idx - search_window)
        right = min(len(self.y_data), idx + search_window)
        
        # Find local minimum
        local_y = self.y_data[left:right]
        if len(local_y) > 0:
            local_min_idx = np.argmin(local_y)
            return left + local_min_idx
        
        return idx

    def load_data_file(self):
        """Load XRD data file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select XRD Data File",
            "",
            "Data files (*.xy *.dat *.chi *.txt);;All files (*.*)"
        )

        if not filename:
            return

        try:
            # Try to load data
            with open(filename, encoding='latin1') as f:
                data = np.genfromtxt(f, comments="#")
            
            if data.shape[1] < 2:
                raise ValueError("File must have at least 2 columns")

            self.x_data = data[:, 0]
            self.y_data = data[:, 1]
            self.y_data_original = self.y_data.copy()
            self.y_smooth = savgol_filter(self.y_data, window_length=11, polyorder=2)
            self.y_display = self.y_data
            self.current_file = os.path.basename(filename)

            # Scan folder for file navigation
            self._scan_folder(filename)

            # Update status
            file_num_text = f"({self.current_file_index + 1}/{len(self.file_list)})" if self.file_list else ""
            self.status_label.setText(f"Loaded: {self.current_file} {file_num_text} ({len(self.x_data)} points)")

            # Clear previous peaks and background
            self.peaks = []
            self.peak_params = []
            self.bg_points = []
            self.background = None
            self.update_peak_table()
            
            # Plot data
            self.plot_data()

            # Remove the success dialog - no popup after loading

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data file:\n{str(e)}")

    def auto_detect_peaks(self):
        """Automatically detect peaks in the data"""
        if self.x_data is None or self.y_data is None:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        try:
            # Save state for undo
            self.save_state_to_undo()
            
            # Use the new PeakDetector class
            filtered_peaks = PeakDetector.auto_find_peaks(self.x_data, self.y_data)

            self.peaks = filtered_peaks.tolist()
            self.update_peak_table()
            self.plot_data()

            # Remove the success dialog - no popup after auto detection
            # Update status label instead
            self.status_label.setText(f"Detected {len(self.peaks)} peaks")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Peak detection failed:\n{str(e)}")

    def toggle_manual_selection(self, state):
        """Toggle manual peak selection mode"""
        if state == Qt.CheckState.Checked.value:
            self.status_label.setText("Manual selection enabled - click on peaks to add/remove")
        else:
            self.status_label.setText(f"Loaded: {self.current_file}")

    def on_plot_click(self, event):
        """Handle plot click for manual peak or background selection
        Left click: Add peak/BG point (with auto-correction)
        Right click: Remove peak/BG point
        """
        if event.inaxes != self.ax:
            return

        if self.x_data is None or self.y_data is None:
            return

        # Find nearest data point
        x_click = event.xdata
        y_click = event.ydata
        idx = np.argmin(np.abs(self.x_data - x_click))

        # Save state for undo
        self.save_state_to_undo()

        if self.bg_selection_mode:
            # Background point mode - auto-correct to local minimum
            remove_threshold = 0.02 * (self.x_data.max() - self.x_data.min())
            
            if event.button == 3:  # Right click - remove
                removed = False
                for i, (px, py) in enumerate(self.bg_points):
                    if abs(px - self.x_data[idx]) < remove_threshold:
                        self.bg_points.pop(i)
                        removed = True
                        break
            elif event.button == 1:  # Left click - add with auto-correction
                # Auto-correct to local minimum for background
                corrected_idx = self.find_nearest_minimum(idx, search_window=15)
                point = (self.x_data[corrected_idx], self.y_data[corrected_idx])
                
                # Check if not too close to existing point
                too_close = False
                for px, py in self.bg_points:
                    if abs(px - self.x_data[corrected_idx]) < remove_threshold:
                        too_close = True
                        break
                if not too_close:
                    self.bg_points.append(point)
                    self.bg_points.sort(key=lambda p: p[0])
            
            self.plot_data()
        else:
            # Peak mode - auto-correct to local maximum
            if event.button == 3:  # Right click - remove peak
                # Find nearest peak to remove
                remove_threshold = 0.02 * (self.x_data.max() - self.x_data.min())
                for peak_idx in self.peaks[:]:
                    if abs(self.x_data[peak_idx] - x_click) < remove_threshold:
                        self.peaks.remove(peak_idx)
                        break
            elif event.button == 1:  # Left click - add peak with auto-correction
                # Auto-correct to local maximum for peak
                corrected_idx = self.find_nearest_peak(idx, search_window=20)
                if corrected_idx not in self.peaks:
                    self.peaks.append(corrected_idx)
                    self.peaks.sort()

            self.update_peak_table()
            self.plot_data()

    def clear_peaks(self):
        """Clear all detected peaks and reset view"""
        self.save_state_to_undo()
        self.peaks = []
        self.peak_params = []
        self.update_peak_table()
        # Reset view to default initial state
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 1000)
        self.plot_data()

    def on_method_changed(self):
        """Handle fitting method change"""
        method_text = self.method_combo.currentText()
        self.fit_method = method_text.lower()

    def voigt(self, x, amplitude, center, sigma, gamma):
        """Voigt profile"""
        z = ((x - center) + 1j * gamma) / (sigma * np.sqrt(2))
        return amplitude * np.real(wofz(z)) / (sigma * np.sqrt(2 * np.pi))

    def pseudo_voigt(self, x, amplitude, center, sigma, gamma, eta):
        """Pseudo-Voigt profile"""
        gaussian = amplitude * np.exp(-(x - center)**2 / (2 * sigma**2)) / (sigma * np.sqrt(2 * np.pi))
        lorentzian = amplitude * gamma**2 / ((x - center)**2 + gamma**2) / (np.pi * gamma)
        return eta * lorentzian + (1 - eta) * gaussian

    def fit_all_peaks(self):
        """Fit all detected peaks - automatically handle overlapping peaks with multi-peak fitting"""
        if not self.peaks:
            QMessageBox.warning(self, "Warning", "No peaks detected! Please detect peaks first.")
            return

        self.peak_params = []
        
        # Step 1: Estimate FWHM for all peaks to determine overlaps
        peak_fwhms = []
        for peak_idx in self.peaks:
            try:
                fwhm, _ = PeakProfile.estimate_fwhm(self.x_data, self.y_data, peak_idx)
                peak_fwhms.append(fwhm)
            except:
                # Fallback FWHM if estimation fails
                peak_fwhms.append(0.5)
        
        # Step 2: Group overlapping peaks using distance-based clustering
        peak_groups = self._group_overlapping_peaks(self.peaks, peak_fwhms)
        
        # Step 3: Fit each group (single peak or multi-peak)
        for group in peak_groups:
            if len(group) == 1:
                # Single peak - fit independently
                self._fit_single_peak(group[0])
            else:
                # Multiple overlapping peaks - fit together
                self._fit_multi_peaks_group(group)
        
        self.update_peak_table()
        self.plot_data()
        # Update status label
        n_fitted = len([p for p in self.peak_params if p is not None])
        n_groups = len(peak_groups)
        multi_groups = len([g for g in peak_groups if len(g) > 1])
        if multi_groups > 0:
            self.status_label.setText(f"Fitted {n_fitted} peaks ({multi_groups} multi-peak groups)")
        else:
            self.status_label.setText(f"Fitted {n_fitted} peaks")
    
    def _group_overlapping_peaks(self, peaks, fwhms):
        """Group overlapping peaks based on their positions and FWHM"""
        if len(peaks) == 0:
            return []
        
        # Get overlap threshold from UI
        try:
            overlap_mult = float(self.overlap_entry.text())
        except:
            overlap_mult = 1.5
        
        # Convert to sorted list with positions
        peak_data = [(self.x_data[idx], idx, fwhm) for idx, fwhm in zip(peaks, fwhms)]
        peak_data.sort(key=lambda x: x[0])  # Sort by position
        
        groups = []
        current_group = [peak_data[0][1]]  # Start with first peak index
        current_end = peak_data[0][0] + overlap_mult * peak_data[0][2]  # Position + overlap_mult*FWHM
        
        for i in range(1, len(peak_data)):
            pos, idx, fwhm = peak_data[i]
            peak_start = pos - overlap_mult * fwhm
            
            # Check if this peak overlaps with current group
            if peak_start <= current_end:
                # Overlapping - add to current group
                current_group.append(idx)
                # Extend the end boundary
                current_end = max(current_end, pos + overlap_mult * fwhm)
            else:
                # Not overlapping - start new group
                groups.append(current_group)
                current_group = [idx]
                current_end = pos + overlap_mult * fwhm
        
        # Add last group
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _fit_single_peak(self, peak_idx):
        """Fit a single peak independently"""
        try:
            # Get peak width and apply fit window multiplier from UI
            results_half = peak_widths(self.y_data, [peak_idx], rel_height=0.5)
            width_pts = results_half[0][0] if len(results_half[0]) > 0 else 40
            
            # Apply fit window multiplier from UI
            try:
                fit_window_mult = float(self.fit_window_entry.text())
            except:
                fit_window_mult = 3.0
            
            window = int(width_pts * fit_window_mult)
            window = max(20, min(window, 200))

            # Extract local region
            left = max(0, peak_idx - window)
            right = min(len(self.x_data), peak_idx + window)
            x_local = self.x_data[left:right]
            y_local = self.y_data[left:right]

            # Background subtraction
            if self.background_cb.isChecked():
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
            else:
                y_fit_input = y_local
                background = np.zeros_like(y_local)

            # Initial guess
            amplitude_guess = np.max(y_fit_input)
            center_guess = x_local[np.argmax(y_fit_input)]
            sigma_guess = np.std(x_local) / 5
            gamma_guess = sigma_guess

            # Fit
            if self.fit_method == "voigt":
                p0 = [amplitude_guess, center_guess, sigma_guess, gamma_guess]
                bounds = ([0, x_local.min(), 0, 0], [np.inf, x_local.max(), np.inf, np.inf])
                popt, _ = curve_fit(self.voigt, x_local, y_fit_input, p0=p0, bounds=bounds, maxfev=10000)
                params = {'amplitude': popt[0], 'center': popt[1], 'sigma': popt[2], 
                         'gamma': popt[3], 'eta': None, 'background': background}
            else:  # pseudo-voigt
                p0 = [amplitude_guess, center_guess, sigma_guess, gamma_guess, 0.5]
                bounds = ([0, x_local.min(), 0, 0, 0], [np.inf, x_local.max(), np.inf, np.inf, 1.0])
                popt, _ = curve_fit(self.pseudo_voigt, x_local, y_fit_input, p0=p0, bounds=bounds, maxfev=10000)
                params = {'amplitude': popt[0], 'center': popt[1], 'sigma': popt[2], 
                         'gamma': popt[3], 'eta': popt[4], 'background': background}

            params['x_range'] = (x_local.min(), x_local.max())
            params['x_local'] = x_local
            params['y_local'] = y_local
            self.peak_params.append(params)

        except Exception as e:
            print(f"Failed to fit peak at index {peak_idx}: {e}")
            self.peak_params.append(None)
    
    def _fit_multi_peaks_group(self, peak_indices):
        """Fit multiple overlapping peaks together"""
        try:
            # Define fitting region for entire group
            min_peak_idx = min(peak_indices)
            max_peak_idx = max(peak_indices)
            
            # Get average width for window estimation
            avg_width = 40
            try:
                results_half = peak_widths(self.y_data, peak_indices, rel_height=0.5)
                if len(results_half[0]) > 0:
                    avg_width = np.mean(results_half[0])
            except:
                pass
            
            # Apply fit window multiplier from UI
            try:
                fit_window_mult = float(self.fit_window_entry.text())
            except:
                fit_window_mult = 3.0
            
            window = int(avg_width * fit_window_mult * 0.8)  # Slightly smaller for multi-peak
            window = max(40, min(window, 250))
            
            # Extract local region covering all peaks in group
            left = max(0, min_peak_idx - window)
            right = min(len(self.x_data), max_peak_idx + window)
            x_local = self.x_data[left:right]
            y_local = self.y_data[left:right]
            
            # Background subtraction
            if self.background_cb.isChecked():
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
            else:
                y_fit_input = y_local
                background = np.zeros_like(y_local)
            
            # Multi-peak fitting function
            def multi_peak_func(x, *params):
                """Sum of multiple peaks"""
                n_peaks = len(peak_indices)
                result = np.zeros_like(x)
                
                if self.fit_method == "voigt":
                    # 4 parameters per peak
                    for i in range(n_peaks):
                        amplitude = params[i*4]
                        center = params[i*4 + 1]
                        sigma = params[i*4 + 2]
                        gamma = params[i*4 + 3]
                        result += self.voigt(x, amplitude, center, sigma, gamma)
                else:  # pseudo-voigt
                    # 5 parameters per peak
                    for i in range(n_peaks):
                        amplitude = params[i*5]
                        center = params[i*5 + 1]
                        sigma = params[i*5 + 2]
                        gamma = params[i*5 + 3]
                        eta = params[i*5 + 4]
                        result += self.pseudo_voigt(x, amplitude, center, sigma, gamma, eta)
                
                return result
            
            # Initial guess for all peaks in group
            p0 = []
            bounds_lower = []
            bounds_upper = []
            
            for peak_idx in peak_indices:
                # Find local peak position in extracted region
                local_peak_idx = peak_idx - left
                if local_peak_idx < 0 or local_peak_idx >= len(y_fit_input):
                    local_peak_idx = np.argmax(y_fit_input)
                
                amplitude_guess = max(y_fit_input[local_peak_idx], np.max(y_fit_input) / len(peak_indices))
                center_guess = x_local[local_peak_idx]
                sigma_guess = np.std(x_local) / (5 * len(peak_indices))
                gamma_guess = sigma_guess
                
                if self.fit_method == "voigt":
                    p0.extend([amplitude_guess, center_guess, sigma_guess, gamma_guess])
                    bounds_lower.extend([0, x_local.min(), 0, 0])
                    bounds_upper.extend([np.inf, x_local.max(), np.inf, np.inf])
                else:  # pseudo-voigt
                    p0.extend([amplitude_guess, center_guess, sigma_guess, gamma_guess, 0.5])
                    bounds_lower.extend([0, x_local.min(), 0, 0, 0])
                    bounds_upper.extend([np.inf, x_local.max(), np.inf, np.inf, 1.0])
            
            # Fit all peaks together
            popt, _ = curve_fit(multi_peak_func, x_local, y_fit_input, 
                               p0=p0, bounds=(bounds_lower, bounds_upper), maxfev=20000)
            
            # Store parameters for each peak
            n_peaks = len(peak_indices)
            if self.fit_method == "voigt":
                for i in range(n_peaks):
                    params = {
                        'amplitude': popt[i*4],
                        'center': popt[i*4 + 1],
                        'sigma': popt[i*4 + 2],
                        'gamma': popt[i*4 + 3],
                        'eta': None,
                        'background': background,
                        'x_range': (x_local.min(), x_local.max()),
                        'x_local': x_local,
                        'y_local': y_local,
                        'is_multi_peak': True
                    }
                    self.peak_params.append(params)
            else:  # pseudo-voigt
                for i in range(n_peaks):
                    params = {
                        'amplitude': popt[i*5],
                        'center': popt[i*5 + 1],
                        'sigma': popt[i*5 + 2],
                        'gamma': popt[i*5 + 3],
                        'eta': popt[i*5 + 4],
                        'background': background,
                        'x_range': (x_local.min(), x_local.max()),
                        'x_local': x_local,
                        'y_local': y_local,
                        'is_multi_peak': True
                    }
                    self.peak_params.append(params)
            
        except Exception as e:
            print(f"Failed to fit multi-peak group: {e}")
            # Add None for each peak in failed group
            for _ in peak_indices:
                self.peak_params.append(None)
    
    def fit_all_peaks_old(self):
        """Old single peak fitting method - kept for reference"""
        if not self.peaks:
            QMessageBox.warning(self, "Warning", "No peaks detected! Please detect peaks first.")
            return

        self.peak_params = []
        
        # Single peak fitting mode
        for peak_idx in self.peaks:
            try:
                # Get peak width
                results_half = peak_widths(self.y_data, [peak_idx], rel_height=0.5)
                width_pts = results_half[0][0] if len(results_half[0]) > 0 else 40
                window = int(width_pts * 1.5)
                window = max(20, min(window, 100))

                # Extract local region
                left = max(0, peak_idx - window)
                right = min(len(self.x_data), peak_idx + window)
                x_local = self.x_data[left:right]
                y_local = self.y_data[left:right]

                # Background subtraction
                if self.background_cb.isChecked():
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
                else:
                    y_fit_input = y_local
                    background = np.zeros_like(y_local)

                # Initial guess
                amplitude_guess = np.max(y_fit_input)
                center_guess = x_local[np.argmax(y_fit_input)]
                sigma_guess = np.std(x_local) / 5
                gamma_guess = sigma_guess

                # Fit
                if self.fit_method == "voigt":
                    p0 = [amplitude_guess, center_guess, sigma_guess, gamma_guess]
                    bounds = ([0, x_local.min(), 0, 0], [np.inf, x_local.max(), np.inf, np.inf])
                    popt, _ = curve_fit(self.voigt, x_local, y_fit_input, p0=p0, bounds=bounds, maxfev=10000)
                    params = {'amplitude': popt[0], 'center': popt[1], 'sigma': popt[2], 
                             'gamma': popt[3], 'eta': None, 'background': background}
                else:  # pseudo-voigt
                    p0 = [amplitude_guess, center_guess, sigma_guess, gamma_guess, 0.5]
                    bounds = ([0, x_local.min(), 0, 0, 0], [np.inf, x_local.max(), np.inf, np.inf, 1.0])
                    popt, _ = curve_fit(self.pseudo_voigt, x_local, y_fit_input, p0=p0, bounds=bounds, maxfev=10000)
                    params = {'amplitude': popt[0], 'center': popt[1], 'sigma': popt[2], 
                             'gamma': popt[3], 'eta': popt[4], 'background': background}

                params['x_range'] = (x_local.min(), x_local.max())
                params['x_local'] = x_local
                params['y_local'] = y_local
                self.peak_params.append(params)

            except Exception as e:
                print(f"Failed to fit peak at index {peak_idx}: {e}")
                self.peak_params.append(None)

        self.plot_data()
        self.status_label.setText(f"Fitted {len([p for p in self.peak_params if p is not None])} peaks")
    
    def fit_multi_peaks_old(self):
        """Fit overlapping peaks together using multi-peak fitting"""
        # Group peaks by cluster label
        unique_labels = set(self.peak_cluster_labels)
        
        for label in unique_labels:
            # Get peaks in this cluster
            cluster_indices = [i for i, l in enumerate(self.peak_cluster_labels) if l == label]
            cluster_peaks = [self.peaks[i] for i in cluster_indices]
            
            if len(cluster_peaks) == 0:
                continue
            
            try:
                # Define fitting region for entire cluster
                min_peak_idx = min(cluster_peaks)
                max_peak_idx = max(cluster_peaks)
                
                # Get average width for window estimation
                avg_width = 40
                try:
                    results_half = peak_widths(self.y_data, cluster_peaks, rel_height=0.5)
                    if len(results_half[0]) > 0:
                        avg_width = np.mean(results_half[0])
                except:
                    pass
                
                window = int(avg_width * 2)
                window = max(40, min(window, 200))
                
                # Extract local region covering all peaks in cluster
                left = max(0, min_peak_idx - window)
                right = min(len(self.x_data), max_peak_idx + window)
                x_local = self.x_data[left:right]
                y_local = self.y_data[left:right]
                
                # Background subtraction
                if self.background_cb.isChecked():
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
                else:
                    y_fit_input = y_local
                    background = np.zeros_like(y_local)
                
                # Multi-peak fitting function
                def multi_peak_func(x, *params):
                    """Sum of multiple pseudo-voigt peaks"""
                    n_peaks = len(cluster_peaks)
                    result = np.zeros_like(x)
                    
                    if self.fit_method == "voigt":
                        # 4 parameters per peak: amplitude, center, sigma, gamma
                        for i in range(n_peaks):
                            amplitude = params[i*4]
                            center = params[i*4 + 1]
                            sigma = params[i*4 + 2]
                            gamma = params[i*4 + 3]
                            result += self.voigt(x, amplitude, center, sigma, gamma)
                    else:  # pseudo-voigt
                        # 5 parameters per peak: amplitude, center, sigma, gamma, eta
                        for i in range(n_peaks):
                            amplitude = params[i*5]
                            center = params[i*5 + 1]
                            sigma = params[i*5 + 2]
                            gamma = params[i*5 + 3]
                            eta = params[i*5 + 4]
                            result += self.pseudo_voigt(x, amplitude, center, sigma, gamma, eta)
                    
                    return result
                
                # Initial guess for all peaks in cluster
                p0 = []
                bounds_lower = []
                bounds_upper = []
                
                for peak_idx in cluster_peaks:
                    # Find local peak position in extracted region
                    local_peak_idx = peak_idx - left
                    if local_peak_idx < 0 or local_peak_idx >= len(y_fit_input):
                        local_peak_idx = np.argmax(y_fit_input)
                    
                    amplitude_guess = max(y_fit_input[local_peak_idx], np.max(y_fit_input) / len(cluster_peaks))
                    center_guess = x_local[local_peak_idx]
                    sigma_guess = np.std(x_local) / (5 * len(cluster_peaks))
                    gamma_guess = sigma_guess
                    
                    if self.fit_method == "voigt":
                        p0.extend([amplitude_guess, center_guess, sigma_guess, gamma_guess])
                        bounds_lower.extend([0, x_local.min(), 0, 0])
                        bounds_upper.extend([np.inf, x_local.max(), np.inf, np.inf])
                    else:  # pseudo-voigt
                        p0.extend([amplitude_guess, center_guess, sigma_guess, gamma_guess, 0.5])
                        bounds_lower.extend([0, x_local.min(), 0, 0, 0])
                        bounds_upper.extend([np.inf, x_local.max(), np.inf, np.inf, 1.0])
                
                # Fit all peaks together
                popt, _ = curve_fit(multi_peak_func, x_local, y_fit_input, 
                                   p0=p0, bounds=(bounds_lower, bounds_upper), maxfev=20000)
                
                # Store parameters for each peak
                n_peaks = len(cluster_peaks)
                if self.fit_method == "voigt":
                    for i in range(n_peaks):
                        params = {
                            'amplitude': popt[i*4],
                            'center': popt[i*4 + 1],
                            'sigma': popt[i*4 + 2],
                            'gamma': popt[i*4 + 3],
                            'eta': None,
                            'background': background,
                            'x_range': (x_local.min(), x_local.max()),
                            'x_local': x_local,
                            'y_local': y_local,
                            'is_multi_peak': True,
                            'cluster_label': label
                        }
                        self.peak_params.append(params)
                else:  # pseudo-voigt
                    for i in range(n_peaks):
                        params = {
                            'amplitude': popt[i*5],
                            'center': popt[i*5 + 1],
                            'sigma': popt[i*5 + 2],
                            'gamma': popt[i*5 + 3],
                            'eta': popt[i*5 + 4],
                            'background': background,
                            'x_range': (x_local.min(), x_local.max()),
                            'x_local': x_local,
                            'y_local': y_local,
                            'is_multi_peak': True,
                            'cluster_label': label
                        }
                        self.peak_params.append(params)
                
            except Exception as e:
                print(f"Failed to fit cluster {label}: {e}")
                # Add None for each peak in failed cluster
                for _ in cluster_peaks:
                    self.peak_params.append(None)
        
        self.plot_data()
        self.status_label.setText(f"Multi-peak fitted {len([p for p in self.peak_params if p is not None])} peaks")

    def plot_data(self):
        """Plot data with peaks, background points, and fits"""
        if self.x_data is None or self.y_data is None:
            return

        # Save current view limits before clearing
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        # Check if this is first load (default limits) or user has zoomed/panned
        is_default_view = (xlim == (0, 100) and ylim == (0, 1000))
        has_custom_limits = xlim != (0, 1) and ylim != (0, 1) and not is_default_view

        self.ax.clear()

        # Plot raw data
        self.ax.plot(self.x_data, self.y_data, 'k-', linewidth=1, label='Raw Data', alpha=0.7)

        # Plot background points if any - small square, darker blue
        if self.bg_points:
            bg_x = [p[0] for p in self.bg_points]
            bg_y = [p[1] for p in self.bg_points]
            # Changed to darker blue square, smaller size (reduced from 4 to 3)
            self.ax.plot(bg_x, bg_y, 's', color='#4682B4', markersize=3, label=f'BG Points ({len(self.bg_points)})', alpha=0.8)
            
            # Plot background line if we have points
            if len(bg_x) > 1:
                bg_line = np.interp(self.x_data, bg_x, bg_y)
                self.ax.plot(self.x_data, bg_line, '--', color='#4682B4', linewidth=1.5, label='BG Fit', alpha=0.5)

        # Plot detected peaks - use 'v' (downward triangle) marker
        if self.peaks:
            peak_x = self.x_data[self.peaks]
            peak_y = self.y_data[self.peaks]
            # Using cross marker with red color and thinner lines
            self.ax.plot(peak_x, peak_y, '+', color='red', markersize=7, markeredgewidth=1.2,
                        linestyle='', label=f'Detected Peaks ({len(self.peaks)})')

        # Plot fitted curves - handle multi-peak groups specially
        if self.peak_params:
            # Group peaks by their shared x_range to identify multi-peak groups
            plotted_groups = {}
            
            for i, params in enumerate(self.peak_params):
                if params is None:
                    continue

                x_local = params['x_local']
                y_local = params['y_local']
                background = params['background']
                x_range = params['x_range']
                is_multi = params.get('is_multi_peak', False)
                
                x_smooth = np.linspace(x_local.min(), x_local.max(), 500)
                
                # Calculate individual peak fit
                if self.fit_method == "voigt":
                    y_fit = self.voigt(x_smooth, params['amplitude'], params['center'], 
                                      params['sigma'], params['gamma'])
                else:
                    y_fit = self.pseudo_voigt(x_smooth, params['amplitude'], params['center'],
                                             params['sigma'], params['gamma'], params['eta'])

                # Calculate background for this region
                if self.background_cb.isChecked():
                    bg_left_y = background[0]
                    bg_left_x = x_local[0]
                    slope = (background[-1] - background[0]) / (x_local[-1] - x_local[0] + 1e-10)
                    bg_smooth = bg_left_y + slope * (x_smooth - bg_left_x)
                else:
                    bg_smooth = np.zeros_like(x_smooth)
                
                # For multi-peak groups, collect all components and plot sum
                if is_multi:
                    group_key = (x_range[0], x_range[1])
                    if group_key not in plotted_groups:
                        plotted_groups[group_key] = {
                            'x_smooth': x_smooth,
                            'components': [],
                            'bg': bg_smooth
                        }
                    plotted_groups[group_key]['components'].append(y_fit)
                    
                    # Plot individual peak component (without background, dashed)
                    self.ax.plot(x_smooth, y_fit + bg_smooth, '--', color='#FF6B6B', linewidth=0.8, 
                               alpha=0.5)
                else:
                    # Single peak - plot directly
                    y_full = y_fit + bg_smooth
                    self.ax.plot(x_smooth, y_full, '-', color='red', linewidth=1.2, 
                               alpha=0.8)
            
            # Plot sum of multi-peak groups
            for group_key, group_data in plotted_groups.items():
                x_smooth = group_data['x_smooth']
                y_sum = np.sum(group_data['components'], axis=0) + group_data['bg']
                self.ax.plot(x_smooth, y_sum, '-', color='red', linewidth=1.5, 
                           label=f'Multi-peak fit', alpha=0.9)

        # Apply consistent styling to axes (same for loaded and unloaded state)
        self.ax.set_facecolor('#FFFFFF')  # White plot area
        self.ax.set_xlabel('2θ (degree)', fontsize=10, color='#4A148C', fontweight='normal')
        # Use labelpad to keep ylabel visible and at good position
        self.ax.set_ylabel('Intensity', fontsize=10, color='#4A148C', fontweight='normal', labelpad=18)
        # Title: show filename if loaded, otherwise show instructions
        title_text = self.current_file if self.current_file else 'Left click: add | Right click: remove | Scroll: zoom'
        self.ax.set_title(title_text, fontsize=9, color='#7B1FA2', fontweight='normal')
        # Legend removed as per user request
        self.ax.grid(True, alpha=0.3, linestyle='--', color='#9575CD')
        
        # Colorful tick labels
        self.ax.tick_params(colors='#4A148C', which='both', labelsize=6, pad=4)
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_color('#4A148C')

        # Restore previous view limits if they existed (don't reset zoom/pan)
        # Or auto-fit to data if this is default view
        if has_custom_limits:
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
        elif is_default_view:
            # First time loading data - auto-fit
            self.ax.autoscale(enable=True, axis='both')

        # Don't use tight_layout - keep fixed margins for consistent axis label positions
        self.canvas.draw()

    def update_peak_table(self):
        """Update peak table with current peaks and fitted parameters"""
        if not self.peak_params:
            # Only show detected peaks without fit parameters
            self.peak_table.setRowCount(len(self.peaks))
            for i, peak_idx in enumerate(self.peaks):
                self.peak_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                position = self.x_data[peak_idx]
                self.peak_table.setItem(i, 1, QTableWidgetItem(f"{position:.4f}"))
                # Leave other columns empty
                for col in range(2, 8):
                    self.peak_table.setItem(i, col, QTableWidgetItem(""))
        else:
            # Show fitted parameters
            self.peak_table.setRowCount(len(self.peak_params))
            for i, params in enumerate(self.peak_params):
                if params is None:
                    continue

                # Peak number
                self.peak_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

                # 2theta (center)
                self.peak_table.setItem(i, 1, QTableWidgetItem(f"{params['center']:.4f}"))

                # FWHM - calculate using both sigma and gamma
                if params['eta'] is not None:
                    # Pseudo-Voigt: weighted average of Gaussian and Lorentzian FWHM
                    fwhm_g = 2.355 * params['sigma']
                    fwhm_l = 2 * params['gamma']
                    fwhm = params['eta'] * fwhm_l + (1 - params['eta']) * fwhm_g
                else:
                    # Voigt: approximation formula
                    fwhm_g = 2.355 * params['sigma']
                    fwhm_l = 2 * params['gamma']
                    fwhm = 0.5346 * fwhm_l + np.sqrt(0.2166 * fwhm_l**2 + fwhm_g**2)
                self.peak_table.setItem(i, 2, QTableWidgetItem(f"{fwhm:.4f}"))

                # Area - integrate the fitted peak
                if params['eta'] is not None:
                    # Pseudo-Voigt: weighted average of Gaussian and Lorentzian areas
                    area_g = params['amplitude'] * params['sigma'] * np.sqrt(2 * np.pi)
                    area_l = params['amplitude'] * np.pi * params['gamma']
                    area = params['eta'] * area_l + (1 - params['eta']) * area_g
                else:
                    # Voigt: sum of Gaussian and Lorentzian contributions
                    area = params['amplitude'] * params['sigma'] * np.sqrt(2 * np.pi)
                self.peak_table.setItem(i, 3, QTableWidgetItem(f"{area:.2f}"))

                # Amplitude
                self.peak_table.setItem(i, 4, QTableWidgetItem(f"{params['amplitude']:.2f}"))

                # Sigma
                self.peak_table.setItem(i, 5, QTableWidgetItem(f"{params['sigma']:.4f}"))

                # Gamma
                self.peak_table.setItem(i, 6, QTableWidgetItem(f"{params['gamma']:.4f}"))

                # Eta (only for pseudo-voigt)
                if params['eta'] is not None:
                    self.peak_table.setItem(i, 7, QTableWidgetItem(f"{params['eta']:.4f}"))
                else:
                    self.peak_table.setItem(i, 7, QTableWidgetItem(""))

    def export_results(self):
        """Export fitted results to CSV"""
        if not self.peak_params:
            QMessageBox.warning(self, "Warning", "No fitted peaks to export!")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Results",
            f"{os.path.splitext(self.current_file)[0]}_fitted.csv",
            "CSV files (*.csv)"
        )

        if not filename:
            return

        try:
            results = []
            for i, params in enumerate(self.peak_params):
                if params is None:
                    continue

                result = {
                    'Peak #': i + 1,
                    'Center (2θ)': params['center'],
                    'Amplitude': params['amplitude'],
                    'Sigma': params['sigma'],
                    'Gamma': params['gamma'],
                }
                
                if params['eta'] is not None:
                    result['Eta'] = params['eta']
                
                results.append(result)

            df = pd.DataFrame(results)
            df.to_csv(filename, index=False)

            QMessageBox.information(self, "Success", f"Results exported to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export results:\n{str(e)}")

    def apply_smoothing_to_data(self):
        """Apply smoothing to the data"""
        if self.y_data_original is None or self.x_data is None:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return
        
        try:
            if not self.smoothing_enable_cb.isChecked():
                QMessageBox.information(self, "Info", "Smoothing is not enabled. Please check 'Enable' first.")
                return
            
            method = self.smooth_method_combo.currentText()
            
            if method == 'gaussian':
                sigma = float(self.sigma_entry.text())
                self.y_data = DataProcessor.gaussian_smoothing(self.y_data_original, sigma=sigma)
            elif method == 'savgol':
                window = int(self.smooth_window_entry.text())
                self.y_data = DataProcessor.savgol_smoothing(self.y_data_original, window_length=window, polyorder=3)
            elif method == 'moving_average':
                window = int(self.smooth_window_entry.text())
                self.y_data = DataProcessor.moving_average_smoothing(self.y_data_original, window_size=window)
                # Pad to original length
                if len(self.y_data) < len(self.y_data_original):
                    pad_len = len(self.y_data_original) - len(self.y_data)
                    self.y_data = np.concatenate([self.y_data, self.y_data[-1] * np.ones(pad_len)])
            
            self.y_display = self.y_data
            self.plot_data()
            self.status_label.setText(f"Smoothing applied: {method}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply smoothing:\n{str(e)}")

    def reset_to_original_data(self):
        """Reset data to original unsmoothed version"""
        if self.y_data_original is None:
            QMessageBox.warning(self, "Warning", "No original data to reset to!")
            return
        
        self.y_data = self.y_data_original.copy()
        self.y_display = self.y_data
        self.plot_data()
        self.status_label.setText("Data reset to original")

    def toggle_bg_selection(self):
        """Toggle background selection mode"""
        self.bg_selection_mode = not self.bg_selection_mode
        
        # Update button color based on state
        bg_btn_style = """
            QPushButton {
                font-family: Arial;
                font-size: 8pt;
                font-weight: bold;
                border: 2px solid #7CB9E8;
                border-radius: 4px;
                padding: 3px 6px;
                min-width: 50px;
            }
            QPushButton:hover {
                opacity: 0.85;
            }
            QPushButton:pressed {
                background-color: #4FC3F7 !important;
                border: 2px solid #29B6F6;
            }
        """
        
        if self.bg_selection_mode:
            # Active state - darker color
            self.select_bg_btn.setStyleSheet(bg_btn_style + f"background-color: #1976D2; color: white; font-weight: bold;")
            self.status_label.setText("Background selection mode ON - Click to add BG points")
        else:
            # Inactive state - lighter color
            self.select_bg_btn.setStyleSheet(bg_btn_style + f"background-color: #A5D8FF; color: black;")
            self.status_label.setText(f"Loaded: {self.current_file}")

    def subtract_background(self):
        """Subtract fitted background from data"""
        if self.x_data is None or self.y_data is None:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return
        
        if len(self.bg_points) < 2:
            QMessageBox.warning(self, "Warning", "Please select at least 2 background points first!")
            return
        
        try:
            # Extract bg points coordinates
            bg_x = np.array([p[0] for p in self.bg_points])
            bg_y = np.array([p[1] for p in self.bg_points])
            
            # Interpolate background
            background = np.interp(self.x_data, bg_x, bg_y)
            self.background = background
            
            # Subtract background
            self.y_data = self.y_data - background
            self.y_data = np.maximum(self.y_data, 0)  # Ensure non-negative
            
            self.plot_data()
            self.status_label.setText(f"Background subtracted using {len(self.bg_points)} points")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to subtract background:\n{str(e)}")

    def clear_background(self):
        """Clear background points and reset data"""
        self.bg_points = []
        self.background = None
        
        if self.y_data_original is not None:
            self.y_data = self.y_data_original.copy()
        
        self.plot_data()
        self.status_label.setText("Background cleared")

    def auto_select_background(self):
        """Automatically select background points"""
        if self.x_data is None or self.y_data is None:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return
        
        try:
            # Find background points
            bg_points = BackgroundFitter.find_auto_background_points(
                self.x_data, self.y_data, n_points=10, window_size=50
            )
            
            self.bg_points = bg_points
            self.plot_data()
            self.status_label.setText(f"Auto-selected {len(bg_points)} background points")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to auto-select background:\n{str(e)}")

    def _scan_folder(self, filepath):
        """Scan folder for compatible data files"""
        directory = os.path.dirname(filepath)
        basename = os.path.basename(filepath)
        
        try:
            all_files = os.listdir(directory)
            # Filter for compatible extensions
            data_files = [f for f in all_files if f.endswith(('.xy', '.dat', '.chi', '.txt'))]
            data_files.sort()
            
            # Create full paths
            self.file_list = [os.path.join(directory, f) for f in data_files]
            
            # Find current file index
            if filepath in self.file_list:
                self.current_file_index = self.file_list.index(filepath)
            else:
                self.current_file_index = 0
                
        except Exception as e:
            print(f"Error scanning folder: {e}")
            self.file_list = [filepath]
            self.current_file_index = 0

    def prev_file(self):
        """Load previous file in directory"""
        if not self.file_list or self.current_file_index < 0:
            QMessageBox.information(self, "Info", "No file list available. Please load a file first.")
            return
        
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self.load_file_by_path(self.file_list[self.current_file_index])
        else:
            QMessageBox.information(self, "Info", "Already at first file")

    def next_file(self):
        """Load next file in directory"""
        if not self.file_list or self.current_file_index < 0:
            QMessageBox.information(self, "Info", "No file list available. Please load a file first.")
            return
        
        if self.current_file_index < len(self.file_list) - 1:
            self.current_file_index += 1
            self.load_file_by_path(self.file_list[self.current_file_index])
        else:
            QMessageBox.information(self, "Info", "Already at last file")

    def load_file_by_path(self, filepath):
        """Load a data file by its path"""
        try:
            # Try to load data
            with open(filepath, encoding='latin1') as f:
                data = np.genfromtxt(f, comments="#")
            
            if data.shape[1] < 2:
                raise ValueError("File must have at least 2 columns")

            self.x_data = data[:, 0]
            self.y_data = data[:, 1]
            self.y_data_original = self.y_data.copy()
            self.y_smooth = savgol_filter(self.y_data, window_length=11, polyorder=2)
            self.y_display = self.y_data
            self.current_file = os.path.basename(filepath)

            # Update status
            self.status_label.setText(f"Loaded: {self.current_file} ({len(self.x_data)} points)")

            # Clear previous peaks and background
            self.peaks = []
            self.peak_params = []
            self.bg_points = []
            self.background = None
            self.update_peak_table()
            
            # Plot data
            self.plot_data()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data file:\n{str(e)}")

    def save_state_to_undo(self):
        """Save current state to undo stack"""
        state = {
            'peaks': self.peaks.copy(),
            'peak_params': self.peak_params.copy() if self.peak_params else [],
            'bg_points': self.bg_points.copy(),
            'background': self.background.copy() if self.background is not None else None,
            'y_data': self.y_data.copy() if self.y_data is not None else None,
        }
        
        self.undo_stack.append(state)
        
        # Limit undo stack size
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)

    def undo_action(self):
        """Undo last action"""
        if not self.undo_stack:
            QMessageBox.information(self, "Info", "Nothing to undo")
            return
        
        # Restore previous state
        state = self.undo_stack.pop()
        
        self.peaks = state['peaks']
        self.peak_params = state['peak_params']
        self.bg_points = state['bg_points']
        self.background = state['background']
        
        if state['y_data'] is not None:
            self.y_data = state['y_data']
        
        self.update_peak_table()
        self.plot_data()
        self.status_label.setText("Undo performed")

    def toggle_overlap_mode(self):
        """Toggle overlap detection mode - currently not used for fitting"""
        # Toggle state
        self.overlap_mode_enabled = not self.overlap_mode_enabled
        
        # Update button color based on state
        btn_style = """
            QPushButton {
                font-family: Arial;
                font-size: 8pt;
                font-weight: bold;
                border: 2px solid #9575CD;
                border-radius: 4px;
                padding: 4px 6px;
                min-width: 50px;
            }
            QPushButton:hover {
                opacity: 0.85;
            }
            QPushButton:pressed {
                background-color: #7B68EE !important;
                border: 2px solid #6A5ACD;
            }
        """
        
        if self.overlap_mode_enabled:
            # Active state - darker color
            self.overlap_btn.setStyleSheet(btn_style + f"background-color: #4FC3F7; color: black; font-weight: bold;")
            self.status_label.setText("Overlap mode ON - Visualization only")
            
            # Perform clustering for visualization if peaks exist
            if self.x_data is not None and self.peaks:
                try:
                    # Get overlap threshold from UI
                    overlap_multiplier = float(self.overlap_entry.text())
                    
                    # Get peak positions
                    peak_positions = self.x_data[self.peaks]
                    
                    # Estimate FWHM for each peak
                    fwhm_estimates = []
                    for peak_idx in self.peaks:
                        fwhm, _ = PeakProfile.estimate_fwhm(self.x_data, self.y_data, peak_idx)
                        fwhm_estimates.append(fwhm)
                    
                    # Calculate eps for clustering based on average FWHM
                    avg_fwhm = np.mean(fwhm_estimates)
                    eps = avg_fwhm * overlap_multiplier
                    
                    # Cluster peaks
                    labels, n_clusters = PeakClusterer.cluster_peaks(peak_positions, eps=eps)
                    
                    # Store cluster labels for visualization only
                    self.peak_cluster_labels = labels
                    
                    self.status_label.setText(f"Overlap ON: {n_clusters} peak groups identified (visualization)")
                except Exception as e:
                    self.status_label.setText(f"Overlap mode ON but clustering failed: {str(e)}")
        else:
            # Inactive state - lighter color
            self.overlap_btn.setStyleSheet(btn_style + f"background-color: #B9F2FF; color: black;")
            self.peak_cluster_labels = None
            self.status_label.setText("Overlap mode OFF")

    def show_batch_info(self):
        """Show batch processing information"""
        QMessageBox.information(
            self,
            "Batch Processing",
            "Batch processing feature:\n\n"
            "This feature allows you to automatically fit peaks for multiple files.\n"
            "Please use the batch_integration.py script for batch processing.\n\n"
            "Usage: python batch_integration.py"
        )

    def show_settings_info(self):
        """Show settings information"""
        msg = (
            "Current Settings:\n\n"
            f"Fit Method: {self.method_combo.currentText()}\n"
            f"Overlap FWHM×: {self.overlap_entry.text()}\n"
            f"Fit Window×: {self.fit_window_entry.text()}\n"
            f"Background Subtraction: {'On' if self.background_cb.isChecked() else 'Off'}\n"
            f"Smoothing: {'On' if self.smoothing_enable_cb.isChecked() else 'Off'}\n"
        )
        if self.smoothing_enable_cb.isChecked():
            msg += f"Smoothing Method: {self.smooth_method_combo.currentText()}\n"
            msg += f"Sigma/Window: {self.sigma_entry.text() if self.smooth_method_combo.currentText() == 'gaussian' else self.smooth_window_entry.text()}\n"
        
        QMessageBox.information(self, "Settings", msg)


def main():
    """Main function to run the GUI"""
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = InteractiveFittingGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()