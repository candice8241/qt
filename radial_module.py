#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
XRD Azimuthal Integration Module - Qt Version
Radial/Azimuthal integration, bin mode processing, and peak analysis

Modified to match the two-column layout from image 2

@author: candicewang928@gmail.com
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QCheckBox, QComboBox, QGroupBox,
                              QFileDialog, QMessageBox, QFrame, QScrollArea, QRadioButton,
                              QButtonGroup)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
# Import configuration dialogs
from unified_config_dialog import UnifiedConfigDialog
from h5_preview_dialog import H5PreviewDialog
from PyQt6.QtGui import QFont
import threading
import os
import glob
import h5py
import numpy as np
import re
from pathlib import Path
from datetime import datetime
from gui_base import GUIBase
from theme_module import CuteSheepProgressBar, ModernButton
from custom_widgets import SpinboxStyleButton, CustomSpinbox

# Import pyFAI (with fallback if not available)
try:
    import pyFAI
    import fabio
    PYFAI_AVAILABLE = True
except ImportError:
    PYFAI_AVAILABLE = False
    print("⚠ Warning: pyFAI not available. Integration features will be disabled.")

# Import matplotlib for plotting (non-interactive backend)
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend for batch plotting
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠ Warning: matplotlib not available. Plotting features will be disabled.")


