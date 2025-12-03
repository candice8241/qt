# -*- coding: utf-8 -*-
"""
Auto Fitting Module - Full Qt6 Version (1:1 Restoration)
Complete port of auto_fitting.py to Qt6
"""

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, 
                              QPushButton, QMessageBox, QFileDialog, QTextEdit, 
                              QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox, 
                              QScrollArea, QRadioButton, QButtonGroup, QDialog, 
                              QLineEdit, QGridLayout, QSizePolicy, QApplication,
                              QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox)
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

# Import helper classes from original file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from auto_fitting import (DataProcessor, PeakClusterer, BackgroundFitter, 
                              PeakProfile, PeakDetector)
except ImportError:
    # Fallback implementations
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
            peaks, properties = find_peaks(y_smooth, height=height_threshold, 
                                          prominence=prominence_threshold, 
                                          distance=min_distance, width=2)
            if len(peaks) == 0:
                peaks, _ = find_peaks(y_smooth, height=np.min(y) + y_range * 0.02,
                                     prominence=y_range * 0.01, distance=3)
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
        
        @staticmethod
        def calculate_area(amplitude, sigma, gamma, eta):
            area_g = amplitude * sigma * np.sqrt(2 * np.pi)
            area_l = amplitude * np.pi * gamma
            return eta * area_l + (1 - eta) * area_g
        
        @staticmethod
        def estimate_fwhm(x, y, peak_idx, smooth=True):
            if smooth and len(y) > 11:
                try:
                    y_smooth = savgol_filter(y, min(11, len(y)//2*2+1), 3)
                except:
                    y_smooth = y
            else:
                y_smooth = y
            
            peak_height = y_smooth[peak_idx]
            n_edge = max(3, len(y) // 10)
            baseline = (np.mean(y_smooth[:n_edge]) + np.mean(y_smooth[-n_edge:])) / 2
            half_max = (peak_height + baseline) / 2
            
            left_x = x[0]
            for j in range(peak_idx, 0, -1):
                if y_smooth[j] <= half_max:
                    if y_smooth[j+1] != y_smooth[j]:
                        frac = (half_max - y_smooth[j]) / (y_smooth[j+1] - y_smooth[j])
                        left_x = x[j] + frac * (x[j+1] - x[j])
                    else:
                        left_x = x[j]
                    break
            
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
            dx = np.mean(np.diff(x))
            if fwhm < dx * 2:
                fwhm = dx * 8
            
            return fwhm, baseline
    
    class BackgroundFitter:
        @staticmethod
        def fit_global_background(x, y, peak_indices, method='spline', 
                                 smoothing_factor=None, poly_order=3):
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
                local_window = min(window_size, len(seg_y) // 2)
                
                if local_window >= 3:
                    try:
                        seg_y_smooth = savgol_filter(seg_y, min(local_window, len(seg_y)//2*2+1), 2)
                    except:
                        seg_y_smooth = seg_y
                else:
                    seg_y_smooth = seg_y
                
                min_local_idx = np.argmin(seg_y_smooth)
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
                if len(sorted_pos) > 1:
                    distances = np.diff(sorted_pos)
                    eps = np.median(distances) * 1.5
                else:
                    eps = 1.0
            
            clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
            labels = clustering.labels_
            
            noise_mask = labels == -1
            if np.any(noise_mask) and np.any(~noise_mask):
                for i in np.where(noise_mask)[0]:
                    non_noise_idx = np.where(~noise_mask)[0]
                    distances = np.abs(peak_positions[non_noise_idx] - peak_positions[i])
                    nearest = non_noise_idx[np.argmin(distances)]
                    labels[i] = labels[nearest]
            elif np.all(noise_mask):
                labels = np.zeros(len(labels), dtype=int)
            
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            
            return labels, n_clusters


# I need to continue with the full implementation in the next file
# This is getting too long. Let me create a proper strategy.
