#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interactive EoS Fitting GUI with Real-time Parameter Adjustment

Similar to EosFit7-GUI, allows manual parameter adjustment with live preview.

@author: candicewang928@gmail.com
Created: 2025-11-24
"""

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QLineEdit, QComboBox, QCheckBox, QTextEdit, QSlider,
                              QFileDialog, QMessageBox, QFrame, QGroupBox, QSplitter,
                              QDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QDoubleValidator
from crysfml_eos_module import CrysFMLEoS, EoSType, EoSParameters


class InteractiveEoSGUI(QWidget):
    """
    Interactive GUI for EoS fitting with real-time parameter adjustment

    Features:
    - Manual parameter input (V0, B0, B0')
    - Parameter lock/unlock (fix or fit)
    - Real-time curve update
    - Automatic fitting
    - Quality metrics display
    - Data loading from CSV
    """

    def __init__(self, parent=None):
        """Initialize the GUI"""
        super().__init__(parent)
        
        # Hide during construction to prevent flash
        self.setVisible(False)
        
        self.setWindowTitle("Interactive EoS Fitting - CrysFML Method")
        self.resize(1480, 900)

        # Palette for a calmer, consistent layout
        self.palette = {
            'background': '#f4f6fb',
            'panel_bg': '#ffffff',
            'section_header': '#dfe4ef',
            'accent': '#3f51b5',
            'text_primary': '#1f2933',
            'muted': '#5f6c7b',
        }

        self.setStyleSheet(f"background-color: {self.palette['background']};")

        # Data storage
        self.V_data = None
        self.P_data = None
        self.current_params = None
        self.fitted_params = None

        # EoS fitter
        self.eos_type = EoSType.BIRCH_MURNAGHAN_3RD
        self.fitter = None
        self.last_initial_params = None

        # Results window state
        self.results_window = None
        self.results_window_text = None
        self.last_results_output = ""

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Main splitter with left/right split
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Controls
        left_panel = QWidget()
        left_panel.setFixedWidth(400)
        left_panel.setStyleSheet(f"background-color: {self.palette['panel_bg']}; border: 1px solid #ccc;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)

        # Right panel splitter - Plot and Results with adjustable height
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        plot_container = QWidget()
        plot_container.setStyleSheet(f"background-color: {self.palette['background']};")

        results_container = QWidget()
        results_container.setStyleSheet(f"background-color: {self.palette['background']};")

        right_splitter.addWidget(plot_container)
        right_splitter.addWidget(results_container)
        right_splitter.setSizes([600, 300])

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([400, 1080])

        main_layout.addWidget(main_splitter)

        # Setup left panel sections
        self.setup_data_section(left_layout)
        self.setup_eos_selection(left_layout)
        self.setup_parameters_section(left_layout)
        self.setup_fitting_section(left_layout)
        left_layout.addStretch()

        # Setup right panel
        self.setup_plot(plot_container)
        self.setup_results_section(results_container)

    def setup_data_section(self, parent_layout):
        """Setup data loading section"""
        frame = QGroupBox("Data")
        frame.setStyleSheet(f"""
            QGroupBox {{
                background-color: {self.palette['panel_bg']};
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: none;
                margin-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)

        # Load button
        load_btn = QPushButton("Load CSV File")
        load_btn.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        load_btn.setFixedHeight(40)
        load_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.palette['accent']};
                color: white;
                border: none;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #303f9f;
            }}
        """)
        load_btn.clicked.connect(self.load_csv)
        layout.addWidget(load_btn)

        # Data info label
        self.data_info_label = QLabel("No data loaded")
        self.data_info_label.setFont(QFont('Arial', 9))
        self.data_info_label.setStyleSheet(f"color: {self.palette['muted']}; background: transparent;")
        self.data_info_label.setWordWrap(True)
        layout.addWidget(self.data_info_label)

        parent_layout.addWidget(frame)

    def setup_eos_selection(self, parent_layout):
        """Setup EoS model selection"""
        frame = QGroupBox("EoS Model")
        frame.setStyleSheet(f"""
            QGroupBox {{
                background-color: {self.palette['panel_bg']};
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: none;
                margin-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(6)

        label = QLabel("Model:")
        label.setStyleSheet(f"color: {self.palette['text_primary']}; font-weight: bold; background: transparent;")
        layout.addWidget(label)

        self.eos_combo = QComboBox()
        self.eos_combo.addItems([
            "Birch-Murnaghan 2nd",
            "Birch-Murnaghan 3rd",
            "Birch-Murnaghan 4th",
            "Murnaghan",
            "Vinet",
            "Natural Strain"
        ])
        self.eos_combo.setCurrentText("Birch-Murnaghan 3rd")
        self.eos_combo.setFont(QFont('Arial', 9))
        self.eos_combo.currentTextChanged.connect(self.on_eos_changed)
        layout.addWidget(self.eos_combo)

        parent_layout.addWidget(frame)

    def setup_parameters_section(self, parent_layout):
        """Setup parameters input section"""
        frame = QGroupBox("EoS Parameters")
        frame.setStyleSheet(f"""
            QGroupBox {{
                background-color: {self.palette['panel_bg']};
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: none;
                margin-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(6)

        # Create parameter entries
        self.param_entries = {}
        self.param_locks = {}

        params = [
            ('V0', 'V₀ (Å³/atom)', 11.5),
            ('B0', 'B₀ (GPa)', 130.0),
            ('B0_prime', "B₀'", 4.0),
        ]

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        param_header = QLabel("Parameter")
        param_header.setFont(QFont('Arial', 8, QFont.Weight.Bold))
        param_header.setStyleSheet(f"color: {self.palette['muted']}; background: transparent;")
        value_header = QLabel("Value")
        value_header.setFont(QFont('Arial', 8, QFont.Weight.Bold))
        value_header.setStyleSheet(f"color: {self.palette['muted']}; background: transparent;")
        lock_header = QLabel("Lock")
        lock_header.setFont(QFont('Arial', 8, QFont.Weight.Bold))
        lock_header.setStyleSheet(f"color: {self.palette['muted']}; background: transparent;")
        header_layout.addWidget(param_header)
        header_layout.addWidget(value_header)
        header_layout.addWidget(lock_header)
        layout.addLayout(header_layout)

        for key, label, default in params:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)

            # Parameter label
            lbl = QLabel(label)
            lbl.setFont(QFont('Arial', 9))
            lbl.setStyleSheet(f"color: {self.palette['text_primary']}; background: transparent;")
            lbl.setFixedWidth(105)
            row_layout.addWidget(lbl)

            # Value entry
            entry = QLineEdit()
            entry.setText(str(default))
            entry.setFont(QFont('Arial', 9))
            entry.setValidator(QDoubleValidator())
            entry.setFixedWidth(110)
            entry.setStyleSheet("""
                QLineEdit {
                    padding: 4px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                }
                QLineEdit:focus {
                    border: 1px solid #3f51b5;
                }
            """)
            entry.returnPressed.connect(self.update_manual_fit)
            entry.editingFinished.connect(self.update_manual_fit)
            self.param_entries[key] = entry
            row_layout.addWidget(entry)

            # Lock checkbox
            lock_cb = QCheckBox()
            lock_cb.setStyleSheet("QCheckBox { margin-left: 8px; }")
            self.param_locks[key] = lock_cb
            row_layout.addWidget(lock_cb)

            row_layout.addStretch()
            layout.addLayout(row_layout)

        # Add spacing before button
        layout.addSpacing(8)
        
        # Update button
        update_btn = QPushButton("Update Plot")
        update_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        update_btn.setFixedHeight(32)
        update_btn.setStyleSheet("""
            QPushButton {
                background-color: #e6ecfb;
                border: none;
                border-radius: 3px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #d4ddf5;
            }
        """)
        update_btn.clicked.connect(self.update_manual_fit)
        layout.addWidget(update_btn)

        parent_layout.addWidget(frame)

    def setup_fitting_section(self, parent_layout):
        """Setup fitting control section"""
        frame = QGroupBox("Fitting Control")
        frame.setStyleSheet(f"""
            QGroupBox {{
                background-color: {self.palette['panel_bg']};
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: none;
                margin-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)

        # Regularization strength control
        reg_label = QLabel("B0' Regularization:")
        reg_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        reg_label.setStyleSheet(f"color: {self.palette['text_primary']}; background: transparent;")
        layout.addWidget(reg_label)

        slider_layout = QHBoxLayout()
        self.reg_slider = QSlider(Qt.Orientation.Horizontal)
        self.reg_slider.setMinimum(1)
        self.reg_slider.setMaximum(100)
        self.reg_slider.setValue(10)  # 1.0 * 10
        self.reg_slider.valueChanged.connect(self.update_reg_label)
        slider_layout.addWidget(self.reg_slider)

        self.reg_label = QLabel("1.0")
        self.reg_label.setFixedWidth(40)
        self.reg_label.setStyleSheet(f"color: {self.palette['text_primary']}; background: transparent;")
        slider_layout.addWidget(self.reg_label)

        layout.addLayout(slider_layout)

        hint_label = QLabel("(Higher = stronger constraint to B0'=4)")
        hint_label.setFont(QFont('Arial', 8))
        hint_label.setStyleSheet(f"color: {self.palette['muted']}; font-style: italic; background: transparent;")
        layout.addWidget(hint_label)

        # Fitting buttons
        btn_style = """
            QPushButton {
                background-color: #dbe3f9;
                color: #1f2933;
                border: none;
                border-radius: 3px;
                padding: 6px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #e1e7f5;
            }
        """

        layout.addSpacing(4)
        
        fit_btn = QPushButton("Fit Unlocked Parameters")
        fit_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        fit_btn.setStyleSheet(btn_style)
        fit_btn.clicked.connect(self.fit_unlocked)
        layout.addWidget(fit_btn)

        multi_btn = QPushButton("Try Multiple Strategies")
        multi_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        multi_btn.setStyleSheet(btn_style.replace('#dbe3f9', '#e9eefc'))
        multi_btn.clicked.connect(self.fit_multiple_strategies)
        layout.addWidget(multi_btn)

        reset_btn = QPushButton("Reset to Initial Guess")
        reset_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        reset_btn.setStyleSheet(btn_style.replace('#dbe3f9', '#f1f4fb'))
        reset_btn.clicked.connect(self.reset_parameters)
        layout.addWidget(reset_btn)

        parent_layout.addWidget(frame)

    def update_reg_label(self):
        """Update regularization label"""
        value = self.reg_slider.value() / 10.0
        self.reg_label.setText(f"{value:.1f}")

    def setup_plot(self, parent):
        """Setup matplotlib plot"""
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 4, 8)

        # Create figure
        self.fig = Figure(figsize=(10, 6), dpi=100, facecolor='white')
        self.ax_main = self.fig.add_subplot(111)

        # Canvas
        self.canvas = FigureCanvasQTAgg(self.fig)
        layout.addWidget(self.canvas)

        # Toolbar
        toolbar = NavigationToolbar2QT(self.canvas, parent)
        layout.addWidget(toolbar)

        self.fig.tight_layout()

    def setup_results_section(self, parent):
        """Setup results display section"""
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 4, 0)

        frame = QGroupBox("Fitting Results")
        frame.setStyleSheet(f"""
            QGroupBox {{
                background-color: {self.palette['panel_bg']};
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: 1px solid #ccc;
                margin-top: 6px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px 0 4px;
            }}
        """)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)

        hint = QLabel("The preview matches the floating information window.")
        hint.setFont(QFont('Arial', 9))
        hint.setStyleSheet(f"color: {self.palette['muted']}; font-style: italic; background: transparent;")
        frame_layout.addWidget(hint)

        open_btn = QPushButton("Open Fitting Information Window")
        open_btn.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #e6ecfb;
                border: none;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #d4ddf5;
            }
        """)
        open_btn.clicked.connect(self.open_results_window)
        frame_layout.addWidget(open_btn)

        self.preview_text = QTextEdit()
        self.preview_text.setFont(QFont('Courier New', 9))
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: #f9fbff;
                color: {self.palette['text_primary']};
                border: 1px solid #e0e6f5;
            }}
        """)
        frame_layout.addWidget(self.preview_text)

        layout.addWidget(frame)
        self.update_results_display()

    def load_csv(self):
        """Load data from CSV file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV file",
            "",
            "CSV files (*.csv);;All files (*.*)"
        )

        if not filename:
            return

        try:
            df = pd.read_csv(filename)

            # Check required columns
            if 'V_atomic' not in df.columns or 'Pressure (GPa)' not in df.columns:
                QMessageBox.critical(self, "Error",
                    "CSV must contain 'V_atomic' and 'Pressure (GPa)' columns")
                return

            self.V_data = df['V_atomic'].dropna().values
            self.P_data = df['Pressure (GPa)'].dropna().values

            # Ensure same length
            min_len = min(len(self.V_data), len(self.P_data))
            self.V_data = self.V_data[:min_len]
            self.P_data = self.P_data[:min_len]

            # Update GUI components
            self.update_data_info()
            self.reset_parameters()
            self.update_plot()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV:\n{str(e)}")

    def update_data_info(self):
        """Update data information display"""
        if self.V_data is None or self.P_data is None:
            self.data_info_label.setText("No data loaded")
            return

        info = f"Data points: {len(self.V_data)}\n"
        info += f"V: {self.V_data.min():.3f} - {self.V_data.max():.3f} Å³\n"
        info += f"P: {self.P_data.min():.2f} - {self.P_data.max():.2f} GPa"
        self.data_info_label.setText(info)

    def on_eos_changed(self):
        """Handle EoS model change"""
        eos_map = {
            "Birch-Murnaghan 2nd": EoSType.BIRCH_MURNAGHAN_2ND,
            "Birch-Murnaghan 3rd": EoSType.BIRCH_MURNAGHAN_3RD,
            "Birch-Murnaghan 4th": EoSType.BIRCH_MURNAGHAN_4TH,
            "Murnaghan": EoSType.MURNAGHAN,
            "Vinet": EoSType.VINET,
            "Natural Strain": EoSType.NATURAL_STRAIN
        }

        self.eos_type = eos_map.get(self.eos_combo.currentText(), EoSType.BIRCH_MURNAGHAN_3RD)
        reg_strength = self.reg_slider.value() / 10.0
        self.fitter = CrysFMLEoS(eos_type=self.eos_type, regularization_strength=reg_strength)

        if self.V_data is not None and self.P_data is not None:
            self.update_manual_fit()

    def reset_parameters(self):
        """Reset parameters to smart initial guess"""
        if self.V_data is None or self.P_data is None:
            return

        reg_strength = self.reg_slider.value() / 10.0
        self.fitter = CrysFMLEoS(eos_type=self.eos_type, regularization_strength=reg_strength)

        # Get smart initial guess
        if hasattr(self.fitter, '_smart_initial_guess'):
            V0_guess, B0_guess, B0_prime_guess = self.fitter._smart_initial_guess(
                self.V_data, self.P_data
            )
        else:
            V0_guess = self.V_data.max() * 1.05
            B0_guess = 130.0
            B0_prime_guess = 4.0

        self.param_entries['V0'].setText(f"{V0_guess:.4f}")
        self.param_entries['B0'].setText(f"{B0_guess:.2f}")
        self.param_entries['B0_prime'].setText(f"{B0_prime_guess:.3f}")

        self.update_manual_fit()

    def get_current_params(self):
        """Get current parameter values from GUI"""
        params = EoSParameters(eos_type=self.eos_type)
        params.V0 = float(self.param_entries['V0'].text())
        params.B0 = float(self.param_entries['B0'].text())
        params.B0_prime = float(self.param_entries['B0_prime'].text())
        return params

    def update_manual_fit(self):
        """Update plot with current manual parameters"""
        if self.V_data is None or self.P_data is None:
            return

        reg_strength = self.reg_slider.value() / 10.0
        if self.fitter is None or self.fitter.eos_type != self.eos_type:
            self.fitter = CrysFMLEoS(eos_type=self.eos_type, regularization_strength=reg_strength)

        try:
            params = self.get_current_params()
            P_fit = self.fitter.calculate_pressure(self.V_data, params)

            residuals = self.P_data - P_fit
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((self.P_data - np.mean(self.P_data))**2)
            params.R_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            params.RMSE = np.sqrt(np.mean(residuals**2))

            self.current_params = params
            self.update_plot()
        except Exception as e:
            print(f"Error calculating pressure: {e}")

    def fit_unlocked(self):
        """Fit only unlocked parameters"""
        if self.V_data is None or self.P_data is None:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        V0_locked = self.param_locks['V0'].isChecked()
        B0_locked = self.param_locks['B0'].isChecked()
        B0_prime_locked = self.param_locks['B0_prime'].isChecked()

        if V0_locked and B0_locked and B0_prime_locked:
            QMessageBox.warning(self, "Warning", "All parameters are locked!")
            return

        reg_strength = self.reg_slider.value() / 10.0
        self.fitter = CrysFMLEoS(eos_type=self.eos_type, regularization_strength=reg_strength)

        try:
            self.last_initial_params = self.get_current_params()
            lock_flags = {
                'V0': V0_locked,
                'B0': B0_locked,
                'B0_prime': B0_prime_locked,
            }

            params = self.fitter.fit(
                self.V_data,
                self.P_data,
                use_smart_guess=True,
                initial_params=self.get_current_params(),
                lock_flags=lock_flags,
            )

            if params is not None:
                if not V0_locked:
                    self.param_entries['V0'].setText(f"{params.V0:.4f}")
                if not B0_locked:
                    self.param_entries['B0'].setText(f"{params.B0:.2f}")
                if not B0_prime_locked:
                    self.param_entries['B0_prime'].setText(f"{params.B0_prime:.3f}")

                self.fitted_params = params
                self.current_params = params
                self.update_plot()
            else:
                self.update_manual_fit()

        except Exception as e:
            print(f"Fit unlocked error: {e}")
            self.update_manual_fit()

    def fit_multiple_strategies(self):
        """Try fitting with multiple strategies"""
        if self.V_data is None or self.P_data is None:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        reg_strength = self.reg_slider.value() / 10.0
        self.fitter = CrysFMLEoS(eos_type=self.eos_type, regularization_strength=reg_strength)

        try:
            self.last_initial_params = self.get_current_params()
            print("\n" + "="*60)
            print("Trying multiple fitting strategies...")
            print("="*60)

            params = self.fitter.fit_with_multiple_strategies(
                self.V_data, self.P_data, verbose=True
            )

            if params is not None:
                self.param_entries['V0'].setText(f"{params.V0:.4f}")
                self.param_entries['B0'].setText(f"{params.B0:.2f}")
                self.param_entries['B0_prime'].setText(f"{params.B0_prime:.3f}")

                self.fitted_params = params
                self.current_params = params
                self.update_plot()

                print("="*60)
                print("Best fit found!")
                print("="*60 + "\n")
            else:
                print("="*60)
                print("All strategies failed - using current manual values")
                print("="*60 + "\n")
                self.update_manual_fit()

        except Exception as e:
            print(f"Error in multiple strategies: {e}")
            self.update_manual_fit()

    def update_plot(self):
        """Update the plot with current data and fit"""
        if self.V_data is None or self.P_data is None:
            return

        self.ax_main.clear()

        # Plot data points
        self.ax_main.scatter(self.V_data, self.P_data, s=60, c='#2196F3',
                           marker='o', label='Experimental Data',
                           alpha=0.8, edgecolors='#0D47A1', linewidths=1.5, zorder=5)

        # Plot fit if available
        if self.current_params is not None:
            V_fit = np.linspace(self.V_data.min()*0.95, self.V_data.max()*1.05, 300)
            P_fit = self.fitter.calculate_pressure(V_fit, self.current_params)

            self.ax_main.plot(V_fit, P_fit, 'r-', linewidth=2.5,
                            label=f'Fitted Curve (R²={self.current_params.R_squared:.4f})',
                            alpha=0.9, zorder=3)

        self.ax_main.set_xlabel('Volume V (Å³/atom)', fontsize=12, fontweight='bold')
        self.ax_main.set_ylabel('Pressure P (GPa)', fontsize=12, fontweight='bold')
        title = f'{self.eos_type.value.replace("_", " ").title()} Equation of State'
        self.ax_main.set_title(title, fontsize=13, fontweight='bold')
        self.ax_main.legend(loc='best', fontsize=11, framealpha=0.9)
        self.ax_main.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        self.ax_main.autoscale(enable=True, axis='both', tight=False)

        self.fig.tight_layout()
        self.canvas.draw()

        self.update_results_display()

    def update_results_display(self):
        """Update results display"""
        text = self._format_results_output()
        self.preview_text.setPlainText(text)
        self.last_results_output = text
        self._refresh_results_window()

    def _format_results_output(self):
        """Create a compact, CrysFML-style summary"""
        if self.current_params is None or self.V_data is None or self.P_data is None:
            return "No fitting results yet.\n\nLoad data and adjust parameters or run a fit."

        if self.fitter is None:
            return "No fitter available for displaying results."

        params = self.current_params

        try:
            P_fit = self.fitter.calculate_pressure(self.V_data, params)
            residuals = self.P_data - P_fit
        except Exception:
            P_fit, residuals = None, None

        cycles = []
        cycles.append(self._format_cycle_output("RESULTS FROM CYCLE 1", params,
                                                self.last_initial_params, P_fit, residuals))

        if self.last_initial_params is not None and self.last_initial_params is not params:
            try:
                start_P_fit = self.fitter.calculate_pressure(self.V_data, self.last_initial_params)
                start_residuals = self.P_data - start_P_fit
            except Exception:
                start_P_fit, start_residuals = None, None

            cycles.append(self._format_cycle_output("RESULTS FROM START", self.last_initial_params,
                                                    None, start_P_fit, start_residuals))

        return "\n\n".join(cycles)

    def _format_cycle_output(self, title, params, reference_params, P_fit, residuals):
        """Format cycle output"""
        lines = [title, "=" * 72, ""]
        lines.append("PARA  REF          NEW        SHIFT       E.S.D.     SHIFT/ERROR")
        lines.append("-" * 72)

        lock_flags = {
            'V0': self.param_locks['V0'].isChecked(),
            'B0': self.param_locks['B0'].isChecked(),
            'B0_prime': self.param_locks['B0_prime'].isChecked(),
        }

        def fmt_param(label, value, err, ref_key):
            ref_locked = lock_flags.get(ref_key, False)
            ref_marker = 0 if ref_locked else 1
            ref_value = reference_params.__dict__.get(ref_key) if reference_params is not None else value
            shift = value - ref_value if ref_value is not None else 0.0
            esd = err if err is not None else 0.0
            shift_over_err = (shift / esd) if esd not in (0, None) else 0.0
            return f"{label:<4}{ref_marker:>2}   {value:10.5f}   {shift:10.5f}   {esd:10.5f}   {shift_over_err:8.2f}"

        lines.append(fmt_param('V0', params.V0, getattr(params, 'V0_err', 0.0), 'V0'))
        lines.append(fmt_param('K0', params.B0, getattr(params, 'B0_err', 0.0), 'B0'))

        kp_locked = lock_flags.get('B0_prime', False)
        kp_marker = 0 if kp_locked else 1
        kp_shift = params.B0_prime - (reference_params.B0_prime if (reference_params and reference_params.B0_prime is not None) else params.B0_prime)
        kp_line = f"Kp   {kp_marker:>1}   {params.B0_prime:10.5f}"
        if kp_locked:
            kp_line += "   [NOT REFINED]"
        else:
            kp_esd = getattr(params, 'B0_prime_err', 0.0)
            kp_shift_over_err = (kp_shift / kp_esd) if kp_esd not in (0, None) else 0.0
            kp_line += f"   {kp_shift:10.5f}   {kp_esd:10.5f}   {kp_shift_over_err:8.2f}"
        lines.append(kp_line)

        kpp_val = getattr(params, 'B0_prime2', 0.0)
        lines.append(f"Kpp  0   {kpp_val:10.5f}   [IMPLIED VALUE]")

        if residuals is not None and len(residuals) > 0:
            chi_value = params.chi2 if getattr(params, 'chi2', 0) else 1.00
            max_idx = int(np.argmax(np.abs(residuals)))
            max_residual = residuals[max_idx]
        else:
            chi_value = params.chi2 if getattr(params, 'chi2', 0) else 1.00
            max_residual = 0.0

        lines.append("")
        lines.append(f"W-CHI^2 = {chi_value:5.2f} (AND ESD'S RESCALED BY W-CHI^2)")
        lines.append(f"MAXIMUM DELTA-PRESSURE = {max_residual:+.2f}")

        return "\n".join(lines)

    def open_results_window(self):
        """Open a toplevel window that mirrors the fitting output"""
        if self.results_window is not None and self.results_window.isVisible():
            self.results_window.raise_()
            self.results_window.activateWindow()
            self._refresh_results_window()
            return

        self.results_window = QDialog(self)
        self.results_window.setWindowTitle("Fitting Information Window")
        self.results_window.resize(820, 480)
        self.results_window.setStyleSheet(f"background-color: {self.palette['panel_bg']};")

        layout = QVBoxLayout(self.results_window)
        layout.setContentsMargins(10, 10, 10, 10)

        self.results_window_text = QTextEdit()
        self.results_window_text.setFont(QFont('Courier New', 10))
        self.results_window_text.setReadOnly(True)
        self.results_window_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: #f9fbff;
                color: {self.palette['text_primary']};
                border: 1px solid #e0e6f5;
            }}
        """)
        layout.addWidget(self.results_window_text)

        self._refresh_results_window()
        self.results_window.show()

    def _refresh_results_window(self):
        """Push the latest text into the floating results window"""
        if self.results_window is None or self.results_window_text is None:
            return
        if not self.results_window.isVisible():
            return

        self.results_window_text.setPlainText(self.last_results_output)


def main():
    """Main function to run the GUI"""
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = InteractiveEoSGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()