class WorkerSignals(QObject):
    """Signals for worker thread"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)


class WorkerThread(threading.Thread):
    """Worker thread for background processing using Python threading"""
    
    def __init__(self, target_func, signals, *args, **kwargs):
        super().__init__(daemon=True)
        self.target_func = target_func
        self.signals = signals
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Run the target function with stdout/stderr redirection"""
        import sys
        from io import StringIO
        
        # Redirect stdout and stderr to prevent GUI blocking
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            result = self.target_func(*self.args, **self.kwargs)
            self.signals.finished.emit(str(result) if result else "Task completed successfully")
        except Exception as e:
            import traceback
            self.signals.error.emit(f"Error: {str(e)}\n{traceback.format_exc()}")
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class AzimuthalIntegrationModule(GUIBase):
    """Azimuthal integration module - Qt version"""

    def __init__(self, parent, root):
        """
        Initialize Azimuthal Integration module

        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        super().__init__()
        self.parent = parent
        self.root = root
        
        # Initialize variables
        self._init_variables()
        
        # Track running threads
        self.running_threads = []

    def _init_variables(self):
        """Initialize all variables"""
        # File paths
        self.poni_path = ""
        self.mask_path = ""
        self.input_pattern = ""
        self.output_dir = ""
        self.dataset_path = "entry/data/data"
        
        # Integration mode
        self.integration_type = "azimuthal"  # Primary: "azimuthal" or "radial"
        self.integration_mode = "single"  # Sector mode: "single" or "multiple"
        
        # Azimuthal integration parameters
        self.npt_azim = 4000  # Number of azimuthal bins (default from image 2)
        self.npt_rad = 1000   # Number of radial points
        self.unit = '2θ (°)'
        
        # Angular range (azimuthal)
        self.azim_range_min = 0.0
        self.azim_range_max = 360.0
        
        # Bin mode settings
        self.bin_mode_enabled = False
        self.n_bins = 10
        self.bin_size = 10.0  # degrees
        
        # Radial range
        self.rad_range_min = 0.0
        self.rad_range_max = 0.0  # 0 means auto
        
        # Output formats
        self.format_xy = True
        self.format_dat = False
        self.format_chi = False
        self.format_csv = False
        self.format_svg = False
        self.format_png = False
        
        # Plot options
        self.create_polar_plot = False
        self.create_intensity_map = False
        self.create_stacked_plot_flag = True  # Default: create stacked plot
        
        # Sector list for multiple sector mode
        self.sectors = []  # List of sector dictionaries
        self.bins = []  # List of bin dictionaries
        
        # Current sector being edited
        self.current_sector_start = 0.0
        self.current_sector_end = 90.0
        self.current_sector_label = "Sector_1"
        self.current_sector_bin = 10.0

    def setup_ui(self):
        """Setup the complete azimuthal integration UI"""
        print("[RadialModule] setup_ui() called")
        
        # Get or create layout for parent
        layout = self.parent.layout()
        if layout is None:
            print("[RadialModule] Creating new layout for parent")
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            print("[RadialModule] Using existing parent layout")
        
        print(f"[RadialModule] Layout widget count before: {layout.count()}")
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {self.colors['bg']}; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Disable vertical scrollbar
        
        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {self.colors['bg']};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Setup modules
        print("[RadialModule] Setting up integration module...")
        self.setup_integration_module(content_layout)
        
        # Progress bar section
        prog_widget = QWidget()
        prog_widget.setStyleSheet(f"background-color: {self.colors['bg']};")
        prog_layout = QVBoxLayout(prog_widget)
        prog_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress = CuteSheepProgressBar(width=780, height=80, parent=prog_widget)
        prog_layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(prog_widget)
        
        # Log area
        log_card = self.create_card_frame(content_widget)
        log_card_layout = QVBoxLayout(log_card)
        log_card_layout.setContentsMargins(20, 12, 20, 12)
        
        # Log header
        log_header = QWidget()
        log_header.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(0, 0, 0, 8)
        log_header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        emoji_label = QLabel("🐰")
        emoji_label.setFont(QFont('Segoe UI Emoji', 14))
        emoji_label.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        log_header_layout.addWidget(emoji_label)
        
        log_title = QLabel("Process Log")
        log_title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        log_title.setStyleSheet(f"color: {self.colors['primary']}; background-color: {self.colors['card_bg']};")
        log_header_layout.addWidget(log_title)
        
        log_card_layout.addWidget(log_header)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Arial', 10))
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: #FAFAFA;
                color: {self.colors['primary']};
                border: none;
                padding: 10px;
            }}
        """)
        self.log_text.setMinimumHeight(200)
        log_card_layout.addWidget(self.log_text)
        
        content_layout.addWidget(log_card)
        
        print("[RadialModule] Adding scroll to layout...")
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        print(f"[RadialModule] Layout widget count after: {layout.count()}")
        print("[RadialModule] setup_ui() complete")

    def setup_integration_module(self, parent_layout):
        """Setup azimuthal/radial integration module UI - Two-column layout matching powder module"""
        print("[RadialModule] setup_integration_module() called")

        # Main card container (like powder module)
        int_card = self.create_card_frame(None)
        int_layout = QVBoxLayout(int_card)
        int_layout.setContentsMargins(20, 15, 20, 15)
        int_layout.setSpacing(12)

        # Header
        header = QLabel("🔄 Azimuthal Integration Settings")
        header.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        int_layout.addWidget(header)

        # Two-column layout
        columns = QHBoxLayout()
        columns.setSpacing(16)

        # LEFT PANEL - Integration Settings
        left_panel = QWidget()
        left_panel.setMinimumWidth(550)
        from PyQt6.QtWidgets import QSizePolicy
        left_panel.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)
        left_panel.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 4, 0, 4)
        left_layout.setSpacing(8)

        # left_title = QLabel("Integration Settings")
        # left_title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        # left_title.setStyleSheet(f"color: {self.colors['primary']}; background-color: {self.colors['card_bg']};")
        # left_layout.addWidget(left_title)

        # File inputs
        self.create_file_input(left_layout, "PONI File", "poni_path")
        self.create_file_input(left_layout, "Mask File", "mask_path")
        self.create_file_input(left_layout, "Input .h5 File", "input_pattern")
        self.create_folder_input(left_layout, "Output Directory", "output_dir")
        self.create_text_input(left_layout, "Dataset Path", "dataset_path", placeholder="entry/data/data")

        # Parameters row (Azimuthal Points, Radial Points, Unit)
        params_row = QWidget()
        params_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        params_row_layout = QHBoxLayout(params_row)
        params_row_layout.setContentsMargins(0, 6, 0, 6)
        params_row_layout.setSpacing(16)

        # Azimuthal Points
        azim_container = QWidget()
        azim_container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        azim_layout = QVBoxLayout(azim_container)
        azim_layout.setContentsMargins(0, 0, 0, 0)

        azim_label = QLabel("Azimuthal Points")
        azim_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        azim_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        azim_layout.addWidget(azim_label)

        self.azim_spinbox = CustomSpinbox(from_=500, to=10000, value=4000,
                                          increment=500, width=110, parent=azim_container)
        self.azim_spinbox.valueChanged.connect(lambda v: setattr(self, 'npt_azim', int(v)))
        azim_layout.addWidget(self.azim_spinbox)
        params_row_layout.addWidget(azim_container)

        # Radial Points
        rad_container = QWidget()
        rad_container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        rad_layout = QVBoxLayout(rad_container)
        rad_layout.setContentsMargins(0, 0, 0, 0)

        rad_label = QLabel("Radial Points")
        rad_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        rad_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        rad_layout.addWidget(rad_label)

        self.rad_spinbox = CustomSpinbox(from_=100, to=5000, value=1000,
                                         increment=100, width=110, parent=rad_container)
        self.rad_spinbox.valueChanged.connect(lambda v: setattr(self, 'npt_rad', int(v)))
        rad_layout.addWidget(self.rad_spinbox)
        params_row_layout.addWidget(rad_container)

        # Unit selection
        unit_container = QWidget()
        unit_container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        unit_layout = QVBoxLayout(unit_container)
        unit_layout.setContentsMargins(0, 0, 0, 0)
        unit_layout.setSpacing(4)

        unit_label = QLabel("Unit")
        unit_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        unit_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        unit_layout.addWidget(unit_label, alignment=Qt.AlignmentFlag.AlignCenter)

        unit_radios = QWidget()
        unit_radios.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        unit_radios_layout = QHBoxLayout(unit_radios)
        unit_radios_layout.setContentsMargins(0, 0, 0, 0)
        unit_radios_layout.setSpacing(10)

        self.unit_group = QButtonGroup(unit_radios)
        unit_options = ['2θ (°)', 'Q (Å⁻¹)', 'r (mm)']
        for option in unit_options:
            radio = QRadioButton(option)
            radio.setChecked(option == '2θ (°)')
            radio.setFont(QFont('Arial', 9))
            radio.setStyleSheet(f"""
                QRadioButton {{
                    color: {self.colors['text_dark']};
                    background-color: {self.colors['card_bg']};
                }}
                QRadioButton::indicator {{
                    width: 10px;
                    height: 10px;
                    border: 1.5px solid #999999;
                    border-radius: 2px;
                    background-color: {self.colors['primary']};
                }}
                QRadioButton::indicator:checked {{
                    border: 1.5px solid #999999;
                    border-radius: 2px;
                    background-color: {self.colors['primary']};
                    image: url(point.png);
                }}
            """)
            radio.toggled.connect(lambda checked, text=option: setattr(self, 'unit', text) if checked else None)
            self.unit_group.addButton(radio)
            unit_radios_layout.addWidget(radio)

        unit_layout.addWidget(unit_radios)
        params_row_layout.addWidget(unit_container)
        params_row_layout.addStretch()

        left_layout.addWidget(params_row)

        # Run Integration button centered in left panel
        run_int_btn_row = QWidget()
        run_int_btn_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        run_int_btn_layout = QHBoxLayout(run_int_btn_row)
        run_int_btn_layout.setContentsMargins(0, 15, 0, 0)
        run_int_btn_layout.setSpacing(0)

        run_int_btn_layout.addStretch()
        run_int_btn = ModernButton(
            "Run Integration",
            self.run_integration,
            bg_color=self.colors['primary'],
            hover_color=self.colors['primary_hover'],
            width=170, height=36,
            parent=run_int_btn_row
        )
        run_int_btn.setFont(QFont('Arial', 9))
        run_int_btn_layout.addWidget(run_int_btn)
        run_int_btn_layout.addStretch()

        left_layout.addWidget(run_int_btn_row)
        left_layout.addStretch()

        # RIGHT PANEL - Azimuthal Sector Settings
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Calculate left Browse area alignment:
        # - Left title (Integration Settings): ~25px
        # - 5 file input boxes, each ~50px = 250px
        # - Browse area center: 25 + 250/2 = 150px
        # Align right container center with left Browse area center
        # Adjusted to 40px for better spacing from top
        from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
        top_spacer = QSpacerItem(20, 22, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        right_layout.addItem(top_spacer)

        settings_card = self.create_card_frame(None)
        # Darken the border of right container
        settings_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card_bg']};
                border: 2px solid rgba(0, 0, 0, 0.4);
                border-radius: 8px;
            }}
        """)
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(15, 12, 15, 12)
        settings_layout.setSpacing(8)

        settings_title = QLabel("Azimuthal Sector Settings")
        settings_title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        settings_title.setStyleSheet(f"color: black; background-color: {self.colors['card_bg']};border:none;")
        settings_layout.addWidget(settings_title)

        # H5 Image Preview Button (moved to top)
        preview_btn_row = QWidget()
        preview_btn_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        preview_btn_layout = QHBoxLayout(preview_btn_row)
        preview_btn_layout.setContentsMargins(10, 5, 10, 5)
        preview_btn_layout.setSpacing(10)
        
        self.h5_preview_btn = QPushButton("📷 Preview H5 Image")
        self.h5_preview_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.h5_preview_btn.setFixedWidth(160)  # Set fixed width
        self.h5_preview_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45A049;
            }}
        """)
        self.h5_preview_btn.clicked.connect(self.open_h5_preview)
        preview_btn_layout.addWidget(self.h5_preview_btn)

        preview_hint = QLabel("View H5 image with angles & radial info")
        preview_hint.setFont(QFont('Arial', 8))
        preview_hint.setStyleSheet("color: #999999; border: none;")
        preview_btn_layout.addWidget(preview_hint)
        preview_btn_layout.addStretch()

        settings_layout.addWidget(preview_btn_row)

        # Unified Configuration Button (Bins & Sectors)
        config_btn_row = QWidget()
        config_btn_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        config_btn_layout = QHBoxLayout(config_btn_row)
        config_btn_layout.setContentsMargins(10, 12, 10, 5)  # Increased top margin from 5 to 12
        config_btn_layout.setSpacing(10)
        
        self.unified_config_btn = QPushButton("⚙ Configure Bins")
        self.unified_config_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.unified_config_btn.setFixedWidth(160)  # Match Preview button width
        self.unified_config_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45A049;
            }}
        """)
        self.unified_config_btn.clicked.connect(self.open_unified_config)
        config_btn_layout.addWidget(self.unified_config_btn)
        
        self.config_status_label = QLabel("No sectors configured")
        self.config_status_label.setFont(QFont('Arial', 9))
        self.config_status_label.setStyleSheet("color: #999999;border: none;")
        self.config_status_label.setMinimumWidth(150)  # Fixed minimum width to prevent container changes
        self.config_status_label.setWordWrap(True)  # Allow word wrap
        config_btn_layout.addWidget(self.config_status_label)
        config_btn_layout.addStretch()
        
        settings_layout.addWidget(config_btn_row)

        # Output formats
        formats_label = QLabel("Output Formats:")
        formats_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        formats_label.setStyleSheet(f"color: black; background-color: {self.colors['card_bg']};border:none;")
        settings_layout.addWidget(formats_label)

        # Format checkboxes in single row
        formats_row = QWidget()
        formats_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        formats_row_layout = QHBoxLayout(formats_row)
        formats_row_layout.setContentsMargins(10, 5, 10, 5)
        formats_row_layout.setSpacing(8)

        format_options = [
            ('xy', 'format_xy', True),
            ('dat', 'format_dat', False),
            ('chi', 'format_chi', False),
            ('csv', 'format_csv', False),
            ('svg', 'format_svg', False),
            ('png', 'format_png', False)
        ]

        # Create all checkboxes in one row
        for label, var, default in format_options:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.setFont(QFont('Arial', 9))
            cb.setFixedWidth(45)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: #666666;
                    background-color: {self.colors['card_bg']};
                }}
                QCheckBox::indicator {{
                    width: 10px;
                    height: 10px;
                    border: 1.5px solid #999999;
                    border-radius: 2px;
                    background-color: {self.colors['primary']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {self.colors['primary']};
                    border: 1.5px solid #999999;
                    border-radius: 2px;
                    image: url(check.png);
                }}
            """)
            cb.stateChanged.connect(lambda state, v=var: setattr(self, v, state == Qt.CheckState.Checked.value))
            formats_row_layout.addWidget(cb)
        
        formats_row_layout.addStretch()
        settings_layout.addWidget(formats_row)
        
        # Visualization options
        viz_label = QLabel("Visualization Options:")
        viz_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        viz_label.setStyleSheet(f"color: black; background-color: {self.colors['card_bg']};border:none;")
        settings_layout.addWidget(viz_label)
        
        viz_grid = QWidget()
        viz_grid.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        viz_grid_layout = QVBoxLayout(viz_grid)
        viz_grid_layout.setContentsMargins(10, 5, 10, 5)
        viz_grid_layout.setSpacing(5)
        
        # Stacked Plot checkbox
        stacked_cb = QCheckBox("Create Stacked Plot")
        stacked_cb.setChecked(True)  # Default enabled
        stacked_cb.setFont(QFont('Arial', 9))
        stacked_cb.setStyleSheet(f"""
            QCheckBox {{
                color: #666666;
                background-color: {self.colors['card_bg']};
            }}
            QCheckBox::indicator {{
                width: 10px;
                height: 10px;
                border: 1.5px solid #999999;
                border-radius: 2px;
                background-color: {self.colors['primary']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 1.5px solid #999999;
                border-radius: 2px;
                image:url(check.png);
            }}
        """)
        stacked_cb.stateChanged.connect(
            lambda state: setattr(self, 'create_stacked_plot_flag', state == Qt.CheckState.Checked.value)
        )
        viz_grid_layout.addWidget(stacked_cb)
        
        # Stacked Plot Offset option
        offset_row = QWidget()
        offset_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        offset_layout = QHBoxLayout(offset_row)
        offset_layout.setContentsMargins(0, 0, 0, 0)  # Align left, remove indent
        offset_layout.setSpacing(8)
        
        offset_label = QLabel("Offset:")
        offset_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        offset_label.setStyleSheet(f"color: black; background-color: {self.colors['card_bg']};border:none;")
        offset_layout.addWidget(offset_label)
        
        self.stacked_offset_entry = QLineEdit("auto")
        self.stacked_offset_entry.setFixedWidth(70)
        self.stacked_offset_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stacked_offset_entry.setFont(QFont('Arial', 9))
        self.stacked_offset_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 1px solid {self.colors['border']};
                padding: 3px;
            }}
        """)
        self.stacked_offset_entry.setPlaceholderText("auto")
        offset_layout.addWidget(self.stacked_offset_entry)
        
        offset_hint = QLabel("(auto or number)")
        offset_hint.setFont(QFont('Arial', 8))
        offset_hint.setStyleSheet("color: #999999;border: none;")
        offset_layout.addWidget(offset_hint)
        
        offset_layout.addStretch()
        viz_grid_layout.addWidget(offset_row)
        
        settings_layout.addWidget(viz_grid)

        right_layout.addWidget(settings_card, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Bottom stretch space
        right_layout.addStretch()

        # Add both panels to columns with stretch ratios
        columns.addWidget(left_panel, 2)
        columns.addWidget(right_panel, 1)

        int_layout.addLayout(columns)
        parent_layout.addWidget(int_card)

        print("[RadialModule] Integration module UI setup complete")

    def adjust_npt(self, delta):
        """Adjust number of points"""
        try:
            current = int(self.npt_entry.text())
            new_value = max(100, current + delta)
            self.npt_entry.setText(str(new_value))
        except ValueError:
            self.npt_entry.setText("4000")

    def open_unified_config(self):
        """Open unified configuration dialog for bins and sectors"""
        # Use root window as parent (stored during __init__)
        parent_widget = self.root if hasattr(self, 'root') else None
        dialog = UnifiedConfigDialog(parent_widget)
        
        # Set existing bins and sectors if any
        if self.bins:
            dialog.bins = self.bins.copy()
            dialog.update_bins_table()
        
        if self.sectors:
            dialog.sectors = self.sectors.copy()
            dialog.update_sectors_table()
        
        def on_config_completed(bins, sectors):
            self.bins = bins.copy()
            self.sectors = sectors.copy()
            self.bin_mode_enabled = len(bins) > 0
            
            # Update status label
            status_parts = []
            if bins:
                status_parts.append(f"{len(bins)} single sector(s)")
            if sectors:
                status_parts.append(f"{len(sectors)} multiple sector(s)")
            
            if status_parts:
                status_text = "✓ " + " & ".join(status_parts) + " configured"
                self.config_status_label.setText(status_text)
                self.config_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;border: none;")
                self.log(f"Configuration completed: {' & '.join(status_parts)}")
            else:
                self.config_status_label.setText("No sectors configured")
                self.config_status_label.setStyleSheet("color: #999999;border: none;")
        
        dialog.config_completed.connect(on_config_completed)
        dialog.exec()

    def create_file_input(self, parent_layout, label_text, var_name):
        """Create a file input widget"""
        container = QWidget()
        container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)
        
        label = QLabel(label_text)
        label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        layout.addWidget(label)
        
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        
        entry = QLineEdit()
        entry.setFont(QFont('Arial', 9))
        entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 1.5px solid rgba(0, 0, 0, 0.3);
                padding: 3px;
            }}
        """)
        entry.textChanged.connect(lambda text: setattr(self, var_name, text))
        input_layout.addWidget(entry)
        
        browse_btn = ModernButton(
            "Browse",
            lambda: self.browse_file(entry),
            bg_color=self.colors['secondary'],
            hover_color=self.colors['primary'],
            width=70, height=26,
            parent=container
        )
        browse_btn.setFont(QFont('Arial', 9))  # Increase font size
        input_layout.addWidget(browse_btn)
        
        layout.addLayout(input_layout)
        parent_layout.addWidget(container)
        
        setattr(self, f"{var_name}_entry", entry)

    def create_folder_input(self, parent_layout, label_text, var_name):
        """Create a folder input widget"""
        container = QWidget()
        container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)
        
        label = QLabel(label_text)
        label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        layout.addWidget(label)
        
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        
        entry = QLineEdit()
        entry.setFont(QFont('Arial', 9))
        entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 1.5px solid rgba(0, 0, 0, 0.3);
                padding: 3px;
            }}
        """)
        entry.textChanged.connect(lambda text: setattr(self, var_name, text))
        input_layout.addWidget(entry)
        
        browse_btn = ModernButton(
            "Browse",
            lambda: self.browse_folder(entry),
            bg_color=self.colors['secondary'],
            hover_color=self.colors['primary'],
            width=70, height=26,
            parent=container
        )
        browse_btn.setFont(QFont('Arial', 9))  # Increase font size
        input_layout.addWidget(browse_btn)
        
        layout.addLayout(input_layout)
        parent_layout.addWidget(container)
        
        setattr(self, f"{var_name}_entry", entry)

    def create_text_input(self, parent_layout, label_text, var_name, placeholder=""):
        """Create a text input widget with browse button (like file input)"""
        container = QWidget()
        container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)
        
        label = QLabel(label_text)
        label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        layout.addWidget(label)
        
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        
        entry = QLineEdit()
        entry.setFont(QFont('Arial', 9))
        entry.setPlaceholderText(placeholder)
        entry.setText(getattr(self, var_name, ""))
        entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 1.5px solid rgba(0, 0, 0, 0.3);
                padding: 3px;
            }}
        """)
        entry.textChanged.connect(lambda text: setattr(self, var_name, text))
        
        input_layout.addWidget(entry)
        
        # Add Browse button for browsing HDF5 file to select dataset
        browse_btn = ModernButton(
            "Browse",
            lambda: self.browse_dataset(entry),
            bg_color=self.colors['secondary'],
            hover_color=self.colors['primary'],
            width=70, height=26,
            parent=container
        )
        browse_btn.setFont(QFont('Arial', 9))  # Increase font size
        input_layout.addWidget(browse_btn)
        
        layout.addLayout(input_layout)
        parent_layout.addWidget(container)
        
        setattr(self, f"{var_name}_entry", entry)

    def browse_file(self, entry):
        """Browse for a file"""
        filename, _ = QFileDialog.getOpenFileName(
            self.root,
            "Select File",
            "",
            "All Files (*.*)"
        )
        if filename:
            # If it's an h5 file, set the pattern to process all h5 files in the same directory
            if filename.lower().endswith('.h5'):
                directory = os.path.dirname(filename)
                # Set pattern to search all h5 files recursively in the directory
                pattern = os.path.join(directory, '**', '*.h5')
                entry.setText(pattern)
                self.log(f"Selected h5 file: {os.path.basename(filename)}")
                self.log(f"Will process all h5 files in: {directory}")
            else:
                entry.setText(filename)

    def browse_folder(self, entry):
        """Browse for a folder"""
        folder = QFileDialog.getExistingDirectory(self.root, "Select Folder")
        if folder:
            entry.setText(folder)
    
    def browse_dataset(self, entry):
        """Browse for HDF5 dataset path"""
        # Simple dataset path input dialog
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self.root, 
            'Dataset Path',
            'Enter HDF5 dataset path:',
            text=entry.text() or 'entry/data/data'
        )
        if ok and text:
            entry.setText(text)

    def log(self, message):
        """Add message to log"""
        self.log_text.append(message)

    def show_error(self, title, message):
        """Show error dialog"""
        QMessageBox.critical(self.root, title, message)

    def show_success(self, title, message):
        """Show success dialog"""
        QMessageBox.information(self.root, title, message)

    def add_sector(self):
        """Add a new sector to the list"""
        try:
            # Get values from sector #1 entries
            start = float(self.s1_start_entry.text())
            end = float(self.s1_end_entry.text())
            label = self.s1_label_entry.text()
            bin_size = float(self.s1_bin_entry.text())
            
            sector = {
                'start': start,
                'end': end,
                'label': label,
                'bin_size': bin_size
            }
            
            self.sectors.append(sector)
            self.log(f"✓ Added sector: {label} ({start}°-{end}°, bin={bin_size}°)")
            self.show_success("Success", f"Sector '{label}' added!\nTotal sectors: {len(self.sectors)}")
            
        except ValueError as e:
            self.show_error("Error", f"Invalid sector parameters:\n{str(e)}")
    
    def delete_sector(self, sector_num):
        """Delete a sector by number"""
        self.log(f"Delete sector #{sector_num} button clicked")
        # In a full implementation, this would remove the sector from the list
        # For now, just show a message
        self.show_success("Info", f"Sector #{sector_num} delete button clicked")

    def clear_all_sectors(self):
        """Clear all sectors"""
        self.sectors = []
        self.log("✓ Cleared all sectors")
        self.show_success("Success", "All sectors cleared!")

    def run_integration(self):
        """Run azimuthal/radial integration"""
        try:
            # Check if pyFAI is available
            if not PYFAI_AVAILABLE:
                self.show_error("Error", "pyFAI is not installed.\nPlease install pyFAI: pip install pyFAI")
                return
            
            # Validate inputs
            if not self.poni_path_entry.text().strip():
                self.show_error("Error", "Please select a PONI file")
                return
            if not self.input_pattern_entry.text().strip():
                self.show_error("Error", "Please specify input pattern")
                return
            if not self.output_dir_entry.text().strip():
                self.show_error("Error", "Please select output directory")
                return
            
            # Get values from entries
            self.poni_path = self.poni_path_entry.text().strip()
            self.mask_path = self.mask_path_entry.text().strip() if hasattr(self, 'mask_path_entry') else ""
            self.input_pattern = self.input_pattern_entry.text().strip()
            self.output_dir = self.output_dir_entry.text().strip()
            self.dataset_path = self.dataset_path_entry.text().strip() or "entry/data/data"
            
            self.log("="*60)
            self.log("Starting Azimuthal Integration...")
            self.log(f"PONI File: {self.poni_path}")
            self.log(f"Mask File: {self.mask_path if self.mask_path else 'None'}")
            self.log(f"Input Pattern: {self.input_pattern}")
            self.log(f"Output Directory: {self.output_dir}")
            self.log(f"Dataset Path: {self.dataset_path}")
            self.log(f"Azimuthal Points: {self.npt_azim}")
            self.log(f"Radial Points: {self.npt_rad}")
            self.log(f"Unit: {self.unit}")
            
            # Start progress animation
            self.progress.start()
            
            # Run integration in background thread
            def integration_work():
                return self._do_integration()
            
            signals = WorkerSignals()
            signals.finished.connect(lambda msg: self._on_integration_finished(msg))
            signals.error.connect(lambda err: self._on_integration_error(err))
            
            worker = WorkerThread(integration_work, signals)
            self.running_threads.append(worker)
            worker.start()
            
        except Exception as e:
            self.progress.stop()
            self.log(f"❌ Error: {str(e)}")
            self.show_error("Error", f"Failed to start integration:\n{str(e)}")

    def _do_integration(self):
        """Perform the actual integration work"""
        try:
            # Initialize integrator
            integrator = BatchIntegrator(
                self.poni_path,
                self.mask_path if self.mask_path else None
            )
            
            # Find input files with intelligent fallback mechanism
            input_files = []
            
            self.log(f"🔍 Searching for input files: {self.input_pattern}")
            
            # Method 1: Try the pattern as-is with recursive search
            input_files = sorted(glob.glob(self.input_pattern, recursive=True))
            # Filter out directories and only keep .h5 files
            input_files = [f for f in input_files if f.endswith('.h5') and os.path.isfile(f)]
            if input_files:
                self.log(f"✓ Method 1: Found {len(input_files)} files")
            
            # Method 2: If no files and it's a directory path, search for **/*.h5 recursively
            if not input_files and os.path.isdir(self.input_pattern):
                pattern = os.path.join(self.input_pattern, '**', '*.h5')
                self.log(f"📂 Method 2: Searching recursively in directory...")
                input_files = sorted(glob.glob(pattern, recursive=True))
                if input_files:
                    self.log(f"✓ Method 2: Found {len(input_files)} files")
            
            # Method 3: If pattern contains *.h5 but no **, try recursive search
            if not input_files and '*.h5' in self.input_pattern and '**' not in self.input_pattern:
                if self.input_pattern.endswith('*.h5'):
                    base_dir = self.input_pattern[:-len('*.h5')].rstrip('/\\')
                    if not base_dir:
                        base_dir = '.'
                    recursive_pattern = os.path.join(base_dir, '**', '*.h5')
                else:
                    recursive_pattern = self.input_pattern.replace('*.h5', '**/*.h5')
                self.log(f"📂 Method 3: Converting to recursive pattern...")
                input_files = sorted(glob.glob(recursive_pattern, recursive=True))
                if input_files:
                    self.log(f"✓ Method 3: Found {len(input_files)} files")
            
            # Method 4: Try as directory with recursive **/*.h5
            if not input_files:
                clean_path = self.input_pattern.rstrip('/*')
                if os.path.isdir(clean_path):
                    recursive_pattern = os.path.join(clean_path, '**', '*.h5')
                    self.log(f"📂 Method 4: Trying cleaned directory path...")
                    input_files = sorted(glob.glob(recursive_pattern, recursive=True))
                    if input_files:
                        self.log(f"✓ Method 4: Found {len(input_files)} files")
            
            # Method 5: Try parent directory
            if not input_files and os.path.sep in self.input_pattern:
                parent_dir = os.path.dirname(self.input_pattern)
                if parent_dir and os.path.isdir(parent_dir):
                    recursive_pattern = os.path.join(parent_dir, '**', '*.h5')
                    self.log(f"📂 Method 5: Trying parent directory...")
                    input_files = sorted(glob.glob(recursive_pattern, recursive=True))
                    if input_files:
                        self.log(f"✓ Method 5: Found {len(input_files)} files")
            
            if not input_files:
                raise ValueError(f"No .h5 files found matching pattern: {self.input_pattern}")
            
            self.log(f"✓ Total found: {len(input_files)} files to process")
            
            # Create output directory if needed
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Determine output formats
            formats = []
            if self.format_xy:
                formats.append('xy')
            if self.format_dat:
                formats.append('dat')
            if self.format_chi:
                formats.append('chi')
            if self.format_csv:
                formats.append('csv')
            if hasattr(self, 'format_svg') and self.format_svg:
                formats.append('svg')
            if hasattr(self, 'format_png') and self.format_png:
                formats.append('png')
            
            if not formats:
                formats = ['xy']  # Default to xy if nothing selected
            
            # Convert unit name for pyFAI
            unit_map = {
                '2θ (°)': '2th_deg',
                'q (nm⁻¹)': 'q_nm^-1',
                'q (A⁻¹)': 'q_A^-1',
                'd (A)': 'd*2_A'
            }
            pyfai_unit = unit_map.get(self.unit, '2th_deg')
            
            # Determine integration mode
            use_bin_mode = len(self.bins) > 0
            use_multiple_sectors = len(self.sectors) > 0
            
            if use_bin_mode and use_multiple_sectors:
                self.log("⚠ Warning: Cannot use both Single Sector and Multiple Sectors simultaneously")
                self.log("Using Single Sector mode only")
                use_multiple_sectors = False
            
            if use_bin_mode:
                self.log(f"✓ Single Sector Mode enabled: {len(self.bins)} sectors configured")
            elif use_multiple_sectors:
                self.log(f"✓ Multiple Sectors Mode enabled: {len(self.sectors)} sectors configured")
            else:
                self.log("Normal Mode: Full integration")
            
            # Process each file
            all_patterns = []
            for i, h5_file in enumerate(input_files, 1):
                basename = os.path.splitext(os.path.basename(h5_file))[0]
                
                try:
                    if use_bin_mode:
                        # Single Sector mode: Process each sector separately
                        self.log(f"Processing ({i}/{len(input_files)}): {basename} - {len(self.bins)} single sectors")
                        for j, bin_data in enumerate(self.bins, 1):
                            bin_name = bin_data['name']
                            azim_start = bin_data['start']
                            azim_end = bin_data['end']
                            rad_min = bin_data.get('rad_min', 0.0)
                            rad_max = bin_data.get('rad_max', 0.0)
                            
                            output_base = os.path.join(self.output_dir, f"{basename}_{bin_name}_{azim_start:.1f}-{azim_end:.1f}")
                            
                            self.log(f"  [{j}/{len(self.bins)}] Sector: {bin_name} ({azim_start}° - {azim_end}°)")
                            
                            # Build kwargs for integration
                            integration_kwargs = {
                                'azimuth_range': (azim_start, azim_end)
                            }
                            if rad_max > 0:
                                integration_kwargs['radial_range'] = (rad_min, rad_max)
                            
                            two_theta, intensity = integrator.integrate_single(
                                h5_file,
                                output_base,
                                npt=self.npt_rad,
                                unit=pyfai_unit,
                                dataset_path=self.dataset_path,
                                formats=formats,
                                **integration_kwargs
                            )
                            
                            all_patterns.append((f"{basename}_{bin_name}", two_theta, intensity))
                        
                        self.log(f"  ✓ Completed all single sectors for {basename}")
                    
                    elif use_multiple_sectors:
                        # Multiple sectors: Process each sector separately
                        self.log(f"Processing ({i}/{len(input_files)}): {basename} - {len(self.sectors)} sectors")
                        for j, sector in enumerate(self.sectors, 1):
                            sector_name = sector['name']
                            azim_start = sector['azim_start']
                            azim_end = sector['azim_end']
                            rad_min = sector['rad_min']
                            rad_max = sector['rad_max'] if sector['rad_max'] > 0 else None
                            
                            output_base = os.path.join(self.output_dir, f"{basename}_{sector_name}")
                            
                            self.log(f"  [{j}/{len(self.sectors)}] Sector: {sector_name} ({azim_start}° - {azim_end}°)")
                            
                            # Build kwargs for integration
                            integration_kwargs = {
                                'azimuth_range': (azim_start, azim_end)
                            }
                            if rad_max:
                                integration_kwargs['radial_range'] = (rad_min, rad_max)
                            
                            two_theta, intensity = integrator.integrate_single(
                                h5_file,
                                output_base,
                                npt=self.npt_rad,
                                unit=pyfai_unit,
                                dataset_path=self.dataset_path,
                                formats=formats,
                                **integration_kwargs
                            )
                            
                            all_patterns.append((f"{basename}_{sector_name}", two_theta, intensity))
                        
                        self.log(f"  ✓ Completed all sectors for {basename}")
                    
                    else:
                        # Normal mode: Full integration
                        output_base = os.path.join(self.output_dir, basename)
                        
                        self.log(f"Processing ({i}/{len(input_files)}): {basename}")
                        
                        two_theta, intensity = integrator.integrate_single(
                            h5_file,
                            output_base,
                            npt=self.npt_rad,
                            unit=pyfai_unit,
                            dataset_path=self.dataset_path,
                            formats=formats
                        )
                        
                        all_patterns.append((basename, two_theta, intensity))
                        self.log(f"  ✓ Completed")
                    
                except Exception as e:
                    self.log(f"  ⚠ Warning: Failed to process {basename}: {str(e)}")
                    continue
            
            if not all_patterns:
                raise ValueError("No files were successfully processed")
            
            self.log(f"✓ Successfully processed {len(all_patterns)} files")
            
            # Create stacked plot if requested
            if hasattr(self, 'create_stacked_plot_flag') and self.create_stacked_plot_flag:
                self.log("Generating stacked plot...")
                try:
                    # Get offset value from GUI
                    offset_value = 'auto'
                    if hasattr(self, 'stacked_offset_entry'):
                        offset_text = self.stacked_offset_entry.text().strip().lower()
                        if offset_text and offset_text != 'auto':
                            try:
                                offset_value = float(offset_text)
                                self.log(f"Using custom offset: {offset_value}")
                            except ValueError:
                                self.log("⚠ Invalid offset value, using 'auto'")
                                offset_value = 'auto'
                        else:
                            offset_value = 'auto'
                    
                    integrator.create_stacked_plot(
                        self.output_dir,
                        offset=offset_value,
                        output_name='stacked_plot.png'
                    )
                    self.log("✓ Stacked plot generated")
                except Exception as e:
                    self.log(f"⚠ Warning: Failed to create stacked plot: {str(e)}")
            
            return f"Integration completed: {len(all_patterns)} files processed"
            
        except Exception as e:
            raise Exception(f"Integration failed: {str(e)}")
    
    def _on_integration_finished(self, message):
        """Handle integration completion"""
        self.progress.stop()
        self.log(message)
        self.log("="*60)
        self.show_success("Success", "Azimuthal integration completed!")
    
    def _on_integration_error(self, error_msg):
        """Handle integration error"""
        self.progress.stop()
        self.log(f"❌ {error_msg}")
        self.log("="*60)
        self.show_error("Error", error_msg)


    def open_h5_preview(self):
        """Open H5 image preview dialog"""
        # Get initial file from input pattern if available
        initial_file = None
        if hasattr(self, 'input_pattern') and self.input_pattern:
            if os.path.exists(self.input_pattern):
                initial_file = self.input_pattern
        
        # Open preview dialog
        dialog = H5PreviewDialog(self.root, initial_file=initial_file)
        dialog.exec()


