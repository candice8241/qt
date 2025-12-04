# -*- coding: utf-8 -*-
"""
Lattice Parameters Module
Extracted from powder_module.py for standalone use

Provides lattice parameter calculation functionality with crystal system selection
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QFileDialog, QMessageBox, QFrame,
                              QRadioButton, QButtonGroup, QSizePolicy)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QFont
import threading
import os
from gui_base import GUIBase
from theme_module import ModernButton, CuteSheepProgressBar


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


class LatticeParamsModule(QWidget, GUIBase):
    """Lattice Parameters Calculation Module"""
    
    def __init__(self, parent=None):
        """Initialize the Lattice Parameters module"""
        QWidget.__init__(self, parent)
        GUIBase.__init__(self)
        
        # Initialize variables
        self.phase_peak_csv = ""
        self.phase_volume_output = ""
        self.phase_volume_system = 'FCC'
        self.phase_wavelength = 0.4133
        self.phase_n_points = 4
        
        # Track running threads
        self.running_threads = []
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(3, 0, 8, 5)
        main_layout.setSpacing(0)
        
        # Create content container
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #FAFAFA;
                border-radius: 5px;
            }
        """)
        
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(container)
        
        # Inner layout
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(20, 10, 20, 10)
        inner_layout.setSpacing(4)
        
        # Create the lattice parameters card
        self.setup_lattice_params_card(inner_layout)
        
        # Add console at the bottom
        self.setup_console(inner_layout)
        
        # Create progress bar
        self.progress = CuteSheepProgressBar(width=400, height=60, parent=self)
        self.progress.hide()
        inner_layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def setup_lattice_params_card(self, parent_layout):
        """Setup lattice parameters calculation card"""
        card = self.create_card_frame(None)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        card_layout.setSpacing(12)
        
        # Header
        header = QLabel("📊 Lattice Parameters Calculation")
        header.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        card_layout.addWidget(header)
        
        # Columns layout
        columns = QHBoxLayout()
        columns.setSpacing(16)
        
        # Left column: file inputs
        left_panel = QWidget()
        left_panel.setMinimumWidth(550)
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
        
        # Add Calculate Lattice Parameters button
        btn_row = QWidget()
        btn_row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.setSpacing(12)
        
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
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        right_panel.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 4, 0, 4)
        right_layout.setSpacing(10)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        
        # Create combined frame for crystal system and wavelength
        combined_frame = QFrame()
        combined_frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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
        
        # Crystal System title
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
            ('Trigonal', 'Trigonal'),
            ('HCP', 'HCP'),
            ('Tetragonal', 'Tetragonal'),
            ('Orthorhombic', 'Orthorhombic'),
            ('Monoclinic', 'Monoclinic'),
            ('Triclinic', 'Triclinic'),
        ]
        
        self.phase_system_group = QButtonGroup(combined_frame)
        
        # Helper function to create proper closure for each radio button
        def make_radio_handler(system_value):
            def handler(checked):
                if checked:
                    self.phase_volume_system = system_value
                    print(f"✓ Crystal system selected: {system_value}")
            return handler
        
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
            radio.toggled.connect(make_radio_handler(value))
            self.phase_system_group.addButton(radio)
            if idx < 4:
                row1_layout.addWidget(radio)
            else:
                row2_layout.addWidget(radio)
        
        row1_layout.addStretch()
        row2_layout.addStretch()
        combined_frame_layout.addWidget(row1)
        combined_frame_layout.addWidget(row2)
        
        # Wavelength section
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
        
        # Add frame to right layout
        right_layout.addWidget(combined_frame)
        right_layout.addStretch()
        
        # Add columns to card
        columns.addWidget(left_panel, stretch=1)
        columns.addWidget(right_panel, stretch=1)
        card_layout.addLayout(columns)
        
        parent_layout.addWidget(card)
    
    def setup_console(self, parent_layout):
        """Setup console/log output area"""
        console_label = QLabel("📋 Console Output")
        console_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        console_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: transparent;")
        parent_layout.addWidget(console_label)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(150)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #2B2B2B;
                color: #CCCCCC;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        parent_layout.addWidget(self.console)
    
    def create_file_input(self, parent_layout, label_text, var_name):
        """Create a file input row with browse button"""
        row = QWidget()
        row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label = QLabel(label_text)
        label.setFixedWidth(240)
        label.setFont(QFont('Arial', 9))
        label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        layout.addWidget(label)
        
        entry = QLineEdit()
        entry.setFont(QFont('Arial', 9))
        entry.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #BBBBBB;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        entry.textChanged.connect(lambda text: setattr(self, var_name, text))
        layout.addWidget(entry)
        
        # Store reference to entry widget
        setattr(self, f"{var_name}_entry", entry)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(70)
        browse_btn.setFont(QFont('Arial', 9))
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 4px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['primary']};
            }}
        """)
        browse_btn.clicked.connect(lambda: self.browse_file(var_name))
        layout.addWidget(browse_btn)
        
        parent_layout.addWidget(row)
    
    def create_folder_input(self, parent_layout, label_text, var_name):
        """Create a folder input row with browse button"""
        row = QWidget()
        row.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label = QLabel(label_text)
        label.setFixedWidth(240)
        label.setFont(QFont('Arial', 9))
        label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        layout.addWidget(label)
        
        entry = QLineEdit()
        entry.setFont(QFont('Arial', 9))
        entry.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #BBBBBB;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        entry.textChanged.connect(lambda text: setattr(self, var_name, text))
        layout.addWidget(entry)
        
        # Store reference to entry widget
        setattr(self, f"{var_name}_entry", entry)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(70)
        browse_btn.setFont(QFont('Arial', 9))
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 4px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['primary']};
            }}
        """)
        browse_btn.clicked.connect(lambda: self.browse_folder(var_name))
        layout.addWidget(browse_btn)
        
        parent_layout.addWidget(row)
    
    def browse_file(self, var_name):
        """Browse for a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            setattr(self, var_name, file_path)
            entry = getattr(self, f"{var_name}_entry", None)
            if entry:
                entry.setText(file_path)
            self.log(f"Selected file: {file_path}")
    
    def browse_folder(self, var_name):
        """Browse for a folder"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            ""
        )
        if folder_path:
            setattr(self, var_name, folder_path)
            entry = getattr(self, f"{var_name}_entry", None)
            if entry:
                entry.setText(folder_path)
            self.log(f"Selected folder: {folder_path}")
    
    def _on_phase_wavelength_changed(self, text):
        """Handle wavelength change"""
        try:
            self.phase_wavelength = float(text)
        except ValueError:
            self.phase_wavelength = 0.0
    
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
            self.log("Starting Lattice Parameters Calculation...")
            self.log(f"Peak CSV: {self.phase_peak_csv}")
            self.log(f"Wavelength: {self.phase_wavelength} Å")
            self.log(f"Crystal System: {self.phase_volume_system}")
            self.log(f"N Points: {self.phase_n_points}")
            self.log(f"Output: {self.phase_volume_output}")
            
            # Start progress animation
            self.progress.show()
            self.progress.start()
            
            # Import and run phase analysis
            from batch_cal_volume import XRayDiffractionAnalyzer
            
            # Create worker thread
            def run_task():
                analyzer = XRayDiffractionAnalyzer(
                    wavelength=self.phase_wavelength,
                    n_pressure_points=self.phase_n_points
                )
                
                # Map crystal system names
                system_map = {
                    'FCC': 'cubic_FCC',
                    'BCC': 'cubic_BCC',
                    'Trigonal': 'Trigonal',
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
            self.progress.hide()
            self.log(f"❌ Error: {str(e)}")
            self.show_error("Error", f"Failed to start lattice parameter calculation:\n{str(e)}")
    
    def _on_phase_analysis_finished(self, message):
        """Handle phase analysis completion"""
        self.progress.stop()
        self.progress.hide()
        self.log("✓ Lattice parameter calculation completed successfully!")
        self.log("="*60)
        self.show_success("Success", "Lattice parameter calculation completed!")
    
    def _on_phase_analysis_error(self, error_msg):
        """Handle phase analysis error"""
        self.progress.stop()
        self.progress.hide()
        self.log(f"❌ Error: {error_msg}")
        self.log("="*60)
        self.show_error("Error", f"Lattice parameter calculation failed:\n{error_msg}")
    
    def log(self, message):
        """Log a message to console"""
        self.console.append(message)
        # Auto-scroll to bottom
        cursor = self.console.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.console.setTextCursor(cursor)
    
    def show_error(self, title, message):
        """Show error message box"""
        QMessageBox.critical(self, title, message)
    
    def show_success(self, title, message):
        """Show success message box"""
        QMessageBox.information(self, title, message)


if __name__ == "__main__":
    """Test the module standalone"""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = LatticeParamsModule()
    window.setWindowTitle("Lattice Parameters Calculation")
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec())
