# -*- coding: utf-8 -*-
"""
BCDI Calibration Module - FCC Bragg Calculator
Detector + Sampling Parameters and Coherence Calculations

Migrated from Streamlit to PyQt6
Original author: candicewang928@gmail.com
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QGroupBox, QScrollArea,
                              QFrame, QDoubleSpinBox, QSpinBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import numpy as np
from gui_base import GUIBase
from theme_module import ModernButton


class BCDICalModule(GUIBase):
    """BCDI Calibration module - FCC Bragg & Coherence Calculator"""

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
        
        # Initialize input variables with default values
        self._init_variables()

    def _init_variables(self):
        """Initialize all input variables with default values"""
        self.E_keV = 9.0
        self.a_angstrom = 3.608
        self.h = 1
        self.k = 1
        self.l = 1
        self.x_det = 55e-6
        self.sigma = 4.0
        self.sample_size = 1e-6
        self.D = 100e-6
        self.energy_resolution = 1e-4
        self.space_resolution = 50e-9
        self.N1 = 256
        self.N2 = 256
        self.N3 = 100
        self.delta = 11.104
        self.gamma = 29.607

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

        # Create scroll area for all content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet(f"background-color: {self.colors['bg']}; border: none;")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(20, 10, 20, 10)
        scroll_layout.setSpacing(15)

        # Title section
        title_label = QLabel("📐 FCC Bragg & Coherence Calculator")
        title_label.setFont(QFont('Microsoft YaHei', 19, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['primary']}; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("📷 Detector + Sampling Parameters")
        subtitle_label.setFont(QFont('Microsoft YaHei', 14, QFont.Weight.Bold))
        subtitle_label.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 5px;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(subtitle_label)

        # ===== Basic Parameters Section =====
        self.setup_basic_params(scroll_layout)

        # ===== Miller Indices Section =====
        self.setup_miller_indices(scroll_layout)

        # ===== Detector Parameters Section =====
        self.setup_detector_params(scroll_layout)

        # ===== Sample Parameters Section =====
        self.setup_sample_params(scroll_layout)

        # ===== Array Dimensions Section =====
        self.setup_array_dimensions(scroll_layout)

        # ===== Angles Section =====
        self.setup_angles(scroll_layout)

        # ===== Calculate Button =====
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 15, 0, 15)
        button_layout.addStretch()
        
        calc_btn = ModernButton("🧮 Calculate", self.calculate,
                               bg_color='#9D4EDD',
                               hover_color='#C77DFF',
                               width=250, height=50,
                               font_size=12,
                               parent=button_container)
        button_layout.addWidget(calc_btn)
        button_layout.addStretch()
        scroll_layout.addWidget(button_container)

        # ===== Results Section =====
        results_group = self.create_group_box("📊 Calculation Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colors['bg']};
                color: {self.colors['text_dark']};
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                padding: 15px;
                font-family: 'Microsoft YaHei', 'Consolas', monospace;
                font-size: 11pt;
                line-height: 1.5;
            }}
        """)
        self.results_text.setMinimumHeight(250)
        self.results_text.setMaximumHeight(350)
        self.results_text.setPlaceholderText("Results will appear here after calculation...")
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        scroll_layout.addWidget(results_group)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def setup_basic_params(self, parent_layout):
        """Setup basic parameters section"""
        group = self.create_group_box("⚡ Basic Parameters")
        layout = QVBoxLayout()

        # Photon energy
        energy_row = QHBoxLayout()
        energy_label = QLabel("Photon energy (keV):")
        energy_label.setFixedWidth(250)
        energy_label.setFont(QFont('Microsoft YaHei', 11))
        energy_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.energy_spin = QDoubleSpinBox()
        self.energy_spin.setRange(0.1, 100.0)
        self.energy_spin.setValue(self.E_keV)
        self.energy_spin.setDecimals(3)
        self.energy_spin.setSingleStep(0.1)
        self.energy_spin.setStyleSheet(self.get_spinbox_style())
        energy_row.addWidget(energy_label)
        energy_row.addWidget(self.energy_spin)
        energy_row.addStretch()
        layout.addLayout(energy_row)

        # Lattice constant
        lattice_row = QHBoxLayout()
        lattice_label = QLabel("Lattice constant a (Å):")
        lattice_label.setFixedWidth(250)
        lattice_label.setFont(QFont('Microsoft YaHei', 11))
        lattice_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.lattice_spin = QDoubleSpinBox()
        self.lattice_spin.setRange(0.1, 20.0)
        self.lattice_spin.setValue(self.a_angstrom)
        self.lattice_spin.setDecimals(4)
        self.lattice_spin.setSingleStep(0.001)
        self.lattice_spin.setStyleSheet(self.get_spinbox_style())
        lattice_row.addWidget(lattice_label)
        lattice_row.addWidget(self.lattice_spin)
        lattice_row.addStretch()
        layout.addLayout(lattice_row)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def setup_miller_indices(self, parent_layout):
        """Setup Miller indices section"""
        group = self.create_group_box("🔢 Miller Indices (hkl)")
        layout = QVBoxLayout()

        hkl_row = QHBoxLayout()
        
        # h
        h_label = QLabel("h:")
        h_label.setFixedWidth(30)
        h_label.setFont(QFont('Microsoft YaHei', 11))
        h_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.h_spin = QSpinBox()
        self.h_spin.setRange(-10, 10)
        self.h_spin.setValue(self.h)
        self.h_spin.setStyleSheet(self.get_spinbox_style())
        hkl_row.addWidget(h_label)
        hkl_row.addWidget(self.h_spin)

        # k
        k_label = QLabel("k:")
        k_label.setFixedWidth(30)
        k_label.setFont(QFont('Microsoft YaHei', 11))
        k_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.k_spin = QSpinBox()
        self.k_spin.setRange(-10, 10)
        self.k_spin.setValue(self.k)
        self.k_spin.setStyleSheet(self.get_spinbox_style())
        hkl_row.addWidget(k_label)
        hkl_row.addWidget(self.k_spin)

        # l
        l_label = QLabel("l:")
        l_label.setFixedWidth(30)
        l_label.setFont(QFont('Microsoft YaHei', 11))
        l_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.l_spin = QSpinBox()
        self.l_spin.setRange(-10, 10)
        self.l_spin.setValue(self.l)
        self.l_spin.setStyleSheet(self.get_spinbox_style())
        hkl_row.addWidget(l_label)
        hkl_row.addWidget(self.l_spin)

        hkl_row.addStretch()
        layout.addLayout(hkl_row)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def setup_detector_params(self, parent_layout):
        """Setup detector parameters section"""
        group = self.create_group_box("📷 Detector Parameters")
        layout = QVBoxLayout()

        # Detector pixel size
        pixel_row = QHBoxLayout()
        pixel_label = QLabel("Detector pixel size x_det (m):")
        pixel_label.setFixedWidth(250)
        pixel_label.setFont(QFont('Microsoft YaHei', 11))
        pixel_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.pixel_spin = QDoubleSpinBox()
        self.pixel_spin.setRange(1e-9, 1e-3)
        self.pixel_spin.setValue(self.x_det)
        self.pixel_spin.setDecimals(10)
        self.pixel_spin.setSingleStep(1e-6)
        self.pixel_spin.setStyleSheet(self.get_spinbox_style())
        pixel_row.addWidget(pixel_label)
        pixel_row.addWidget(self.pixel_spin)
        pixel_row.addStretch()
        layout.addLayout(pixel_row)

        # Oversampling ratio
        sigma_row = QHBoxLayout()
        sigma_label = QLabel("Oversampling ratio σ:")
        sigma_label.setFixedWidth(250)
        sigma_label.setFont(QFont('Microsoft YaHei', 11))
        sigma_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.sigma_spin = QDoubleSpinBox()
        self.sigma_spin.setRange(1.0, 100.0)
        self.sigma_spin.setValue(self.sigma)
        self.sigma_spin.setDecimals(2)
        self.sigma_spin.setSingleStep(0.1)
        self.sigma_spin.setStyleSheet(self.get_spinbox_style())
        sigma_row.addWidget(sigma_label)
        sigma_row.addWidget(self.sigma_spin)
        sigma_row.addStretch()
        layout.addLayout(sigma_row)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def setup_sample_params(self, parent_layout):
        """Setup sample parameters section"""
        group = self.create_group_box("🔬 Sample Parameters")
        layout = QVBoxLayout()

        # Sample size
        sample_row = QHBoxLayout()
        sample_label = QLabel("Sample size (m):")
        sample_label.setFixedWidth(250)
        sample_label.setFont(QFont('Microsoft YaHei', 11))
        sample_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.sample_spin = QDoubleSpinBox()
        self.sample_spin.setRange(1e-9, 1e-3)
        self.sample_spin.setValue(self.sample_size)
        self.sample_spin.setDecimals(10)
        self.sample_spin.setSingleStep(1e-7)
        self.sample_spin.setStyleSheet(self.get_spinbox_style())
        sample_row.addWidget(sample_label)
        sample_row.addWidget(self.sample_spin)
        sample_row.addStretch()
        layout.addLayout(sample_row)

        # Beam spot size
        beam_row = QHBoxLayout()
        beam_label = QLabel("Beam spot size D (m):")
        beam_label.setFixedWidth(250)
        beam_label.setFont(QFont('Microsoft YaHei', 11))
        beam_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.beam_spin = QDoubleSpinBox()
        self.beam_spin.setRange(1e-9, 1e-3)
        self.beam_spin.setValue(self.D)
        self.beam_spin.setDecimals(10)
        self.beam_spin.setSingleStep(1e-6)
        self.beam_spin.setStyleSheet(self.get_spinbox_style())
        beam_row.addWidget(beam_label)
        beam_row.addWidget(self.beam_spin)
        beam_row.addStretch()
        layout.addLayout(beam_row)

        # Energy resolution
        energy_res_row = QHBoxLayout()
        energy_res_label = QLabel("Energy resolution Δλ/λ:")
        energy_res_label.setFixedWidth(250)
        energy_res_label.setFont(QFont('Microsoft YaHei', 11))
        energy_res_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.energy_res_spin = QDoubleSpinBox()
        self.energy_res_spin.setRange(1e-6, 1e-2)
        self.energy_res_spin.setValue(self.energy_resolution)
        self.energy_res_spin.setDecimals(10)
        self.energy_res_spin.setSingleStep(1e-5)
        self.energy_res_spin.setStyleSheet(self.get_spinbox_style())
        energy_res_row.addWidget(energy_res_label)
        energy_res_row.addWidget(self.energy_res_spin)
        energy_res_row.addStretch()
        layout.addLayout(energy_res_row)

        # Spatial resolution
        space_res_row = QHBoxLayout()
        space_res_label = QLabel("Spatial resolution (m):")
        space_res_label.setFixedWidth(250)
        space_res_label.setFont(QFont('Microsoft YaHei', 11))
        space_res_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.space_res_spin = QDoubleSpinBox()
        self.space_res_spin.setRange(1e-12, 1e-6)
        self.space_res_spin.setValue(self.space_resolution)
        self.space_res_spin.setDecimals(12)
        self.space_res_spin.setSingleStep(1e-9)
        self.space_res_spin.setStyleSheet(self.get_spinbox_style())
        space_res_row.addWidget(space_res_label)
        space_res_row.addWidget(self.space_res_spin)
        space_res_row.addStretch()
        layout.addLayout(space_res_row)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def setup_array_dimensions(self, parent_layout):
        """Setup array dimensions section"""
        group = self.create_group_box("📐 Array Dimensions")
        layout = QVBoxLayout()

        dims_row = QHBoxLayout()

        # N1
        n1_label = QLabel("N1:")
        n1_label.setFixedWidth(50)
        n1_label.setFont(QFont('Microsoft YaHei', 11))
        n1_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.n1_spin = QSpinBox()
        self.n1_spin.setRange(1, 10000)
        self.n1_spin.setValue(self.N1)
        self.n1_spin.setStyleSheet(self.get_spinbox_style())
        dims_row.addWidget(n1_label)
        dims_row.addWidget(self.n1_spin)

        # N2
        n2_label = QLabel("N2:")
        n2_label.setFixedWidth(50)
        n2_label.setFont(QFont('Microsoft YaHei', 11))
        n2_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.n2_spin = QSpinBox()
        self.n2_spin.setRange(1, 10000)
        self.n2_spin.setValue(self.N2)
        self.n2_spin.setStyleSheet(self.get_spinbox_style())
        dims_row.addWidget(n2_label)
        dims_row.addWidget(self.n2_spin)

        # N3
        n3_label = QLabel("N3:")
        n3_label.setFixedWidth(50)
        n3_label.setFont(QFont('Microsoft YaHei', 11))
        n3_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.n3_spin = QSpinBox()
        self.n3_spin.setRange(1, 10000)
        self.n3_spin.setValue(self.N3)
        self.n3_spin.setStyleSheet(self.get_spinbox_style())
        dims_row.addWidget(n3_label)
        dims_row.addWidget(self.n3_spin)

        dims_row.addStretch()
        layout.addLayout(dims_row)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def setup_angles(self, parent_layout):
        """Setup detector angles section"""
        group = self.create_group_box("📐 Detector Angles")
        layout = QVBoxLayout()

        # Delta (elevation)
        delta_row = QHBoxLayout()
        delta_label = QLabel("Detector elevation δ (deg):")
        delta_label.setFixedWidth(250)
        delta_label.setFont(QFont('Microsoft YaHei', 11))
        delta_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.delta_spin = QDoubleSpinBox()
        self.delta_spin.setRange(-180.0, 180.0)
        self.delta_spin.setValue(self.delta)
        self.delta_spin.setDecimals(3)
        self.delta_spin.setSingleStep(0.1)
        self.delta_spin.setStyleSheet(self.get_spinbox_style())
        delta_row.addWidget(delta_label)
        delta_row.addWidget(self.delta_spin)
        delta_row.addStretch()
        layout.addLayout(delta_row)

        # Gamma (azimuth)
        gamma_row = QHBoxLayout()
        gamma_label = QLabel("Detector azimuth γ (deg):")
        gamma_label.setFixedWidth(250)
        gamma_label.setFont(QFont('Microsoft YaHei', 11))
        gamma_label.setStyleSheet(f"color: {self.colors['text_dark']};")
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(-180.0, 180.0)
        self.gamma_spin.setValue(self.gamma)
        self.gamma_spin.setDecimals(3)
        self.gamma_spin.setSingleStep(0.1)
        self.gamma_spin.setStyleSheet(self.get_spinbox_style())
        gamma_row.addWidget(gamma_label)
        gamma_row.addWidget(self.gamma_spin)
        gamma_row.addStretch()
        layout.addLayout(gamma_row)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def calculate(self):
        """Perform calculations and display results"""
        try:
            # Get values from spinboxes
            E_keV = self.energy_spin.value()
            a_angstrom = self.lattice_spin.value()
            h = self.h_spin.value()
            k = self.k_spin.value()
            l = self.l_spin.value()
            x_det = self.pixel_spin.value()
            sigma = self.sigma_spin.value()
            sample_size = self.sample_spin.value()
            D = self.beam_spin.value()
            energy_resolution = self.energy_res_spin.value()
            space_resolution = self.space_res_spin.value()
            N1 = self.n1_spin.value()
            N2 = self.n2_spin.value()
            N3 = self.n3_spin.value()
            delta = self.delta_spin.value()
            gamma = self.gamma_spin.value()

            # Convert keV → λ
            lambda_ = 1.24e-9 / E_keV

            # d_spacing
            d_spacing = self.d_fcc(a_angstrom * 1e-10, h, k, l)

            # Bragg angle
            theta_deg = self.bragg_theta(lambda_, d_spacing, deg=True)

            # Calculations
            L_min = (x_det * sigma * sample_size) / lambda_
            delta_omega = lambda_ / (2 * np.sin(np.radians(theta_deg / 2)) * sample_size * sigma) * (180 / np.pi)
            L_T = (lambda_ / 2) * (L_min / D)
            L_L = lambda_ / (2 * energy_resolution)
            delta_q_speckle = (lambda_ * L_min) / sample_size
            q_max = 1 / (2 * space_resolution)
            delta_q = (2 * np.pi * x_det) / (L_min * lambda_)

            # Matrix calculations (convert angles to radians)
            delta_rad = np.radians(delta)
            gamma_rad = np.radians(gamma)
            Bdet = self.compute_Bdet(delta_rad, gamma_rad)
            Brecip = self.compute_Brecip(x_det, D, delta_rad, gamma_rad, np.radians(delta_omega), lambda_)
            Breal = self.compute_Breal(Brecip, N1, N2, N3)

            # Format results
            results = []
            results.append("=" * 70)
            results.append("CALCULATION RESULTS")
            results.append("=" * 70)
            results.append("")
            results.append("Basic Parameters:")
            results.append(f"  λ (wavelength) = {lambda_:.3e} m")
            results.append(f"  d(hkl) = {d_spacing:.3e} m")
            results.append(f"  θ (Bragg angle) = {theta_deg:.3f}°")
            results.append("")
            results.append("Coherence & Resolution:")
            results.append(f"  L_min = {L_min:.3f} m")
            results.append(f"  Δω = {delta_omega:.4f}°")
            results.append(f"  L_T (Transverse coherence length) = {L_T*1e6:.3f} µm")
            results.append(f"  L_L (Longitudinal coherence length) = {L_L*1e6:.3f} µm")
            results.append(f"  Δq_speckle = {delta_q_speckle*1e6:.2f} µm")
            results.append(f"  q_max = {q_max*1e-6:.2f} µm⁻¹")
            results.append(f"  Δq = {delta_q*1e-9:.6f} nm⁻¹")
            results.append("")
            results.append("B_det (Detector matrix):")
            results.append(self.format_matrix(Bdet))
            results.append("")
            results.append("B_recip (Reciprocal space matrix):")
            results.append(self.format_matrix(Brecip))
            results.append("")
            results.append("B_real (Real space matrix):")
            results.append(self.format_matrix(Breal))
            results.append("")
            results.append("=" * 70)

            self.results_text.setPlainText("\n".join(results))

        except Exception as e:
            import traceback
            error_msg = f"Error during calculation:\n\n{str(e)}\n\n{traceback.format_exc()}"
            self.results_text.setPlainText(error_msg)

    # -------------------
    # Core Physics Functions
    # -------------------
    def bragg_theta(self, lambda_, d_spacing, n=1, deg=False):
        """Calculate Bragg angle"""
        sin_theta = n * lambda_ / (2 * d_spacing)
        if sin_theta > 1:
            raise ValueError("No solution: sin(theta) > 1, check wavelength and plane spacing")
        theta = np.arcsin(sin_theta)
        return np.degrees(theta) if deg else theta

    def d_fcc(self, a, h, k, l):
        """Calculate d-spacing for FCC lattice"""
        return a / np.sqrt(h**2 + k**2 + l**2)

    def compute_Bdet(self, delta, gamma):
        """Compute detector matrix"""
        cosd, sind = np.cos(delta), np.sin(delta)
        cosg, sing = np.cos(gamma), np.sin(gamma)
        Bdet = np.array([
            [cosd, -sing*sind, cosg*sind],
            [0, cosg, sing],
            [-sind, -cosd*sing, cosd*cosg]
        ])
        return Bdet

    def compute_Brecip(self, P, D, delta, gamma, delta_theta, lambda_):
        """Compute reciprocal space matrix"""
        cosd, sind = np.cos(delta), np.sin(delta)
        cosg, sing = np.cos(gamma), np.sin(gamma)
        Brecip = np.array([
            [P/(lambda_*D)*cosd, -P/(lambda_*D)*sing*sind, delta_theta/lambda_*(1 - cosg*cosd)],
            [0, P/(lambda_*D)*cosg, 0],
            [-P/(lambda_*D)*sind, -P/(lambda_*D)*cosd*sing, delta_theta/lambda_*cosg*sind]
        ])
        return Brecip

    def compute_Breal(self, Brecip, N1, N2, N3):
        """Compute real space matrix"""
        D_inv = np.diag([1/N1, 1/N2, 1/N3])
        Breal = np.linalg.inv(Brecip.T) @ D_inv
        return Breal

    def format_matrix(self, matrix):
        """Format numpy matrix for display"""
        lines = []
        for row in matrix:
            formatted_row = "  [" + "  ".join([f"{val:12.6e}" for val in row]) + "]"
            lines.append(formatted_row)
        return "\n".join(lines)

    def get_spinbox_style(self):
        """Get style for spinboxes with beautiful arrows"""
        return f"""
            QSpinBox, QDoubleSpinBox {{
                padding: 6px;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                background-color: white;
                color: {self.colors['text_dark']};
                min-width: 150px;
                font-family: 'Microsoft YaHei';
                font-size: 11pt;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {self.colors['primary']};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {self.colors['border']};
                border-bottom: 1px solid {self.colors['border']};
                border-top-right-radius: 4px;
                background-color: {self.colors['card_bg']};
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
                background-color: {self.colors['light_purple']};
            }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 7px solid {self.colors['text_dark']};
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid {self.colors['border']};
                border-top: 1px solid {self.colors['border']};
                border-bottom-right-radius: 4px;
                background-color: {self.colors['card_bg']};
            }}
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {self.colors['light_purple']};
            }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid {self.colors['text_dark']};
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
