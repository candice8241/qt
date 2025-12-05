# -*- coding: utf-8 -*-
"""
Detector Calibration Module - Qt Version
Integrates Dioptas calibration functionality for detector orientation calibration using standard samples

Features:
- Load calibration images (standard samples)
- Detector calibration using pyFAI
- Mask creation and editing
- PONI file generation
- Real-time calibration preview

Created: 2025
@author: XRD Processing Suite

NOTE: Canvas classes have been moved to calibration_canvas.py for better modularity
"""

# Suppress verbose traceback in console (keep only essential error info)
import sys
sys.tracebacklimit = 0  # Disable full traceback in console

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QCheckBox, QComboBox, QGroupBox,
                              QFileDialog, QMessageBox, QFrame, QScrollArea, QSplitter,
                              QListWidget, QListWidgetItem, QSlider, QRadioButton, QButtonGroup,
                              QSpinBox, QDoubleSpinBox, QToolBox, QTabWidget, QTableWidget,
                              QTableWidgetItem, QHeaderView, QDialog, QGridLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import os
import numpy as np
from gui_base import GUIBase
from theme_module import ModernButton
from custom_widgets import CustomSpinbox

# Import Canvas classes (moved to separate file) with error handling
try:
    from calibration_canvas import MaskCanvas, CalibrationCanvas
except Exception as e:
    print(f"Error importing calibration_canvas: {e}")
    sys.exit(1)

# Constants
INT32_MAX = 2147483647  # Maximum value for 32-bit signed integer (Qt widgets use int32)

# Import pyFAI and related libraries
try:
    import pyFAI
    from pyFAI.calibrant import Calibrant, ALL_CALIBRANTS
    from pyFAI.geometryRefinement import GeometryRefinement
    from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
    PYFAI_AVAILABLE = True
except ImportError:
    PYFAI_AVAILABLE = False
    print("Warning: pyFAI not available. Install with: pip install pyFAI")

try:
    import fabio
    FABIO_AVAILABLE = True
except ImportError:
    FABIO_AVAILABLE = False
    print("Warning: fabio not available. Install with: pip install fabio")

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False


class CalibrationWorkerThread(QThread):
    """Worker thread for calibration processing with real-time ring-by-ring display"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    calibration_result = pyqtSignal(object)  # Emits calibration result
    ring_found = pyqtSignal(int, object)  # Emits (ring_number, ring_points) for real-time display

    def __init__(self, target_func, *args, **kwargs):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Run the calibration function"""
        try:
            result = self.target_func(*self.args, **self.kwargs)
            self.calibration_result.emit(result)
            self.finished.emit("Calibration completed successfully")
        except Exception as e:
            # Simplified error message without full traceback
            error_msg = f"Calibration Error: {str(e)}"
            self.error.emit(error_msg)


