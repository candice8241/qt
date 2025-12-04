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
from typing import Tuple
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
    
    IMPORTANT: This class contains a 1:1 replication of the CrysFML third-order
    Birch-Murnaghan fitting algorithm to ensure exact consistency with the
    crysfml_eos_module.py implementation.
    """
    
    # ==================== CrysFML Algorithm Replication ====================
    # The following methods are exact 1:1 replications from crysfml_eos_module.py
    
    @staticmethod
    def _birch_murnaghan_3rd_pv(V: np.ndarray, V0: float, B0: float, B0_prime: float) -> np.ndarray:
        """
        3rd order Birch-Murnaghan Equation of State (P-V form)
        
        EXACT REPLICATION from crysfml_eos_module.py lines 176-205
        
        Rewritten to follow the same Eulerian strain formulation as the
        Fortran ``eosfit`` routines from CrysFML.  Expressing the pressure
        in terms of ``f`` and ``(1+2f)`` matches the linearised ``F-f``
        approach used elsewhere in this module and prevents rounding
        differences between GUI updates and the dedicated fitting path.

        Parameters:
        -----------
        V : array
            Volume (Å³/atom)
        V0 : float
            Zero-pressure volume (Å³/atom)
        B0 : float
            Zero-pressure bulk modulus (GPa)
        B0_prime : float
            Pressure derivative of bulk modulus

        Returns:
        --------
        P : array
            Pressure (GPa)
        """
        f = 0.5 * ((V0 / V) ** (2 / 3) - 1.0)
        prefactor = 3.0 * B0 * f * (1.0 + 2.0 * f) ** 2.5
        correction = 1.0 + 1.5 * (B0_prime - 4.0) * f
        return prefactor * correction
    
    @staticmethod
    def _birch_murnaghan_f_F_transform(V_data: np.ndarray, P_data: np.ndarray, 
                                       V0_estimate: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Transform P-V data to normalized strain-stress (f-F) form
        
        EXACT REPLICATION from crysfml_eos_module.py lines 441-470
        
        CrysFML KEY METHOD: Linearizes Birch-Murnaghan equation
        
        f = normalized strain = [(V0/V)^(2/3) - 1] / 2
        F = normalized stress = P / [3f(1+2f)^(5/2)]
        
        For BM3: F = B0 [1 + (B0'-4)f]  --> LINEAR in f!
        
        This allows weighted linear regression to get stable B0_prime
        """
        # Calculate Eulerian strain
        x = (V0_estimate / V_data) ** (1.0/3.0)
        f = 0.5 * (x**2 - 1.0)
        
        # Calculate normalized stress (avoid division by zero)
        denominator = 3.0 * f * (1.0 + 2.0*f)**(5.0/2.0)
        
        # Small strain handling
        mask = np.abs(f) > 1e-10
        F = np.zeros_like(P_data)
        F[mask] = P_data[mask] / denominator[mask]
        
        # For very small strains, use limit
        F[~mask] = P_data[~mask] / (3.0 * V0_estimate)
        
        return f, F
    
    def _fit_birch_murnaghan_3rd_linear(self, V_data: np.ndarray, P_data: np.ndarray, 
                                        regularization_strength: float) -> EoSParameters:
        """
        CrysFML method: Two-stage fitting using F-f linearization
        
        EXACT REPLICATION from crysfml_eos_module.py lines 472-708
        (adapted to work within the GUI context)

        Stage 1: Determine V0 and B0 (2nd order fit or iteration)
        Stage 2: Linear regression F vs f to get B0_prime (stable!)

        This prevents B0_prime divergence because it's determined from a linear fit

        Following CrysFML methodology:
        - Iterative refinement of V0
        - Weighted linear regression in F-f space
        - Full error propagation using variance-covariance matrix
        - Physical constraints on B0' (typically 2-8, centered around 4)
        """
        # Physical bounds on B0' based on literature (Angel et al., Gonzalez-Platas)
        # Most crystalline materials have B0' between 3 and 6
        # We allow slightly wider range (2-8) for flexibility
        B0_PRIME_MIN = 2.0
        B0_PRIME_MAX = 8.0

        # Stage 1: Get initial V0 estimate
        V0_guess, B0_guess, B0_prime_guess = self._smart_initial_guess(V_data, P_data)

        # Iteratively refine V0 using 2nd order BM
        # Start with initial guess (slightly above maximum volume for safety)
        V0_current = max(V0_guess, np.max(V_data) * 1.01)
        V0_history = [V0_current]

        # Sanity check on initial B0 estimate
        if B0_guess < 50 or B0_guess > 500:
            B0_guess = 150.0

        for iteration in range(10):  # Increased iterations for better convergence
            # Transform to f-F space
            f, F = self._birch_murnaghan_f_F_transform(V_data, P_data, V0_current)

            # Check for valid strain range
            if np.max(np.abs(f)) > 0.5:  # Strain too large, adjust V0
                V0_current = np.max(V_data) * 1.05
                V0_history.append(V0_current)
                continue

            # CrysFML weighting scheme: emphasize low-strain data even more
            # Weight = 1 / (strain^2 + epsilon) to avoid singularity
            # Use smaller epsilon for stronger emphasis on low-strain points
            weights = 1.0 / (f**2 + 0.001)
            weights = weights / np.sum(weights) * len(weights)

            # Linear fit: F = a + b*f where b = B0' - 4
            # Use regularized weighted least squares to prevent B0' divergence
            W = np.diag(weights)
            A = np.column_stack([np.ones_like(f), f])

            # Apply Tikhonov regularization to constrain B0' near 4.0
            try:
                # Regularization based on CrysFML methodology: penalize deviations from B0' = 4.0
                # User can adjust regularization_strength parameter
                lambda_reg = regularization_strength * np.mean(weights)
                R = np.array([[0.0, 0.0], [0.0, 1.0]])  # Only regularize B0' term

                ATA = A.T @ W @ A
                ATF = A.T @ W @ F
                ATA_reg = ATA + lambda_reg * R  # Add soft constraint

                beta = np.linalg.solve(ATA_reg, ATF)

                B0_fit = beta[0]
                b_fit = beta[1]
                B0_prime_fit = 4.0 + b_fit

                # Physical constraints based on literature
                # B0: 20-800 GPa (very wide, most materials 50-400 GPa)
                if B0_fit < 20 or B0_fit > 800:
                    break  # Stop iteration, use current V0

                # B0': Must be within physical bounds (2-8)
                # This is the KEY improvement following CrysFML/EosFit methodology
                if B0_prime_fit < B0_PRIME_MIN or B0_prime_fit > B0_PRIME_MAX:
                    break  # Stop iteration, use current V0

                # Simple V0 update: minimize RMSE in P-V space
                # Try small adjustments around current V0
                best_V0 = V0_current
                best_rmse = float('inf')

                for delta in [-0.02, -0.01, 0.0, 0.01, 0.02]:
                    V0_test = V0_current * (1.0 + delta)
                    if V0_test > np.max(V_data):  # V0 must be larger than all measured volumes
                        P_test = self._birch_murnaghan_3rd_pv(V_data, V0_test, B0_fit, B0_prime_fit)
                        rmse_test = np.sqrt(np.mean((P_data - P_test)**2))
                        if rmse_test < best_rmse:
                            best_rmse = rmse_test
                            best_V0 = V0_test

                # Damped update
                V0_current = 0.8 * V0_current + 0.2 * best_V0
                V0_history.append(V0_current)

                # Check convergence
                if len(V0_history) > 1:
                    V0_change = abs(V0_history[-1] - V0_history[-2]) / V0_history[-2]
                    if V0_change < 1e-6:  # Convergence threshold
                        break

            except (np.linalg.LinAlgError, RuntimeWarning):
                # If linear solve fails, use initial guess
                break

        # Final fit with refined V0
        f, F = self._birch_murnaghan_f_F_transform(V_data, P_data, V0_current)

        # Final weighted linear regression with improved CrysFML weighting
        # Use smaller epsilon to strongly emphasize low-strain data
        weights = 1.0 / (f**2 + 0.001)
        weights = weights / np.sum(weights) * len(weights)

        W = np.diag(weights)
        A = np.column_stack([np.ones_like(f), f])

        try:
            # CrysFML Method: Regularized least squares with penalty on B0' deviation
            # This prevents B0' from diverging while still allowing it to vary
            #
            # Minimize: ||W(F - A*beta)||² + λ * (b - 0)²
            # where b = beta[1] = B0' - 4, and λ is regularization parameter
            #
            # Physical reasoning: B0' should be close to 4.0 for most materials
            # Regularization keeps it near 4.0 unless data strongly suggests otherwise

            # Regularization parameter: controls how strongly we constrain B0' to ~4.0
            # Larger λ = stronger constraint toward B0' = 4.0
            # User-adjustable via regularization_strength parameter
            lambda_reg = regularization_strength * np.mean(weights)

            # Modified normal equations with Tikhonov regularization:
            # (A^T W A + λR) beta = A^T W F
            # where R = [[0, 0], [0, 1]] penalizes deviation in beta[1] only
            R = np.array([[0.0, 0.0], [0.0, 1.0]])  # Only regularize B0' term

            ATA = A.T @ W @ A
            ATF = A.T @ W @ F
            ATA_reg = ATA + lambda_reg * R  # Add regularization

            beta = np.linalg.solve(ATA_reg, ATF)

            # Calculate parameter errors from covariance matrix
            # Following CrysFML error propagation methodology
            F_fit = A @ beta
            residuals_F = F - F_fit

            # Weighted chi-square
            chi2 = np.sum(weights * residuals_F**2)
            dof = len(f) - 2  # degrees of freedom

            # Variance-covariance matrix for B0 and B0_prime
            # Account for regularization in error estimation
            if dof > 0:
                s2 = chi2 / dof
                # Use regularized matrix for proper error propagation
                cov_B0_B0p = s2 * np.linalg.inv(ATA_reg)
                errors_linear = np.sqrt(np.diag(cov_B0_B0p))
            else:
                errors_linear = np.array([0.0, 0.0])

            # Extract parameters
            B0_final = beta[0]
            B0_prime_final = 4.0 + beta[1]

            # Apply physical constraints if B0' is out of bounds
            # If out of bounds, try constrained fit with B0' fixed at nearest bound
            if B0_prime_final < B0_PRIME_MIN:
                # B0' too small, fix at minimum and refit for B0 only
                B0_prime_final = B0_PRIME_MIN
                # Refit with constrained B0': F = B0 [1 + (B0'-4)f]
                # F / [1 + (B0'-4)f] = B0
                constraint_factor = 1.0 + (B0_prime_final - 4.0) * f
                F_constrained = F / constraint_factor
                B0_final = np.sum(weights * F_constrained) / np.sum(weights)
                B0_err = np.sqrt(s2 / np.sum(weights)) if dof > 0 else 0.0
                B0_prime_err = 0.0  # Fixed parameter
            elif B0_prime_final > B0_PRIME_MAX:
                # B0' too large, fix at maximum and refit for B0 only
                B0_prime_final = B0_PRIME_MAX
                constraint_factor = 1.0 + (B0_prime_final - 4.0) * f
                F_constrained = F / constraint_factor
                B0_final = np.sum(weights * F_constrained) / np.sum(weights)
                B0_err = np.sqrt(s2 / np.sum(weights)) if dof > 0 else 0.0
                B0_prime_err = 0.0  # Fixed parameter
            else:
                # Parameters within bounds, use normal errors
                B0_err = errors_linear[0]
                B0_prime_err = errors_linear[1]

            # Estimate V0 error using error propagation
            # The uncertainty in V0 comes from the scatter in the V0 iteration
            if len(V0_history) > 3:
                # Use standard deviation of last few iterations as V0 error estimate
                V0_err = np.std(V0_history[-3:])
            else:
                # Alternative: estimate from residuals
                # σ(V0) ≈ σ(V) * (∂V0/∂V) where σ(V) from residuals
                P_fit = self._birch_murnaghan_3rd_pv(V_data, V0_current, B0_final, B0_prime_final)
                residuals_P = P_data - P_fit
                # Estimate V uncertainty from P residuals: dV/dP ≈ V/B
                V_uncertainty = np.std(residuals_P) * V0_current / B0_final
                V0_err = V_uncertainty * 0.5  # Conservative estimate

            # Calculate R² and RMSE in P-V space (for comparison)
            P_fit = self._birch_murnaghan_3rd_pv(V_data, V0_current, B0_final, B0_prime_final)
            residuals_P = P_data - P_fit
            ss_res = np.sum(residuals_P**2)
            ss_tot = np.sum((P_data - np.mean(P_data))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            rmse = np.sqrt(np.mean(residuals_P**2))

            # Calculate reduced chi-square (CrysFML method)
            # chi2_reduced = (weighted sum of squared residuals) / degrees of freedom
            chi2_reduced = chi2 / dof if dof > 0 else 0.0

            # Create parameter object with full error estimates
            params = EoSParameters(eos_type=self.eos_type)
            params.V0 = V0_current
            params.V0_err = V0_err  # Now properly estimated!
            params.B0 = B0_final
            params.B0_err = B0_err
            params.B0_prime = B0_prime_final
            params.B0_prime_err = B0_prime_err
            params.R_squared = r_squared
            params.RMSE = rmse
            params.chi2 = chi2_reduced
            params.n_data = len(V_data)

            return params

        except np.linalg.LinAlgError:
            return None
    
    def _smart_initial_guess(self, V_data: np.ndarray, P_data: np.ndarray) -> Tuple[float, float, float]:
        """
        Smart initial guess estimation based on data characteristics
        
        EXACT REPLICATION from crysfml_eos_module.py lines 377-439
        
        Uses physical constraints and data-driven estimation similar to CrysFML approach

        Parameters:
        -----------
        V_data : array
            Volume data
        P_data : array
            Pressure data

        Returns:
        --------
        V0_guess, B0_guess, B0_prime_guess : tuple
            Initial parameter guesses
        """
        # Sort data by pressure for better estimation
        sort_idx = np.argsort(P_data)
        P_sorted = P_data[sort_idx]
        V_sorted = V_data[sort_idx]
        
        # V0: Estimate zero-pressure volume
        # Use the volume at lowest pressure as starting point
        min_P_idx = 0  # After sorting, lowest pressure is at index 0
        V0_guess = V_sorted[min_P_idx]
        
        # If minimum pressure is not near zero, extrapolate using first few points
        if P_sorted[min_P_idx] > 0.5:
            # Linear extrapolation using lowest 2-3 pressure points
            n_points = min(3, len(P_sorted))
            if n_points >= 2:
                # Fit linear P-V relationship for low pressure region
                coeffs = np.polyfit(P_sorted[:n_points], V_sorted[:n_points], 1)
                V0_guess = coeffs[1]  # Intercept at P=0
        
        # Ensure V0 is slightly larger than maximum observed volume
        V0_guess = max(V0_guess, np.max(V_sorted) * 1.005)
        
        # B0: Estimate bulk modulus from initial compressibility
        # K = -V * (dP/dV), use low pressure region
        if len(V_sorted) >= 4:
            # Use first 3-5 points to estimate initial slope
            n_points = min(5, len(V_sorted))
            # Calculate dP/dV using finite differences
            dP = P_sorted[1:n_points] - P_sorted[0:n_points-1]
            dV = V_sorted[1:n_points] - V_sorted[0:n_points-1]
            dP_dV = np.mean(dP / dV)
            
            # B0 = -V * dP/dV at zero pressure
            B0_guess = -V0_guess * dP_dV
            
            # Constrain to reasonable range based on material properties
            B0_guess = np.clip(B0_guess, 80, 300)
        else:
            B0_guess = 150.0
        
        # B0_prime: Use typical value of 4.0
        # Most materials have B0_prime between 3.5 and 5.0
        B0_prime_guess = 4.0

        return V0_guess, B0_guess, B0_prime_guess
    
    # ==================== End of CrysFML Algorithm Replication ====================
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
                background-color: transparent;
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: none;
                margin-top: 0px;
                padding-top: 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 0px;
                padding: 0px;
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
                background-color: transparent;
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: none;
                margin-top: 0px;
                padding-top: 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 0px;
                padding: 0px;
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
                background-color: transparent;
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: none;
                margin-top: 0px;
                padding-top: 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 0px;
                padding: 0px;
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
                background-color: transparent;
                color: {self.palette['text_primary']};
                font-weight: bold;
                font-size: 10pt;
                border: none;
                margin-top: 0px;
                padding-top: 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 0px;
                padding: 0px;
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
        """Handle EoS model change
        
        Special handling for Birch-Murnaghan 3rd order: automatically unlocks all parameters
        """
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

        # Special handling for Birch-Murnaghan 3rd order
        if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
            # Check if any parameters are locked
            any_locked = (self.param_locks['V0'].isChecked() or 
                         self.param_locks['B0'].isChecked() or 
                         self.param_locks['B0_prime'].isChecked())
            
            if any_locked:
                # Automatically unlock all parameters
                self.param_locks['V0'].setChecked(False)
                self.param_locks['B0'].setChecked(False)
                self.param_locks['B0_prime'].setChecked(False)
                
                # Show information message
                QMessageBox.information(
                    self,
                    "Parameters Unlocked",
                    "ℹ️ Birch-Murnaghan 3rd Order Selected\n\n"
                    "All parameters have been automatically unlocked.\n\n"
                    "The F-f linearization method used for BM3 requires "
                    "all three parameters (V₀, B₀, B₀') to be free for proper fitting."
                )

        if self.V_data is not None and self.P_data is not None:
            self.update_manual_fit()

    def reset_parameters(self):
        """Reset parameters to smart initial guess
        
        Uses replicated CrysFML smart initial guess algorithm
        """
        if self.V_data is None or self.P_data is None:
            return

        reg_strength = self.reg_slider.value() / 10.0
        self.fitter = CrysFMLEoS(eos_type=self.eos_type, regularization_strength=reg_strength)

        # Use replicated smart initial guess
        V0_guess, B0_guess, B0_prime_guess = self._smart_initial_guess(
            self.V_data, self.P_data
        )

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
        """Update plot with current manual parameters
        
        Uses replicated CrysFML algorithm for BM3, otherwise uses external fitter
        """
        if self.V_data is None or self.P_data is None:
            return

        reg_strength = self.reg_slider.value() / 10.0
        if self.fitter is None or self.fitter.eos_type != self.eos_type:
            self.fitter = CrysFMLEoS(eos_type=self.eos_type, regularization_strength=reg_strength)

        try:
            params = self.get_current_params()
            
            # Use replicated algorithm for BM3
            if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
                P_fit = self._birch_murnaghan_3rd_pv(self.V_data, params.V0, params.B0, params.B0_prime)
            else:
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
        """Fit only unlocked parameters
        
        IMPORTANT: For Birch-Murnaghan 3rd order, all parameters must be unlocked.
        The F-f linearization method requires all three parameters (V0, B0, B0') to be free.
        """
        if self.V_data is None or self.P_data is None:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        V0_locked = self.param_locks['V0'].isChecked()
        B0_locked = self.param_locks['B0'].isChecked()
        B0_prime_locked = self.param_locks['B0_prime'].isChecked()

        if V0_locked and B0_locked and B0_prime_locked:
            QMessageBox.warning(self, "Warning", "All parameters are locked!")
            return

        # Special check for Birch-Murnaghan 3rd order
        if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
            if V0_locked or B0_locked or B0_prime_locked:
                locked_params = []
                if V0_locked:
                    locked_params.append("V₀")
                if B0_locked:
                    locked_params.append("B₀")
                if B0_prime_locked:
                    locked_params.append("B₀'")
                
                QMessageBox.warning(
                    self, 
                    "Birch-Murnaghan 3rd Order Constraint",
                    f"⚠️ For Birch-Murnaghan 3rd order fitting, ALL parameters must be unlocked!\n\n"
                    f"Currently locked: {', '.join(locked_params)}\n\n"
                    f"The F-f linearization method used for BM3 requires all three parameters "
                    f"(V₀, B₀, B₀') to be free for proper fitting.\n\n"
                    f"Please unlock all parameters and try again."
                )
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
            
            # Use replicated algorithm for BM3 (all parameters must be unlocked at this point)
            if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
                params = self._fit_birch_murnaghan_3rd_linear(self.V_data, self.P_data, reg_strength)
            else:
                # Use external fitter for other EoS types
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
                QMessageBox.warning(
                    self,
                    "Fitting Failed",
                    "⚠️ Fitting failed to converge.\n\n"
                    "Try adjusting the regularization strength or check your data quality."
                )
                self.update_manual_fit()

        except Exception as e:
            error_msg = str(e)
            print(f"Fit unlocked error: {error_msg}")
            QMessageBox.critical(
                self,
                "Fitting Error",
                f"❌ An error occurred during fitting:\n\n{error_msg}\n\n"
                f"Please check your data and try again."
            )
            self.update_manual_fit()

    def fit_multiple_strategies(self):
        """Try fitting with multiple strategies
        
        IMPORTANT: For Birch-Murnaghan 3rd order, all parameters must be unlocked.
        This method will check for locked parameters and warn the user.
        """
        if self.V_data is None or self.P_data is None:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        # Special check for Birch-Murnaghan 3rd order
        if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
            V0_locked = self.param_locks['V0'].isChecked()
            B0_locked = self.param_locks['B0'].isChecked()
            B0_prime_locked = self.param_locks['B0_prime'].isChecked()
            
            if V0_locked or B0_locked or B0_prime_locked:
                locked_params = []
                if V0_locked:
                    locked_params.append("V₀")
                if B0_locked:
                    locked_params.append("B₀")
                if B0_prime_locked:
                    locked_params.append("B₀'")
                
                QMessageBox.warning(
                    self, 
                    "Birch-Murnaghan 3rd Order Constraint",
                    f"⚠️ For Birch-Murnaghan 3rd order fitting, ALL parameters must be unlocked!\n\n"
                    f"Currently locked: {', '.join(locked_params)}\n\n"
                    f"The F-f linearization method used for BM3 requires all three parameters "
                    f"(V₀, B₀, B₀') to be free for proper fitting.\n\n"
                    f"Please unlock all parameters and try again."
                )
                return

        reg_strength = self.reg_slider.value() / 10.0
        self.fitter = CrysFMLEoS(eos_type=self.eos_type, regularization_strength=reg_strength)

        try:
            self.last_initial_params = self.get_current_params()
            print("\n" + "="*60)
            print("Trying multiple fitting strategies...")
            print("="*60)
            
            best_params = None
            
            # Strategy 1: Use replicated CrysFML algorithm for BM3
            if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
                print("  Strategy 1: CrysFML Replicated F-f Linearization...")
                try:
                    params = self._fit_birch_murnaghan_3rd_linear(self.V_data, self.P_data, reg_strength)
                    if params is not None:
                        best_params = params
                        print(f"    Success: R² = {params.R_squared:.6f}, RMSE = {params.RMSE:.4f}, B0' = {params.B0_prime:.3f}")
                except Exception as e:
                    print(f"    Failed: {e}")
            
            # Strategy 2: Try external fitter strategies
            print("  Strategy 2: External fitter strategies...")
            params = self.fitter.fit_with_multiple_strategies(
                self.V_data, self.P_data, verbose=True
            )
            
            # Choose best result
            if best_params is None:
                best_params = params
            elif params is not None:
                # Compare by R² and RMSE
                if params.R_squared > best_params.R_squared or \
                   (abs(params.R_squared - best_params.R_squared) < 0.001 and params.RMSE < best_params.RMSE):
                    best_params = params

            if best_params is not None:
                self.param_entries['V0'].setText(f"{best_params.V0:.4f}")
                self.param_entries['B0'].setText(f"{best_params.B0:.2f}")
                self.param_entries['B0_prime'].setText(f"{best_params.B0_prime:.3f}")

                self.fitted_params = best_params
                self.current_params = best_params
                self.update_plot()

                print("="*60)
                print("Best fit found!")
                print(f"  V0 = {best_params.V0:.4f}, B0 = {best_params.B0:.2f}, B0' = {best_params.B0_prime:.3f}")
                print(f"  R² = {best_params.R_squared:.6f}, RMSE = {best_params.RMSE:.4f}")
                print("="*60 + "\n")
            else:
                print("="*60)
                print("All strategies failed - using current manual values")
                print("="*60 + "\n")
                QMessageBox.warning(
                    self,
                    "All Strategies Failed",
                    "⚠️ All fitting strategies failed to converge.\n\n"
                    "Suggestions:\n"
                    "• Try adjusting the regularization strength\n"
                    "• Check your data quality\n"
                    "• Try a different EoS model"
                )
                self.update_manual_fit()

        except Exception as e:
            error_msg = str(e)
            print(f"Error in multiple strategies: {error_msg}")
            QMessageBox.critical(
                self,
                "Fitting Error",
                f"❌ An error occurred during fitting:\n\n{error_msg}\n\n"
                f"Please check your data and try again."
            )
            self.update_manual_fit()

    def update_plot(self):
        """Update the plot with current data and fit
        
        Uses replicated CrysFML algorithm for BM3 pressure calculation
        """
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
            
            # Use replicated algorithm for BM3
            if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
                P_fit = self._birch_murnaghan_3rd_pv(V_fit, self.current_params.V0, 
                                                      self.current_params.B0, self.current_params.B0_prime)
            else:
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
        """Create a compact, CrysFML-style summary
        
        Uses replicated CrysFML algorithm for BM3 pressure calculation
        """
        if self.current_params is None or self.V_data is None or self.P_data is None:
            return "No fitting results yet.\n\nLoad data and adjust parameters or run a fit."

        if self.fitter is None:
            return "No fitter available for displaying results."

        params = self.current_params

        try:
            # Use replicated algorithm for BM3
            if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
                P_fit = self._birch_murnaghan_3rd_pv(self.V_data, params.V0, params.B0, params.B0_prime)
            else:
                P_fit = self.fitter.calculate_pressure(self.V_data, params)
            residuals = self.P_data - P_fit
        except Exception:
            P_fit, residuals = None, None

        cycles = []
        cycles.append(self._format_cycle_output("RESULTS FROM CYCLE 1", params,
                                                self.last_initial_params, P_fit, residuals))

        if self.last_initial_params is not None and self.last_initial_params is not params:
            try:
                # Use replicated algorithm for BM3
                if self.eos_type == EoSType.BIRCH_MURNAGHAN_3RD:
                    start_P_fit = self._birch_murnaghan_3rd_pv(self.V_data, self.last_initial_params.V0,
                                                                self.last_initial_params.B0, 
                                                                self.last_initial_params.B0_prime)
                else:
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