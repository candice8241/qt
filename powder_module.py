# -*- coding: utf-8 -*-
"""
Powder XRD Module - Qt Version
Contains integration, peak fitting, phase analysis, and Birch-Murnaghan fitting

Migration Status:
✓ Integration module UI - Complete with all parameters
  - File inputs (PONI, mask, input pattern, output directory)
  - Integration parameters (NPT spinbox, unit selector, dataset path)
  - Output format checkboxes (XY, DAT, CHI, FXYE, SVG, PNG)
  - Stacked plot options
  - Full batch integration functionality using batch_integration.py

✓ Analysis module UI - Complete with all parameters
  - Phase analysis section with wavelength, crystal system, N points
  - Birch-Murnaghan/EoS fitting section
  - Full phase analysis functionality using batch_cal_volume.py

✓ Progress bar and logging - Complete
  - Cute sheep progress animation
  - Comprehensive process logging

TODO: 
  - Peak fitting functionality
  - Interactive fitting window
  - Birch-Murnaghan fitting implementation
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QCheckBox, QComboBox, QGroupBox,
                              QFileDialog, QMessageBox, QFrame, QScrollArea, QRadioButton,
                              QButtonGroup)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import threading
import subprocess
import sys
import os
from gui_base import GUIBase
from theme_module import CuteSheepProgressBar, ModernButton
from custom_widgets import SpinboxStyleButton, CustomSpinbox


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


class PowderXRDModule(GUIBase):
    """Powder XRD processing module - Qt version"""

    def __init__(self, parent, root):
        """
        Initialize Powder XRD module

        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        super().__init__()
        self.parent = parent
        self.root = root
        self.current_module = "integration"

        # Initialize variables
        self._init_variables()

        # Track windows and threads
        # Note: Interactive windows are now managed by main GUI
        self.interactive_eos_window = None
        self.running_threads = []

    def _init_variables(self):
        """Initialize all variables"""
        # Integration and fitting variables
        self.poni_path = ""
        self.mask_path = ""
        self.input_pattern = ""
        self.output_dir = ""
        self.dataset_path = "entry/data/data"
        self.npt = 4000
        self.unit = '2θ (°)'
        self.fit_method = 'pseudo'

        # Output format options
        self.format_xy = True
        self.format_dat = False
        self.format_chi = False
        self.format_fxye = False
        self.format_svg = False
        self.format_png = False

        # Stacked plot options
        self.create_stacked_plot = False
        self.stacked_plot_offset = 'auto'

        # Phase analysis variables
        self.phase_peak_csv = ""
        self.phase_volume_csv = ""
        self.phase_volume_system = 'FCC'
        self.phase_volume_output = ""
        self.phase_wavelength = 0.4133
        self.phase_n_points = 4

        # Birch-Murnaghan / EoS variables
        self.bm_input_file = ""
        self.bm_output_dir = ""
        self.bm_order = '3'
        self.eos_model = 'BM-3rd'

    def setup_ui(self):
        """Setup the complete powder XRD UI"""
        # Get or create layout for parent
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background-color: {self.colors['bg']}; border: none;")

        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {self.colors['bg']};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Setup modules
        self.setup_integration_module(content_layout)
        self.setup_analysis_module(content_layout)

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

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def prebuild_interactive_windows(self, force=False):
        """Placeholder for prebuilding interactive windows"""
        # TODO: Implement interactive window prebuilding
        pass

    def setup_integration_module(self, parent_layout):
        """Setup integration module UI to mirror provided layout"""
        int_card = self.create_card_frame(None)
        int_layout = QVBoxLayout(int_card)
        int_layout.setContentsMargins(20, 15, 20, 15)
        int_layout.setSpacing(12)

        header = QLabel("⚗️ Integration Settings & Output Options")
        header.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        int_layout.addWidget(header)

        columns = QHBoxLayout()
        columns.setSpacing(16)

        # Left: Integration settings
        left_panel = QWidget()
        left_panel.setMinimumWidth(550)  # Set minimum width to ensure alignment with lower module
        from PyQt6.QtWidgets import QSizePolicy
        left_panel.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)
        left_panel.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 4, 0, 4)
        left_layout.setSpacing(8)
        
        left_title = QLabel("")
        left_title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        left_title.setStyleSheet(f"color: {self.colors['primary']}; background-color: {self.colors['card_bg']};")
        left_layout.addWidget(left_title)

        self.create_file_input(left_layout, "PONI File:", "poni_path")
        self.create_file_input(left_layout, "Mask File:", "mask_path")
        self.create_file_input(left_layout, "Input Pattern:", "input_pattern")
        self.create_folder_input(left_layout, "Output Directory:", "output_dir")
        self.create_text_input(left_layout, "Dataset Directory:", "dataset_path", placeholder="entry/data/data", with_browse=True)

        # Add Run Integration button centered
        run_int_btn_row = QWidget()
        run_int_btn_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        run_int_btn_layout = QHBoxLayout(run_int_btn_row)
        run_int_btn_layout.setContentsMargins(0, 15, 0, 0)
        run_int_btn_layout.setSpacing(0)
        
        run_int_btn_layout.addStretch()
        run_int_btn = ModernButton(
            "Run Integration",
            self.run_integration,
            bg_color=self.colors['secondary'],
            hover_color=self.colors['primary_hover'],
            width=170, height=36,
            parent=run_int_btn_row
        )
        run_int_btn.setFont(QFont('Arial', 9))
        run_int_btn_layout.addWidget(run_int_btn)
        run_int_btn_layout.addStretch()

        left_layout.addWidget(run_int_btn_row)
        left_layout.addStretch()

        # Right: output options and quick actions stacked vertically
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 4, 0, 4)
        right_layout.setSpacing(12)

        output_card = self.create_card_frame(None)
        output_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card_bg']};
                border: 2px solid #888888;
                border-radius: 8px;
            }}
        """)
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(15, 12, 15, 12)
        output_layout.setSpacing(8)

        # Number of Points - horizontal layout
        npt_row = QWidget()
        npt_row.setStyleSheet(f"background-color: transparent; border: none;")
        npt_layout = QHBoxLayout(npt_row)
        npt_layout.setContentsMargins(0, 0, 0, 8)
        npt_layout.setSpacing(10)

        npt_label = QLabel("Number of Points")
        npt_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        npt_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: transparent; border: none;")
        npt_layout.addWidget(npt_label)

        from PyQt6.QtWidgets import QSpinBox
        self.npt_spinbox = QSpinBox()
        self.npt_spinbox.setRange(500, 1000000)
        self.npt_spinbox.setValue(4000)
        self.npt_spinbox.setSingleStep(500)
        self.npt_spinbox.setFixedWidth(80)
        self.npt_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.npt_spinbox.setFont(QFont('Arial', 9))
        self.npt_spinbox.setStyleSheet(f"""
            QSpinBox {{
                background-color: white;
                color: #444444;
                border: 2px solid #AAAAAA;
                padding: 3px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 0px;
                border: none;
            }}
        """)
        self.npt_spinbox.valueChanged.connect(lambda v: setattr(self, 'npt', int(v)))
        npt_layout.addWidget(self.npt_spinbox)
        npt_layout.addStretch()
        output_layout.addWidget(npt_row)

        # Unit - vertical layout, label on top, options below
        unit_container = QWidget()
        unit_container.setStyleSheet(f"background-color: transparent; border: none;")
        unit_layout = QVBoxLayout(unit_container)
        unit_layout.setContentsMargins(0, 0, 0, 16)
        unit_layout.setSpacing(10)

        unit_label = QLabel("Unit")
        unit_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        unit_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: transparent; border: none;")
        unit_layout.addWidget(unit_label)

        # Radio buttons in horizontal layout
        unit_radios_row = QWidget()
        unit_radios_row.setStyleSheet(f"background-color: transparent; border: none;")
        unit_radios_layout = QHBoxLayout(unit_radios_row)
        unit_radios_layout.setContentsMargins(0, 0, 0, 0)
        unit_radios_layout.setSpacing(20)

        self.unit_group = QButtonGroup(unit_container)
        unit_options = ['2θ (°)', 'q (A⁻¹)', 'r (mm)']
        for option in unit_options:
            radio = QRadioButton(option)
            radio.setChecked(option == '2θ (°)')
            radio.setFont(QFont('Arial', 9))
            radio.setStyleSheet(f"""
                QRadioButton {{
                    color: {self.colors['text_dark']};
                    background-color: transparent;
                    border: none;
                }}
                QRadioButton::indicator {{
                    width: 10px;
                    height: 10px;
                    border: 1.5px solid #999999;
                    border-radius: 2px;
                    background-color:{self.colors['primary']};
                }}
                QRadioButton::indicator:checked {{
                    background-color: {self.colors['primary']};
                    border: 1.5px solid #999999;
                    border-radius: 2px;
                    image: url(point.png);
                }}
            """)
            radio.toggled.connect(lambda checked, text=option: setattr(self, 'unit', text) if checked else None)
            self.unit_group.addButton(radio)
            unit_radios_layout.addWidget(radio)

        unit_radios_layout.addStretch()
        unit_layout.addWidget(unit_radios_row)
        output_layout.addWidget(unit_container)

        formats_label = QLabel("Select Output Formats:")
        formats_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        formats_label.setStyleSheet(f"color: #666666; background-color: {self.colors['card_bg']}; margin-bottom: 0px;border:none;")
        output_layout.addWidget(formats_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Format checkboxes without frame
        formats_container = QWidget()
        formats_container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        formats_frame_layout = QVBoxLayout(formats_container)
        formats_frame_layout.setContentsMargins(0, 8, 0, 8)
        formats_frame_layout.setSpacing(6)

        formats_row1 = QWidget()
        formats_row1.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        formats_row1_layout = QHBoxLayout(formats_row1)
        formats_row1_layout.setContentsMargins(0, 0, 0, 0)
        formats_row1_layout.setSpacing(20)

        self.format_checkboxes = {}
        for key, label, default in [('xy', '.xy', True), ('dat', '.dat', False), ('chi', '.chi', False)]:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.setFont(QFont('Arial', 9))
            cb.setFixedWidth(47)  # 固定宽度以实现垂直对齐
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
                    background-color: #E8D5F0;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {self.colors['primary']};
                    
                    border: 1.5px solid #999999;
                    border-radius: 2px;
                    image:url(check.png);
                    
                }}
                
            """)
            cb.stateChanged.connect(lambda state, k=key: setattr(self, f'format_{k}', state == Qt.CheckState.Checked.value))
            self.format_checkboxes[key] = cb
            formats_row1_layout.addWidget(cb)
        formats_row1_layout.addStretch()
        formats_frame_layout.addWidget(formats_row1)

        formats_row2 = QWidget()
        formats_row2.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        formats_row2_layout = QHBoxLayout(formats_row2)
        formats_row2_layout.setContentsMargins(0, 0, 0, 0)
        formats_row2_layout.setSpacing(20)
        for key, label, default in [('fxye', '.fxye', False), ('svg', '.svg', False), ('png', '.png', False)]:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.setFont(QFont('Arial', 9))
            cb.setFixedWidth(47)  # 固定宽度以实现垂直对齐
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
                    image:url(check.png);
                }}
            """)
            cb.stateChanged.connect(lambda state, k=key: setattr(self, f'format_{k}', state == Qt.CheckState.Checked.value))
            self.format_checkboxes[key] = cb
            formats_row2_layout.addWidget(cb)
        formats_row2_layout.addStretch()
        formats_frame_layout.addWidget(formats_row2)

        output_layout.addWidget(formats_container)

        stacked_box = QWidget()
        stacked_box.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        stacked_layout = QVBoxLayout(stacked_box)
        stacked_layout.setContentsMargins(0, 12, 0, 0)
        stacked_layout.setSpacing(6)

        # Add "Stacked Plot Options:" label
        stacked_options_label = QLabel("Stacked Plot Options:")
        stacked_options_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        stacked_options_label.setStyleSheet(f"color: #666666; background-color: {self.colors['card_bg']};border:none;")
        stacked_layout.addWidget(stacked_options_label)

        self.stacked_plot_cb = QCheckBox("Create Stacked Plot")
        self.stacked_plot_cb.setFont(QFont('Arial', 9))
        self.stacked_plot_cb.setStyleSheet(f"""
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
                image:url(point.png);
            }}
        """)
        self.stacked_plot_cb.stateChanged.connect(
            lambda state: setattr(self, 'create_stacked_plot', state == Qt.CheckState.Checked.value))
        stacked_layout.addWidget(self.stacked_plot_cb)

        offset_row = QWidget()
        offset_row.setStyleSheet(f"background-color: transparent; border: none;")
        offset_row_layout = QHBoxLayout(offset_row)
        offset_row_layout.setContentsMargins(0, 0, 0, 0)
        offset_row_layout.setSpacing(10)

        offset_label = QLabel("Offset:")
        offset_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        offset_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: transparent; border: none;")
        offset_row_layout.addWidget(offset_label)

        self.offset_entry = QLineEdit("auto")
        self.offset_entry.setFixedWidth(70)
        self.offset_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.offset_entry.setFont(QFont('Arial', 9))
        self.offset_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 2px solid #AAAAAA;
                padding: 3px;
            }}
        """)
        self.offset_entry.textChanged.connect(lambda text: setattr(self, 'stacked_plot_offset', text))
        offset_row_layout.addWidget(self.offset_entry)
        offset_row_layout.addStretch()
        stacked_layout.addWidget(offset_row)

        # Add help text below offset
        offset_help = QLabel("(use 'auto' or number for offset)")
        offset_help.setFont(QFont('Arial', 8))
        offset_help.setStyleSheet(f"color: #999999; background-color: transparent; border: none;")
        stacked_layout.addWidget(offset_help)

        output_layout.addWidget(stacked_box)

        # Wrap output_card in container to prevent horizontal stretching and center it
        output_card_container = QWidget()
        output_card_container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        output_card_container_layout = QHBoxLayout(output_card_container)
        output_card_container_layout.setContentsMargins(0, 0, 0, 0)
        output_card_container_layout.setSpacing(0)
        output_card_container_layout.addStretch()
        output_card_container_layout.addWidget(output_card)
        output_card_container_layout.addStretch()

        # Add vertical centering for output card to align with left panel file inputs
        right_layout.addStretch(1)
        right_layout.addWidget(output_card_container)
        right_layout.addStretch(2)

        columns.addWidget(left_panel, stretch=2)
        columns.addWidget(right_panel, stretch=1)
        int_layout.addLayout(columns)

        parent_layout.addWidget(int_card)

    def setup_analysis_module(self, parent_layout):
        """Setup analysis module UI following provided mockups"""

        analysis_card = self.create_card_frame(None)
        analysis_layout = QVBoxLayout(analysis_card)
        analysis_layout.setContentsMargins(20, 15, 20, 15)
        analysis_layout.setSpacing(12)

        header = QLabel("📊 Lattice Parameters Calculation")
        header.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        analysis_layout.addWidget(header)

        columns = QHBoxLayout()
        columns.setSpacing(16)

        # Left column: file inputs
        left_panel = QWidget()
        left_panel.setMinimumWidth(550)  # Set minimum width to ensure alignment with upper module
        from PyQt6.QtWidgets import QSizePolicy
        left_panel.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)
        left_panel.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 4, 0, 4)
        left_layout.setSpacing(10)

        left_title = QLabel("")
        left_title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        left_title.setStyleSheet(f"color: {self.colors['primary']}; background-color: {self.colors['card_bg']};")
        left_layout.addWidget(left_title)

        self.create_file_input(left_layout, "Input CSV (Volume Calculation):", "phase_peak_csv")
        self.create_folder_input(left_layout, "Output Directory:", "phase_volume_output")

        # Add Calculate Lattice Parameters button centered in left panel
        btn_row = QWidget()
        btn_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.setSpacing(12)

        # Center the button by adding stretch before and after
        btn_layout.addStretch()
        phase_btn = ModernButton(
            "Calculate Lattice Parameters",
            self.run_phase_analysis,
            bg_color=self.colors['secondary'],
            hover_color=self.colors['primary_hover'],
            width=200, height=36,
            parent=btn_row
        )
        phase_btn.setFont(QFont('Arial', 10))
        btn_layout.addWidget(phase_btn)
        btn_layout.addStretch()

        left_layout.addWidget(btn_row)
        left_layout.addStretch()

        # Right column: crystal system and wavelength
        right_panel = QWidget()
        from PyQt6.QtWidgets import QSizePolicy
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        right_panel.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 4, 0, 4)
        right_layout.setSpacing(10)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)  # Center horizontally

        # Create a single frame for both crystal system and wavelength
        combined_frame = QFrame()
        combined_frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Fixed size to fit content
        combined_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card_bg']};
                border: 2px solid #888888;
                border-radius: 6px;
            }}
        """)

        combined_frame_layout = QVBoxLayout(combined_frame)
        combined_frame_layout.setContentsMargins(10, 8, 10, 8)
        combined_frame_layout.setSpacing(15)

        # Crystal System title inside the frame
        right_title = QLabel("Crystal System")
        right_title.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        right_title.setStyleSheet(f"color: {self.colors['text_dark']};border: none; background-color: {self.colors['card_bg']};")
        combined_frame_layout.addWidget(right_title)

        # First row of crystal systems
        row1 = QWidget()
        row1.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(19)

        # Second row of crystal systems
        row2 = QWidget()
        row2.setStyleSheet(f"background-color: {self.colors['card_bg']}; ")
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(30)

        systems = [
            ('FCC', 'FCC'),
            ('BCC', 'BCC'),
            ('Hexagonal', 'Hexagonal'),
            ('Tetragonal', 'Tetragonal'),
            ('Orthorhombic', 'Orthorhombic'),
            ('Monoclinic', 'Monoclinic'),
            ('Triclinic', 'Triclinic'),
        ]

        self.phase_system_group = QButtonGroup(combined_frame)
        for idx, (label, value) in enumerate(systems):
            radio = QRadioButton(label)
            radio.setChecked(value == self.phase_volume_system)
            radio.setFont(QFont('Arial', 8))
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
                    background-color:{self.colors['primary']} ;
                }}
                QRadioButton::indicator:checked {{
                    background-color: {self.colors['primary']};
                    
                    border: 1.5px solid #999999;
                    border-radius: 2px;
                    image:url(check.png);
                }}
            """)
            radio.toggled.connect(lambda checked, text=value: setattr(self, 'phase_volume_system', text) if checked else None)
            self.phase_system_group.addButton(radio)
            if idx < 4:
                row1_layout.addWidget(radio)
            else:
                row2_layout.addWidget(radio)

        row1_layout.addStretch()
        row2_layout.addStretch()
        combined_frame_layout.addWidget(row1)
        combined_frame_layout.addWidget(row2)

        # Wavelength section inside the same frame - label and input in same row, aligned left
        wl_row = QWidget()
        wl_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        wl_row_layout = QHBoxLayout(wl_row)
        wl_row_layout.setContentsMargins(0, 0, 0, 0)
        wl_row_layout.setSpacing(10)
        
        wl_label = QLabel("Wavelength (Å)")
        wl_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        wl_label.setStyleSheet(f"color: {self.colors['text_dark']}; border: none;background-color: transparent;")
        wl_row_layout.addWidget(wl_label)
        
        self.phase_wavelength_entry = QLineEdit(str(self.phase_wavelength))
        self.phase_wavelength_entry.setFixedWidth(80)
        self.phase_wavelength_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phase_wavelength_entry.setFont(QFont('Arial', 9))
        self.phase_wavelength_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 2px solid #AAAAAA;
                padding: 3px;
            }}
        """)
        self.phase_wavelength_entry.textChanged.connect(self._on_phase_wavelength_changed)
        wl_row_layout.addWidget(self.phase_wavelength_entry)
        
        wl_row_layout.addStretch()
        
        combined_frame_layout.addWidget(wl_row)

        # Add frame directly to right layout
        right_layout.addWidget(combined_frame)
        right_layout.addStretch()

        # Same layout as Integration Settings (2:1 ratio)
        columns.addWidget(left_panel, stretch=2)
        columns.addWidget(right_panel, stretch=1)
        analysis_layout.addLayout(columns)

        parent_layout.addWidget(analysis_card)

    def _on_phase_wavelength_changed(self, text):
        """Handle wavelength edits safely"""
        try:
            self.phase_wavelength = float(text)
        except ValueError:
            self.phase_wavelength = 0.0

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
                border: 2px solid #AAAAAA;
                padding: 3px;
            }}
        """)
        entry.textChanged.connect(lambda text: setattr(self, var_name, text))
        input_layout.addWidget(entry, stretch=1)  # Allow entry to stretch with panel

        browse_btn = ModernButton(
            "Browse",
            lambda: self.browse_file(entry),
            bg_color=self.colors['secondary'],
            hover_color=self.colors['primary'],
            width=75, height=28,
            parent=container
        )
        browse_btn.setFont(QFont('Arial', 9))
        input_layout.addWidget(browse_btn, stretch=0)  # Keep button fixed size

        layout.addLayout(input_layout)
        parent_layout.addWidget(container)

        # Store reference to entry
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
                border: 2px solid #AAAAAA;
                padding: 3px;
            }}
        """)
        entry.textChanged.connect(lambda text: setattr(self, var_name, text))
        input_layout.addWidget(entry, stretch=1)  # Allow entry to stretch with panel

        browse_btn = ModernButton(
            "Browse",
            lambda: self.browse_folder(entry),
            bg_color=self.colors['secondary'],
            hover_color=self.colors['primary'],
            width=75, height=28,
            parent=container
        )
        browse_btn.setFont(QFont('Arial', 9))
        input_layout.addWidget(browse_btn, stretch=0)  # Keep button fixed size

        layout.addLayout(input_layout)
        parent_layout.addWidget(container)

        # Store reference to entry
        setattr(self, f"{var_name}_entry", entry)

    def create_text_input(self, parent_layout, label_text, var_name, placeholder="", with_browse=False):
        """Create a simple text input widget with optional browse button"""
        container = QWidget()
        container.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)

        label = QLabel(label_text)
        label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        layout.addWidget(label)

        if with_browse:
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
                    border: 2px solid #AAAAAA;
                    padding: 3px;
                }}
            """)
            entry.textChanged.connect(lambda text: setattr(self, var_name, text))
            input_layout.addWidget(entry, stretch=1)  # Allow entry to stretch

            browse_btn = ModernButton(
                "Browse",
                lambda: self.browse_folder(entry),
                bg_color=self.colors['secondary'],
                hover_color=self.colors['primary'],
                width=75, height=28,
                parent=container
            )
            browse_btn.setFont(QFont('Arial', 9))
            input_layout.addWidget(browse_btn, stretch=0)  # Keep button fixed size
            layout.addLayout(input_layout)
        else:
            entry = QLineEdit()
            entry.setFont(QFont('Arial', 9))
            entry.setPlaceholderText(placeholder)
            entry.setText(getattr(self, var_name, ""))
            entry.setStyleSheet(f"""
                QLineEdit {{
                    background-color: white;
                    color: {self.colors['text_dark']};
                    border: 2px solid #AAAAAA;
                    padding: 3px;
                }}
            """)
            entry.textChanged.connect(lambda text: setattr(self, var_name, text))
            layout.addWidget(entry)

        parent_layout.addWidget(container)

        # Store reference to entry
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
            entry.setText(filename)

    def browse_folder(self, entry):
        """Browse for a folder"""
        folder = QFileDialog.getExistingDirectory(self.root, "Select Folder")
        if folder:
            entry.setText(folder)

    def log(self, message):
        """Add message to log"""
        self.log_text.append(message)

    def show_error(self, title, message):
        """Show error dialog"""
        QMessageBox.critical(self.root, title, message)

    def show_success(self, title, message):
        """Show success dialog"""
        QMessageBox.information(self.root, title, message)

    # Functionality methods
    def run_integration(self):
        """Run batch integration using subprocess (isolated process)"""
        try:
            # Validate inputs
            if not self.poni_path:
                self.show_error("Error", "Please select a PONI file")
                return
            if not self.input_pattern:
                self.show_error("Error", "Please specify input pattern")
                return
            if not self.output_dir:
                self.show_error("Error", "Please select output directory")
                return
            
            # Check if files exist
            if not os.path.exists(self.poni_path):
                self.show_error("Error", f"PONI file not found: {self.poni_path}")
                return
            
            # Collect output formats
            formats = []
            if self.format_xy:
                formats.append('xy')
            if self.format_dat:
                formats.append('dat')
            if self.format_chi:
                formats.append('chi')
            if self.format_fxye:
                formats.append('fxye')
            if self.format_svg:
                formats.append('svg')
            if self.format_png:
                formats.append('png')
            
            if not formats:
                formats = ['xy']  # Default
            
            # Convert unit name to pyFAI format
            unit_map = {
                '2θ (°)': '2th_deg',
                'q (nm⁻¹)': 'q_nm^-1',
                'q (A⁻¹)': 'q_A^-1',
                'r (mm)': 'r_mm'
            }
            unit_pyFAI = unit_map.get(self.unit, '2th_deg')
            
            # Log start
            self.log("="*60)
            self.log("Starting Batch Integration in subprocess...")
            self.log(f"PONI: {self.poni_path}")
            self.log(f"Mask: {self.mask_path if self.mask_path else 'None'}")
            self.log(f"Input: {self.input_pattern}")
            self.log(f"Output: {self.output_dir}")
            self.log(f"NPT: {self.npt}")
            self.log(f"Unit: {self.unit}")
            self.log(f"Output formats: {', '.join(formats)}")
            
            # Start progress animation
            self.progress.start()
            
            # Create integration script for subprocess
            script = self._create_integration_script(
                poni_path=self.poni_path,
                mask_path=self.mask_path if self.mask_path else "",
                input_pattern=self.input_pattern,
                output_dir=self.output_dir,
                dataset_path=self.dataset_path if self.dataset_path else "",
                npt=self.npt,
                unit=unit_pyFAI,
                formats=formats,
                create_stacked_plot=self.create_stacked_plot,
                stacked_plot_offset=self.stacked_plot_offset
            )
            
            # Start subprocess
            self.integration_process = subprocess.Popen(
                [sys.executable, '-c', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()
            )
            
            self.log("✓ Subprocess started successfully")
            
            # Start checking subprocess status
            if hasattr(self, 'check_timer'):
                self.check_timer.stop()
            
            self.check_timer = QTimer()
            self.check_timer.timeout.connect(self._check_integration_status)
            self.check_timer.start(500)  # Check every 500ms
            
        except Exception as e:
            self.progress.stop()
            self.log(f"❌ Error: {str(e)}")
            self.show_error("Error", f"Failed to start integration:\n{str(e)}")
    
    def _create_integration_script(self, **params):
        """Create Python script for subprocess execution"""
        # Escape strings for Python script
        def escape(s):
            return s.replace('\\', '\\\\').replace('"', '\\"') if s else ""
        
        return f'''
import sys
import os

# Add current directory to path
sys.path.insert(0, "{escape(os.path.dirname(os.path.abspath(__file__)))}")

try:
    from batch_integration import run_batch_integration
    
    print("Starting integration...", flush=True)
    
    run_batch_integration(
        poni_file="{escape(params['poni_path'])}",
        mask_file="{escape(params['mask_path'])}" if "{escape(params['mask_path'])}" else None,
        input_pattern="{escape(params['input_pattern'])}",
        output_dir="{escape(params['output_dir'])}",
        dataset_path="{escape(params['dataset_path'])}" if "{escape(params['dataset_path'])}" else None,
        npt={params['npt']},
        unit="{params['unit']}",
        formats={params['formats']},
        create_stacked_plot={params['create_stacked_plot']},
        stacked_plot_offset="{params['stacked_plot_offset']}",
        disable_progress_bar=True
    )
    
    print("\\n\\n=== INTEGRATION_SUCCESS ===", flush=True)
    
except Exception as e:
    print(f"\\n\\n=== INTEGRATION_ERROR: {{e}} ===", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    def _check_integration_status(self):
        """Check subprocess status periodically"""
        if hasattr(self, 'integration_process'):
            retcode = self.integration_process.poll()
            
            if retcode is not None:
                # Process has finished
                self.check_timer.stop()
                self.progress.stop()
                
                try:
                    stdout, stderr = self.integration_process.communicate(timeout=1)
                except:
                    stdout, stderr = "", ""
                
                if "INTEGRATION_SUCCESS" in stdout:
                    self.log("✓ Integration completed successfully!")
                    self.log("="*60)
                    self.show_success("Success", "Batch integration completed!")
                else:
                    self.log("❌ Integration failed or was interrupted")
                    if stderr:
                        # Show first 500 chars of error
                        error_preview = stderr[:500]
                        self.log(f"Error output:\n{error_preview}")
                        if len(stderr) > 500:
                            self.log("... (error message truncated)")
                    self.log("="*60)
                    self.show_error("Error", "Integration failed. Check log for details.")
                
                # Cleanup
                del self.integration_process
    
    def _on_integration_finished(self, message):
        """Handle integration completion"""
        self.progress.stop()
        self.log("✓ Integration completed successfully!")
        self.log("="*60)
        self.show_success("Success", "Batch integration completed!")
    
    def _on_integration_error(self, error_msg):
        """Handle integration error"""
        self.progress.stop()
        self.log(f"❌ Error: {error_msg}")
        self.log("="*60)
        self.show_error("Error", f"Integration failed:\n{error_msg}")

    def run_fitting(self):
        """TODO: Implement fitting functionality"""
        self.log("Peak Fitting: Feature not yet implemented")
        self.show_error("Not Implemented", "Peak fitting feature is not yet implemented in Qt version")

    def open_interactive_fitting(self):
        """Open interactive fitting window - now handled by main GUI"""
        # This method is kept for compatibility but is no longer used
        # The main GUI now manages the interactive fitting window directly
        self.log("Interactive Fitting GUI is now managed by the main window")
        pass

    def run_phase_analysis(self):
        """Run phase analysis and lattice parameter fitting"""
        try:
            # Validate inputs
            if not self.phase_peak_csv:
                self.show_error("Error", "Please select peak CSV file")
                return
            
            if not os.path.exists(self.phase_peak_csv):
                self.show_error("Error", f"Peak CSV file not found: {self.phase_peak_csv}")
                return
            
            if not self.phase_volume_output:
                self.show_error("Error", "Please select output directory")
                return
            
            self.log("="*60)
            self.log("Starting Phase Analysis...")
            self.log(f"Peak CSV: {self.phase_peak_csv}")
            self.log(f"Wavelength: {self.phase_wavelength} Å")
            self.log(f"Crystal System: {self.phase_volume_system}")
            self.log(f"N Points: {self.phase_n_points}")
            self.log(f"Output: {self.phase_volume_output}")
            
            # Start progress animation
            self.progress.start()
            
            # Import and run phase analysis
            from batch_cal_volume import XRayDiffractionAnalyzer
            
            # Create worker thread with signals
            def run_task():
                analyzer = XRayDiffractionAnalyzer(
                    wavelength=self.phase_wavelength,
                    n_pressure_points=self.phase_n_points
                )
                
                # Map crystal system names
                system_map = {
                    'FCC': 'cubic_FCC',
                    'BCC': 'cubic_BCC',
                    'SC': 'cubic_SC',
                    'HCP': 'Hexagonal',
                    'Tetragonal': 'Tetragonal',
                    'Orthorhombic': 'Orthorhombic'
                }
                crystal_system = system_map.get(self.phase_volume_system, 'cubic_FCC')
                
                # Run analysis in auto mode
                results = analyzer.analyze(
                    csv_path=self.phase_peak_csv,
                    original_system=crystal_system,
                    new_system=crystal_system,
                    auto_mode=True
                )
                
                return results
            
            signals = WorkerSignals()
            signals.finished.connect(self._on_phase_analysis_finished)
            signals.error.connect(self._on_phase_analysis_error)
            
            worker = WorkerThread(run_task, signals)
            self.running_threads.append(worker)
            worker.start()
            
        except Exception as e:
            self.progress.stop()
            self.log(f"❌ Error: {str(e)}")
            self.show_error("Error", f"Failed to start phase analysis:\n{str(e)}")
    
    def _on_phase_analysis_finished(self, message):
        """Handle phase analysis completion"""
        self.progress.stop()
        self.log("✓ Phase analysis completed successfully!")
        self.log("="*60)
        self.show_success("Success", "Phase analysis completed!")
    
    def _on_phase_analysis_error(self, error_msg):
        """Handle phase analysis error"""
        self.progress.stop()
        self.log(f"❌ Error: {error_msg}")
        self.log("="*60)
        self.show_error("Error", f"Phase analysis failed:\n{error_msg}")

    def run_birch_murnaghan(self):
        """TODO: Implement Birch-Murnaghan fitting"""
        self.log("Birch-Murnaghan: Feature not yet implemented")
        self.show_error("Not Implemented", "Birch-Murnaghan fitting is not yet implemented in Qt version")

    def open_interactive_eos_gui(self):
        """Open interactive EoS GUI - now handled by main GUI"""
        # This method is kept for compatibility but is no longer used
        # The main GUI now manages the interactive EoS window directly
        self.log("Interactive EoS GUI is now managed by the main window")
        pass