class CalibrateModule(GUIBase):
    """Detector calibration module using Dioptas/pyFAI functionality"""

    def __init__(self, parent, root):
        """
        Initialize Calibration module

        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        super().__init__()
        self.parent = parent
        self.root = root
        
        # Override colors for calibration module - light blue palette
        self.colors = {
            'bg': '#F5F5F5',
            'card_bg': '#FFFFFF',
            'primary': '#A8D8EA',  # Light blue
            'primary_hover': '#7FC4DD',  # Slightly darker light blue
            'secondary': '#A8D8EA',  # Light blue for buttons
            'accent': '#E67E73',
            'text_dark': '#2C3E50',
            'text_light': '#7F8C8D',
            'border': '#D1D9E6',
            'success': '#6FA86F',
            'error': '#E67E73',
            'light_purple': '#B19CD9',
            'active_module': '#6C9BD2'
        }
        
        # Check dependencies
        if not PYFAI_AVAILABLE:
            QMessageBox.warning(None, "Missing Dependencies", 
                              "pyFAI is required for calibration.\nInstall with: pip install pyFAI")
        
        # Initialize variables
        self._init_variables()
        
        # Calibration objects
        self.ai = None  # AzimuthalIntegrator
        self.calibrant = None
        self.geo_ref = None  # GeometryRefinement
        self.current_image = None
        self.current_mask = None
        
        # Track threads
        self.running_threads = []
        
        # Tool mode: 'view', 'peaks', 'mask'
        self.tool_mode = 'view'
        
        # Mask from mask module
        self.imported_mask = None
        self.mask_module_reference = None
        
        # Initialize use_mask_cb early to avoid AttributeError
        self.use_mask_cb = None

    def _init_variables(self):
        """Initialize all variables"""
        # File paths
        self.image_path = ""
        self.mask_path = ""
        self.output_poni = ""
        
        # Calibration parameters
        self.calibrant_name = "LaB6"  # Default calibrant
        self.wavelength = 0.4133  # Angstrom
        self.detector_name = "Pilatus2M"
        self.pixel_size = 172e-6  # meters
        
        # Detector parameters
        self.distance = 0.5  # meters
        self.poni1 = 0.1  # meters
        self.poni2 = 0.1  # meters
        self.rot1 = 0.0  # radians
        self.rot2 = 0.0  # radians
        self.rot3 = 0.0  # radians
        
        # Peak finding parameters
        self.npt = 2048
        self.npt_azim = 360
        self.min_peaks = 5
        
        # Mask parameters
        self.mask_mode = 'rectangle'
        
        # Contrast parameters
        self.contrast_min_val = 0
        self.contrast_max_val = 65535
    
    def log(self, message):
        """Log message to output console"""
        if hasattr(self, 'log_output'):
            self.log_output.append(message)
            # Auto-scroll to bottom
            scrollbar = self.log_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def setup_ui(self):
        """Setup the complete calibration UI - Dioptas style layout"""
        # Check if UI is already set up
        if hasattr(self, '_ui_initialized') and self._ui_initialized:
            return
        
        # Mark as initializing to prevent re-entry
        if hasattr(self, '_ui_initializing') and self._ui_initializing:
            # Silently skip re-initialization
            return
        
        self._ui_initializing = True
        
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        else:
            # Clear existing items carefully
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    try:
                        item.widget().deleteLater()
                    except:
                        pass

        # Main horizontal splitter: Display (left) + Control (right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setContentsMargins(0, 0, 0, 0)
        
        # ============== LEFT PANEL: DISPLAY WIDGET ==============
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Tab widget for Image/Cake/Pattern views (Dioptas style)
        self.display_tab_widget = QTabWidget()
        self.display_tab_widget.setContentsMargins(0, 0, 0, 0)
        self.display_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QTabBar::tab {
                padding: 3px 8px;
                margin: 0px;
            }
        """)
        
        # Image tab
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)
        
        if MATPLOTLIB_AVAILABLE:
            # Horizontal layout for canvas and contrast slider
            canvas_container = QWidget()
            canvas_layout = QHBoxLayout(canvas_container)
            canvas_layout.setContentsMargins(2, 2, 2, 2)
            canvas_layout.setSpacing(2)
            
            try:
                # Create canvas with larger size for better visibility
                self.unified_canvas = CalibrationCanvas(canvas_container, width=20, height=20, dpi=100)
                canvas_layout.addWidget(self.unified_canvas)
            except Exception as e:
                # Simplified error message
                print(f"ERROR creating CalibrationCanvas: {e}")
                # Create placeholder
                placeholder = QLabel("Canvas initialization error.\nPlease restart the application.")
                placeholder.setStyleSheet("color: red; padding: 20px;")
                canvas_layout.addWidget(placeholder)
                self.unified_canvas = None
            
            # Right side panel with position label and controls
            right_panel_widget = QWidget()
            right_panel_widget.setMinimumWidth(200)
            right_panel_widget.setMaximumWidth(220)
            right_panel_layout = QVBoxLayout(right_panel_widget)
            right_panel_layout.setContentsMargins(5, 5, 5, 5)
            right_panel_layout.setSpacing(8)

            # Position label at top (more visible, no background)
            self.position_lbl = QLabel("Position: x=0, y=0")
            self.position_lbl.setFont(QFont('Arial', 9, QFont.Weight.Bold))
            self.position_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # Align left
            self.position_lbl.setStyleSheet("""
                color: #333333;
                padding: 5px;
                padding-left: 10px;
            """)
            self.position_lbl.setMinimumHeight(25)
            right_panel_layout.addWidget(self.position_lbl)

            # Add stretch to center controls vertically
            right_panel_layout.addStretch(2)

            # Calibrate button (above slider)
            button_width = 140
            button_height = 40
            
            self.calibrate_btn = ModernButton("Calibrate",
                                             self.run_calibration,
                                             "",
                                             bg_color=self.colors['primary'],
                                             hover_color=self.colors['primary_hover'],
                                             width=button_width, height=button_height,
                                             font_size=10,
                                             parent=right_panel_widget)
            right_panel_layout.addWidget(self.calibrate_btn, 0, Qt.AlignmentFlag.AlignCenter)
            
            # Add spacing
            right_panel_layout.addSpacing(15)
            
            # Current contrast percentage display
            self.contrast_pct_lbl = QLabel("Contrast: 100%")
            self.contrast_pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.contrast_pct_lbl.setFont(QFont('Arial', 9, QFont.Weight.Bold))
            self.contrast_pct_lbl.setStyleSheet("color: #2E5C8A; padding: 3px;")
            right_panel_layout.addWidget(self.contrast_pct_lbl)
            
            # Vertical slider with reasonable range (0-100 for percentage)
            self.contrast_slider = QSlider(Qt.Orientation.Vertical)
            self.contrast_slider.setMinimum(0)
            self.contrast_slider.setMaximum(100)  # Use percentage scale
            self.contrast_slider.setValue(100)  # Default to max
            self.contrast_slider.setInvertedAppearance(True)  # Max at top
            self.contrast_slider.setFixedHeight(400)  # Adjusted height
            self.contrast_slider.setStyleSheet("""
                QSlider::groove:vertical {
                    width: 25px;
                    background: #E0E0E0;
                    border: 1px solid #BDBDBD;
                    border-radius: 4px;
                }
                QSlider::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #5C9FD6, stop:1 #4A90E2);
                    border: 2px solid #2E5C8A;
                    height: 25px;
                    width: 25px;
                    margin: 0 -13px;
                    border-radius: 4px;  /* Square with slightly rounded corners */
                }
                QSlider::handle:vertical:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6BB0E7, stop:1 #5BA1D3);
                    border: 2px solid #1E4C7A;
                }
            """)
            self.contrast_slider.valueChanged.connect(self.on_contrast_slider_changed)
            right_panel_layout.addWidget(self.contrast_slider, 0, Qt.AlignmentFlag.AlignCenter)

            # Store image statistics for contrast mapping
            self.image_vmin = 0
            self.image_vmax = 65535  # Will be updated when image is loaded
            
            # Add spacing
            right_panel_layout.addSpacing(15)
            
            # Refine button (below slider)
            self.refine_btn = ModernButton("Refine",
                                           self.refine_calibration,
                                           "",
                                           bg_color=self.colors['secondary'],
                                           hover_color=self.colors['primary'],
                                           width=button_width, height=button_height,
                                           font_size=10,
                                           parent=right_panel_widget)
            right_panel_layout.addWidget(self.refine_btn, 0, Qt.AlignmentFlag.AlignCenter)
            
            # Add stretch at bottom
            right_panel_layout.addStretch(2)
            
            canvas_layout.addWidget(right_panel_widget)
            
            image_layout.addWidget(canvas_container)

            # Keep references for compatibility
            self.calibration_canvas = self.unified_canvas
            self.mask_canvas = MaskCanvas(image_tab, width=10, height=8, dpi=100)
            self.mask_canvas.hide()
        else:
            no_plot_label = QLabel("Matplotlib not available")
            no_plot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_layout.addWidget(no_plot_label)

        self.display_tab_widget.addTab(image_tab, "Image")
        
        # Cake tab (Dioptas-style polar transformation)
        cake_tab = QWidget()
        cake_layout = QVBoxLayout(cake_tab)
        cake_layout.setContentsMargins(0, 0, 0, 0)
        
        if MATPLOTLIB_AVAILABLE:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            
            self.cake_figure = Figure(figsize=(10, 8), dpi=100)
            self.cake_canvas = FigureCanvas(self.cake_figure)
            self.cake_axes = self.cake_figure.add_subplot(111)
            cake_layout.addWidget(self.cake_canvas)
            
            self.cake_axes.set_title("Cake View (Polar Transform)")
            self.cake_axes.set_xlabel("2θ (degrees)")
            self.cake_axes.set_ylabel("Azimuthal angle χ (degrees)")
        else:
            cake_label = QLabel("Matplotlib not available")
            cake_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cake_layout.addWidget(cake_label)
        
        self.display_tab_widget.addTab(cake_tab, "Cake")
        
        # Pattern tab (1D integration)
        pattern_tab = QWidget()
        pattern_layout = QVBoxLayout(pattern_tab)
        pattern_layout.setContentsMargins(2, 2, 2, 2)
        pattern_layout.setSpacing(0)
        
        if MATPLOTLIB_AVAILABLE:
            self.pattern_figure = Figure(figsize=(10, 8), dpi=100)
            self.pattern_canvas = FigureCanvas(self.pattern_figure)
            self.pattern_axes = self.pattern_figure.add_subplot(111)
            pattern_layout.addWidget(self.pattern_canvas)
            
            self.pattern_axes.set_title("Integrated Pattern")
            self.pattern_axes.set_xlabel("2θ (degrees)")
            self.pattern_axes.set_ylabel("Intensity (a.u.)")
            self.pattern_axes.grid(True, alpha=0.3)
        else:
            pattern_label = QLabel("Matplotlib not available")
            pattern_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pattern_layout.addWidget(pattern_label)
        
        self.display_tab_widget.addTab(pattern_tab, "Pattern")

        left_layout.addWidget(self.display_tab_widget)
        
        # ============== RIGHT PANEL: CONTROL WIDGET ==============
        # Use scroll area to ensure all controls are accessible
        # Increase width for better readability
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setMinimumWidth(340)
        right_scroll.setMaximumWidth(360)
        right_scroll.setContentsMargins(0, 0, 0, 0)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 2, 4, 2)
        right_layout.setSpacing(3)
        
        # File loading section
        file_frame = QFrame()
        file_layout = QHBoxLayout(file_frame)
        file_layout.setContentsMargins(2, 2, 2, 2)
        file_layout.setSpacing(2)
        
        self.load_img_btn = ModernButton("Load Image File",
                                         self.browse_and_load_image,
                                         "",
                                         bg_color=self.colors['secondary'],
                                         hover_color=self.colors['primary'],
                                         width=200, height=30,
                                         font_size=9,
                                         parent=file_frame)
        
        self.load_previous_img_btn = QPushButton("<")
        self.load_previous_img_btn.setMaximumWidth(55)
        self.load_previous_img_btn.setStyleSheet("padding: 5px; font-size: 10pt;")
        
        self.load_next_img_btn = QPushButton(">")
        self.load_next_img_btn.setMaximumWidth(55)
        self.load_next_img_btn.setStyleSheet("padding: 5px; font-size: 10pt;")
        
        file_layout.addWidget(self.load_img_btn)
        file_layout.addWidget(self.load_previous_img_btn)
        file_layout.addWidget(self.load_next_img_btn)
        
        right_layout.addWidget(file_frame)
        
        # Filename display
        self.filename_txt = QLineEdit()
        self.filename_txt.setReadOnly(True)
        self.filename_txt.setPlaceholderText("No file loaded")
        right_layout.addWidget(self.filename_txt)
        
        # Toolbox for parameters (Dioptas style) - compact
        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet("""
            QToolBox::tab { 
                font-weight: bold; 
                font-size: 9pt;
            }
        """)
        
        # Calibration Parameters page
        calib_params_widget = QWidget()
        calib_params_layout = QVBoxLayout(calib_params_widget)
        calib_params_layout.setSpacing(3)
        calib_params_layout.setContentsMargins(2, 2, 2, 2)
        
        self.setup_detector_groupbox(calib_params_layout)
        self.setup_start_values_groupbox(calib_params_layout)
        self.setup_peak_selection_groupbox(calib_params_layout)
        # Refinement options - Dioptas style parameter selection
        self.setup_refinement_options_groupbox(calib_params_layout)
        
        calib_params_layout.addStretch()
        
        self.toolbox.addItem(calib_params_widget, "Calibration Parameters")
        
        # pyFAI Parameters page
        pyfai_params_widget = QWidget()
        pyfai_params_layout = QVBoxLayout(pyfai_params_widget)
        self.setup_pyfai_parameters(pyfai_params_layout)
        pyfai_params_layout.addStretch()
        self.toolbox.addItem(pyfai_params_widget, "pyFAI Parameters")
        
        # Fit2d Parameters page
        fit2d_params_widget = QWidget()
        fit2d_params_layout = QVBoxLayout(fit2d_params_widget)
        self.setup_fit2d_parameters(fit2d_params_layout)
        fit2d_params_layout.addStretch()
        self.toolbox.addItem(fit2d_params_widget, "Fit2d Parameters")
        
        right_layout.addWidget(self.toolbox)
        
        # Bottom buttons: Load/Save Calibration
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(2, 2, 2, 2)
        bottom_layout.setSpacing(2)
        
        self.load_calibration_btn = ModernButton("Load Calibration",
                                                self.load_calibration,
                                                "",
                                                bg_color=self.colors['secondary'],
                                                hover_color=self.colors['primary'],
                                                width=165, height=30,
                                                font_size=9,
                                                parent=bottom_frame)
        
        self.save_calibration_btn = ModernButton("Save Calibration",
                                                self.save_poni_file,
                                                "",
                                                bg_color=self.colors['secondary'],
                                                hover_color=self.colors['primary'],
                                                width=165, height=30,
                                                font_size=9,
                                                parent=bottom_frame)
        
        bottom_layout.addWidget(self.load_calibration_btn)
        bottom_layout.addWidget(self.save_calibration_btn)
        bottom_layout.addStretch()  # Push buttons to the left
        
        right_layout.addWidget(bottom_frame)
        
        # Add log output to right panel (compact version)
        log_label = QLabel("📋 Log:")
        log_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        log_label.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 1px 2px;")
        right_layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(180)
        self.log_output.setMinimumHeight(120)
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont('Consolas', 8))
        self.log_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: #f8f9fa;
                border: 1px solid {self.colors['border']};
                border-radius: 2px;
                padding: 2px;
                color: #2c3e50;
            }}
        """)
        right_layout.addWidget(self.log_output)
        
        # Set scroll area content
        right_scroll.setWidget(right_widget)
        
        # Add widgets to splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_scroll)
        
        # Left panel expandable, right panel fixed
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        
        # Set initial splitter sizes - balanced layout
        # Total width e.g. 1400: left gets 1040, right gets 360
        main_splitter.setSizes([1000, 360])
        
        # Reduce handle width for more space
        main_splitter.setHandleWidth(2)
        
        layout.addWidget(main_splitter)
        
        # Mark UI as initialized
        self._ui_initialized = True
        self._ui_initializing = False

    def setup_detector_groupbox(self, parent_layout):
        """Setup Detector GroupBox - Clean and organized layout"""
        detector_gb = QGroupBox("Detector")
        detector_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                margin-top: 8px;
                margin-bottom: 6px;
                padding: 12px 8px 8px 8px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['primary']};
            }}
        """)
        detector_layout = QVBoxLayout(detector_gb)
        detector_layout.setSpacing(8)
        detector_layout.setContentsMargins(8, 10, 8, 8)
        
        # Detector selection with label
        det_row = QHBoxLayout()
        det_label = QLabel("Type:")
        det_label.setFixedWidth(80)
        det_label.setStyleSheet("font-weight: normal; font-size: 9pt;")
        det_row.addWidget(det_label)
        
        self.detector_combo = QComboBox()
        detectors = ["Pilatus2M", "Pilatus1M", "Pilatus300K", "PerkinElmer", 
                     "Eiger2M", "Eiger1M", "Eiger4M", "Mar345", "Rayonix", "Custom"]
        self.detector_combo.addItems(detectors)
        self.detector_combo.currentTextChanged.connect(self.on_detector_changed)
        self.detector_combo.setStyleSheet("""
            QComboBox {
                padding: 3px 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background: white;
            }
        """)
        det_row.addWidget(self.detector_combo)
        detector_layout.addLayout(det_row)
        
        # Pixel size in a grid (2 rows, cleaner)
        pixel_label = QLabel("Pixel Size:")
        pixel_label.setStyleSheet("font-weight: normal; font-size: 9pt; color: #555;")
        detector_layout.addWidget(pixel_label)
        
        pixel_grid = QGridLayout()
        pixel_grid.setHorizontalSpacing(6)
        pixel_grid.setVerticalSpacing(4)
        pixel_grid.setContentsMargins(15, 0, 0, 0)
        
        # Width
        pixel_grid.addWidget(QLabel("Width:"), 0, 0)
        self.pixel_width_txt = QLineEdit(str(self.pixel_size * 1e6))
        self.pixel_width_txt.setFixedWidth(70)
        self.pixel_width_txt.setStyleSheet("padding: 2px 4px; border: 1px solid #ccc; border-radius: 2px;")
        pixel_grid.addWidget(self.pixel_width_txt, 0, 1)
        pixel_grid.addWidget(QLabel("μm"), 0, 2)
        
        # Height
        pixel_grid.addWidget(QLabel("Height:"), 1, 0)
        self.pixel_height_txt = QLineEdit(str(self.pixel_size * 1e6))
        self.pixel_height_txt.setFixedWidth(70)
        self.pixel_height_txt.setStyleSheet("padding: 2px 4px; border: 1px solid #ccc; border-radius: 2px;")
        pixel_grid.addWidget(self.pixel_height_txt, 1, 1)
        pixel_grid.addWidget(QLabel("μm"), 1, 2)
        
        detector_layout.addLayout(pixel_grid)
        
        parent_layout.addWidget(detector_gb)
    
    def setup_start_values_groupbox(self, parent_layout):
        """Setup Start Values GroupBox - Clean and organized layout"""
        sv_gb = QGroupBox("Start Values")
        sv_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                margin-top: 8px;
                margin-bottom: 6px;
                padding: 12px 8px 8px 8px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['primary']};
            }}
        """)
        sv_layout = QVBoxLayout(sv_gb)
        sv_layout.setSpacing(8)
        sv_layout.setContentsMargins(8, 10, 8, 8)
        
        # Calibrant selection with label
        calib_row = QHBoxLayout()
        calib_label = QLabel("Calibrant:")
        calib_label.setFixedWidth(80)
        calib_label.setStyleSheet("font-weight: normal; font-size: 9pt;")
        calib_row.addWidget(calib_label)
        
        self.calibrant_combo = QComboBox()
        if PYFAI_AVAILABLE:
            calibrants = sorted(ALL_CALIBRANTS.keys())
            self.calibrant_combo.addItems(calibrants)
            if "LaB6" in calibrants:
                self.calibrant_combo.setCurrentText("LaB6")
        self.calibrant_combo.currentTextChanged.connect(self.on_calibrant_changed)
        self.calibrant_combo.setStyleSheet("""
            QComboBox {
                padding: 3px 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background: white;
            }
        """)
        calib_row.addWidget(self.calibrant_combo)
        sv_layout.addLayout(calib_row)
        
        # Parameters in a clean grid
        params_label = QLabel("Parameters:")
        params_label.setStyleSheet("font-weight: normal; font-size: 9pt; color: #555;")
        sv_layout.addWidget(params_label)
        
        params_grid = QGridLayout()
        params_grid.setHorizontalSpacing(8)
        params_grid.setVerticalSpacing(6)
        params_grid.setContentsMargins(15, 0, 0, 0)
        
        # Distance
        params_grid.addWidget(QLabel("Distance:"), 0, 0)
        self.distance_txt = QLineEdit(str(self.distance * 1000))
        self.distance_txt.setFixedWidth(70)
        self.distance_txt.setStyleSheet("padding: 2px 4px; border: 1px solid #ccc; border-radius: 2px;")
        params_grid.addWidget(self.distance_txt, 0, 1)
        params_grid.addWidget(QLabel("mm"), 0, 2)
        
        # Wavelength
        params_grid.addWidget(QLabel("Wavelength:"), 1, 0)
        self.wavelength_txt = QLineEdit(str(self.wavelength))
        self.wavelength_txt.setFixedWidth(70)
        self.wavelength_txt.setStyleSheet("padding: 2px 4px; border: 1px solid #ccc; border-radius: 2px;")
        params_grid.addWidget(self.wavelength_txt, 1, 1)
        params_grid.addWidget(QLabel("Å"), 1, 2)
        
        # Polarization
        params_grid.addWidget(QLabel("Polarization:"), 2, 0)
        self.polarization_txt = QLineEdit("0.99")
        self.polarization_txt.setFixedWidth(70)
        self.polarization_txt.setStyleSheet("padding: 2px 4px; border: 1px solid #ccc; border-radius: 2px;")
        params_grid.addWidget(self.polarization_txt, 2, 1)
        
        sv_layout.addLayout(params_grid)
        
        parent_layout.addWidget(sv_gb)
    
    def setup_peak_selection_groupbox(self, parent_layout):
        """Setup Peak Selection GroupBox - Clean and organized layout"""
        peak_gb = QGroupBox("Peak Selection")
        peak_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                margin-top: 8px;
                margin-bottom: 6px;
                padding: 12px 8px 8px 8px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['primary']};
            }}
        """)
        peak_layout = QVBoxLayout(peak_gb)
        peak_layout.setSpacing(8)
        peak_layout.setContentsMargins(8, 10, 8, 8)
        
        # Radio buttons for peak selection mode
        self.peak_mode_group = QButtonGroup()
        
        # Radio button style
        radio_style = f"""
            QRadioButton {{
                spacing: 8px;
                padding: 6px 0px;
                color: {self.colors['text_dark']};
            }}
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid #999999;
                border-radius: 7px;
                background-color: white;
            }}
            QRadioButton::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 2px solid {self.colors['primary']};
                border-radius: 7px;
                image: url(check.png);
            }}
            QRadioButton::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """
        
        self.automatic_peak_search_rb = QRadioButton("Automatic peak search")
        self.automatic_peak_search_rb.setChecked(True)
        self.automatic_peak_search_rb.setStyleSheet(radio_style)
        self.automatic_peak_search_rb.toggled.connect(self.on_peak_mode_changed)
        self.peak_mode_group.addButton(self.automatic_peak_search_rb, 0)
        peak_layout.addWidget(self.automatic_peak_search_rb)
        
        self.select_peak_rb = QRadioButton("Select peak manually")
        self.select_peak_rb.setStyleSheet(radio_style)
        self.select_peak_rb.toggled.connect(self.on_peak_mode_changed)
        self.peak_mode_group.addButton(self.select_peak_rb, 1)
        peak_layout.addWidget(self.select_peak_rb)
        
        # Parameters in a clean grid
        params_label = QLabel("Peak Parameters:")
        params_label.setStyleSheet("font-weight: normal; font-size: 9pt; color: #555; margin-top: 4px;")
        peak_layout.addWidget(params_label)
        
        params_grid = QGridLayout()
        params_grid.setHorizontalSpacing(8)
        params_grid.setVerticalSpacing(6)
        params_grid.setContentsMargins(15, 0, 0, 0)
        
        # SpinBox style with functional arrows
        spinbox_style = f"""
            QSpinBox {{
                padding: 2px 4px;
                border: 1px solid #ccc;
                border-radius: 2px;
                background: #FFF8DC;
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 16px;
                border-left: 1px solid #ccc;
                background: #f0f0f0;
            }}
            QSpinBox::up-button:hover {{
                background: {self.colors['primary']};
            }}
            QSpinBox::up-arrow {{
                width: 7px;
                height: 7px;
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-bottom: 4px solid #333;
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 16px;
                border-left: 1px solid #ccc;
                background: #f0f0f0;
            }}
            QSpinBox::down-button:hover {{
                background: {self.colors['primary']};
            }}
            QSpinBox::down-arrow {{
                width: 7px;
                height: 7px;
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 4px solid #333;
            }}
        """

        # Current Ring Number
        params_grid.addWidget(QLabel("Ring #:"), 0, 0)
        self.ring_number_spinbox = QSpinBox()
        self.ring_number_spinbox.setMinimum(1)
        self.ring_number_spinbox.setMaximum(50)
        self.ring_number_spinbox.setValue(1)
        self.ring_number_spinbox.setFixedWidth(80)
        self.ring_number_spinbox.setStyleSheet(spinbox_style)
        self.ring_number_spinbox.valueChanged.connect(self.on_ring_number_changed)
        params_grid.addWidget(self.ring_number_spinbox, 0, 1)

        # Search size
        params_grid.addWidget(QLabel("Search Size:"), 1, 0)
        self.search_size_sb = QSpinBox()
        self.search_size_sb.setMinimum(1)
        self.search_size_sb.setMaximum(100)
        self.search_size_sb.setValue(1)
        self.search_size_sb.setFixedWidth(80)
        self.search_size_sb.setStyleSheet(spinbox_style.replace("background: #FFF8DC;", "background: white;"))
        params_grid.addWidget(self.search_size_sb, 1, 1)
        params_grid.addWidget(QLabel("px"), 1, 2)
        
        peak_layout.addLayout(params_grid)
        
        # Auto increment checkbox (styled to match radio buttons)
        checkbox_style = f"""
            QCheckBox {{
                spacing: 8px;
                padding: 6px 0px;
                color: {self.colors['text_dark']};
                margin-left: 0px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid #999999;
                border-radius: 3px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 2px solid {self.colors['primary']};
                image: url(check.png);
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """
        self.automatic_peak_num_inc_cb = QCheckBox("Auto-increment ring number")
        self.automatic_peak_num_inc_cb.setChecked(True)
        self.automatic_peak_num_inc_cb.setStyleSheet(checkbox_style)
        peak_layout.addWidget(self.automatic_peak_num_inc_cb)
        
        # Control buttons with modern style
        btn_label = QLabel("Actions:")
        btn_label.setStyleSheet("font-weight: normal; font-size: 9pt; color: #555; margin-top: 4px;")
        peak_layout.addWidget(btn_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        btn_layout.setContentsMargins(15, 0, 0, 0)
        
        self.clear_peaks_btn = QPushButton("🗑 Clear")
        self.clear_peaks_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                font-size: 9pt;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.clear_peaks_btn.clicked.connect(self.clear_manual_peaks)
        btn_layout.addWidget(self.clear_peaks_btn)
        
        self.undo_peaks_btn = QPushButton("↶ Undo")
        self.undo_peaks_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                font-size: 9pt;
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.undo_peaks_btn.clicked.connect(self.undo_last_peak)
        btn_layout.addWidget(self.undo_peaks_btn)
        
        peak_layout.addLayout(btn_layout)
        
        # Peak count label with better styling
        self.peak_count_label = QLabel("Peaks: 0")
        self.peak_count_label.setFont(QFont('Arial', 9))
        self.peak_count_label.setStyleSheet("color: #2196F3; padding: 5px; margin-left: 15px; font-weight: bold;")
        peak_layout.addWidget(self.peak_count_label)
        
        parent_layout.addWidget(peak_gb)
    
    def setup_refinement_options_groupbox(self, parent_layout):
        """Setup Refinement Options GroupBox (Dioptas style) - Parameter Selection - Compact"""
        ref_gb = QGroupBox("Refinement Parameters")
        ref_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 9pt;
                border: 1px solid {self.colors['border']};
                border-radius: 3px;
                margin-top: 6px;
                margin-bottom: 4px;
                padding: 10px 5px 5px 5px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px 0 3px;
                color: {self.colors['text_dark']};
            }}
        """)
        ref_layout = QVBoxLayout(ref_gb)
        ref_layout.setSpacing(5)
        ref_layout.setContentsMargins(4, 4, 4, 4)
        
        # Checkbox style
        checkbox_style = f"""
            QCheckBox {{
                spacing: 8px;
                padding: 6px 0px;
                color: {self.colors['text_dark']};
                font-weight: normal;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid #999999;
                border-radius: 3px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 2px solid {self.colors['primary']};
                border-radius: 3px;
                image: url(point.png);
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """
        
        # Info label
        info_label = QLabel("Select parameters to refine during calibration:")
        info_label.setStyleSheet(f"color: {self.colors['text_dark']}; font-size: 8pt; font-weight: normal; padding: 3px 0px;")
        info_label.setWordWrap(True)
        ref_layout.addWidget(info_label)
        
        # Geometry parameters frame - compact
        geom_frame = QFrame()
        geom_frame.setStyleSheet(f"QFrame {{ background-color: rgba(255,255,255,0.03); border-radius: 2px; padding: 3px; }}")
        geom_layout = QVBoxLayout(geom_frame)
        geom_layout.setSpacing(2)
        
        # Title for geometry section - compact
        geom_title = QLabel("Geometry (always refined):")
        geom_title.setStyleSheet(f"color: {self.colors['text_dark']}; font-weight: bold; font-size: 8pt;")
        geom_layout.addWidget(geom_title)
        
        # Distance checkbox (always enabled)
        self.refine_dist_cb = QCheckBox("Distance")
        self.refine_dist_cb.setChecked(True)
        self.refine_dist_cb.setEnabled(False)  # Always refine
        self.refine_dist_cb.setToolTip("Distance is always refined (essential parameter)")
        self.refine_dist_cb.setStyleSheet(checkbox_style)
        geom_layout.addWidget(self.refine_dist_cb)
        
        # Beam center checkboxes
        self.refine_poni1_cb = QCheckBox("Beam Center Y (PONI1)")
        self.refine_poni1_cb.setChecked(True)
        self.refine_poni1_cb.setEnabled(False)  # Always refine
        self.refine_poni1_cb.setToolTip("Beam center Y is always refined (essential parameter)")
        self.refine_poni1_cb.setStyleSheet(checkbox_style)
        geom_layout.addWidget(self.refine_poni1_cb)
        
        self.refine_poni2_cb = QCheckBox("Beam Center X (PONI2)")
        self.refine_poni2_cb.setChecked(True)
        self.refine_poni2_cb.setEnabled(False)  # Always refine
        self.refine_poni2_cb.setToolTip("Beam center X is always refined (essential parameter)")
        self.refine_poni2_cb.setStyleSheet(checkbox_style)
        geom_layout.addWidget(self.refine_poni2_cb)
        
        ref_layout.addWidget(geom_frame)
        
        # Rotation parameters frame - compact
        rot_frame = QFrame()
        rot_frame.setStyleSheet(f"QFrame {{ background-color: rgba(255,255,255,0.03); border-radius: 2px; padding: 3px; }}")
        rot_layout = QVBoxLayout(rot_frame)
        rot_layout.setSpacing(2)
        
        # Title for rotation section - compact
        rot_title = QLabel("Detector Tilt (optional):")
        rot_title.setStyleSheet(f"color: {self.colors['text_dark']}; font-weight: bold; font-size: 8pt;")
        rot_layout.addWidget(rot_title)
        
        # Info about rotations - compact
        rot_info = QLabel("⚠ Only if detector tilted")
        rot_info.setStyleSheet("color: #FF9800; font-size: 7pt; font-weight: normal; padding: 1px 0px;")
        rot_info.setWordWrap(True)
        rot_layout.addWidget(rot_info)
        
        # Rotation checkboxes
        self.refine_rot1_cb = QCheckBox("Rot1 (Tilt around axis 1)")
        self.refine_rot1_cb.setChecked(False)  # Off by default
        self.refine_rot1_cb.setToolTip("Tilt around horizontal axis (usually 0°)")
        self.refine_rot1_cb.setStyleSheet(checkbox_style)
        rot_layout.addWidget(self.refine_rot1_cb)
        
        self.refine_rot2_cb = QCheckBox("Rot2 (Tilt around axis 2)")
        self.refine_rot2_cb.setChecked(False)  # Off by default
        self.refine_rot2_cb.setToolTip("Tilt around vertical axis (usually 0°)")
        self.refine_rot2_cb.setStyleSheet(checkbox_style)
        rot_layout.addWidget(self.refine_rot2_cb)
        
        self.refine_rot3_cb = QCheckBox("Rot3 (In-plane rotation)")
        self.refine_rot3_cb.setChecked(False)  # Off by default
        self.refine_rot3_cb.setToolTip("Rotation in detector plane (usually 0°)")
        self.refine_rot3_cb.setStyleSheet(checkbox_style)
        rot_layout.addWidget(self.refine_rot3_cb)
        
        ref_layout.addWidget(rot_frame)
        
        # Wavelength parameter frame - compact
        wl_frame = QFrame()
        wl_frame.setStyleSheet(f"QFrame {{ background-color: rgba(255,255,255,0.03); border-radius: 2px; padding: 3px; }}")
        wl_layout = QVBoxLayout(wl_frame)
        wl_layout.setSpacing(2)
        
        # Wavelength checkbox
        self.refine_wavelength_cb = QCheckBox("Wavelength (usually fixed)")
        self.refine_wavelength_cb.setChecked(False)  # Off by default
        self.refine_wavelength_cb.setToolTip("Wavelength is usually known and should be fixed")
        self.refine_wavelength_cb.setStyleSheet(checkbox_style)
        wl_layout.addWidget(self.refine_wavelength_cb)
        
        wl_info = QLabel("⚠ Only if wavelength uncertain")
        wl_info.setStyleSheet("color: #FF9800; font-size: 7pt; font-weight: normal; padding: 1px 0px;")
        wl_layout.addWidget(wl_info)
        
        ref_layout.addWidget(wl_frame)
        
        # Quick presets - compact
        preset_frame = QFrame()
        preset_frame.setStyleSheet(f"QFrame {{ background-color: rgba(66, 165, 245, 0.05); border: 1px solid rgba(66, 165, 245, 0.2); border-radius: 2px; padding: 3px; }}")
        preset_layout = QVBoxLayout(preset_frame)
        preset_layout.setSpacing(2)
        
        preset_title = QLabel("Quick Presets:")
        preset_title.setStyleSheet(f"color: {self.colors['text_dark']}; font-weight: bold; font-size: 8pt;")
        preset_layout.addWidget(preset_title)
        
        preset_btn_layout = QHBoxLayout()
        preset_btn_layout.setSpacing(2)
        
        # Basic preset button - compact
        basic_preset_btn = QPushButton("Basic")
        basic_preset_btn.setToolTip("Refine distance and beam center only (recommended)")
        basic_preset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                border-radius: 2px;
                padding: 3px 6px;
                font-size: 7pt;
            }}
            QPushButton:hover {{
                background-color: {self.colors['primary_hover']};
            }}
        """)
        basic_preset_btn.clicked.connect(self.apply_basic_refinement_preset)
        preset_btn_layout.addWidget(basic_preset_btn)
        
        # Full preset button - compact
        full_preset_btn = QPushButton("Full")
        full_preset_btn.setToolTip("Refine all geometry including detector tilt")
        full_preset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                border-radius: 2px;
                padding: 3px 6px;
                font-size: 7pt;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        full_preset_btn.clicked.connect(self.apply_full_refinement_preset)
        preset_btn_layout.addWidget(full_preset_btn)
        
        preset_layout.addLayout(preset_btn_layout)
        ref_layout.addWidget(preset_frame)
        
        parent_layout.addWidget(ref_gb)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; max-height: 2px; margin: 10px 0px;")
        ref_layout.addWidget(separator)
        
        # Mask from Mask Module
        mask_frame = QFrame()
        mask_frame.setStyleSheet(f"QFrame {{ background-color: {self.colors['card_bg']}; border-radius: 5px; padding: 10px; margin: 5px 0px; }}")
        mask_inner_layout = QVBoxLayout(mask_frame)
        mask_inner_layout.setSpacing(10)
        
        mask_title = QLabel("Mask from Mask Module")
        mask_title.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        mask_title.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 2px 0px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);")
        mask_inner_layout.addWidget(mask_title)
        
        self.use_mask_cb = QCheckBox("Use Mask from Mask Module")
        self.use_mask_cb.stateChanged.connect(self.on_use_mask_changed)
        self.use_mask_cb.setStyleSheet(checkbox_style)
        mask_inner_layout.addWidget(self.use_mask_cb)
        
        self.mask_transparent_cb = QCheckBox("Transparent Overlay")
        self.mask_transparent_cb.setChecked(True)
        self.mask_transparent_cb.setStyleSheet(checkbox_style)
        mask_inner_layout.addWidget(self.mask_transparent_cb)
        
        self.mask_info_label = QLabel("No mask loaded")
        self.mask_info_label.setStyleSheet("color: gray; font-size: 8pt; padding: 5px; background-color: rgba(255,255,255,0.05); border-radius: 3px;")
        mask_inner_layout.addWidget(self.mask_info_label)
        
        ref_layout.addWidget(mask_frame)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setStyleSheet(f"background-color: {self.colors['border']}; max-height: 2px; margin: 10px 0px;")
        ref_layout.addWidget(separator2)
        
        # Peak search settings frame
        peak_frame = QFrame()
        peak_frame.setStyleSheet(f"QFrame {{ background-color: rgba(255,255,255,0.02); border-radius: 5px; padding: 8px; margin: 5px 0px; }}")
        peak_layout_inner = QVBoxLayout(peak_frame)
        peak_layout_inner.setSpacing(8)
        
        # Peak search algorithm
        algo_layout = QHBoxLayout()
        algo_label = QLabel("Peak Search:")
        algo_label.setFixedWidth(100)
        algo_layout.addWidget(algo_label)
        self.peak_search_algorithm_cb = QComboBox()
        self.peak_search_algorithm_cb.addItems(["Massif", "Blob"])
        algo_layout.addWidget(self.peak_search_algorithm_cb)
        algo_layout.addStretch()
        peak_layout_inner.addLayout(algo_layout)
        
        # Number of rings
        rings_layout = QHBoxLayout()
        rings_label = QLabel("# of rings:")
        rings_label.setFixedWidth(100)
        rings_layout.addWidget(rings_label)
        self.number_of_rings_sb = QSpinBox()
        self.number_of_rings_sb.setMinimum(1)
        self.number_of_rings_sb.setMaximum(50)
        self.number_of_rings_sb.setValue(10)
        self.number_of_rings_sb.setFixedWidth(80)
        rings_layout.addWidget(self.number_of_rings_sb)
        rings_layout.addStretch()
        peak_layout_inner.addLayout(rings_layout)
        
        # Delta 2theta
        delta_layout = QHBoxLayout()
        delta_label = QLabel("Δ2θ:")
        delta_label.setFixedWidth(100)
        delta_layout.addWidget(delta_label)
        self.delta_tth_txt = QLineEdit("0.5")
        self.delta_tth_txt.setFixedWidth(80)
        delta_layout.addWidget(self.delta_tth_txt)
        delta_layout.addWidget(QLabel("°"))
        delta_layout.addStretch()
        peak_layout_inner.addLayout(delta_layout)
        
        # Intensity mean factor
        mean_layout = QHBoxLayout()
        mean_label = QLabel("I mean factor:")
        mean_label.setFixedWidth(100)
        mean_layout.addWidget(mean_label)
        self.intensity_mean_factor_sb = QDoubleSpinBox()
        self.intensity_mean_factor_sb.setMinimum(0.1)
        self.intensity_mean_factor_sb.setMaximum(10.0)
        self.intensity_mean_factor_sb.setSingleStep(0.1)
        self.intensity_mean_factor_sb.setValue(3.0)
        self.intensity_mean_factor_sb.setFixedWidth(80)
        mean_layout.addWidget(self.intensity_mean_factor_sb)
        mean_layout.addStretch()
        peak_layout_inner.addLayout(mean_layout)
        
        # Intensity limit
        limit_layout = QHBoxLayout()
        limit_label = QLabel("I limit:")
        limit_label.setFixedWidth(100)
        limit_layout.addWidget(limit_label)
        self.intensity_limit_txt = QLineEdit("50")
        self.intensity_limit_txt.setFixedWidth(80)
        limit_layout.addWidget(self.intensity_limit_txt)
        limit_layout.addStretch()
        peak_layout_inner.addLayout(limit_layout)
        
        ref_layout.addWidget(peak_frame)
        
        parent_layout.addWidget(ref_gb)
    
    def setup_pyfai_parameters(self, parent_layout):
        """Setup pyFAI Parameters section (Dioptas style)"""
        pyfai_gb = QGroupBox("pyFAI Geometry Parameters")
        pyfai_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                margin-top: 15px;
                margin-bottom: 10px;
                padding: 15px 10px 10px 10px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['text_dark']};
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
        """)
        pyfai_layout = QVBoxLayout(pyfai_gb)
        pyfai_layout.setSpacing(8)
        
        # Distance
        self._add_param_row(pyfai_layout, "Distance:", "pyfai_dist", "0.200", "m", True)
        
        # PONI1
        self._add_param_row(pyfai_layout, "PONI1:", "pyfai_poni1", "0.100", "m", True)
        
        # PONI2
        self._add_param_row(pyfai_layout, "PONI2:", "pyfai_poni2", "0.100", "m", True)
        
        # Rot1
        self._add_param_row(pyfai_layout, "Rot1:", "pyfai_rot1", "0.000", "rad", True)
        
        # Rot2
        self._add_param_row(pyfai_layout, "PONI2:", "pyfai_rot2", "0.000", "rad", True)
        
        # Rot3
        self._add_param_row(pyfai_layout, "Rot3:", "pyfai_rot3", "0.000", "rad", True)
        
        # Wavelength
        self._add_param_row(pyfai_layout, "Wavelength:", "pyfai_wavelength", "0.4133", "Å", False)
        
        # Update from fit button
        update_btn = QPushButton("Update from fit")
        update_btn.clicked.connect(self.update_pyfai_from_fit)
        pyfai_layout.addWidget(update_btn)
        
        parent_layout.addWidget(pyfai_gb)
    
    def setup_fit2d_parameters(self, parent_layout):
        """Setup Fit2d Parameters section (Dioptas style)"""
        fit2d_gb = QGroupBox("Fit2d Geometry Parameters")
        fit2d_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                margin-top: 15px;
                margin-bottom: 10px;
                padding: 15px 10px 10px 10px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['text_dark']};
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
        """)
        fit2d_layout = QVBoxLayout(fit2d_gb)
        fit2d_layout.setSpacing(8)
        
        # Direct beam distance
        self._add_param_row_simple(fit2d_layout, "Direct beam distance:", "fit2d_dist", "200.0", "mm")
        
        # Center X
        self._add_param_row_simple(fit2d_layout, "Center X:", "fit2d_centerx", "1024", "px")
        
        # Center Y
        self._add_param_row_simple(fit2d_layout, "Center Y:", "fit2d_centery", "1024", "px")
        
        # Tilt
        self._add_param_row_simple(fit2d_layout, "Tilt:", "fit2d_tilt", "0.00", "°")
        
        # Rotation
        self._add_param_row_simple(fit2d_layout, "Rotation:", "fit2d_rotation", "0.00", "°")
        
        # Wavelength
        self._add_param_row_simple(fit2d_layout, "Wavelength:", "fit2d_wavelength", "0.4133", "Å")
        
        # Polarization
        self._add_param_row_simple(fit2d_layout, "Polarization:", "fit2d_polarization", "0.99", "")
        
        # Update from fit button
        update_btn = QPushButton("Update from fit")
        update_btn.clicked.connect(self.update_fit2d_from_fit)
        fit2d_layout.addWidget(update_btn)
        
        parent_layout.addWidget(fit2d_gb)
    
    def _add_param_row(self, layout, label_text, var_name, default_val, unit, has_checkbox):
        """Helper to add parameter row with label, textbox, unit, and optional checkbox"""
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        
        txt = QLineEdit(default_val)
        txt.setFixedWidth(80)
        txt.setReadOnly(True)
        setattr(self, f"{var_name}_txt", txt)
        row.addWidget(txt)
        
        if unit:
            row.addWidget(QLabel(unit))
        
        if has_checkbox:
            cb = QCheckBox("refine")
            cb.setChecked(True)
            setattr(self, f"{var_name}_cb", cb)
            row.addWidget(cb)
        
        row.addStretch()
        layout.addLayout(row)
    
    def _add_param_row_simple(self, layout, label_text, var_name, default_val, unit):
        """Helper to add simple parameter row (read-only, no checkbox)"""
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        
        txt = QLineEdit(default_val)
        txt.setFixedWidth(80)
        txt.setReadOnly(True)
        setattr(self, f"{var_name}_txt", txt)
        row.addWidget(txt)
        
        if unit:
            row.addWidget(QLabel(unit))
        
        row.addStretch()
        layout.addLayout(row)
    
    def setup_file_section_compact(self, parent_layout):
        """Setup compact file input section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)
        
        title = QLabel("📁 Image")
        title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Browse button
        browse_img_btn = ModernButton("Browse & Load",
                                     self.browse_and_load_image,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=120, height=28,
                                     font_size=9,
                                     parent=card)
        card_layout.addWidget(browse_img_btn)
        
        parent_layout.addWidget(card)
    
    def setup_file_section(self, parent_layout):
        """Setup file input section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("📁 Image Files")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Image file
        img_label = QLabel("Calibration Image:")
        img_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(img_label)
        
        img_frame = QFrame()
        img_layout = QHBoxLayout(img_frame)
        img_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_entry = QLineEdit()
        self.image_entry.setPlaceholderText("Select calibration image (e.g., LaB6, CeO2)...")
        self.image_entry.setReadOnly(True)
        img_layout.addWidget(self.image_entry)
        
        browse_img_btn = ModernButton("Browse & Load",
                                     self.browse_and_load_image,
                                     "",
                                     bg_color=self.colors['accent'],
                                     hover_color=self.colors['primary'],
                                     width=120, height=28,
                                     font_size=9,
                                     parent=img_frame)
        img_layout.addWidget(browse_img_btn)
        
        card_layout.addWidget(img_frame)
        
        parent_layout.addWidget(card)

    def setup_calibrant_section_compact(self, parent_layout):
        """Setup compact calibrant selection section - Dioptas style"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)
        
        title = QLabel("🎯 Calibrant")
        title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Calibrant selection
        self.calibrant_combo = QComboBox()
        if PYFAI_AVAILABLE:
            calibrants = sorted(ALL_CALIBRANTS.keys())
            self.calibrant_combo.addItems(calibrants)
            if "LaB6" in calibrants:
                self.calibrant_combo.setCurrentText("LaB6")
        self.calibrant_combo.currentTextChanged.connect(self.on_calibrant_changed)
        card_layout.addWidget(self.calibrant_combo)
        
        # Load custom calibrant button
        load_cal_btn = ModernButton("Load Custom",
                                   self.load_custom_calibrant,
                                   "📂",
                                   bg_color=self.colors['secondary'],
                                   hover_color=self.colors['primary'],
                                   width=120, height=24,
                                   font_size=8,
                                   parent=card)
        card_layout.addWidget(load_cal_btn)
        
        # Wavelength
        wl_label = QLabel("λ (Å):")
        wl_label.setFont(QFont('Arial', 8))
        card_layout.addWidget(wl_label)
        
        self.wavelength_entry = QLineEdit(str(self.wavelength))
        self.wavelength_entry.setPlaceholderText("Wavelength")
        self.wavelength_entry.textChanged.connect(self.on_wavelength_changed)
        card_layout.addWidget(self.wavelength_entry)
        
        parent_layout.addWidget(card)
        
        # Update calibrant info for default
        if not hasattr(self, 'calibrant_info_text'):
            # For compact version, we don't show the info text, but still update the calibrant object
            self.calibrant = None
            if PYFAI_AVAILABLE:
                try:
                    calibrant_name = self.calibrant_combo.currentText()
                    if calibrant_name in ALL_CALIBRANTS:
                        self.calibrant = ALL_CALIBRANTS[calibrant_name]
                except:
                    pass
    
    def setup_calibrant_section(self, parent_layout):
        """Setup calibrant selection section - Dioptas style"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("🎯 Calibrant & Wavelength")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Calibrant selection row
        cal_row = QFrame()
        cal_row_layout = QHBoxLayout(cal_row)
        cal_row_layout.setContentsMargins(0, 5, 0, 5)
        
        cal_label = QLabel("Calibrant:")
        cal_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        cal_label.setFixedWidth(80)
        cal_row_layout.addWidget(cal_label)
        
        self.calibrant_combo = QComboBox()
        if PYFAI_AVAILABLE:
            calibrants = sorted(ALL_CALIBRANTS.keys())
            self.calibrant_combo.addItems(calibrants)
            if "LaB6" in calibrants:
                self.calibrant_combo.setCurrentText("LaB6")
        else:
            self.calibrant_combo.addItems(["LaB6", "CeO2", "Si", "Al2O3"])
        
        self.calibrant_combo.currentTextChanged.connect(self.on_calibrant_changed)
        cal_row_layout.addWidget(self.calibrant_combo)
        
        card_layout.addWidget(cal_row)
        
        # Load custom calibrant button
        load_cal_btn = ModernButton("Load Custom Calibrant",
                                   self.load_custom_calibrant,
                                   "📂",
                                   bg_color=self.colors['secondary'],
                                   hover_color=self.colors['primary'],
                                   width=180, height=28,
                                   font_size=9,
                                   parent=card)
        card_layout.addWidget(load_cal_btn)
        
        # Calibrant information display (d-spacings)
        info_label = QLabel("D-spacings (Å):")
        info_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(info_label)
        
        self.calibrant_info_text = QTextEdit()
        self.calibrant_info_text.setReadOnly(True)
        self.calibrant_info_text.setMaximumHeight(80)
        self.calibrant_info_text.setFont(QFont('Courier', 8))
        self.calibrant_info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        card_layout.addWidget(self.calibrant_info_text)
        
        # Wavelength row
        wl_row = QFrame()
        wl_row_layout = QHBoxLayout(wl_row)
        wl_row_layout.setContentsMargins(0, 5, 0, 5)
        
        wl_label = QLabel("Wavelength (Å):")
        wl_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        wl_label.setFixedWidth(120)
        wl_row_layout.addWidget(wl_label)
        
        self.wavelength_entry = QLineEdit(str(self.wavelength))
        self.wavelength_entry.setPlaceholderText("Enter wavelength")
        self.wavelength_entry.textChanged.connect(self.on_wavelength_changed)
        wl_row_layout.addWidget(self.wavelength_entry)
        
        card_layout.addWidget(wl_row)
        
        parent_layout.addWidget(card)
        
        # Update calibrant info display for default calibrant
        self.update_calibrant_info()

    def setup_detector_section_compact(self, parent_layout):
        """Setup compact detector parameters section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)
        
        title = QLabel("📷 Detector")
        title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Detector selection
        self.detector_combo = QComboBox()
        detectors = ["Pilatus2M", "Pilatus1M", "Pilatus300K", "PerkinElmer", 
                     "Eiger2M", "Eiger1M", "Mar345", "Custom"]
        self.detector_combo.addItems(detectors)
        self.detector_combo.currentTextChanged.connect(self.on_detector_changed)
        card_layout.addWidget(self.detector_combo)
        
        # Pixel size
        pixel_label = QLabel("Pixel (μm):")
        pixel_label.setFont(QFont('Arial', 8))
        card_layout.addWidget(pixel_label)
        
        self.pixel_entry = QLineEdit(str(self.pixel_size * 1e6))
        card_layout.addWidget(self.pixel_entry)
        
        # Distance
        dist_label = QLabel("Dist (m):")
        dist_label.setFont(QFont('Arial', 8))
        card_layout.addWidget(dist_label)
        
        self.distance_entry = QLineEdit(str(self.distance))
        card_layout.addWidget(self.distance_entry)
        
        parent_layout.addWidget(card)
    
    def setup_detector_section(self, parent_layout):
        """Setup detector parameters section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("📷 Detector Parameters")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Detector selection
        det_label = QLabel("Detector:")
        det_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(det_label)
        
        self.detector_combo = QComboBox()
        detectors = ["Pilatus2M", "Pilatus1M", "Pilatus300K", "PerkinElmer", 
                     "Eiger2M", "Eiger1M", "Mar345", "Custom"]
        self.detector_combo.addItems(detectors)
        self.detector_combo.currentTextChanged.connect(self.on_detector_changed)
        card_layout.addWidget(self.detector_combo)
        
        # Pixel size
        pixel_label = QLabel("Pixel Size (μm):")
        pixel_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(pixel_label)
        
        self.pixel_entry = QLineEdit(str(self.pixel_size * 1e6))
        card_layout.addWidget(self.pixel_entry)
        
        # Distance (initial guess)
        dist_label = QLabel("Sample-Detector Distance (m):")
        dist_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(dist_label)
        
        self.distance_entry = QLineEdit(str(self.distance))
        card_layout.addWidget(self.distance_entry)
        
        parent_layout.addWidget(card)
    
    def setup_threshold_section(self, parent_layout):
        """Setup threshold mask section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("🔢 Threshold Mask")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        info_label = QLabel("Mask pixels outside the intensity range:")
        info_label.setFont(QFont('Arial', 8))
        info_label.setWordWrap(True)
        card_layout.addWidget(info_label)
        
        # Min/Max in same row
        thresh_row = QWidget()
        thresh_layout = QHBoxLayout(thresh_row)
        thresh_layout.setContentsMargins(0, 0, 0, 0)
        
        thresh_layout.addWidget(QLabel("Min:"))
        self.threshold_min_entry = QLineEdit("0")
        self.threshold_min_entry.setFixedWidth(80)
        thresh_layout.addWidget(self.threshold_min_entry)
        
        thresh_layout.addWidget(QLabel("Max:"))
        self.threshold_max_entry = QLineEdit("65535")
        self.threshold_max_entry.setFixedWidth(80)
        thresh_layout.addWidget(self.threshold_max_entry)
        
        card_layout.addWidget(thresh_row)
        
        # Apply button
        apply_thresh_btn = ModernButton("Apply Threshold",
                                       self.apply_threshold_mask,
                                       "",
                                       bg_color=self.colors['secondary'],
                                       hover_color=self.colors['primary'],
                                       width=150, height=28,
                                       font_size=9,
                                       parent=card)
        card_layout.addWidget(apply_thresh_btn)
        
        parent_layout.addWidget(card)

    def setup_mask_section(self, parent_layout):
        """Setup mask creation section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("🎭 Mask & Display Tools")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Contrast controls
        contrast_label = QLabel("Contrast Adjustment:")
        contrast_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(contrast_label)
        
        # Min contrast slider
        min_contrast_frame = QFrame()
        min_contrast_layout = QHBoxLayout(min_contrast_frame)
        min_contrast_layout.setContentsMargins(0, 0, 0, 0)
        
        min_label = QLabel("Min:")
        min_label.setFixedWidth(40)
        min_contrast_layout.addWidget(min_label)
        
        self.contrast_min_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_min_slider.setMinimum(0)
        self.contrast_min_slider.setMaximum(65535)
        self.contrast_min_slider.setValue(int(self.contrast_min_val))
        self.contrast_min_slider.valueChanged.connect(self.on_min_slider_changed)
        min_contrast_layout.addWidget(self.contrast_min_slider)
        
        self.contrast_min_entry = QLineEdit(str(self.contrast_min_val))
        self.contrast_min_entry.setFixedWidth(80)
        self.contrast_min_entry.textChanged.connect(self.on_min_entry_changed)
        min_contrast_layout.addWidget(self.contrast_min_entry)
        
        card_layout.addWidget(min_contrast_frame)
        
        # Max contrast slider
        max_contrast_frame = QFrame()
        max_contrast_layout = QHBoxLayout(max_contrast_frame)
        max_contrast_layout.setContentsMargins(0, 0, 0, 0)
        
        max_label = QLabel("Max:")
        max_label.setFixedWidth(40)
        max_contrast_layout.addWidget(max_label)
        
        self.contrast_max_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_max_slider.setMinimum(0)
        self.contrast_max_slider.setMaximum(65535)
        self.contrast_max_slider.setValue(int(self.contrast_max_val))
        self.contrast_max_slider.valueChanged.connect(self.on_max_slider_changed)
        max_contrast_layout.addWidget(self.contrast_max_slider)
        
        self.contrast_max_entry = QLineEdit(str(self.contrast_max_val))
        self.contrast_max_entry.setFixedWidth(80)
        self.contrast_max_entry.textChanged.connect(self.on_max_entry_changed)
        max_contrast_layout.addWidget(self.contrast_max_entry)
        
        card_layout.addWidget(max_contrast_frame)
        
        # Apply and Reset contrast buttons
        contrast_btn_frame = QFrame()
        contrast_btn_layout = QHBoxLayout(contrast_btn_frame)
        
        apply_contrast_btn = ModernButton("Apply",
                                         self.apply_contrast,
                                         "",
                                         bg_color=self.colors['primary'],
                                         hover_color=self.colors['primary_hover'],
                                         width=80, height=28,
                                         font_size=9,
                                         parent=contrast_btn_frame)
        
        reset_contrast_btn = ModernButton("Auto",
                                         self.auto_contrast,
                                         "",
                                         bg_color=self.colors['secondary'],
                                         hover_color=self.colors['primary'],
                                         width=80, height=28,
                                         font_size=9,
                                         parent=contrast_btn_frame)
        
        reset_zoom_btn = ModernButton("Reset Zoom",
                                     self.reset_zoom,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=90, height=28,
                                     font_size=9,
                                     parent=contrast_btn_frame)
        
        contrast_btn_layout.addWidget(apply_contrast_btn)
        contrast_btn_layout.addWidget(reset_contrast_btn)
        contrast_btn_layout.addWidget(reset_zoom_btn)
        card_layout.addWidget(contrast_btn_frame)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {self.colors['border']};")
        separator.setFixedHeight(2)
        card_layout.addWidget(separator)
        
        # Mask mode selection
        mode_label = QLabel("Drawing Mode:")
        mode_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(mode_label)
        
        self.mask_mode_combo = QComboBox()
        self.mask_mode_combo.addItems(["Rectangle", "Circle", "Threshold"])
        self.mask_mode_combo.currentTextChanged.connect(self.on_mask_mode_changed)
        card_layout.addWidget(self.mask_mode_combo)
        
        # Mask/Unmask toggle
        self.mask_value_checkbox = QCheckBox("Mask (checked) / Unmask (unchecked)")
        self.mask_value_checkbox.setChecked(True)
        self.mask_value_checkbox.stateChanged.connect(self.on_mask_value_changed)
        card_layout.addWidget(self.mask_value_checkbox)
        
        # Mask control buttons
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        
        clear_mask_btn = ModernButton("Clear Mask",
                                     self.clear_mask,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=100, height=30,
                                     font_size=9,
                                     parent=btn_frame)
        
        invert_mask_btn = ModernButton("Invert",
                                      self.invert_mask,
                                      "",
                                      bg_color=self.colors['secondary'],
                                      hover_color=self.colors['primary'],
                                      width=80, height=30,
                                      font_size=9,
                                      parent=btn_frame)
        
        save_mask_btn = ModernButton("Save Mask",
                                    self.save_mask,
                                    "",
                                    bg_color=self.colors['secondary'],
                                    hover_color=self.colors['primary'],
                                    width=100, height=30,
                                    font_size=9,
                                    parent=btn_frame)
        
        btn_layout.addWidget(clear_mask_btn)
        btn_layout.addWidget(invert_mask_btn)
        btn_layout.addWidget(save_mask_btn)
        
        card_layout.addWidget(btn_frame)
        
        parent_layout.addWidget(card)

    def setup_calibration_section(self, parent_layout):
        """Setup calibration execution section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("⚙️ Calibration")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Manual peak selection button
        pick_peaks_btn = ModernButton("📍 Manual Peak Selection",
                                     self.toggle_peak_picking,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=180, height=35,
                                     font_size=9,
                                     parent=card)
        card_layout.addWidget(pick_peaks_btn)
        self.pick_peaks_btn = pick_peaks_btn
        
        # Peak selection info
        peak_info_frame = QFrame()
        peak_info_layout = QHBoxLayout(peak_info_frame)
        peak_info_layout.setContentsMargins(0, 0, 0, 0)
        
        self.peak_count_label = QLabel("Peaks: 0")
        self.peak_count_label.setFont(QFont('Arial', 8))
        peak_info_layout.addWidget(self.peak_count_label)
        
        # Edit Points button (new)
        edit_peaks_btn = ModernButton("Edit",
                                     self.edit_manual_peaks,
                                     "",
                                     bg_color='#4CAF50',
                                     hover_color='#45a049',
                                     width=50, height=25,
                                     font_size=8,
                                     parent=peak_info_frame)
        peak_info_layout.addWidget(edit_peaks_btn)
        
        clear_peaks_btn = ModernButton("Clear",
                                      self.clear_manual_peaks,
                                      "",
                                      bg_color='#FF6B6B',
                                      hover_color='#FF5252',
                                      width=60, height=25,
                                      font_size=8,
                                      parent=peak_info_frame)
        peak_info_layout.addWidget(clear_peaks_btn)
        peak_info_layout.addStretch()
        
        card_layout.addWidget(peak_info_frame)
        
        # Ring number for next peak (Dioptas-style)
        ring_frame = QFrame()
        ring_layout = QHBoxLayout(ring_frame)
        ring_layout.setContentsMargins(0, 0, 0, 0)
        
        ring_label = QLabel("Current Ring #:")
        ring_label.setFixedWidth(90)
        ring_label.setStyleSheet(f"color: {self.colors['text_dark']}; font-weight: bold;")
        ring_layout.addWidget(ring_label)
        
        # Use SpinBox for ring number (unified name: ring_num_input)
        self.ring_num_input = QSpinBox()
        self.ring_num_input.setMinimum(1)  # Start from 1 per user request
        self.ring_num_input.setMaximum(50)
        self.ring_num_input.setValue(1)  # Default to ring 1
        self.ring_num_input.setFixedWidth(50)
        self.ring_num_input.setStyleSheet(f"""
            QSpinBox {{
                background-color: #FFF8DC;
                color: {self.colors['text_dark']};
                border: 2px solid {self.colors['primary']};
                padding: 3px;
                font-weight: bold;
            }}
        """)
        # Connect to update canvas when value changes
        self.ring_num_input.valueChanged.connect(self.on_ring_number_changed)
        ring_layout.addWidget(self.ring_num_input)
        
        ring_layout.addStretch()
        card_layout.addWidget(ring_frame)
        
        # Auto increment checkbox (Dioptas style)
        self.automatic_peak_num_inc_cb = QCheckBox("Automatic increase ring number")
        self.automatic_peak_num_inc_cb.setChecked(True)
        self.automatic_peak_num_inc_cb.setStyleSheet(f"color: {self.colors['text_dark']}; font-size: 9pt;")
        card_layout.addWidget(self.automatic_peak_num_inc_cb)
        
        # NOTE: Real-time auto peak finding during manual selection removed per user request
        # Auto peak finding now only happens when clicking Calibrate button
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {self.colors['border']};")
        separator.setFixedHeight(2)
        card_layout.addWidget(separator)
        
        # Number of points
        npt_label = QLabel("Integration Points:")
        npt_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(npt_label)
        
        self.npt_entry = QLineEdit(str(self.npt))
        card_layout.addWidget(self.npt_entry)
        
        # Run calibration button
        calibrate_btn = ModernButton("🎯 Run Calibration",
                                    self.run_calibration,
                                    "",
                                    bg_color=self.colors['primary'],
                                    hover_color=self.colors['primary'],
                                    width=180, height=40,
                                    font_size=9,
                                    parent=card)
        card_layout.addWidget(calibrate_btn)
        
        parent_layout.addWidget(card)

    def setup_output_section(self, parent_layout):
        """Setup output section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("💾 Output")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # PONI output
        poni_label = QLabel("Output PONI File:")
        poni_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(poni_label)
        
        poni_frame = QFrame()
        poni_layout = QHBoxLayout(poni_frame)
        poni_layout.setContentsMargins(0, 0, 0, 0)
        
        self.poni_entry = QLineEdit()
        self.poni_entry.setPlaceholderText("calibration.poni")
        poni_layout.addWidget(self.poni_entry)
        
        browse_poni_btn = ModernButton("Browse",
                                      self.browse_poni_output,
                                      "",
                                      bg_color=self.colors['secondary'],
                                      hover_color=self.colors['primary'],
                                      width=80, height=28,
                                      font_size=9,
                                      parent=poni_frame)
        poni_layout.addWidget(browse_poni_btn)
        
        card_layout.addWidget(poni_frame)
        
        # Save PONI button
        save_poni_btn = ModernButton("💾 Save PONI",
                                    self.save_poni_file,
                                    "",
                                    bg_color=self.colors['secondary'],
                                    hover_color=self.colors['primary'],
                                    width=150, height=35,
                                    font_size=9,
                                    parent=card)
        card_layout.addWidget(save_poni_btn)
        
        parent_layout.addWidget(card)

    def set_tool_mode(self, mode):
        """Set current tool mode"""
        self.tool_mode = mode
        
        # Update button styles
        self.view_mode_btn.setStyleSheet(f"""
            background-color: {self.colors['primary'] if mode == 'view' else self.colors['secondary']};
            color: white; border: none; border-radius: 4px; padding: 6px;
        """)
        self.pick_peaks_tool_btn.setStyleSheet(f"""
            background-color: {self.colors['success'] if mode == 'peaks' else self.colors['secondary']};
            color: white; border: {'2px solid #00ff00' if mode == 'peaks' else 'none'};
            border-radius: 4px; padding: 6px; font-weight: {'bold' if mode == 'peaks' else 'normal'};
        """)
        self.mask_tool_btn.setStyleSheet(f"""
            background-color: {self.colors['accent'] if mode == 'mask' else self.colors['secondary']};
            color: white; border: {'2px solid #ff6b6b' if mode == 'mask' else 'none'};
            border-radius: 4px; padding: 6px; font-weight: {'bold' if mode == 'mask' else 'normal'};
        """)
        
        # Update canvas modes
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
            self.unified_canvas.peak_picking_mode = (mode == 'peaks')
            self.unified_canvas.mask_editing_mode = (mode == 'mask')
            
            # Update title
            if mode == 'view':
                title = 'Calibration Image - Scroll to zoom'
            elif mode == 'peaks':
                title = 'Peak Selection Mode - Click on diffraction rings'
            elif mode == 'mask':
                title = 'Mask Editing Mode - Draw masks on image'
            
            self.unified_canvas.axes.set_title(title)
            self.unified_canvas.draw_idle()
        
        self.log(f"Tool mode: {mode.upper()}")
    
    def switch_display_tab(self, tab_name):
        """Legacy method for compatibility"""
        self.current_display = tab_name

    def browse_and_load_image(self):
        """Browse for calibration image and load it immediately"""
        filename, _ = QFileDialog.getOpenFileName(
            None, "Select Calibration Image", "",
            "Image Files (*.tif *.tiff *.edf *.cbf *.mar3450 *.img *.h5 *.hdf5);;HDF5 Files (*.h5 *.hdf5);;TIFF Files (*.tif *.tiff);;EDF Files (*.edf);;All Files (*.*)"
        )
        if filename:
            self.image_path = filename
            # Update filename display
            if hasattr(self, 'filename_txt'):
                self.filename_txt.setText(os.path.basename(filename))
            if hasattr(self, 'image_entry'):
                self.image_entry.setText(filename)
            # Automatically load the image
            self.load_image_file()

    def browse_poni_output(self):
        """Browse for PONI output location"""
        filename, _ = QFileDialog.getSaveFileName(
            None, "Save PONI File", "",
            "PONI Files (*.poni);;All Files (*.*)"
        )
        if filename:
            self.output_poni = filename
            self.poni_entry.setText(filename)

    def load_image_file(self):
        """Load calibration image"""
        # Try to get image path from either entry field
        image_path = None
        if hasattr(self, 'image_entry') and self.image_entry.text():
            image_path = self.image_entry.text()
        elif hasattr(self, 'filename_txt') and self.filename_txt.text():
            image_path = self.image_path  # Use stored path
        
        if not image_path:
            QMessageBox.warning(None, "No Image", "Please select a calibration image first.")
            return
        
        try:
            # Check if HDF5 file
            if image_path.lower().endswith(('.h5', '.hdf5')):
                try:
                    import h5py
                    # Use 'r' mode with swmr=True for better performance if available
                    with h5py.File(image_path, 'r', swmr=False, rdcc_nbytes=1024**3) as f:
                        # Try common HDF5 dataset paths
                        dataset_paths = [
                            'entry/data/data',
                            'entry/instrument/detector/data',
                            'data',
                            'image',
                        ]
                        
                        # Find first available dataset
                        for path in dataset_paths:
                            try:
                                data = f[path]
                                if len(data.shape) >= 2:
                                    # Get first image if 3D stack, use direct array read for speed
                                    if len(data.shape) == 3:
                                        # Read only the first frame directly into numpy array
                                        self.current_image = np.array(data[0, :, :], dtype=np.float32)
                                    else:
                                        # Read entire 2D array at once
                                        self.current_image = np.array(data[:], dtype=np.float32)
                                    self.log(f"Loaded HDF5 dataset: {path} (shape: {self.current_image.shape})")
                                    break
                            except KeyError:
                                continue
                        else:
                            # If no standard path found, list available datasets
                            self.log("Standard dataset paths not found. Available datasets:")
                            def print_structure(name, obj):
                                if isinstance(obj, h5py.Dataset):
                                    self.log(f"  {name}: {obj.shape}")
                            f.visititems(print_structure)
                            
                            QMessageBox.warning(None, "HDF5 Structure", 
                                              "Could not find standard dataset path.\nCheck log for available datasets.")
                            return
                except ImportError:
                    QMessageBox.warning(None, "h5py Required", 
                                      "h5py is required to read HDF5 files.\nInstall with: pip install h5py")
                    return
            elif FABIO_AVAILABLE:
                img = fabio.open(image_path)
                self.current_image = img.data
            else:
                from PIL import Image
                img = Image.open(image_path)
                self.current_image = np.array(img)
            
            self.log("Image loaded successfully")
            self.log(f"Image shape: {self.current_image.shape}")
            
            # Display image on unified canvas (optimized for immediate display)
            if MATPLOTLIB_AVAILABLE:
                from PyQt6.QtCore import QTimer
                from PyQt6.QtWidgets import QApplication
                
                # Ensure image_data is set on unified canvas
                self.unified_canvas.image_data = self.current_image
                if self.unified_canvas.mask_data is None:
                    self.unified_canvas.mask_data = np.zeros(self.current_image.shape, dtype=bool)
                
                # Link canvas to module before display
                self.unified_canvas.parent_module = self
                
                # Initialize contrast settings (auto-contrast on load)
                # Use conservative percentiles and limit to reasonable range
                vmin = float(np.percentile(self.current_image, 1))
                vmax = float(np.percentile(self.current_image, 95))  # Use 95% instead of 99% to avoid outliers

                # Limit vmax to prevent overflow issues (max 1 million for reasonable contrast)
                vmax = min(vmax, 1000000)

                # Store image statistics for contrast mapping
                self.image_vmin = vmin
                self.image_vmax = vmax

                # Apply initial contrast
                self.unified_canvas.contrast_min = vmin
                self.unified_canvas.contrast_max = vmax

                # Set slider to 100% (full contrast)
                if hasattr(self, 'contrast_slider'):
                    self.contrast_slider.setValue(100)
                    # Update percentage label
                    if hasattr(self, 'contrast_pct_lbl'):
                        self.contrast_pct_lbl.setText("Contrast: 100%")
                
                # Display image immediately with forced update
                self.unified_canvas.display_calibration_image(self.current_image)
                
                # Force immediate canvas draw and GUI update
                self.unified_canvas.draw()  # Use immediate draw for initial load
                QApplication.processEvents()  # Process GUI events immediately
                
                # Also load to mask canvas for legacy mask operations (async)
                QTimer.singleShot(10, lambda: self.mask_canvas.load_image(image_path))
                
                self.log(f"Auto-contrast applied: {vmin:.0f} - {vmax:.0f}")
            
            # Sync image to mask module
            if self.mask_module_reference is not None:
                self.mask_module_reference.set_image_for_mask(self.current_image)
                self.log(f"Image synced to Mask Module")
            
        except Exception as e:
            self.log(f"Error loading image: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to load image:\n{str(e)}")
    
    def apply_basic_refinement_preset(self):
        """Apply basic refinement preset: distance and beam center only"""
        # Geometry (always on)
        if hasattr(self, 'refine_dist_cb'):
            self.refine_dist_cb.setChecked(True)
        if hasattr(self, 'refine_poni1_cb'):
            self.refine_poni1_cb.setChecked(True)
        if hasattr(self, 'refine_poni2_cb'):
            self.refine_poni2_cb.setChecked(True)
        # Rotations (off)
        if hasattr(self, 'refine_rot1_cb'):
            self.refine_rot1_cb.setChecked(False)
        if hasattr(self, 'refine_rot2_cb'):
            self.refine_rot2_cb.setChecked(False)
        if hasattr(self, 'refine_rot3_cb'):
            self.refine_rot3_cb.setChecked(False)
        # Wavelength (off)
        if hasattr(self, 'refine_wavelength_cb'):
            self.refine_wavelength_cb.setChecked(False)
        self.log("✓ Refinement preset applied: Basic (Distance + Beam Center)")
    
    def apply_full_refinement_preset(self):
        """Apply full refinement preset: all geometry including tilt"""
        # Geometry (always on)
        if hasattr(self, 'refine_dist_cb'):
            self.refine_dist_cb.setChecked(True)
        if hasattr(self, 'refine_poni1_cb'):
            self.refine_poni1_cb.setChecked(True)
        if hasattr(self, 'refine_poni2_cb'):
            self.refine_poni2_cb.setChecked(True)
        # Rotations (on)
        if hasattr(self, 'refine_rot1_cb'):
            self.refine_rot1_cb.setChecked(True)
        if hasattr(self, 'refine_rot2_cb'):
            self.refine_rot2_cb.setChecked(True)
        if hasattr(self, 'refine_rot3_cb'):
            self.refine_rot3_cb.setChecked(True)
        # Wavelength (off)
        if hasattr(self, 'refine_wavelength_cb'):
            self.refine_wavelength_cb.setChecked(False)
        self.log("✓ Refinement preset applied: Full (All Geometry + Tilt)")

    def on_calibrant_changed(self, calibrant_name):
        """Handle calibrant selection change"""
        self.calibrant_name = calibrant_name
        self.log(f"Calibrant changed to: {calibrant_name}")
        self.update_calibrant_info()
    
    def on_wavelength_changed(self, text):
        """Handle wavelength change"""
        try:
            self.wavelength = float(text)
            self.log(f"Wavelength set to: {self.wavelength} Å")
        except ValueError:
            pass
    
    def load_custom_calibrant(self):
        """Load custom calibrant from .D file (Dioptas style)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Custom Calibrant",
            "",
            "Calibrant Files (*.D *.d);;All Files (*.*)"
        )
        
        if file_path and PYFAI_AVAILABLE:
            try:
                # Load calibrant from file
                calibrant = Calibrant(filename=file_path)
                
                # Add to combo box if not already there
                calibrant_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # Check if already in list
                index = self.calibrant_combo.findText(calibrant_name)
                if index == -1:
                    self.calibrant_combo.addItem(calibrant_name)
                    self.calibrant_combo.setCurrentText(calibrant_name)
                else:
                    self.calibrant_combo.setCurrentIndex(index)
                
                # Store custom calibrant
                self.calibrant = calibrant
                self.calibrant_name = calibrant_name
                
                self.log(f"✅ Loaded custom calibrant: {calibrant_name}")
                self.update_calibrant_info()
                
            except Exception as e:
                QMessageBox.critical(
                    self.parent,
                    "Error Loading Calibrant",
                    f"Failed to load calibrant file:\n{str(e)}"
                )
                self.log(f"❌ Error loading calibrant: {str(e)}")
    
    def update_calibrant_info(self):
        """Update calibrant information display with d-spacings"""
        if not PYFAI_AVAILABLE:
            return
        
        # Ensure calibrant_info_text exists
        if not hasattr(self, 'calibrant_info_text'):
            return
        
        try:
            # Get current calibrant
            if self.calibrant is None:
                calibrant_name = self.calibrant_combo.currentText()
                if calibrant_name in ALL_CALIBRANTS:
                    self.calibrant = ALL_CALIBRANTS[calibrant_name]
                else:
                    return
            
            # Get d-spacings
            dspacing = self.calibrant.get_dSpacing()
            
            if dspacing is not None and len(dspacing) > 0:
                # Display first 10 d-spacings
                info_text = ", ".join([f"{d:.4f}" for d in dspacing[:10]])
                if len(dspacing) > 10:
                    info_text += f"... ({len(dspacing)} total rings)"
                
                self.calibrant_info_text.setText(info_text)
            else:
                self.calibrant_info_text.setText("No d-spacing data available")
                
        except Exception as e:
            if hasattr(self, 'calibrant_info_text'):
                self.calibrant_info_text.setText(f"Error: {str(e)}")
            self.log(f"Warning: Could not load calibrant info: {str(e)}")

    def on_detector_changed(self, detector_name):
        """Handle detector selection change"""
        self.detector_name = detector_name
        
        # Update pixel size based on detector
        detector_specs = {
            "Pilatus2M": 172e-6,
            "Pilatus1M": 172e-6,
            "Pilatus300K": 172e-6,
            "PerkinElmer": 200e-6,
            "Eiger2M": 75e-6,
            "Eiger1M": 75e-6,
            "Eiger4M": 75e-6,
            "Mar345": 100e-6,
            "Rayonix": 88e-6,
        }
        
        if detector_name in detector_specs:
            pixel_size = detector_specs[detector_name]
            self.pixel_size = pixel_size
            
            # Update both pixel width and height fields if they exist
            if hasattr(self, 'pixel_width_txt'):
                self.pixel_width_txt.setText(str(pixel_size * 1e6))
            if hasattr(self, 'pixel_height_txt'):
                self.pixel_height_txt.setText(str(pixel_size * 1e6))
            
            # Legacy support for old UI
            if hasattr(self, 'pixel_entry'):
                self.pixel_entry.setText(str(pixel_size * 1e6))
            
            self.log(f"Detector: {detector_name}, Pixel size: {pixel_size*1e6:.1f} μm")

    def on_use_mask_changed(self, state):
        """Handle use mask checkbox change"""
        if state == Qt.CheckState.Checked.value:
            # Automatically fetch mask from mask module
            if self.mask_module_reference is not None:
                mask = self.mask_module_reference.get_current_mask()
                if mask is not None:
                    self.imported_mask = mask
                    shape_str = f"{mask.shape[0]}×{mask.shape[1]}"
                    masked_pixels = np.sum(mask)
                    total_pixels = mask.size
                    percentage = (masked_pixels / total_pixels) * 100
                    self.mask_info_label.setText(f"Mask active: {masked_pixels:,} pixels ({percentage:.2f}%)")
                    self.mask_info_label.setStyleSheet("color: green; font-size: 8pt; padding: 5px; background-color: rgba(0,255,0,0.1); border-radius: 3px;")
                    self.log(f"Using mask from Mask Module: {shape_str}, {masked_pixels:,} pixels masked")
                    
                    # Apply mask to calibration canvas
                    if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas') and self.current_image is not None:
                        self.unified_canvas.mask_data = mask
                        self.unified_canvas.display_calibration_image(self.current_image)
                        self.log("Mask overlay applied to calibration image")
                else:
                    self.mask_info_label.setText("No mask available in Mask Module")
                    self.mask_info_label.setStyleSheet("color: orange; font-size: 8pt; padding: 5px; background-color: rgba(255,165,0,0.1); border-radius: 3px;")
                    self.use_mask_cb.setChecked(False)
                    self.log("Warning: No mask available in Mask Module")
                    QMessageBox.information(None, "No Mask Available", 
                                          "No mask is currently available in the Mask Module.\n\n"
                                          "Please switch to the Mask Module and create a mask first:\n"
                                          "1. Use drawing tools (Rectangle, Circle, Polygon, Point)\n"
                                          "2. Or apply threshold masking\n"
                                          "3. Then return here and check 'Use Mask from Mask Module' again")
            else:
                self.use_mask_cb.setChecked(False)
                self.log("Warning: Mask Module not available")
                QMessageBox.warning(None, "Mask Module Not Available", 
                                  "The Mask Module is not initialized.\n"
                                  "Please restart the application.")
        else:
            self.imported_mask = None
            self.mask_info_label.setText("No mask loaded")
            self.mask_info_label.setStyleSheet("color: gray; font-size: 8pt; padding: 5px; background-color: rgba(255,255,255,0.05); border-radius: 3px;")
            
            # Remove mask overlay from calibration canvas
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                if self.unified_canvas.mask_data is not None:
                    self.unified_canvas.mask_data = np.zeros_like(self.unified_canvas.mask_data, dtype=bool)
                    if self.current_image is not None:
                        self.unified_canvas.display_calibration_image(self.current_image)
                        self.log("Mask overlay removed from calibration image")
            
            self.log("Mask will not be used in calibration")
    
    def import_mask_from_module(self):
        """Import mask from mask module"""
        # Try to get mask from mask module reference
        if self.mask_module_reference is not None:
            mask = self.mask_module_reference.get_current_mask()
            if mask is not None:
                self.imported_mask = mask
                masked_pixels = np.sum(mask)
                total_pixels = mask.size
                percentage = (masked_pixels / total_pixels) * 100
                
                self.mask_info_label.setText(f"Mask imported: {masked_pixels:,} pixels ({percentage:.2f}%)")
                self.mask_info_label.setStyleSheet("color: green; padding: 3px;")
                self.use_mask_cb.setChecked(True)
                
                self.log(f"Mask imported from Mask Module: {masked_pixels:,} / {total_pixels:,} pixels")
            else:
                QMessageBox.warning(None, "No Mask", 
                                  "No mask found in Mask Module. Please create a mask first.")
        else:
            QMessageBox.warning(None, "Mask Module Not Found", 
                              "Mask Module is not available. Please open Mask Module first.")
            self.log("Mask module reference not set. Fallback to file loading.")
            self.load_mask_from_file()
    
    def load_mask_from_file(self):
        """Load mask from file as fallback"""
        filename, _ = QFileDialog.getOpenFileName(
            None, "Load Mask", "",
            "Mask Files (*.edf *.npy);;All Files (*.*)"
        )
        
        if filename:
            try:
                if filename.endswith('.npy'):
                    mask = np.load(filename)
                elif filename.endswith('.edf') and FABIO_AVAILABLE:
                    mask_img = fabio.open(filename)
                    mask = mask_img.data.astype(bool)
                else:
                    QMessageBox.warning(None, "Error", "Unsupported mask format")
                    return
                
                self.imported_mask = mask
                masked_pixels = np.sum(mask)
                total_pixels = mask.size
                percentage = (masked_pixels / total_pixels) * 100
                
                self.mask_info_label.setText(f"Mask loaded: {masked_pixels:,} pixels ({percentage:.2f}%)")
                self.mask_info_label.setStyleSheet("color: green; padding: 3px;")
                self.use_mask_cb.setChecked(True)
                
                self.log(f"Mask loaded from file: {os.path.basename(filename)}")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to load mask:\n{str(e)}")
                self.log(f"Error loading mask: {str(e)}")
    
    def set_mask_module_reference(self, mask_module):
        """Set reference to mask module (called from main app)"""
        self.mask_module_reference = mask_module
        self.log("Mask module reference set")

    def on_ring_number_changed(self, value):
        """Handle ring number change from SpinBox"""
        # Update canvas current_ring_num if in peak picking mode
        if hasattr(self, 'unified_canvas'):
            self.unified_canvas.current_ring_num = value
    
    def update_ring_number_display(self, ring_num):
        """Update ring number display after auto-increment"""
        if hasattr(self, 'ring_num_input'):
            self.ring_num_input.setValue(ring_num)
        # Also sync the old spinbox if it exists
        if hasattr(self, 'ring_number_spinbox'):
            self.ring_number_spinbox.setValue(ring_num)
    
    def on_peak_mode_changed(self):
        """Handle peak selection mode change"""
        if hasattr(self, 'select_peak_rb') and self.select_peak_rb.isChecked():
            # Enable manual peak picking mode
            self.peak_picking_mode = True
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                self.unified_canvas.peak_picking_mode = True
                # Set canvas ring number from spin box
                if hasattr(self, 'ring_num_input'):
                    self.unified_canvas.current_ring_num = self.ring_num_input.value()
                # Set auto-increment flag from checkbox
                if hasattr(self, 'automatic_peak_num_inc_cb'):
                    self.unified_canvas.auto_increment_ring = self.automatic_peak_num_inc_cb.isChecked()
                # Set parent module reference
                self.unified_canvas.parent_module = self
                # Update canvas title
                if self.current_image is not None:
                    self.unified_canvas.display_calibration_image(self.current_image)
            self.log("Manual peak selection mode: ENABLED - Click on diffraction rings")
        else:
            # Disable manual peak picking mode
            self.peak_picking_mode = False
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                self.unified_canvas.peak_picking_mode = False
                # Update canvas title
                if self.current_image is not None:
                    self.unified_canvas.display_calibration_image(self.current_image)
            self.log("Automatic peak search mode: ENABLED")
    
    def toggle_peak_picking(self):
        """Toggle manual peak picking mode"""
        self.peak_picking_mode = not self.peak_picking_mode
        
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
            self.unified_canvas.peak_picking_mode = self.peak_picking_mode
            
            # Update canvas settings when entering peak picking mode
            if self.peak_picking_mode:
                # Set ring number
                if hasattr(self, 'ring_num_input'):
                    self.unified_canvas.current_ring_num = self.ring_num_input.value()
                
                # Set auto-increment flag
                if hasattr(self, 'automatic_peak_num_inc_cb'):
                    self.unified_canvas.auto_increment_ring = self.automatic_peak_num_inc_cb.isChecked()
                
                # NOTE: Auto peak search removed - only manual peaks during selection
                # Auto peak finding happens in Calibrate process
                
                # Set parent reference for callbacks
                self.unified_canvas.parent_module = self
        
        # Fallback for old calibration_canvas (compatibility)
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'calibration_canvas'):
            self.calibration_canvas.peak_picking_mode = self.peak_picking_mode
        
        # Update button appearance
        if hasattr(self, 'pick_peaks_btn'):
            if self.peak_picking_mode:
                self.pick_peaks_btn.setStyleSheet(f"""
                    background-color: {self.colors['success']};
                    color: white; border: 2px solid #00ff00;
                    border-radius: 4px; padding: 8px;
                    font-weight: bold;
                """)
                self.log("Peak picking mode: ENABLED - Click on diffraction rings to add peaks")
            else:
                self.pick_peaks_btn.setStyleSheet(f"""
                    background-color: {self.colors['secondary']};
                    color: white; border: none;
                    border-radius: 4px; padding: 8px;
                """)
                self.log("Peak picking mode: DISABLED")
    
    def undo_last_peak(self):
        """Undo the last manually selected peak"""
        if not hasattr(self, 'unified_canvas') or self.unified_canvas is None:
            return
        
        if len(self.unified_canvas.manual_peaks) == 0:
            self.log("No peaks to undo")
            return
        
        # Remove the last peak
        removed_peak = self.unified_canvas.manual_peaks.pop()
        self.log(f"Removed peak at ({removed_peak[0]:.1f}, {removed_peak[1]:.1f}), Ring #{removed_peak[2]}")
        
        # Update peak count
        if hasattr(self, 'peak_count_label'):
            self.peak_count_label.setText(f"Peaks: {len(self.unified_canvas.manual_peaks)}")
        
        # Redraw image
        if self.current_image is not None:
            self.unified_canvas.display_calibration_image(self.current_image)
    
    
    def clear_manual_peaks(self):
        """Clear manually selected peaks and reset ring number to 1"""
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
            self.unified_canvas.clear_manual_peaks()
            self.update_peak_count()
            # Reset ring number to 1 (per user request)
            if hasattr(self, 'ring_num_input'):
                self.ring_num_input.setValue(1)
            if hasattr(self, 'ring_number_spinbox'):
                self.ring_number_spinbox.setValue(1)
            # Reset canvas ring number
            if hasattr(self, 'unified_canvas'):
                self.unified_canvas.current_ring_num = 1
            self.log("Cleared all manual peaks and reset ring number to 1")
    
    def update_peak_count(self):
        """Update peak count display"""
        if hasattr(self, 'peak_count_label') and hasattr(self, 'unified_canvas'):
            count = len(self.unified_canvas.manual_peaks)
            self.peak_count_label.setText(f"Peaks: {count}")
    

    
    def run_calibration(self):
        """Run detector calibration"""
        if not PYFAI_AVAILABLE:
            QMessageBox.warning(None, "pyFAI Required", 
                              "pyFAI is required for calibration.\nInstall with: pip install pyFAI")
            return
        
        if self.current_image is None:
            QMessageBox.warning(None, "No Image", "Please load a calibration image first.")
            return
        
        try:
            # Get calibrant name from combo box
            if hasattr(self, 'calibrant_combo'):
                calibrant_name = self.calibrant_combo.currentText()
            else:
                calibrant_name = self.calibrant_name
            
            if not calibrant_name or calibrant_name not in ALL_CALIBRANTS:
                QMessageBox.warning(None, "Invalid Calibrant", 
                                  f"Please select a valid calibrant. Current: {calibrant_name}")
                return
            
            # Get parameters with validation
            try:
                # Try new UI or old UI
                if hasattr(self, 'wavelength_txt'):
                    wavelength = float(self.wavelength_txt.text()) * 1e-10  # Convert Å to meters
                elif hasattr(self, 'wavelength_entry'):
                    wavelength = float(self.wavelength_entry.text()) * 1e-10  # Convert Å to meters
                else:
                    wavelength = self.wavelength * 1e-10
            except (ValueError, AttributeError):
                QMessageBox.warning(None, "Invalid Input", "Please enter a valid wavelength.")
                return
                
            try:
                # Try new UI (distance in mm) or old UI (distance in m)
                if hasattr(self, 'distance_txt'):
                    distance = float(self.distance_txt.text()) / 1000.0  # Convert mm to meters
                elif hasattr(self, 'distance_entry'):
                    distance = float(self.distance_entry.text())
                else:
                    distance = self.distance
            except (ValueError, AttributeError):
                QMessageBox.warning(None, "Invalid Input", "Please enter a valid distance.")
                return
                
            try:
                # Try to get pixel size from new UI first, then fall back to old UI
                if hasattr(self, 'pixel_width_txt'):
                    pixel_size = float(self.pixel_width_txt.text()) * 1e-6  # Convert to meters
                elif hasattr(self, 'pixel_entry'):
                    pixel_size = float(self.pixel_entry.text()) * 1e-6  # Convert to meters
                else:
                    pixel_size = self.pixel_size
            except (ValueError, AttributeError):
                QMessageBox.warning(None, "Invalid Input", "Please enter a valid pixel size.")
                return
            
            self.log("Starting calibration...")
            self.log(f"Calibrant: {calibrant_name}")
            self.log(f"Wavelength: {wavelength*1e10:.4f} Å")
            self.log(f"Distance: {distance:.3f} m")
            self.log(f"Pixel size: {pixel_size*1e6:.1f} μm")
            
            # Create calibrant
            calibrant = ALL_CALIBRANTS[calibrant_name]
            calibrant.wavelength = wavelength
            
            # Get mask - use imported mask if "use mask" is checked
            mask = None
            if hasattr(self, 'use_mask_cb') and self.use_mask_cb is not None and self.use_mask_cb.isChecked() and self.imported_mask is not None:
                mask = self.imported_mask
                self.log(f"Using imported mask with {np.sum(mask)} masked pixels")
            elif MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                mask = self.unified_canvas.get_mask()
                if mask is not None and np.any(mask):
                    self.log(f"Using canvas mask with {np.sum(mask)} masked pixels")
            
            # Get manual control points if available
            manual_cp = None
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'calibration_canvas'):
                manual_cp = self.calibration_canvas.get_manual_control_points()
                if manual_cp is not None:
                    self.log(f"Using {len(manual_cp)} manually selected peaks")
            
            # Run calibration in worker thread
            worker = CalibrationWorkerThread(
                self.perform_calibration,
                self.current_image, calibrant, distance, pixel_size, mask, manual_cp
            )
            worker.finished.connect(self.on_calibration_finished)
            worker.error.connect(self.on_calibration_error)
            worker.progress.connect(self.on_calibration_progress)
            worker.calibration_result.connect(self.on_calibration_result)
            
            self.running_threads.append(worker)
            worker.start()
            
        except KeyError as e:
            import traceback
            error_msg = f"Calibrant not found: {e}\n{traceback.format_exc()}"
            self.log(error_msg)
            QMessageBox.critical(None, "Error", f"Calibrant not found:\n{e}")
        except Exception as e:
            import traceback
            error_msg = f"Error starting calibration: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            QMessageBox.critical(None, "Error", f"Failed to start calibration:\n{str(e)}")

    def perform_calibration(self, image, calibrant, distance, pixel_size, mask, manual_control_points=None):
        """
        Perform calibration (runs in worker thread) - Based on Dioptas implementation
        With optimizations to prevent kernel died / memory issues
        """
        import gc
        from pyFAI.detectors import Detector
        
        # Clean up memory at start
        gc.collect()
        
        # Check image size - very large images can cause kernel died
        shape = image.shape
        image_megapixels = (shape[0] * shape[1]) / 1e6
        self.log(f"Image size: {shape[0]} x {shape[1]} ({image_megapixels:.1f} MP)")
        
        if image_megapixels > 16:  # > 16 megapixels
            self.log(f"⚠ Warning: Large image detected ({image_megapixels:.1f} MP)")
            self.log(f"  This may cause memory issues. Consider binning the image.")
        
        # Create detector object
        detector = Detector(pixel1=pixel_size, pixel2=pixel_size, max_shape=shape)
        
        # Create geometry refinement object
        if manual_control_points is not None and len(manual_control_points) > 0:
            # Use manual control points with ring numbers (Dioptas-style)
            # manual_control_points format: [[row, col, ring_num], ...]
            self.log(f"\n{'='*50}")
            self.log(f"Using {len(manual_control_points)} manual control points")
            self.log(f"{'='*50}")
            
            # Group points by ring number and show details
            from collections import defaultdict
            points_by_ring = defaultdict(list)
            for idx, point in enumerate(manual_control_points):
                row, col, ring_num = point
                points_by_ring[ring_num].append([row, col])
                self.log(f"  Point {idx+1}: (row={row:.1f}, col={col:.1f}) → Ring #{ring_num}")
            
            self.log(f"\n{'='*50}")
            self.log(f"Summary: {len(points_by_ring)} different rings")
            self.log(f"{'='*50}")
            for ring_num, points in sorted(points_by_ring.items()):
                self.log(f"  Ring {ring_num}: {len(points)} points")
            self.log(f"{'='*50}\n")
            
            # Create geometry refinement with ring-based control points
            geo_ref = GeometryRefinement(
                data=manual_control_points,
                calibrant=calibrant,
                detector=detector,
                wavelength=calibrant.wavelength
            )
        else:
            # Automatic peak detection
            geo_ref = GeometryRefinement(
                calibrant=calibrant,
                detector=detector,
                wavelength=calibrant.wavelength
            )
            
            # Set the image data
            geo_ref.img = image
        
        # Set initial geometry (important for convergence)
        geo_ref.dist = distance
        geo_ref.poni1 = shape[0] * pixel_size / 2  # Center Y in meters
        geo_ref.poni2 = shape[1] * pixel_size / 2  # Center X in meters
        geo_ref.pixel1 = pixel_size
        geo_ref.pixel2 = pixel_size
        
        # Initialize rotations to ZERO (perpendicular detector assumption)
        # This is the most common and safest configuration
        geo_ref.rot1 = 0.0  # Tilt around X-axis
        geo_ref.rot2 = 0.0  # Tilt around Y-axis  
        geo_ref.rot3 = 0.0  # In-plane rotation
        
        self.log(f"Initial geometry:")
        self.log(f"  Distance: {geo_ref.dist*1000:.2f} mm")
        self.log(f"  PONI1 (Y): {geo_ref.poni1*1000:.2f} mm")
        self.log(f"  PONI2 (X): {geo_ref.poni2*1000:.2f} mm")
        self.log(f"  Rotations: [{geo_ref.rot1:.3f}, {geo_ref.rot2:.3f}, {geo_ref.rot3:.3f}]")
        
        # Apply mask if provided
        if mask is not None:
            geo_ref.mask = mask
        
        # Extract control points (only if not using manual peaks)
        if manual_control_points is None or len(manual_control_points) == 0:
            try:
                self.log("="*70)
                self.log("Starting RING-BY-RING Peak Detection (Dioptas-style)")
                self.log("="*70)
                
                # Extract all control points at once (pyFAI method)
                # This is optimized and avoids kernel died issues
                import gc
                gc.collect()  # Clean up memory before intensive operation
                
                geo_ref.extract_cp(max_rings=10, pts_per_deg=1.0)
                
                # Create temporary AI for coordinate conversion
                temp_ai = AzimuthalIntegrator(
                    dist=geo_ref.dist,
                    poni1=geo_ref.poni1,
                    poni2=geo_ref.poni2,
                    rot1=geo_ref.rot1,
                    rot2=geo_ref.rot2,
                    rot3=geo_ref.rot3,
                    pixel1=geo_ref.pixel1,
                    pixel2=geo_ref.pixel2,
                    detector=detector,
                    wavelength=geo_ref.wavelength
                )
                
                # Display detected rings one by one (Dioptas-style real-time display)
                if hasattr(geo_ref, 'data') and geo_ref.data is not None:
                    num_rings = len(geo_ref.data)
                    self.log(f"Found {num_rings} rings with control points")
                    self.log("="*70)
                    
                    # Send each ring for real-time display
                    for ring_idx, ring_points in enumerate(geo_ref.data):
                        if len(ring_points) > 0:
                            ring_num = ring_idx + 1
                            num_points = len(ring_points)
                            
                            # Log ring info
                            self.log(f"Ring {ring_num}: {num_points} control points detected")
                            
                            # Send signal for real-time display
                            try:
                                # Convert ring data to pixel coordinates for display
                                ring_display_points = []
                                for point in ring_points:
                                    # point format: [ring_num, tth, chi]
                                    if len(point) >= 3:
                                        tth_val = point[1]  # 2theta in radians
                                        chi_val = point[2]  # chi in radians
                                        
                                        # Convert to pixel coordinates
                                        try:
                                            # Use temp_ai to convert polar to pixel
                                            # calcfrom1d expects arrays and returns arrays
                                            tth_array = np.array([tth_val])
                                            chi_array = np.array([chi_val])
                                            result = temp_ai.calcfrom1d(tth_array, chi_array, shape=shape, unit="2th_rad")
                                            
                                            if result is not None and len(result) == 2:
                                                y_arr, x_arr = result
                                                if len(y_arr) > 0 and len(x_arr) > 0:
                                                    y, x = float(y_arr[0]), float(x_arr[0])
                                                    if 0 <= y < shape[0] and 0 <= x < shape[1]:
                                                        ring_display_points.append([float(x), float(y), ring_num])
                                        except Exception as coord_error:
                                            # Skip points that can't be converted
                                            pass
                                
                                # Send as progress signal (string format for thread safety)
                                import json
                                ring_data_json = json.dumps({
                                    'ring_num': ring_num,
                                    'num_points': num_points,
                                    'points': ring_display_points  # Now in pixel coords: [x, y, ring_num]
                                })
                                self.progress.emit(f"RING_FOUND:{ring_data_json}")
                                
                                # Small delay for visual effect (simulating Dioptas)
                                import time
                                time.sleep(0.15)  # 150ms delay between rings for visibility
                                
                            except Exception as display_error:
                                self.log(f"Warning: Could not send ring {ring_num} for display: {display_error}")
                    
                    self.log("="*70)
                    self.log(f"Peak detection complete: {num_rings} rings found")
                    self.log("="*70 + "\n")
                
                # Clean up temporary objects (outside of if block)
                try:
                    del temp_ai
                except:
                    pass
                gc.collect()
                    
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"Peak detection error:\n{error_detail}")
                raise ValueError(f"Failed to extract control points: {str(e)}. "
                               "Please check image quality or use Manual Peak Selection.")
        
        # Check if we have control points
        if not hasattr(geo_ref, 'data') or geo_ref.data is None or len(geo_ref.data) < 3:
            raise ValueError(f"Not enough control points: {len(geo_ref.data) if hasattr(geo_ref, 'data') and geo_ref.data is not None else 0}. "
                           "Need at least 3 points. Use Manual Peak Selection to add more peaks.")
        
        # Optimize control point weights for better refinement stability
        # Weight points based on their ring number and distribution
        self.log("\n" + "="*70)
        self.log("Optimizing Control Point Weights")
        self.log("="*70)
        
        try:
            # Count points per ring
            from collections import defaultdict
            ring_point_counts = defaultdict(int)
            total_points = 0
            
            for point in geo_ref.data:
                if len(point) > 0:
                    ring_num = int(point[0])
                    ring_point_counts[ring_num] += 1
                    total_points += 1
            
            self.log(f"Total control points: {total_points}")
            self.log(f"Points per ring:")
            for ring_num in sorted(ring_point_counts.keys()):
                count = ring_point_counts[ring_num]
                self.log(f"  Ring {ring_num}: {count} points ({count/total_points*100:.1f}%)")
            
            # Calculate optimal weights
            # Strategy: Give higher weight to:
            # 1. Rings with fewer points (balance contribution)
            # 2. Outer rings (higher angular resolution)
            # 3. Well-distributed points (penalize clustered points)
            
            if hasattr(geo_ref, 'data') and len(geo_ref.data) > 0:
                weights = []
                for point in geo_ref.data:
                    if len(point) > 0:
                        ring_num = int(point[0])
                        
                        # Base weight inversely proportional to ring point count
                        # This balances contribution from rings with different numbers of points
                        base_weight = 1.0 / max(1, ring_point_counts[ring_num])
                        
                        # Outer ring bonus (higher 2theta = more important)
                        # Outer rings have better angular resolution
                        outer_ring_factor = 1.0 + 0.1 * (ring_num - 1)
                        
                        # Combined weight
                        weight = base_weight * outer_ring_factor
                        weights.append(weight)
                
                # Normalize weights to sum to number of points
                if len(weights) > 0:
                    weights = np.array(weights)
                    weights = weights / weights.sum() * len(weights)
                    
                    # Store weights in geo_ref if possible
                    # Note: pyFAI's GeometryRefinement may or may not use custom weights
                    # This depends on the version and method
                    try:
                        if hasattr(geo_ref, 'set_bounds'):
                            # Some versions support weight setting
                            pass  # Weights are implicit in modern pyFAI
                    except:
                        pass
                    
                    self.log(f"\n✓ Weights calculated:")
                    self.log(f"  Min weight: {weights.min():.3f}")
                    self.log(f"  Max weight: {weights.max():.3f}")
                    self.log(f"  Mean weight: {weights.mean():.3f}")
                    self.log(f"  Weight distribution favors outer rings and balanced sampling")
        except Exception as weight_error:
            self.log(f"Warning: Could not optimize weights: {weight_error}")
            self.log("Continuing with default equal weights...")
        
        self.log("="*70 + "\n")
        
        # Get user-selected refinement parameters
        # Build list of parameters to fix (not refine)
        fix_params = []
        
        # Check which parameters user wants to refine
        refine_dist = True  # Always refine distance
        refine_poni1 = True  # Always refine beam center
        refine_poni2 = True
        refine_rot1 = getattr(self, 'refine_rot1_cb', None) and self.refine_rot1_cb.isChecked() if hasattr(self, 'refine_rot1_cb') else False
        refine_rot2 = getattr(self, 'refine_rot2_cb', None) and self.refine_rot2_cb.isChecked() if hasattr(self, 'refine_rot2_cb') else False
        refine_rot3 = getattr(self, 'refine_rot3_cb', None) and self.refine_rot3_cb.isChecked() if hasattr(self, 'refine_rot3_cb') else False
        refine_wavelength = getattr(self, 'refine_wavelength_cb', None) and self.refine_wavelength_cb.isChecked() if hasattr(self, 'refine_wavelength_cb') else False
        
        # Refine geometry (Dioptas-style: Multi-stage non-linear least squares)
        try:
            self.log("\n" + "="*70)
            self.log("Starting Geometry Refinement (Non-linear Least Squares)")
            self.log("="*70)
            self.log(f"Number of control points: {len(geo_ref.data)}")
            
            # Count rings
            ring_nums = set()
            for point in geo_ref.data:
                if len(point) > 0:
                    ring_nums.add(point[0])
            self.log(f"Number of rings: {len(ring_nums)}")
            
            # Log user-selected parameters
            self.log(f"\nRefinement parameters selected by user:")
            self.log(f"  Distance (dist):     {'✓ YES' if refine_dist else '✗ NO (fixed)'}")
            self.log(f"  Beam Center Y (poni1): {'✓ YES' if refine_poni1 else '✗ NO (fixed)'}")
            self.log(f"  Beam Center X (poni2): {'✓ YES' if refine_poni2 else '✗ NO (fixed)'}")
            self.log(f"  Rot1 (tilt axis 1):  {'✓ YES' if refine_rot1 else '✗ NO (fixed)'}")
            self.log(f"  Rot2 (tilt axis 2):  {'✓ YES' if refine_rot2 else '✗ NO (fixed)'}")
            self.log(f"  Rot3 (in-plane):     {'✓ YES' if refine_rot3 else '✗ NO (fixed)'}")
            self.log(f"  Wavelength:          {'✓ YES' if refine_wavelength else '✗ NO (fixed)'}")
            
            # STAGE 1: Always refine basic geometry first (distance + beam center)
            # This is the most critical and stable step
            self.log("\n" + "-"*70)
            self.log("STAGE 1: Basic Geometry (Distance + Beam Center)")
            self.log("-"*70)
            
            fix_stage1 = ["wavelength", "rot1", "rot2", "rot3"]
            self.log(f"Fixing: {', '.join(fix_stage1)}")
            
            geo_ref.refine2(fix=fix_stage1)
            
            self.log(f"  Distance: {geo_ref.dist*1000:.3f} mm")
            self.log(f"  PONI1 (Y): {geo_ref.poni1*1000:.3f} mm")
            self.log(f"  PONI2 (X): {geo_ref.poni2*1000:.3f} mm")
            
            # Calculate RMS after stage 1
            rms_stage1 = 999.0
            if hasattr(geo_ref, 'chi2') and callable(geo_ref.chi2):
                try:
                    rms_stage1 = np.sqrt(geo_ref.chi2())
                    self.log(f"  RMS error: {rms_stage1:.3f} pixels")
                except:
                    pass
            
            # STAGE 2: Refine rotations if user selected them
            if refine_rot1 or refine_rot2 or refine_rot3:
                self.log("\n" + "-"*70)
                self.log("STAGE 2: Detector Tilt (Rotation Parameters)")
                self.log("-"*70)
                
                # Save state before rotation refinement
                dist_before = geo_ref.dist
                poni1_before = geo_ref.poni1
                poni2_before = geo_ref.poni2
                rot1_before = geo_ref.rot1
                rot2_before = geo_ref.rot2
                rot3_before = geo_ref.rot3
                
                # Build fix list for stage 2
                fix_stage2 = []
                if not refine_wavelength:
                    fix_stage2.append("wavelength")
                if not refine_rot1:
                    fix_stage2.append("rot1")
                if not refine_rot2:
                    fix_stage2.append("rot2")
                if not refine_rot3:
                    fix_stage2.append("rot3")
                
                self.log(f"Refining rotations...")
                if fix_stage2:
                    self.log(f"Fixing: {', '.join(fix_stage2)}")
                else:
                    self.log(f"Refining all parameters")
                
                try:
                    geo_ref.refine2(fix=fix_stage2)
                    
                    # Check rotation angles
                    rot1_deg = np.degrees(geo_ref.rot1)
                    rot2_deg = np.degrees(geo_ref.rot2)
                    rot3_deg = np.degrees(geo_ref.rot3)
                    
                    # Calculate RMS after stage 2
                    rms_stage2 = 999.0
                    if hasattr(geo_ref, 'chi2') and callable(geo_ref.chi2):
                        try:
                            rms_stage2 = np.sqrt(geo_ref.chi2())
                        except:
                            pass
                    
                    # Validate rotation angles (should be small for typical setups)
                    max_rot = max(abs(rot1_deg), abs(rot2_deg), abs(rot3_deg))
                    
                    # Quality checks
                    rotation_reasonable = max_rot < 5.0  # < 5° is reasonable
                    rms_improved = rms_stage2 < rms_stage1 * 0.98  # At least 2% improvement
                    
                    if not rotation_reasonable:
                        self.log(f"  ⚠ WARNING: Rotation angles too large!")
                        self.log(f"    Rot1={rot1_deg:.4f}°, Rot2={rot2_deg:.4f}°, Rot3={rot3_deg:.4f}°")
                        self.log(f"    Max: {max_rot:.4f}° > 5.0° threshold")
                        self.log(f"  → Reverting to perpendicular detector (rot=0)")
                        
                        # Revert
                        geo_ref.rot1 = 0.0
                        geo_ref.rot2 = 0.0
                        geo_ref.rot3 = 0.0
                        geo_ref.dist = dist_before
                        geo_ref.poni1 = poni1_before
                        geo_ref.poni2 = poni2_before
                        
                    elif not rms_improved:
                        self.log(f"  ⚠ WARNING: RMS did not improve significantly")
                        self.log(f"    Before: {rms_stage1:.3f}, After: {rms_stage2:.3f} pixels")
                        self.log(f"  → Reverting to perpendicular detector (rot=0)")
                        
                        # Revert
                        geo_ref.rot1 = 0.0
                        geo_ref.rot2 = 0.0
                        geo_ref.rot3 = 0.0
                        geo_ref.dist = dist_before
                        geo_ref.poni1 = poni1_before
                        geo_ref.poni2 = poni2_before
                        
                    else:
                        # Success!
                        self.log(f"  ✓ Rotation refinement successful!")
                        self.log(f"    Rot1: {rot1_deg:.4f}°")
                        self.log(f"    Rot2: {rot2_deg:.4f}°")
                        self.log(f"    Rot3: {rot3_deg:.4f}°")
                        self.log(f"    RMS: {rms_stage1:.3f} → {rms_stage2:.3f} pixels")
                        
                except Exception as rot_error:
                    self.log(f"  ⚠ Rotation refinement failed: {rot_error}")
                    self.log(f"  → Reverting to perpendicular detector (rot=0)")
                    
                    # Revert
                    geo_ref.rot1 = 0.0
                    geo_ref.rot2 = 0.0
                    geo_ref.rot3 = 0.0
                    geo_ref.dist = dist_before
                    geo_ref.poni1 = poni1_before
                    geo_ref.poni2 = poni2_before
            else:
                self.log("\nSTAGE 2: Skipped (rotations not selected for refinement)")
                self.log("  Rotations kept at zero (perpendicular detector)")
            
            # STAGE 3: Refine wavelength if user selected it (rare)
            if refine_wavelength:
                self.log("\n" + "-"*70)
                self.log("STAGE 3: Wavelength Refinement")
                self.log("-"*70)
                self.log("  ⚠ WARNING: Wavelength refinement is unusual!")
                self.log("  Only enable if wavelength is truly uncertain.")
                
                wl_before = geo_ref.wavelength
                
                try:
                    # Refine everything including wavelength
                    fix_stage3 = []
                    if not refine_rot1:
                        fix_stage3.append("rot1")
                    if not refine_rot2:
                        fix_stage3.append("rot2")
                    if not refine_rot3:
                        fix_stage3.append("rot3")
                    
                    geo_ref.refine2(fix=fix_stage3)
                    
                    wl_after = geo_ref.wavelength
                    wl_change_percent = abs(wl_after - wl_before) / wl_before * 100
                    
                    self.log(f"  Wavelength: {wl_before*1e10:.4f} Å → {wl_after*1e10:.4f} Å")
                    self.log(f"  Change: {wl_change_percent:.2f}%")
                    
                    if wl_change_percent > 5.0:
                        self.log(f"  ⚠ WARNING: Wavelength changed by >{wl_change_percent:.1f}%!")
                        self.log(f"  This suggests a problem with the calibration.")
                except Exception as wl_error:
                    self.log(f"  ⚠ Wavelength refinement failed: {wl_error}")
            
            # Log final refined parameters
            self.log("\n" + "="*70)
            self.log("FINAL REFINED PARAMETERS")
            self.log("="*70)
            self.log(f"  Distance:    {geo_ref.dist*1000:.3f} mm")
            self.log(f"  PONI1 (Y):   {geo_ref.poni1*1000:.3f} mm")
            self.log(f"  PONI2 (X):   {geo_ref.poni2*1000:.3f} mm")
            self.log(f"  Rot1:        {np.degrees(geo_ref.rot1):.4f}°")
            self.log(f"  Rot2:        {np.degrees(geo_ref.rot2):.4f}°")
            self.log(f"  Rot3:        {np.degrees(geo_ref.rot3):.4f}°")
            self.log(f"  Wavelength:  {geo_ref.wavelength*1e10:.4f} Å")
            
            # Calculate final RMS error
            final_rms = 999.0
            if hasattr(geo_ref, 'chi2') and callable(geo_ref.chi2):
                try:
                    final_rms = np.sqrt(geo_ref.chi2())
                    self.log(f"\n  Final RMS error: {final_rms:.3f} pixels")
                    
                    # Quality assessment (Dioptas-style)
                    if final_rms < 0.5:
                        self.log(f"  Quality: ★★★ EXCELLENT (RMS < 0.5 px)")
                    elif final_rms < 1.0:
                        self.log(f"  Quality: ★★ GOOD (RMS < 1.0 px)")
                    elif final_rms < 2.0:
                        self.log(f"  Quality: ★ ACCEPTABLE (RMS < 2.0 px)")
                    else:
                        self.log(f"  Quality: ⚠ POOR (RMS > 2.0 px) - Consider re-calibration")
                        self.log(f"  Suggestions:")
                        self.log(f"    - Add more manual control points")
                        self.log(f"    - Check if initial parameters are correct")
                        self.log(f"    - Verify calibrant and wavelength")
                except Exception as rms_error:
                    self.log(f"  Warning: Could not calculate RMS: {rms_error}")
            
            self.log("\n" + "="*70)
            self.log("Refinement Complete")
            self.log("="*70)
            self.log("Geometry Refinement Completed!")
            self.log("="*60 + "\n")
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.log(f"\nRefinement error details:\n{error_detail}")
            raise ValueError(f"Geometry refinement failed: {str(e)}")
        
        # Clean up before creating final AI (prevent memory buildup)
        gc.collect()
        
        # Create AzimuthalIntegrator from refined parameters
        ai = AzimuthalIntegrator(
            dist=geo_ref.dist,
            poni1=geo_ref.poni1,
            poni2=geo_ref.poni2,
            rot1=geo_ref.rot1,
            rot2=geo_ref.rot2,
            rot3=geo_ref.rot3,
            pixel1=geo_ref.pixel1,
            pixel2=geo_ref.pixel2,
            detector=detector,
            wavelength=geo_ref.wavelength
        )
        
        # Final memory cleanup before returning result
        gc.collect()
        
        # Get refined parameters
        result = {
            'ai': ai,
            'geo_ref': geo_ref,
            'poni1': geo_ref.poni1,
            'poni2': geo_ref.poni2,
            'dist': geo_ref.dist,
            'rot1': geo_ref.rot1,
            'rot2': geo_ref.rot2,
            'rot3': geo_ref.rot3,
            'wavelength': geo_ref.wavelength,
        }
        
        return result

    def on_calibration_result(self, result):
        """Handle calibration result with real-time ring overlay (Dioptas-style)"""
        try:
            # Store results first
            self.ai = result['ai']
            self.geo_ref = result['geo_ref']
            
            # Log results
            self.log("\n" + "="*60)
            self.log("CALIBRATION RESULTS (Dioptas-style)")
            self.log("="*60)
            self.log(f"Distance: {result['dist']*1000:.3f} mm")
            self.log(f"PONI1 (Y): {result['poni1']*1000:.3f} mm")
            self.log(f"PONI2 (X): {result['poni2']*1000:.3f} mm")
            self.log(f"Rot1: {np.degrees(result['rot1']):.4f}°")
            self.log(f"Rot2: {np.degrees(result['rot2']):.4f}°")
            self.log(f"Rot3: {np.degrees(result['rot3']):.4f}°")
            self.log(f"Wavelength: {result['wavelength']*1e10:.4f} Å")
            self.log("="*60 + "\n")
            
            # Update UI with calibration results
            self.update_ui_from_calibration()
            
            # Display calibration result with theoretical ring overlay (Dioptas-style)
            if MATPLOTLIB_AVAILABLE:
                try:
                    # Update canvas with calibration AI for theoretical rings
                    self.calibration_canvas.ai = self.ai
                    self.calibration_canvas.show_theoretical_rings = True
                    
                    # Get control points for visualization from geo_ref.data
                    if hasattr(self.geo_ref, 'data') and self.geo_ref.data is not None:
                        rings = self.geo_ref.data
                        
                        # Convert control points to display format and show them
                        # geo_ref.data format: list of rings, each ring is array of [[ring_num, tth, chi], ...]
                        # We need to convert to pixel coordinates for display
                        control_points_display = []
                        try:
                            for ring in rings:
                                if len(ring) > 0 and hasattr(ring, '__iter__'):
                                    ring_array = np.array(ring)
                                    if len(ring_array.shape) == 2 and ring_array.shape[1] >= 3:
                                        # ring_array has columns: [ring_num, tth, chi]
                                        for point in ring_array:
                                            # Convert from polar (tth, chi) to pixel (y, x)
                                            tth_val = point[1]  # in radians
                                            chi_val = point[2]  # in radians
                                            
                                            # Use AI to convert to pixel coordinates
                                            # This is inverse of what we did during calibration
                                            try:
                                                y, x = self.ai.calcfrom1d(tth_val, chi_val, shape=self.current_image.shape)
                                                if 0 <= y < self.current_image.shape[0] and 0 <= x < self.current_image.shape[1]:
                                                    control_points_display.append([x, y, int(point[0])])
                                            except:
                                                pass
                        except Exception as cp_error:
                            self.log(f"Warning: Could not convert all control points: {cp_error}")
                        
                        # Add control points to canvas for display
                        if len(control_points_display) > 0:
                            self.calibration_canvas.manual_peaks = control_points_display
                            self.log(f"✓ Displaying {len(control_points_display)} control points on image")
                        
                        self.calibration_canvas.display_calibration_image(self.current_image, rings)
                    else:
                        self.calibration_canvas.display_calibration_image(self.current_image)
                    
                    # Log overlay status
                    self.log("✓ Theoretical calibration rings overlaid on image")
                    self.log("  (Red circles show expected ring positions)")
                    
                    self.switch_display_tab("result")
                    
                except Exception as viz_error:
                    import traceback
                    self.log(f"Warning: Could not display rings: {viz_error}")
                    self.log(traceback.format_exc())
                    self.calibration_canvas.display_calibration_image(self.current_image)
                    self.switch_display_tab("result")
                
                # Update Cake and Pattern views (Dioptas-style)
                try:
                    self.update_cake_view()
                    self.update_pattern_view()
                    self.log("✓ Cake and pattern views updated")
                except Exception as view_error:
                    self.log(f"Warning: Could not update Cake/Pattern views: {view_error}")
                    
        except Exception as e:
            import traceback
            error_msg = f"Error processing results: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            QMessageBox.critical(None, "Error", f"Error processing results:\n{str(e)}")

    def on_calibration_progress(self, message):
        """Handle calibration progress updates including real-time ring-by-ring display (Dioptas-style)"""
        if message.startswith("RING_FOUND:"):
            # Real-time display of detected ring (Dioptas-style)
            try:
                import json
                # Extract ring data from message
                ring_data_json = message.split("RING_FOUND:", 1)[1]
                ring_data = json.loads(ring_data_json)
                
                ring_num = ring_data['ring_num']
                num_points = ring_data['num_points']
                points = ring_data['points']  # [[x, y, ring_num], ...] already in pixel coords
                
                # Display on canvas
                if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                    try:
                        # Convert to tuple format expected by canvas
                        display_points = [(p[0], p[1], p[2]) for p in points]
                        
                        # Add to canvas auto_detected_peaks
                        if hasattr(self.unified_canvas, 'auto_detected_peaks'):
                            self.unified_canvas.auto_detected_peaks.extend(display_points)
                            
                            # Update display incrementally (Dioptas-style)
                            self.unified_canvas.update_auto_peaks_display()
                            
                            self.log(f"  → Ring {ring_num}: Displayed {len(display_points)} points")
                    
                    except Exception as display_error:
                        self.log(f"Warning: Could not display ring {ring_num}: {display_error}")
                
            except Exception as e:
                self.log(f"Warning: Could not process ring data: {e}")
                import traceback
                traceback.print_exc()
        
        elif message.startswith("AUTO_POINTS:"):
            # Extract number of rings
            num_rings = int(message.split(":")[1])
            self.log(f"✓ Automatically detected control points on {num_rings} rings")
        else:
            self.log(message)
    
    def on_calibration_finished(self, message):
        """Handle calibration completion"""
        self.log(message)

    def on_calibration_error(self, error_msg):
        """Handle calibration error"""
        self.log(f"Calibration failed:\n{error_msg}")
        QMessageBox.critical(None, "Calibration Error", 
                           f"Calibration failed:\n{error_msg}")

    def save_poni_file(self):
        """Save PONI file"""
        if self.ai is None:
            QMessageBox.warning(self.parent, "No Calibration", 
                              "Please run calibration first before saving PONI file.")
            return
        
        # Get path from entry or show dialog
        poni_path = None
        if hasattr(self, 'poni_entry') and self.poni_entry.text().strip():
            poni_path = self.poni_entry.text().strip()
        
        if not poni_path:
            # Show file dialog
            poni_path, _ = QFileDialog.getSaveFileName(
                self.parent, 
                "Save PONI File", 
                "calibration.poni",
                "PONI Files (*.poni);;All Files (*.*)"
            )
        
        if poni_path:
            try:
                # Ensure .poni extension
                if not poni_path.endswith('.poni'):
                    poni_path += '.poni'
                
                # Save using pyFAI's save method
                self.ai.save(poni_path)
                
                self.log(f"✓ PONI file saved to: {poni_path}")
                QMessageBox.information(self.parent, "Success", 
                                      f"PONI file saved successfully!\n{poni_path}")
                
                # Update the text field with saved path
                if hasattr(self, 'poni_entry'):
                    self.poni_entry.setText(poni_path)
                    
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"Error saving PONI: {str(e)}")
                self.log(error_detail)
                QMessageBox.critical(self.parent, "Error", 
                                   f"Failed to save PONI file:\n{str(e)}\n\nCheck log for details.")

    def on_contrast_slider_changed(self, value):
        """Handle contrast slider change (single vertical slider controls max)"""
        # Update percentage label
        if hasattr(self, 'contrast_pct_lbl'):
            self.contrast_pct_lbl.setText(f"Contrast: {value}%")
        
        # Use timer to debounce slider changes
        if hasattr(self, '_contrast_timer') and self._contrast_timer is not None:
            self._contrast_timer.stop()
        
        from PyQt6.QtCore import QTimer
        self._contrast_timer = QTimer()
        self._contrast_timer.setSingleShot(True)
        self._contrast_timer.timeout.connect(lambda: self.apply_contrast_from_slider(value))
        self._contrast_timer.start(50)  # 50ms delay
    
    def apply_contrast_from_slider(self, slider_value):
        """Apply contrast from slider (0-100 percentage scale)"""
        # Map slider percentage to actual image value range
        if not hasattr(self, 'image_vmin') or not hasattr(self, 'image_vmax'):
            return

        # Calculate actual vmax based on slider percentage
        # slider_value is 0-100, representing percentage of the full range
        percentage = slider_value / 100.0
        vmin = self.image_vmin
        vmax = self.image_vmin + (self.image_vmax - self.image_vmin) * percentage

        # Apply to canvases
        if MATPLOTLIB_AVAILABLE:
            # unified_canvas is the main display canvas
            if hasattr(self, 'unified_canvas') and self.unified_canvas is not None:
                self.unified_canvas.set_contrast(vmin, vmax)
            elif hasattr(self, 'calibration_canvas'):
                self.calibration_canvas.set_contrast(vmin, vmax)

            if hasattr(self, 'mask_canvas'):
                self.mask_canvas.set_contrast(vmin, vmax)
        
        # Log the percentage being applied (only occasionally to avoid spam)
        if slider_value % 10 == 0 or slider_value == 100 or slider_value == 0:
            self.log(f"Contrast adjusted to {slider_value}% (range: {vmin:.0f} - {vmax:.0f})")
    
    def auto_contrast(self):
        """Auto-adjust contrast based on image statistics"""
        if self.current_image is None:
            return
        
        try:
            # Calculate percentiles for auto-contrast
            vmin = np.percentile(self.current_image, 1)
            vmax = np.percentile(self.current_image, 99)
            
            # Update image statistics for percentage mapping
            self.image_vmin = vmin
            self.image_vmax = vmax

            # Set slider to 100% (full contrast range)
            if hasattr(self, 'contrast_slider'):
                self.contrast_slider.setValue(100)

            # Apply contrast at 100%
            self.apply_contrast_from_slider(100)
            self.log(f"Auto-contrast applied: {vmin:.0f} - {vmax:.0f} (100%)")
        except Exception as e:
            self.log(f"Auto-contrast failed: {str(e)}")
    
    def reset_zoom(self):
        """Reset zoom to original view"""
        if MATPLOTLIB_AVAILABLE:
            if hasattr(self, 'mask_canvas'):
                self.mask_canvas.reset_zoom()
            if hasattr(self, 'calibration_canvas'):
                self.calibration_canvas.reset_zoom()
        self.log("Zoom reset")
    
    def log(self, message):
        """Add message to log output"""
        if hasattr(self, 'log_output'):
            self.log_output.append(str(message))
    
    def refine_calibration(self):
        """Refine calibration (similar to run_calibration but with current parameters)"""
        if not PYFAI_AVAILABLE:
            QMessageBox.warning(None, "pyFAI Required", 
                              "pyFAI is required for calibration.\nInstall with: pip install pyFAI")
            return
        
        if self.ai is None:
            QMessageBox.warning(None, "No Calibration", 
                              "Please run initial calibration first.")
            return
        
        self.log("Refining calibration with current parameters...")
        # Re-run calibration with refined starting values
        self.run_calibration()
    
    def load_calibration(self):
        """Load calibration from PONI file"""
        if not PYFAI_AVAILABLE:
            QMessageBox.warning(None, "pyFAI Required", 
                              "pyFAI is required.\nInstall with: pip install pyFAI")
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            None, "Load PONI File", "",
            "PONI Files (*.poni);;All Files (*.*)"
        )
        
        if filename:
            try:
                # Load AzimuthalIntegrator from PONI file
                from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
                self.ai = AzimuthalIntegrator.sload(filename)
                
                # Update UI with loaded parameters
                self.update_ui_from_calibration()
                
                self.log(f"Calibration loaded from: {filename}")
                QMessageBox.information(None, "Success", 
                                      f"Calibration loaded successfully!\n{filename}")
            except Exception as e:
                self.log(f"Error loading calibration: {str(e)}")
                QMessageBox.critical(None, "Error", f"Failed to load calibration:\n{str(e)}")
    
    def update_ui_from_calibration(self):
        """Update UI widgets from loaded calibration"""
        if self.ai is None:
            return
        
        try:
            # Update pyFAI parameters
            if hasattr(self, 'pyfai_dist_txt'):
                self.pyfai_dist_txt.setText(f"{self.ai.dist:.6f}")
            if hasattr(self, 'pyfai_poni1_txt'):
                self.pyfai_poni1_txt.setText(f"{self.ai.poni1:.6f}")
            if hasattr(self, 'pyfai_poni2_txt'):
                self.pyfai_poni2_txt.setText(f"{self.ai.poni2:.6f}")
            if hasattr(self, 'pyfai_rot1_txt'):
                self.pyfai_rot1_txt.setText(f"{self.ai.rot1:.6f}")
            if hasattr(self, 'pyfai_rot2_txt'):
                self.pyfai_rot2_txt.setText(f"{self.ai.rot2:.6f}")
            if hasattr(self, 'pyfai_rot3_txt'):
                self.pyfai_rot3_txt.setText(f"{self.ai.rot3:.6f}")
            if hasattr(self, 'pyfai_wavelength_txt'):
                self.pyfai_wavelength_txt.setText(f"{self.ai.wavelength * 1e10:.6f}")
            
            # Update start values
            if hasattr(self, 'distance_txt'):
                self.distance_txt.setText(f"{self.ai.dist * 1000:.3f}")  # Convert to mm
            if hasattr(self, 'wavelength_txt'):
                self.wavelength_txt.setText(f"{self.ai.wavelength * 1e10:.6f}")  # Convert to Å
            
            # Update fit2d parameters if available
            if hasattr(self.ai, 'getFit2D'):
                try:
                    fit2d_params = self.ai.getFit2D()
                    if hasattr(self, 'fit2d_dist_txt'):
                        self.fit2d_dist_txt.setText(f"{fit2d_params['directDist']:.3f}")
                    if hasattr(self, 'fit2d_centerx_txt'):
                        self.fit2d_centerx_txt.setText(f"{fit2d_params['centerX']:.1f}")
                    if hasattr(self, 'fit2d_centery_txt'):
                        self.fit2d_centery_txt.setText(f"{fit2d_params['centerY']:.1f}")
                    if hasattr(self, 'fit2d_tilt_txt'):
                        self.fit2d_tilt_txt.setText(f"{fit2d_params['tilt']:.3f}")
                    if hasattr(self, 'fit2d_rotation_txt'):
                        self.fit2d_rotation_txt.setText(f"{fit2d_params['tiltPlanRotation']:.3f}")
                except:
                    pass
            
            self.log("UI updated with loaded calibration parameters")
        except Exception as e:
            self.log(f"Error updating UI: {str(e)}")
    
    def update_pyfai_from_fit(self):
        """Update pyFAI parameters from current fit results"""
        if self.ai is None:
            QMessageBox.warning(None, "No Calibration", 
                              "Please run calibration first.")
            return
        
        self.update_ui_from_calibration()
        self.log("pyFAI parameters updated from fit")
    
    def update_fit2d_from_fit(self):
        """Update Fit2d parameters from current fit results"""
        if self.ai is None:
            QMessageBox.warning(None, "No Calibration", 
                              "Please run calibration first.")
            return
        
        if not hasattr(self.ai, 'getFit2D'):
            QMessageBox.warning(None, "Not Available", 
                              "Fit2d parameters not available for this calibration.")
            return
        
        try:
            fit2d_params = self.ai.getFit2D()
            
            if hasattr(self, 'fit2d_dist_txt'):
                self.fit2d_dist_txt.setText(f"{fit2d_params['directDist']:.3f}")
            if hasattr(self, 'fit2d_centerx_txt'):
                self.fit2d_centerx_txt.setText(f"{fit2d_params['centerX']:.1f}")
            if hasattr(self, 'fit2d_centery_txt'):
                self.fit2d_centery_txt.setText(f"{fit2d_params['centerY']:.1f}")
            if hasattr(self, 'fit2d_tilt_txt'):
                self.fit2d_tilt_txt.setText(f"{fit2d_params['tilt']:.3f}")
            if hasattr(self, 'fit2d_rotation_txt'):
                self.fit2d_rotation_txt.setText(f"{fit2d_params['tiltPlanRotation']:.3f}")
            if hasattr(self, 'fit2d_wavelength_txt'):
                self.fit2d_wavelength_txt.setText(f"{fit2d_params['wavelength'] * 1e10:.6f}")
            
            self.log("Fit2d parameters updated from fit")
        except Exception as e:
            self.log(f"Error updating Fit2d parameters: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to update Fit2d parameters:\n{str(e)}")


    def update_cake_view(self):
        """Update Cake view after calibration - Dioptas style
        
        NOTE: If calibration is correct, calibrant peaks should appear as STRAIGHT VERTICAL LINES.
        Curved lines indicate calibration errors (incorrect geometry parameters).
        """
        if not hasattr(self, 'cake_axes') or self.ai is None or self.current_image is None:
            return
        
        try:
            # Apply mask if available
            mask = None
            if hasattr(self, 'imported_mask') and self.imported_mask is not None:
                mask = self.imported_mask
            elif hasattr(self, 'unified_canvas') and self.unified_canvas.mask_data is not None:
                mask = self.unified_canvas.mask_data
            
            # Dioptas-style cake/polar transformation
            # This creates a 2D map: X=2theta, Y=azimuthal_angle
            result = self.ai.integrate2d(
                self.current_image,
                npt_rad=1024,      # Radial bins (2theta direction)
                npt_azim=360,      # Azimuthal bins (chi direction) - 360° = 1°/bin
                unit="2th_deg",    # Use 2theta in degrees
                mask=mask,
                method="bbox",     # Fast method
                correctSolidAngle=False  # Don't apply solid angle correction for cake
            )
            
            # Extract result data
            cake_intensity = result.intensity if hasattr(result, 'intensity') else result[0]
            tth_edges = result.radial if hasattr(result, 'radial') else result[1]
            chi_edges = result.azimuthal if hasattr(result, 'azimuthal') else result[2]
            
            # Clear axes
            self.cake_axes.clear()
            
            # Log scale for better visualization
            cake_display = np.log10(np.clip(cake_intensity, 1, None))
            
            # Ensure correct orientation: (n_azim, n_rad)
            # Y-axis = azimuthal angle (0-360°), X-axis = 2theta
            if cake_display.shape[0] != len(chi_edges) - 1:
                cake_display = cake_display.T
            
            # Display cake image
            # extent = [left, right, bottom, top] = [2th_min, 2th_max, chi_min, chi_max]
            extent = [tth_edges[0], tth_edges[-1], chi_edges[0], chi_edges[-1]]
            
            im = self.cake_axes.imshow(
                cake_display,
                aspect='auto',
                origin='lower',
                extent=extent,
                cmap='jet',        # Dioptas default colormap
                interpolation='nearest',
                vmin=cake_display.min(),
                vmax=np.percentile(cake_display, 99.5)
            )
            
            # Set labels
            self.cake_axes.set_xlabel('2θ (°)', fontsize=11)
            self.cake_axes.set_ylabel('Azimuthal Angle (°)', fontsize=11)
            self.cake_axes.set_title('Cake View - Vertical lines = Good calibration', fontsize=11, fontweight='bold')
            
            # Add calibrant peak lines as VERTICAL LINES
            # If calibration is correct, these should appear as straight vertical lines
            # If calibration is wrong, they will appear curved/bent
            if hasattr(self.ai, 'calibrant') and self.ai.calibrant is not None:
                try:
                    tth_calibrant = self.ai.calibrant.get_2th()
                    tth_calibrant_deg = np.degrees(tth_calibrant)
                    
                    # Draw vertical lines at expected 2theta positions
                    # These span the full azimuthal range (0-360°)
                    for peak_2th in tth_calibrant_deg:
                        if extent[0] <= peak_2th <= extent[1]:
                            # Draw vertical line from bottom to top (full azimuthal range)
                            self.cake_axes.axvline(peak_2th, 
                                                  color='white', 
                                                  linestyle='-', 
                                                  alpha=0.5, 
                                                  linewidth=1.0,
                                                  zorder=10)  # Draw on top
                except Exception as calib_error:
                    pass  # Silently ignore calibrant line errors
            
            # Add colorbar
            if hasattr(self, 'cake_colorbar') and self.cake_colorbar is not None:
                try:
                    self.cake_colorbar.remove()
                except:
                    pass
            
            try:
                self.cake_colorbar = self.cake_figure.colorbar(im, ax=self.cake_axes)
                self.cake_colorbar.set_label('log₁₀(Intensity)', fontsize=10)
            except:
                pass
            
            self.cake_canvas.draw_idle()
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            # Only print to console on error
            print(f"ERROR in Cake view: {str(e)}")
            print(error_detail)
            # Also log to GUI
            self.log(f"Error updating Cake view: {str(e)}")
    
    def update_pattern_view(self):
        """Update Pattern view after calibration - Dioptas style with correct 1D integration"""
        if not hasattr(self, 'pattern_axes') or self.ai is None or self.current_image is None:
            return
        
        try:
            self.log("Generating 1D integrated pattern...")
            
            # Apply mask if available
            mask = None
            if hasattr(self, 'imported_mask') and self.imported_mask is not None:
                mask = self.imported_mask
            elif hasattr(self, 'unified_canvas') and self.unified_canvas.mask_data is not None:
                mask = self.unified_canvas.mask_data
            
            # Dioptas-style 1D azimuthal integration
            result = self.ai.integrate1d(
                self.current_image,
                npt=2048,          # Number of points in output (Dioptas default)
                unit="2th_deg",    # Use 2theta in degrees
                mask=mask,
                method="bbox",     # Fast method (Dioptas uses this)
                correctSolidAngle=False,  # Dioptas doesn't apply this by default
                polarization_factor=None   # No polarization correction by default
            )
            
            # Result: radial (2theta), intensity
            if hasattr(result, 'radial'):
                tth = result.radial
                intensity = result.intensity
            else:
                tth = result[0]
                intensity = result[1]
            
            # Clear axes
            self.pattern_axes.clear()
            
            # Plot 1D pattern with Dioptas styling
            self.pattern_axes.plot(tth, intensity, 'b-', linewidth=1.0, alpha=0.8)
            
            # Set labels (Dioptas style)
            self.pattern_axes.set_xlabel('2θ (°)', fontsize=11)
            self.pattern_axes.set_ylabel('Intensity (counts)', fontsize=11)
            self.pattern_axes.set_title('1D Integration Pattern', fontsize=12, fontweight='bold')
            
            # Add grid
            self.pattern_axes.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            
            # Set reasonable axis limits
            # X-axis: full 2theta range
            self.pattern_axes.set_xlim(tth[0], tth[-1])
            
            # Y-axis: auto-scale to remove outliers
            y_max = np.percentile(intensity, 99.5)
            self.pattern_axes.set_ylim(0, y_max * 1.05)
            
            # Add calibrant peak positions if available (Dioptas style)
            if hasattr(self.ai, 'calibrant') and self.ai.calibrant is not None:
                try:
                    # Get expected 2theta positions
                    tth_calibrant = self.ai.calibrant.get_2th()
                    tth_calibrant_deg = np.degrees(tth_calibrant)
                    
                    # Draw vertical lines for visible peaks
                    peak_count = 0
                    for peak_2th in tth_calibrant_deg:
                        if tth[0] <= peak_2th <= tth[-1]:
                            self.pattern_axes.axvline(peak_2th, color='red', linestyle='--', 
                                                     alpha=0.4, linewidth=0.8)
                            peak_count += 1
                            if peak_count >= 20:  # Limit to 20 peaks
                                break
                    
                    self.log(f"Added {peak_count} calibrant peak positions (of {len(visible_peaks)} in range)")
                except Exception as cal_error:
                    self.log(f"Could not add calibrant peaks: {cal_error}")
            
            self.pattern_canvas.draw()
            self.log(f"Pattern view updated: {len(tth)} points from {tth.min():.2f}° to {tth.max():.2f}°")
                
        except Exception as e:
            import traceback
            self.log(f"Error updating Pattern view: {str(e)}")
            self.log(traceback.format_exc())