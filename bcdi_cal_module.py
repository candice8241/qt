# -*- coding: utf-8 -*-
"""
BCDI Calibration Module - Qt Version
X-ray Diffraction Analysis Tool for phase transition identification and lattice parameter fitting

Migrated from Streamlit to PyQt6
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QCheckBox, QComboBox, QGroupBox,
                              QFileDialog, QMessageBox, QFrame, QSpinBox, QDoubleSpinBox,
                              QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import os
import sys
from gui_base import GUIBase
from theme_module import CuteSheepProgressBar, ModernButton
from custom_widgets import SpinboxStyleButton, CustomSpinbox
from batch_cal_volume import XRayDiffractionAnalyzer


class AnalysisWorkerThread(QThread):
    """Worker thread for X-ray diffraction analysis"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, analyzer, csv_path, original_system, new_system, auto_mode=True):
        super().__init__()
        self.analyzer = analyzer
        self.csv_path = csv_path
        self.original_system = original_system
        self.new_system = new_system
        self.auto_mode = auto_mode

    def run(self):
        """Run the analysis"""
        try:
            self.progress.emit("Starting analysis...")
            results = self.analyzer.analyze(
                self.csv_path,
                original_system=self.original_system,
                new_system=self.new_system,
                auto_mode=self.auto_mode
            )
            
            if results:
                self.finished.emit("Analysis completed successfully!")
            else:
                self.error.emit("Analysis failed - no results returned")
        except Exception as e:
            import traceback
            error_msg = f"Error during analysis:\n{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class BCDICalModule(GUIBase):
    """BCDI Calibration module for X-ray Diffraction Analysis"""

    # Crystal system mapping
    CRYSTAL_SYSTEM_MAP = {
        "Face-Centered Cubic (FCC)": "cubic_FCC",
        "Body-Centered Cubic (BCC)": "cubic_BCC",
        "Simple Cubic (SC)": "cubic_SC",
        "Hexagonal Close-Packed (HCP)": "Hexagonal",
        "Tetragonal": "Tetragonal",
        "Orthorhombic": "Orthorhombic",
        "Monoclinic": "Monoclinic",
        "Triclinic": "Triclinic"
    }

    def __init__(self, parent, root):
        """
        Initialize BCDI Calibration module

        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        super().__init__()
        self.parent = parent
        self.root = root

        # Initialize analyzer
        self.analyzer = None
        
        # Initialize variables
        self._init_variables()

        # Track threads
        self.running_threads = []

    def _init_variables(self):
        """Initialize all variables"""
        self.csv_file_path = ""
        self.wavelength = 0.4133  # Default wavelength in Angstroms
        self.n_pressure_points = 4  # Default number of pressure points
        self.original_crystal_system = "cubic_FCC"
        self.new_crystal_system = "cubic_FCC"
        
        # Tolerances (using default values from XRayDiffractionAnalyzer)
        self.peak_tolerance_1 = 0.3
        self.peak_tolerance_2 = 0.4
        self.peak_tolerance_3 = 0.01

    def setup_ui(self):
        """Setup the user interface"""
        # Get or create main layout
        if self.parent.layout() is None:
            main_layout = QVBoxLayout(self.parent)
            self.parent.setLayout(main_layout)
        else:
            main_layout = self.parent.layout()

        # Clear existing widgets
        self.clear_layout(main_layout)

        # Title section
        title_label = QLabel("BCDI Calibration - X-ray Diffraction Analysis")
        title_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['primary']}; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Phase transition identification and lattice parameter fitting for X-ray diffraction data"
        )
        desc_label.setFont(QFont('Arial', 9))
        desc_label.setStyleSheet(f"color: {self.colors['text_light']}; padding: 5px;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # ===== Input Section =====
        input_group = self.create_group_box("Input Data")
        input_layout = QVBoxLayout()

        # CSV file input
        csv_row = QHBoxLayout()
        csv_label = QLabel("Peak Data CSV:")
        csv_label.setFixedWidth(150)
        csv_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.csv_file_entry = QLineEdit()
        self.csv_file_entry.setPlaceholderText("Select CSV file containing peak data...")
        self.csv_file_entry.setStyleSheet(self.get_input_style())
        csv_browse_btn = ModernButton("Browse", self.browse_csv_file)
        csv_row.addWidget(csv_label)
        csv_row.addWidget(self.csv_file_entry)
        csv_row.addWidget(csv_browse_btn)
        input_layout.addLayout(csv_row)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # ===== Parameters Section =====
        params_group = self.create_group_box("Analysis Parameters")
        params_layout = QVBoxLayout()

        # Wavelength
        wavelength_row = QHBoxLayout()
        wavelength_label = QLabel("X-ray Wavelength (Å):")
        wavelength_label.setFixedWidth(200)
        wavelength_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.wavelength_spinbox = QDoubleSpinBox()
        self.wavelength_spinbox.setRange(0.1, 10.0)
        self.wavelength_spinbox.setValue(self.wavelength)
        self.wavelength_spinbox.setDecimals(4)
        self.wavelength_spinbox.setSingleStep(0.001)
        self.wavelength_spinbox.setStyleSheet(self.get_spinbox_style())
        self.wavelength_spinbox.valueChanged.connect(
            lambda v: setattr(self, 'wavelength', v)
        )
        wavelength_row.addWidget(wavelength_label)
        wavelength_row.addWidget(self.wavelength_spinbox)
        wavelength_row.addStretch()
        params_layout.addLayout(wavelength_row)

        # N pressure points
        n_points_row = QHBoxLayout()
        n_points_label = QLabel("Min Pressure Points for Stability:")
        n_points_label.setFixedWidth(200)
        n_points_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.n_points_spinbox = QSpinBox()
        self.n_points_spinbox.setRange(1, 100)
        self.n_points_spinbox.setValue(self.n_pressure_points)
        self.n_points_spinbox.setStyleSheet(self.get_spinbox_style())
        self.n_points_spinbox.valueChanged.connect(
            lambda v: setattr(self, 'n_pressure_points', v)
        )
        n_points_row.addWidget(n_points_label)
        n_points_row.addWidget(self.n_points_spinbox)
        n_points_row.addStretch()
        params_layout.addLayout(n_points_row)

        # Peak tolerances section
        tolerances_label = QLabel("Peak Tolerances (degrees):")
        tolerances_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        tolerances_label.setStyleSheet(f"color: {self.colors['text_dark']}; margin-top: 10px;")
        params_layout.addWidget(tolerances_label)

        # Tolerance 1
        tol1_row = QHBoxLayout()
        tol1_label = QLabel("  Phase Transition Detection:")
        tol1_label.setFixedWidth(200)
        tol1_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.tolerance1_spinbox = QDoubleSpinBox()
        self.tolerance1_spinbox.setRange(0.01, 5.0)
        self.tolerance1_spinbox.setValue(self.peak_tolerance_1)
        self.tolerance1_spinbox.setDecimals(2)
        self.tolerance1_spinbox.setSingleStep(0.1)
        self.tolerance1_spinbox.setStyleSheet(self.get_spinbox_style())
        tol1_row.addWidget(tol1_label)
        tol1_row.addWidget(self.tolerance1_spinbox)
        tol1_row.addStretch()
        params_layout.addLayout(tol1_row)

        # Tolerance 2
        tol2_row = QHBoxLayout()
        tol2_label = QLabel("  Peak Tracking:")
        tol2_label.setFixedWidth(200)
        tol2_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.tolerance2_spinbox = QDoubleSpinBox()
        self.tolerance2_spinbox.setRange(0.01, 5.0)
        self.tolerance2_spinbox.setValue(self.peak_tolerance_2)
        self.tolerance2_spinbox.setDecimals(2)
        self.tolerance2_spinbox.setSingleStep(0.1)
        self.tolerance2_spinbox.setStyleSheet(self.get_spinbox_style())
        tol2_row.addWidget(tol2_label)
        tol2_row.addWidget(self.tolerance2_spinbox)
        tol2_row.addStretch()
        params_layout.addLayout(tol2_row)

        # Tolerance 3
        tol3_row = QHBoxLayout()
        tol3_label = QLabel("  Peak Exclusion:")
        tol3_label.setFixedWidth(200)
        tol3_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.tolerance3_spinbox = QDoubleSpinBox()
        self.tolerance3_spinbox.setRange(0.001, 1.0)
        self.tolerance3_spinbox.setValue(self.peak_tolerance_3)
        self.tolerance3_spinbox.setDecimals(3)
        self.tolerance3_spinbox.setSingleStep(0.01)
        self.tolerance3_spinbox.setStyleSheet(self.get_spinbox_style())
        tol3_row.addWidget(tol3_label)
        tol3_row.addWidget(self.tolerance3_spinbox)
        tol3_row.addStretch()
        params_layout.addLayout(tol3_row)

        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)

        # ===== Crystal System Selection =====
        crystal_group = self.create_group_box("Crystal System Selection")
        crystal_layout = QVBoxLayout()

        # Original peaks crystal system
        original_label = QLabel("Original Phase Crystal System:")
        original_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        original_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        crystal_layout.addWidget(original_label)

        self.original_system_combo = QComboBox()
        self.original_system_combo.addItems(list(self.CRYSTAL_SYSTEM_MAP.keys()))
        self.original_system_combo.setStyleSheet(self.get_combo_style())
        self.original_system_combo.currentTextChanged.connect(
            lambda text: setattr(self, 'original_crystal_system', 
                               self.CRYSTAL_SYSTEM_MAP[text])
        )
        crystal_layout.addWidget(self.original_system_combo)

        # New peaks crystal system
        new_label = QLabel("New Phase Crystal System:")
        new_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        new_label.setStyleSheet(f"color: {self.colors['text_dark']}; margin-top: 10px;")
        crystal_layout.addWidget(new_label)

        self.new_system_combo = QComboBox()
        self.new_system_combo.addItems(list(self.CRYSTAL_SYSTEM_MAP.keys()))
        self.new_system_combo.setStyleSheet(self.get_combo_style())
        self.new_system_combo.currentTextChanged.connect(
            lambda text: setattr(self, 'new_crystal_system',
                               self.CRYSTAL_SYSTEM_MAP[text])
        )
        crystal_layout.addWidget(self.new_system_combo)

        crystal_group.setLayout(crystal_layout)
        main_layout.addWidget(crystal_group)

        # ===== Action Buttons =====
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.run_analysis_btn = ModernButton("🚀 Run Analysis", self.run_analysis)
        self.run_analysis_btn.setFixedHeight(50)
        button_layout.addWidget(self.run_analysis_btn)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # ===== Progress Section =====
        progress_group = self.create_group_box("Progress")
        progress_layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = CuteSheepProgressBar(width=600, height=60)
        progress_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colors['bg']};
                color: {self.colors['text_dark']};
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }}
        """)
        self.log_text.setMinimumHeight(200)
        progress_layout.addWidget(self.log_text)

        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        main_layout.addStretch()

    def browse_csv_file(self):
        """Browse for CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Peak Data CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.csv_file_path = file_path
            self.csv_file_entry.setText(file_path)
            self.log_message(f"Selected CSV file: {file_path}")

    def log_message(self, message):
        """Add message to log"""
        self.log_text.append(message)
        # Scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def run_analysis(self):
        """Run the X-ray diffraction analysis"""
        # Validate inputs
        if not self.csv_file_path:
            QMessageBox.warning(
                self.parent,
                "Missing Input",
                "Please select a CSV file containing peak data."
            )
            return

        if not os.path.exists(self.csv_file_path):
            QMessageBox.warning(
                self.parent,
                "File Not Found",
                f"The selected CSV file does not exist:\n{self.csv_file_path}"
            )
            return

        # Update tolerances from spinboxes
        self.peak_tolerance_1 = self.tolerance1_spinbox.value()
        self.peak_tolerance_2 = self.tolerance2_spinbox.value()
        self.peak_tolerance_3 = self.tolerance3_spinbox.value()

        # Clear log
        self.log_text.clear()
        self.log_message("="*60)
        self.log_message("X-RAY DIFFRACTION ANALYSIS")
        self.log_message("="*60)
        self.log_message(f"CSV File: {self.csv_file_path}")
        self.log_message(f"Wavelength: {self.wavelength} Å")
        self.log_message(f"Min Pressure Points: {self.n_pressure_points}")
        self.log_message(f"Original System: {self.original_crystal_system}")
        self.log_message(f"New System: {self.new_crystal_system}")
        self.log_message("="*60)
        self.log_message("")

        # Disable run button
        self.run_analysis_btn.setEnabled(False)

        # Start progress animation
        self.progress_bar.start()

        # Create analyzer with current parameters
        self.analyzer = XRayDiffractionAnalyzer(
            wavelength=self.wavelength,
            n_pressure_points=self.n_pressure_points
        )
        
        # Update tolerances
        self.analyzer.peak_tolerance_1 = self.peak_tolerance_1
        self.analyzer.peak_tolerance_2 = self.peak_tolerance_2
        self.analyzer.peak_tolerance_3 = self.peak_tolerance_3

        # Create and start worker thread
        self.worker_thread = AnalysisWorkerThread(
            self.analyzer,
            self.csv_file_path,
            self.original_crystal_system,
            self.new_crystal_system,
            auto_mode=True
        )

        # Connect signals
        self.worker_thread.progress.connect(self.log_message)
        self.worker_thread.finished.connect(self.on_analysis_finished)
        self.worker_thread.error.connect(self.on_analysis_error)

        # Start thread
        self.running_threads.append(self.worker_thread)
        self.worker_thread.start()

    def on_analysis_finished(self, message):
        """Handle analysis completion"""
        self.log_message("")
        self.log_message("="*60)
        self.log_message(message)
        self.log_message("="*60)
        
        # Show results summary
        if self.analyzer:
            if self.analyzer.transition_pressure:
                self.log_message(f"\nPhase transition detected at: {self.analyzer.transition_pressure:.2f} GPa")
            else:
                self.log_message("\nNo phase transition detected")
            
            # Show output files
            base_filename = self.csv_file_path.replace('.csv', '')
            self.log_message("\nOutput files:")
            if self.analyzer.transition_pressure:
                self.log_message(f"  - {base_filename}_new_peaks_dataset.csv")
                self.log_message(f"  - {base_filename}_original_peaks_dataset.csv")
                self.log_message(f"  - {base_filename}_original_peaks_lattice.csv")
                self.log_message(f"  - {base_filename}_new_peaks_lattice.csv")
            else:
                self.log_message(f"  - {base_filename}_lattice_results.csv")

        # Stop progress animation
        self.progress_bar.stop()
        
        # Re-enable run button
        self.run_analysis_btn.setEnabled(True)

        # Show completion message
        QMessageBox.information(
            self.parent,
            "Analysis Complete",
            "X-ray diffraction analysis completed successfully!\nCheck the log for details and output file locations."
        )

    def on_analysis_error(self, error_message):
        """Handle analysis error"""
        self.log_message("")
        self.log_message("="*60)
        self.log_message("ERROR")
        self.log_message("="*60)
        self.log_message(error_message)
        
        # Stop progress animation
        self.progress_bar.stop()
        
        # Re-enable run button
        self.run_analysis_btn.setEnabled(True)

        # Show error message
        QMessageBox.critical(
            self.parent,
            "Analysis Error",
            f"An error occurred during analysis:\n\n{error_message}"
        )

    def get_input_style(self):
        """Get style for input fields"""
        return f"""
            QLineEdit {{
                padding: 8px;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                background-color: white;
                color: {self.colors['text_dark']};
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.colors['primary']};
            }}
        """

    def get_spinbox_style(self):
        """Get style for spinboxes"""
        return f"""
            QSpinBox, QDoubleSpinBox {{
                padding: 5px;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                background-color: white;
                color: {self.colors['text_dark']};
                min-width: 150px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {self.colors['primary']};
            }}
        """

    def get_combo_style(self):
        """Get style for combo boxes"""
        return f"""
            QComboBox {{
                padding: 8px;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                background-color: white;
                color: {self.colors['text_dark']};
                font-size: 10pt;
            }}
            QComboBox:focus {{
                border: 2px solid {self.colors['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.colors['text_dark']};
                margin-right: 10px;
            }}
        """

    @staticmethod
    def clear_layout(layout):
        """Clear all widgets from a layout"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                BCDICalModule.clear_layout(item.layout())