class BatchIntegrator:
    """Batch integration processor - migrated from batch_integration.py"""
    
    def __init__(self, poni_file, mask_file=None):
        """
        Initialize the integrator
        
        Args:
            poni_file (str): Path to calibration file (.poni)
            mask_file (str, optional): Path to mask file
        """
        if not PYFAI_AVAILABLE:
            raise ImportError("pyFAI is required for integration")
        
        self.ai = pyFAI.load(poni_file)
        print(f"✓ Successfully loaded calibration file: {poni_file}")
        print(f"  Detector: {self.ai.detector}")
        print(f"  Wavelength: {self.ai.wavelength*1e10:.4f} Å")
        print(f"  Sample-detector distance: {self.ai.dist*1000:.2f} mm")
        
        self.mask = None
        if mask_file and os.path.exists(mask_file):
            self.mask = self._load_mask(mask_file)
            print(f"✓ Successfully loaded mask file: {mask_file}")
            print(f"  Mask shape: {self.mask.shape}")
            print(f"  Masked pixels: {np.sum(self.mask)}")
        elif mask_file:
            print(f"⚠ Warning: Mask file not found: {mask_file}")
    
    def _load_mask(self, mask_file):
        """Load mask file"""
        ext = os.path.splitext(mask_file)[1].lower()
        
        if ext == '.npy':
            mask = np.load(mask_file)
        elif ext in ['.edf', '.tif', '.tiff', '.png']:
            mask = fabio.open(mask_file).data
        else:
            raise ValueError(f"Unsupported mask file format: {ext}")
        
        if mask.dtype != bool:
            mask = mask.astype(bool)
        
        return mask
    
    def _read_h5_image(self, h5_file, dataset_path=None, frame_index=0):
        """
        Read image data from HDF5 file
        
        Args:
            h5_file (str): Path to HDF5 file
            dataset_path (str, optional): Dataset path within HDF5
            frame_index (int): Frame index if multi-frame data
        
        Returns:
            numpy.ndarray: Image data
        """
        with h5py.File(h5_file, 'r') as f:
            if dataset_path is None:
                dataset_path = self._find_image_dataset(f)
            
            if dataset_path not in f:
                raise ValueError(f"Dataset not found in HDF5 file: {dataset_path}")
            
            data = f[dataset_path]
            
            if len(data.shape) == 3:
                if frame_index >= data.shape[0]:
                    raise ValueError(f"Frame index {frame_index} out of bounds (total frames: {data.shape[0]})")
                img_data = data[frame_index]
            else:
                img_data = data[()]
        
        return img_data
    
    def _find_image_dataset(self, h5_file_obj):
        """Automatically find image dataset path in HDF5"""
        common_paths = [
            '/entry/data/data',
            '/entry/instrument/detector/data',
            '/entry/data/image',
            '/data/data',
            '/data',
            '/image',
            'data',
        ]
        
        for path in common_paths:
            if path in h5_file_obj:
                return path
        
        def find_dataset(obj, path=''):
            if isinstance(obj, h5py.Dataset):
                if len(obj.shape) >= 2:
                    return path
            elif isinstance(obj, h5py.Group):
                for key in obj.keys():
                    result = find_dataset(obj[key], path + '/' + key)
                    if result:
                        return result
            return None
        
        result = find_dataset(h5_file_obj)
        if result:
            print(f"  Automatically found dataset: {result}")
            return result
        else:
            raise ValueError("No suitable image dataset found in HDF5 file")
    
    def integrate_single(self, h5_file, output_base, npt=2000, unit="2th_deg",
                        dataset_path=None, frame_index=0, formats=['xy'], **kwargs):
        """
        Integrate a single HDF5 file and save in multiple formats
        
        Args:
            h5_file (str): Path to HDF5 file
            output_base (str): Base filename for output (without extension)
            npt (int): Number of points in output pattern
            unit (str): Unit for integration ('2th_deg', 'q_nm^-1', etc.)
            dataset_path (str, optional): Dataset path within HDF5
            frame_index (int): Frame index if multi-frame data
            formats (list): List of output formats ('xy', 'dat', 'chi', 'fxye')
        
        Returns:
            tuple: (two_theta, intensity) arrays
        """
        # Read image
        img_data = self._read_h5_image(h5_file, dataset_path, frame_index)
        
        # Perform integration
        result = self.ai.integrate1d(
            img_data,
            npt,
            mask=self.mask,
            unit=unit,
            **kwargs
        )
        
        two_theta = result.radial
        intensity = result.intensity
        
        # Save in requested formats
        for fmt in formats:
            if fmt == 'xy':
                self._save_xy(output_base + '.xy', two_theta, intensity)
            elif fmt == 'dat':
                self._save_dat(output_base + '.dat', two_theta, intensity)
            elif fmt == 'chi':
                self._save_chi(output_base + '.chi', two_theta, intensity)
            elif fmt == 'fxye':
                self._save_fxye(output_base + '.fxye', two_theta, intensity)
            elif fmt == 'svg':
                self._save_svg(two_theta, intensity, output_base + '.svg')
            elif fmt == 'png':
                self._save_png(two_theta, intensity, output_base + '.png')
        
        return two_theta, intensity
    
    def _save_xy(self, filename, x, y):
        """Save as .xy format (two columns)"""
        np.savetxt(filename, np.column_stack((x, y)), fmt='%.6f  %.6f', delimiter='  ')
    
    def _save_dat(self, filename, x, y):
        """Save as .dat format"""
        with open(filename, 'w') as f:
            f.write("# 2Theta   Intensity\n")
            for xi, yi in zip(x, y):
                f.write(f"{xi:.6f}  {yi:.6f}\n")
    
    def _save_chi(self, filename, x, y):
        """Save as .chi format (GSAS-II compatible)"""
        with open(filename, 'w') as f:
            f.write(f"{os.path.basename(filename)}\n")
            f.write(f"Wavelength: {self.ai.wavelength*1e10:.6f}\n")
            f.write(f"2-Theta    Intensity\n")
            for xi, yi in zip(x, y):
                f.write(f"{xi:.4f}  {yi:.4f}\n")
    
    def _save_fxye(self, filename, x, y):
        """Save as .fxye format (GSAS format)"""
        with open(filename, 'w') as f:
            f.write("XYDATA\n")
            for xi, yi in zip(x, y):
                sigma = np.sqrt(max(yi, 1))  # Poisson statistics
                f.write(f"{xi:.6f}  {yi:.6f}  {sigma:.6f}\n")
    
    def _save_svg(self, x, y, filename):
        """Save as SVG plot"""
        if not MATPLOTLIB_AVAILABLE:
            print("⚠ matplotlib not available, skipping SVG output")
            return
        
        plt.figure(figsize=(10, 6))
        plt.plot(x, y, 'b-', linewidth=1)
        plt.xlabel('2θ (degree)', fontsize=12)
        plt.ylabel('Intensity', fontsize=12)
        plt.title('Integrated Diffraction Pattern', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filename, format='svg')
        plt.close()
    
    def _save_png(self, x, y, filename):
        """Save as PNG plot"""
        if not MATPLOTLIB_AVAILABLE:
            print("⚠ matplotlib not available, skipping PNG output")
            return
        
        plt.figure(figsize=(10, 6))
        plt.plot(x, y, 'b-', linewidth=1)
        plt.xlabel('2θ (degree)', fontsize=12)
        plt.ylabel('Intensity', fontsize=12)
        plt.title('Integrated Diffraction Pattern', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filename, format='png', dpi=300)
        plt.close()
    
    def _extract_pressure(self, filename):
        """
        Extract pressure value from filename
        
        Supports both loading and unloading data:
        - Loading: 10, 10.5, 40, etc.
        - Unloading: d3.21, d38.2, etc. (prefix 'd' indicates unloading)
        
        Returns:
            tuple: (pressure, is_unload)
        """
        basename = os.path.basename(filename)
        name_without_ext = os.path.splitext(basename)[0]
        
        is_unload = False
        
        # Check if filename starts with 'd' (unloading data)
        if name_without_ext.startswith('d') or name_without_ext.startswith('D'):
            is_unload = True
            name_without_ext = name_without_ext[1:]
        
        # Try various patterns
        patterns = [
            r'(\d+\.?\d*)[_\s]?GPa',  # 10GPa, 10.5GPa, 10_GPa
            r'[Pp](\d+\.?\d*)',        # P10, p10.5
            r'pressure[_\s]?(\d+\.?\d*)',  # pressure_10
            r'^(\d+\.?\d*)',           # Just numbers at start
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                return float(match.group(1)), is_unload
        
        return 0.0, is_unload
    
    def _extract_range_average(self, filename):
        """
        Extract range values from filename and calculate average
        Example: 0.72_Bin001_0.0-10.0.xy -> 5.0
        
        Returns:
            float or None: Average of the range, or None if no range found
        """
        basename = os.path.basename(filename)
        
        # Match pattern like "number-number"
        pattern = r'(\d+\.?\d*)[_\s]*-[_\s]*(\d+\.?\d*)'
        match = re.search(pattern, basename)
        
        if match:
            start = float(match.group(1))
            end = float(match.group(2))
            average = (start + end) / 2.0
            return average
        
        return None
    
    def create_stacked_plot(self, output_dir, offset='auto', output_name='stacked_plot.png'):
        """
        Create stacked diffraction pattern plot
        
        Two modes:
        1. If same pressure has multiple data files (e.g., bin data), create separate plot for each pressure
        2. Otherwise, create one stacked plot for all pressures
        
        Args:
            output_dir (str): Directory containing .xy or .dat files
            offset (str or float): Offset between curves ('auto' or specific value)
            output_name (str): Output filename
        """
        if not MATPLOTLIB_AVAILABLE:
            print("⚠ matplotlib not available, cannot create stacked plot")
            return
        
        # Find all .xy or .dat files
        xy_files = glob.glob(os.path.join(output_dir, '*.xy'))
        if not xy_files:
            xy_files = glob.glob(os.path.join(output_dir, '*.dat'))
        
        if not xy_files:
            print("⚠ No .xy or .dat files found for stacked plot")
            return
        
        # Group files by pressure
        from collections import defaultdict
        pressure_groups = defaultdict(list)
        
        for f in xy_files:
            pressure, is_unload = self._extract_pressure(f)
            range_avg = self._extract_range_average(f)
            pressure_groups[pressure].append((f, range_avg))
        
        # Check if any pressure group contains more than 2 files
        has_multi_file_groups = any(len(files) > 2 for files in pressure_groups.values())
        
        if has_multi_file_groups:
            # Mode 1: Generate separate stacked plot for each pressure group
            print(f"Detected multiple data files at same pressure, generating separate plots...")
            
            for pressure, file_list in sorted(pressure_groups.items()):
                if len(file_list) <= 2:
                    continue
                
                print(f"  Generating stacked plot for pressure {pressure:.2f} GPa ({len(file_list)} files)...")
                self._create_single_pressure_stacked_plot(
                    pressure, file_list, output_dir, offset,
                    f'stacked_plot_{pressure:.2f}GPa.png'
                )
        else:
            # Mode 2: All pressures in one plot
            print(f"Generating stacked plot for all pressures...")
            self._create_all_pressure_stacked_plot(xy_files, output_dir, offset, output_name)
    
    def _create_single_pressure_stacked_plot(self, pressure, file_list, output_dir, offset, output_name):
        """
        Create stacked plot for multiple data files at a single pressure point
        """
        if not MATPLOTLIB_AVAILABLE:
            return
        
        # Sort by range average
        file_list_sorted = sorted(file_list, key=lambda x: x[1] if x[1] is not None else 0)
        
        # Load data
        data_list = []
        range_avgs = []
        for file_path, range_avg in file_list_sorted:
            try:
                data = np.loadtxt(file_path)
                data_list.append(data)
                range_avgs.append(range_avg if range_avg is not None else 0)
            except Exception as e:
                print(f"    Warning: Could not load {file_path}: {e}")
        
        if not data_list:
            return
        
        # Calculate offset
        if offset == 'auto':
            max_intensities = [np.max(data[:, 1]) for data in data_list]
            calc_offset = np.mean(max_intensities) * 1.2
        else:
            calc_offset = float(offset)
        
        # Create figure
        plt.figure(figsize=(12, 10))
        
        # Color map (cycles every 90 degrees)
        base_colors = plt.cm.tab20(np.linspace(0, 1, 20))
        
        for idx, (data, range_avg) in enumerate(zip(data_list, range_avgs)):
            y_offset = idx * calc_offset
            color_idx = int(range_avg // 90) if range_avg is not None else idx
            color = base_colors[color_idx % len(base_colors)]
            label = f'{range_avg:.1f}°' if range_avg is not None else f'Data {idx+1}'
            
            plt.plot(data[:, 0], data[:, 1] + y_offset,
                    color=color, linewidth=1.2, label=label)
            
            # Add label between current baseline and next baseline
            x_pos = data[0, 0] + (data[-1, 0] - data[0, 0]) * 0.02
            # Position in the middle between current and next baseline
            if idx < len(data_list) - 1:
                # Not the last curve: middle between two baselines
                y_pos = y_offset + calc_offset / 2
            else:
                # Last curve: above its baseline
                y_pos = y_offset + calc_offset * 0.3
            
            plt.text(x_pos, y_pos, label,
                    fontsize=8, verticalalignment='bottom',
                    color='black', fontname='Arial')
        
        plt.xlabel('2θ (degrees)', fontsize=12)
        plt.ylabel('Intensity (offset)', fontsize=12)
        plt.title(f'Stacked Diffraction Patterns at {pressure:.2f} GPa',
                 fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(output_dir, output_name)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"    ✓ Stacked plot saved: {output_path}")
    
    def _create_all_pressure_stacked_plot(self, xy_files, output_dir, offset, output_name):
        """
        Create stacked plot for all pressures
        
        Supports loading/unloading data:
        - Loading data: sorted by pressure low to high
        - Unloading data (prefix 'd'): sorted high to low, stacked on top
        """
        if not MATPLOTLIB_AVAILABLE:
            return
        
        # Extract pressure, is_unload and sort
        file_info_list = []
        for f in xy_files:
            pressure, is_unload = self._extract_pressure(f)
            file_info_list.append((f, pressure, is_unload))
        
        # Separate loading and unloading data
        loading_data = [(f, p) for f, p, u in file_info_list if not u]
        unloading_data = [(f, p) for f, p, u in file_info_list if u]
        
        # Sort
        loading_data.sort(key=lambda x: x[1])
        unloading_data.sort(key=lambda x: x[1], reverse=True)
        
        # Combine
        file_pressure_pairs = loading_data + unloading_data
        
        # Load data
        data_list = []
        pressures = []
        is_unload_list = []
        for file_path, pressure in file_pressure_pairs:
            try:
                data = np.loadtxt(file_path)
                data_list.append(data)
                pressures.append(pressure)
                _, is_unload = self._extract_pressure(file_path)
                is_unload_list.append(is_unload)
            except Exception as e:
                print(f"Warning: Could not load {file_path}: {e}")
        
        if not data_list:
            return
        
        # Calculate offset
        if offset == 'auto':
            max_intensities = [np.max(data[:, 1]) for data in data_list]
            calc_offset = np.mean(max_intensities) * 1.2
        else:
            calc_offset = float(offset)
        
        # Color map (change every 10 GPa)
        colors = plt.cm.tab10(np.arange(10))
        
        # Create plot
        plt.figure(figsize=(12, 10))
        
        for idx, (data, pressure, is_unload) in enumerate(zip(data_list, pressures, is_unload_list)):
            color_idx = int(pressure // 10) % 10
            y_offset = idx * calc_offset
            label = f'd{pressure:.1f} GPa' if is_unload else f'{pressure:.1f} GPa'
            
            plt.plot(data[:, 0], data[:, 1] + y_offset,
                    color=colors[color_idx], linewidth=1.2, label=label)
            
            # Add pressure label between current baseline and next baseline
            x_pos = data[0, 0] + (data[-1, 0] - data[0, 0]) * 0.02
            # Position in the middle between current and next baseline
            if idx < len(data_list) - 1:
                # Not the last curve: middle between two baselines
                y_pos = y_offset + calc_offset / 2
            else:
                # Last curve: above its baseline
                y_pos = y_offset + calc_offset * 0.3
            
            plt.text(x_pos, y_pos, label,
                    fontsize=8, verticalalignment='bottom',
                    color='black', fontname='Arial')
        
        plt.xlabel('2θ (degrees)', fontsize=12)
        plt.ylabel('Intensity (offset)', fontsize=12)
        plt.title('Stacked Diffraction Patterns (Loading + Unloading)',
                 fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save plot
        output_path = os.path.join(output_dir, output_name)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Stacked plot saved: {output_path}")
        print(f"  Total patterns: {len(data_list)}")
        print(f"  Loading data: {len(loading_data)}, Unloading data: {len(unloading_data)}")
        if pressures:
            print(f"  Pressure range: {min(pressures):.1f} - {max(pressures):.1f} GPa")