# -*- coding: utf-8 -*-
"""
Lattice Parameter Calculator - Simplified Version
Created on Thu Nov 13 14:30:34 2025

This tool calculates lattice parameters from XRD peak positions using least squares fitting.

Features:
- Direct CSV input of peak positions (already separated by user)
- Support for multiple crystal systems
- Least squares fitting of lattice parameters
- Export results to CSV

@author: 16961
"""

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
import warnings
import re
warnings.filterwarnings('ignore')


class LatticeParameterCalculator:
    """
    Lattice Parameter Calculator for X-ray Diffraction Data
    
    This class provides lattice parameter fitting for various crystal systems
    using least squares optimization.
    """

    # Crystal system definitions
    CRYSTAL_SYSTEMS = {
        'cubic_FCC': {
            'name': 'FCC',
            'min_peaks': 1,
            'atoms_per_cell': 4,
            'hkl_list': [
                (1,1,1), (2,0,0), (2,2,0), (3,1,1), (2,2,2),
                (4,0,0), (3,3,1), (4,2,0), (4,2,2), (3,3,3),
                (5,1,1), (4,4,0), (5,3,1), (6,0,0), (6,2,0),
                (5,3,3), (6,2,2), (4,4,4), (5,5,1), (6,4,0)
            ]
        },
        'cubic_BCC': {
            'name': 'BCC',
            'min_peaks': 1,
            'atoms_per_cell': 2,
            'hkl_list': [
                (1,1,0), (2,0,0), (2,1,1), (2,2,0), (3,1,0),
                (2,2,2), (3,2,1), (4,0,0), (3,3,0), (4,1,1),
                (3,3,2), (4,2,0), (4,2,2), (3,3,3), (5,1,0),
                (4,3,1), (5,2,1), (4,4,0), (5,3,0), (6,0,0)
            ]
        },
        'Trigonal': {
            'name': 'Trigonal',
            'min_peaks': 2,
            'atoms_per_cell': 1,
            'hkl_list': [
                (1,0,0), (0,1,0), (1,0,1), (0,1,1), (1,1,0),
                (1,1,1), (2,0,0), (0,2,0), (1,0,2), (0,1,2),
                (2,1,0), (1,2,0), (2,0,1), (0,2,1), (2,1,1),
                (1,2,1), (3,0,0), (0,3,0), (2,0,2), (0,2,2),
                (3,1,0), (1,3,0), (2,1,2), (1,2,2), (3,0,1)
            ]
        },
        'Hexagonal': {
            'name': 'HCP',
            'min_peaks': 2,
            'atoms_per_cell': 2,
            'hkl_list': [
                (1,0,0), (1,0,1), (1,0,2), (1,1,0),
                (1,0,3), (2,0,0), (1,1,2), (2,0,1), (0,0,4),
                (2,0,2), (1,0,4), (2,0,3), (2,1,0), (2,1,1),
                (2,0,4), (2,1,2), (3,0,0), (2,1,3), (2,2,0)
            ]
        },
        'Tetragonal': {
            'name': 'Tetragonal',
            'min_peaks': 2,
            'atoms_per_cell': 1,
            'hkl_list': [
                (1,0,0), (0,0,1), (1,1,0), (1,0,1), (1,1,1),
                (2,0,0), (2,1,0), (0,0,2), (2,1,1), (2,0,1),
                (2,2,0), (2,1,2), (3,0,0), (2,2,1), (3,1,0),
                (2,0,2), (3,1,1), (2,2,2), (3,2,0), (3,0,1)
            ]
        },
        'Orthorhombic': {
            'name': 'Orthorhombic',
            'min_peaks': 3,
            'atoms_per_cell': 1,
            'hkl_list': [
                (1,0,0), (0,1,0), (0,0,1), (1,1,0), (1,0,1),
                (0,1,1), (1,1,1), (2,0,0), (2,1,0), (2,0,1),
                (1,2,0), (0,2,0), (1,2,1), (0,2,1), (2,1,1),
                (2,2,0), (2,0,2), (0,0,2), (2,2,1), (3,0,0)
            ]
        },
        'Monoclinic': {
            'name': 'Monoclinic',
            'min_peaks': 4,
            'atoms_per_cell': 1,
            'hkl_list': [
                (1,0,0), (0,1,0), (0,0,1), (1,1,0), (1,0,1),
                (0,1,1), (1,-1,0), (1,0,-1), (1,1,1), (2,0,0),
                (1,-1,1), (2,1,0), (0,2,0), (2,0,1), (1,2,0),
                (0,0,2), (2,1,1), (1,1,-1), (2,-1,0), (2,0,-1)
            ]
        },
        'Triclinic': {
            'name': 'Triclinic',
            'min_peaks': 6,
            'atoms_per_cell': 1,
            'hkl_list': [
                (1,0,0), (0,1,0), (0,0,1), (1,1,0), (1,0,1),
                (0,1,1), (1,-1,0), (1,0,-1), (0,1,-1), (1,1,1),
                (1,-1,1), (1,1,-1), (2,0,0), (0,2,0), (0,0,2),
                (2,1,0), (2,0,1), (1,2,0), (0,2,1), (1,0,2)
            ]
        }
    }

    def __init__(self, wavelength=0.4133, n_pressure_points=4):
        """
        Initialize LatticeParameterCalculator
        
        Parameters:
            wavelength (float): X-ray wavelength in Angstroms (default: 0.4133 Å)
            n_pressure_points (int): Number of pressure points (kept for backward compatibility, not used in simplified version)
        """
        self.wavelength = wavelength
        self.n_pressure_points = n_pressure_points  # Kept for backward compatibility
        self.pressure_data = None
        self.results = None

    # ==================== Utility Functions ====================

    @staticmethod
    def two_theta_to_d(two_theta, wavelength):
        """Convert 2theta angle to d-spacing"""
        theta_rad = np.deg2rad(two_theta / 2.0)
        return wavelength / (2.0 * np.sin(theta_rad))

    @staticmethod
    def calculate_d_cubic(hkl, a):
        """Calculate d-spacing for cubic crystal system"""
        h, k, l = hkl
        return a / np.sqrt(h**2 + k**2 + l**2)

    @staticmethod
    def calculate_d_hexagonal(hkl, a, c):
        """Calculate d-spacing for hexagonal crystal system"""
        h, k, l = hkl
        return 1.0 / np.sqrt(4.0/3.0 * (h**2 + h*k + k**2) / a**2 + l**2 / c**2)

    @staticmethod
    def calculate_d_tetragonal(hkl, a, c):
        """Calculate d-spacing for tetragonal crystal system"""
        h, k, l = hkl
        return 1.0 / np.sqrt((h**2 + k**2) / a**2 + l**2 / c**2)

    @staticmethod
    def calculate_d_orthorhombic(hkl, a, b, c):
        """Calculate d-spacing for orthorhombic crystal system"""
        h, k, l = hkl
        return 1.0 / np.sqrt(h**2 / a**2 + k**2 / b**2 + l**2 / c**2)

    @staticmethod
    def calculate_d_monoclinic(hkl, a, b, c, beta):
        """Calculate d-spacing for monoclinic crystal system"""
        h, k, l = hkl
        beta_rad = np.deg2rad(beta)
        sin_beta = np.sin(beta_rad)
        cos_beta = np.cos(beta_rad)
        term = (h**2 / a**2 + k**2 * sin_beta**2 / b**2 + l**2 / c**2
                - 2*h*l*cos_beta / (a*c)) / sin_beta**2
        return 1.0 / np.sqrt(term)

    @staticmethod
    def calculate_cell_volume_cubic(a):
        """Calculate unit cell volume for cubic system"""
        return a**3

    @staticmethod
    def calculate_cell_volume_hexagonal(a, c):
        """Calculate unit cell volume for hexagonal system"""
        return np.sqrt(3) / 2 * a**2 * c

    @staticmethod
    def calculate_cell_volume_tetragonal(a, c):
        """Calculate unit cell volume for tetragonal system"""
        return a**2 * c

    @staticmethod
    def calculate_cell_volume_orthorhombic(a, b, c):
        """Calculate unit cell volume for orthorhombic system"""
        return a * b * c

    @staticmethod
    def calculate_cell_volume_monoclinic(a, b, c, beta):
        """Calculate unit cell volume for monoclinic system"""
        beta_rad = np.deg2rad(beta)
        return a * b * c * np.sin(beta_rad)

    # ==================== Data Reading ====================

    def read_peak_data(self, csv_path):
        """
        Read CSV file and extract pressure points and peak positions
        
        CSV Format:
        - Column 'File': Pressure values (e.g., "10", "10.5", "40 GPa")
        - Column 'Center': Peak positions in 2theta (degrees)
        - Empty rows separate different pressure points
        
        Parameters:
            csv_path (str): Path to CSV file
            
        Returns:
            dict: Dictionary with pressure values (GPa) as keys and peak position lists (2theta) as values
        """
        df = pd.read_csv(csv_path)
        
        if 'File' not in df.columns or 'Center' not in df.columns:
            raise ValueError("CSV file must contain 'File' and 'Center' columns")
        
        pressure_data = {}
        
        for idx, row in df.iterrows():
            # Check if this is a blank row
            if pd.isna(row['File']) or row['File'] == '':
                continue
            
            # Extract pressure value
            try:
                file_str = str(row['File'])
                numbers = re.findall(r'[-+]?\d*\.?\d+', file_str)
                if numbers:
                    pressure = float(numbers[0])
                else:
                    pressure = float(file_str)
            except:
                print(f"Warning: Cannot parse pressure value: {row['File']}")
                continue
            
            # Extract peak position
            try:
                peak_position = float(row['Center'])
            except:
                print(f"Warning: Cannot parse peak position: {row['Center']}")
                continue
            
            if pressure not in pressure_data:
                pressure_data[pressure] = []
            pressure_data[pressure].append(peak_position)
        
        # Sort peak positions for each pressure point
        for pressure in pressure_data:
            pressure_data[pressure] = sorted(pressure_data[pressure])
        
        self.pressure_data = pressure_data
        return pressure_data

    # ==================== Lattice Parameter Fitting ====================

    def fit_lattice_parameters_cubic(self, peak_dataset, crystal_system_key):
        """Fit lattice parameters for cubic crystal systems"""
        results = {}
        hkl_list = self.CRYSTAL_SYSTEMS[crystal_system_key]['hkl_list']
        atoms_per_cell = self.CRYSTAL_SYSTEMS[crystal_system_key]['atoms_per_cell']
        
        for pressure, peaks in peak_dataset.items():
            if isinstance(peaks, dict):
                peaks = peaks.get('peaks', [])
            
            if len(peaks) == 0:
                continue
            
            d_obs = [self.two_theta_to_d(peak, self.wavelength) for peak in peaks]
            
            num_peaks = min(len(peaks), len(hkl_list))
            matched_hkl = hkl_list[:num_peaks]
            
            def residuals(params):
                a = params[0]
                errors = []
                for i, hkl in enumerate(matched_hkl):
                    d_calc = self.calculate_d_cubic(hkl, a)
                    errors.append(d_obs[i] - d_calc)
                return errors
            
            a_init = d_obs[0] * np.sqrt(sum(x**2 for x in matched_hkl[0]))
            result = least_squares(residuals, [a_init], bounds=([0], [np.inf]))
            a_fitted = result.x[0]
            
            V_cell = self.calculate_cell_volume_cubic(a_fitted)
            V_atomic = V_cell / atoms_per_cell
            
            results[pressure] = {
                'a': a_fitted,
                'b': a_fitted,  # Cubic: a = b = c
                'c': a_fitted,
                'alpha': 90.0,  # Cubic: α = β = γ = 90°
                'beta': 90.0,
                'gamma': 90.0,
                'V_cell': V_cell,
                'V_atomic': V_atomic,
                'num_peaks_used': num_peaks
            }
            
            print(f"Pressure: {pressure:.2f} GPa")
            print(f"  Lattice parameters: a = b = c = {a_fitted:.6f} Å")
            print(f"  Angles: α = β = γ = 90.0°")
            print(f"  Unit cell volume V = {V_cell:.6f} Å³")
            print(f"  Average atomic volume = {V_atomic:.6f} Å³/atom")
        
        return results

    def fit_lattice_parameters_hexagonal(self, peak_dataset, crystal_system_key):
        """Fit lattice parameters for hexagonal crystal systems"""
        results = {}
        hkl_list = self.CRYSTAL_SYSTEMS[crystal_system_key]['hkl_list']
        atoms_per_cell = self.CRYSTAL_SYSTEMS[crystal_system_key]['atoms_per_cell']
        
        for pressure, peaks in peak_dataset.items():
            if isinstance(peaks, dict):
                peaks = peaks.get('peaks', [])
            
            if len(peaks) < 2:
                continue
            
            d_obs = [self.two_theta_to_d(peak, self.wavelength) for peak in peaks]
            
            num_peaks = min(len(peaks), len(hkl_list))
            matched_hkl = hkl_list[:num_peaks]
            
            def residuals(params):
                a, c = params
                errors = []
                for i, hkl in enumerate(matched_hkl):
                    d_calc = self.calculate_d_hexagonal(hkl, a, c)
                    errors.append(d_obs[i] - d_calc)
                
                # Soft constraint for c/a ratio ~ 1.633
                target_ratio = 1.633
                ratio = c / a
                penalty_weight = 0.1
                penalty = penalty_weight * (ratio - target_ratio)
                errors.append(penalty)
                
                return errors
            
            a_init = 3.0
            c_init = 5.0
            
            result = least_squares(residuals, [a_init, c_init],
                                  bounds=([0, 0], [np.inf, np.inf]))
            a_fitted, c_fitted = result.x
            
            V_cell = self.calculate_cell_volume_hexagonal(a_fitted, c_fitted)
            V_atomic = V_cell / atoms_per_cell
            
            results[pressure] = {
                'a': a_fitted,
                'b': a_fitted,  # Hexagonal: a = b ≠ c
                'c': c_fitted,
                'alpha': 90.0,  # Hexagonal: α = β = 90°, γ = 120°
                'beta': 90.0,
                'gamma': 120.0,
                'c/a': c_fitted / a_fitted,
                'V_cell': V_cell,
                'V_atomic': V_atomic,
                'num_peaks_used': num_peaks
            }
            
            print(f"Pressure: {pressure:.2f} GPa")
            print(f"  Lattice parameters: a = b = {a_fitted:.6f} Å, c = {c_fitted:.6f} Å")
            print(f"  Angles: α = β = 90.0°, γ = 120.0°")
            print(f"  c/a ratio = {c_fitted/a_fitted:.6f}")
            print(f"  Unit cell volume V = {V_cell:.6f} Å³")
            print(f"  Average atomic volume = {V_atomic:.6f} Å³/atom")
        
        return results

    def fit_lattice_parameters_trigonal(self, peak_dataset, crystal_system_key):
        """Fit lattice parameters for trigonal crystal systems (hexagonal setting)"""
        results = {}
        hkl_list = self.CRYSTAL_SYSTEMS[crystal_system_key]['hkl_list']
        atoms_per_cell = self.CRYSTAL_SYSTEMS[crystal_system_key]['atoms_per_cell']
        
        for pressure, peaks in peak_dataset.items():
            if isinstance(peaks, dict):
                peaks = peaks.get('peaks', [])
            
            if len(peaks) < 2:
                continue
            
            d_obs = [self.two_theta_to_d(peak, self.wavelength) for peak in peaks]
            
            num_peaks = min(len(peaks), len(hkl_list))
            matched_hkl = hkl_list[:num_peaks]
            
            def residuals(params):
                a, c = params
                errors = []
                for i, hkl in enumerate(matched_hkl):
                    d_calc = self.calculate_d_hexagonal(hkl, a, c)
                    errors.append(d_obs[i] - d_calc)
                return errors
            
            a_init = 3.0
            c_init = 5.0
            
            result = least_squares(residuals, [a_init, c_init],
                                  bounds=([0, 0], [np.inf, np.inf]))
            a_fitted, c_fitted = result.x
            
            V_cell = self.calculate_cell_volume_hexagonal(a_fitted, c_fitted)
            V_atomic = V_cell / atoms_per_cell
            
            results[pressure] = {
                'a': a_fitted,
                'b': a_fitted,  # Trigonal (hexagonal setting): a = b ≠ c
                'c': c_fitted,
                'alpha': 90.0,  # Trigonal (hexagonal setting): α = β = 90°, γ = 120°
                'beta': 90.0,
                'gamma': 120.0,
                'c/a': c_fitted / a_fitted,
                'V_cell': V_cell,
                'V_atomic': V_atomic,
                'num_peaks_used': num_peaks
            }
            
            print(f"Pressure: {pressure:.2f} GPa")
            print(f"  Lattice parameters: a = b = {a_fitted:.6f} Å, c = {c_fitted:.6f} Å")
            print(f"  Angles: α = β = 90.0°, γ = 120.0°")
            print(f"  c/a ratio = {c_fitted/a_fitted:.6f}")
            print(f"  Unit cell volume V = {V_cell:.6f} Å³")
            print(f"  Average atomic volume = {V_atomic:.6f} Å³/atom")
        
        return results

    def fit_lattice_parameters_tetragonal(self, peak_dataset, crystal_system_key):
        """Fit lattice parameters for tetragonal crystal systems"""
        results = {}
        hkl_list = self.CRYSTAL_SYSTEMS[crystal_system_key]['hkl_list']
        atoms_per_cell = self.CRYSTAL_SYSTEMS[crystal_system_key]['atoms_per_cell']
        
        for pressure, peaks in peak_dataset.items():
            if isinstance(peaks, dict):
                peaks = peaks.get('peaks', [])
            
            if len(peaks) < 2:
                continue
            
            d_obs = [self.two_theta_to_d(peak, self.wavelength) for peak in peaks]
            
            num_peaks = min(len(peaks), len(hkl_list))
            matched_hkl = hkl_list[:num_peaks]
            
            def residuals(params):
                a, c = params
                errors = []
                for i, hkl in enumerate(matched_hkl):
                    d_calc = self.calculate_d_tetragonal(hkl, a, c)
                    errors.append(d_obs[i] - d_calc)
                return errors
            
            a_init = 3.0
            c_init = 4.0
            
            result = least_squares(residuals, [a_init, c_init],
                                  bounds=([0, 0], [np.inf, np.inf]))
            a_fitted, c_fitted = result.x
            
            V_cell = self.calculate_cell_volume_tetragonal(a_fitted, c_fitted)
            V_atomic = V_cell / atoms_per_cell
            
            results[pressure] = {
                'a': a_fitted,
                'b': a_fitted,  # Tetragonal: a = b ≠ c
                'c': c_fitted,
                'alpha': 90.0,  # Tetragonal: α = β = γ = 90°
                'beta': 90.0,
                'gamma': 90.0,
                'c/a': c_fitted / a_fitted,
                'V_cell': V_cell,
                'V_atomic': V_atomic,
                'num_peaks_used': num_peaks
            }
            
            print(f"Pressure: {pressure:.2f} GPa")
            print(f"  Lattice parameters: a = b = {a_fitted:.6f} Å, c = {c_fitted:.6f} Å")
            print(f"  Angles: α = β = γ = 90.0°")
            print(f"  c/a ratio = {c_fitted/a_fitted:.6f}")
            print(f"  Unit cell volume V = {V_cell:.6f} Å³")
            print(f"  Average atomic volume = {V_atomic:.6f} Å³/atom")
        
        return results

    def fit_lattice_parameters_orthorhombic(self, peak_dataset, crystal_system_key):
        """Fit lattice parameters for orthorhombic crystal systems"""
        results = {}
        hkl_list = self.CRYSTAL_SYSTEMS[crystal_system_key]['hkl_list']
        atoms_per_cell = self.CRYSTAL_SYSTEMS[crystal_system_key]['atoms_per_cell']
        
        for pressure, peaks in peak_dataset.items():
            if isinstance(peaks, dict):
                peaks = peaks.get('peaks', [])
            
            if len(peaks) < 3:
                continue
            
            d_obs = [self.two_theta_to_d(peak, self.wavelength) for peak in peaks]
            
            num_peaks = min(len(peaks), len(hkl_list))
            matched_hkl = hkl_list[:num_peaks]
            
            def residuals(params):
                a, b, c = params
                errors = []
                for i, hkl in enumerate(matched_hkl):
                    d_calc = self.calculate_d_orthorhombic(hkl, a, b, c)
                    errors.append(d_obs[i] - d_calc)
                return errors
            
            a_init = 3.0
            b_init = 4.0
            c_init = 5.0
            
            result = least_squares(residuals, [a_init, b_init, c_init],
                                  bounds=([0, 0, 0], [np.inf, np.inf, np.inf]))
            a_fitted, b_fitted, c_fitted = result.x
            
            V_cell = self.calculate_cell_volume_orthorhombic(a_fitted, b_fitted, c_fitted)
            V_atomic = V_cell / atoms_per_cell
            
            results[pressure] = {
                'a': a_fitted,
                'b': b_fitted,
                'c': c_fitted,
                'alpha': 90.0,  # Orthorhombic: α = β = γ = 90°
                'beta': 90.0,
                'gamma': 90.0,
                'V_cell': V_cell,
                'V_atomic': V_atomic,
                'num_peaks_used': num_peaks
            }
            
            print(f"Pressure: {pressure:.2f} GPa")
            print(f"  Lattice parameters: a = {a_fitted:.6f} Å, b = {b_fitted:.6f} Å, c = {c_fitted:.6f} Å")
            print(f"  Angles: α = β = γ = 90.0°")
            print(f"  Unit cell volume V = {V_cell:.6f} Å³")
            print(f"  Average atomic volume = {V_atomic:.6f} Å³/atom")
        
        return results

    def fit_lattice_parameters(self, peak_dataset, crystal_system_key):
        """
        Main function to fit lattice parameters based on crystal system
        
        Parameters:
            peak_dataset (dict): Peak dataset dictionary {pressure: [peak1, peak2, ...]}
            crystal_system_key (str): Crystal system key
            
        Returns:
            dict: Fitting results including lattice parameters and volumes
        """
        system_type = crystal_system_key.split('_')[0]
        
        print(f"\n{'='*60}")
        print(f"Fitting Lattice Parameters for {self.CRYSTAL_SYSTEMS[crystal_system_key]['name']}")
        print(f"{'='*60}\n")
        
        if system_type == 'cubic':
            return self.fit_lattice_parameters_cubic(peak_dataset, crystal_system_key)
        elif crystal_system_key == 'Hexagonal':
            return self.fit_lattice_parameters_hexagonal(peak_dataset, crystal_system_key)
        elif crystal_system_key == 'Trigonal':
            return self.fit_lattice_parameters_trigonal(peak_dataset, crystal_system_key)
        elif crystal_system_key == 'Tetragonal':
            return self.fit_lattice_parameters_tetragonal(peak_dataset, crystal_system_key)
        elif crystal_system_key == 'Orthorhombic':
            return self.fit_lattice_parameters_orthorhombic(peak_dataset, crystal_system_key)
        else:
            print(f"Warning: Fitting for {crystal_system_key} not yet implemented")
            return {}

    # ==================== User Interaction ====================

    @staticmethod
    def select_crystal_system():
        """Interactive crystal system selection"""
        print("\nSelect crystal system:")
        print("[1] Face-Centered Cubic (FCC)")
        print("[2] Body-Centered Cubic (BCC)")
        print("[3] Trigonal")
        print("[4] Hexagonal Close-Packed (HCP)")
        print("[5] Tetragonal")
        print("[6] Orthorhombic")
        print("[7] Monoclinic")
        print("[8] Triclinic")
        
        choice = input("Enter your choice (1-8): ").strip()
        
        mapping = {
            "1": "cubic_FCC",
            "2": "cubic_BCC",
            "3": "Trigonal",
            "4": "Hexagonal",
            "5": "Tetragonal",
            "6": "Orthorhombic",
            "7": "Monoclinic",
            "8": "Triclinic"
        }
        
        selected = mapping.get(choice)
        if selected:
            print(f"✓ Selected crystal system: {LatticeParameterCalculator.CRYSTAL_SYSTEMS[selected]['name']}")
            return selected
        else:
            print("⚠️ Invalid choice, defaulting to 'cubic_FCC'")
            return "cubic_FCC"

    # ==================== Results Export ====================

    @staticmethod
    def save_results_to_csv(results, filename):
        """Save lattice parameter fitting results to CSV file"""
        if not results:
            print("No results to save.")
            return
        
        data_rows = []
        for pressure, params in sorted(results.items()):
            row = {'Pressure (GPa)': pressure}
            row.update(params)
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        
        # Reorder columns to ensure 6 lattice parameters come first
        base_columns = ['Pressure (GPa)', 'a', 'b', 'c', 'alpha', 'beta', 'gamma']
        available_base = [col for col in base_columns if col in df.columns]
        other_columns = [col for col in df.columns if col not in base_columns]
        column_order = available_base + other_columns
        df = df[column_order]
        
        df.to_csv(filename, index=False)
        print(f"\n✓ Results saved to: {filename}")

    # ==================== Main Workflow ====================

    def calculate(self, csv_path, crystal_system_key=None):
        """
        Calculate lattice parameters from CSV file
        
        Parameters:
            csv_path (str): Path to input CSV file with peak positions
            crystal_system_key (str, optional): Crystal system key. If None, will prompt user
            
        Returns:
            dict: Lattice parameter results
        """
        print("\n" + "="*60)
        print("LATTICE PARAMETER CALCULATION")
        print("="*60)
        
        # Step 1: Read peak data
        try:
            self.read_peak_data(csv_path)
            print(f"\n✓ Successfully read data from {csv_path}")
            print(f"  Total pressure points: {len(self.pressure_data)}")
        except Exception as e:
            print(f"❌ Error reading CSV file: {e}")
            return None
        
        # Step 2: Select crystal system
        if crystal_system_key is None:
            crystal_system_key = self.select_crystal_system()
        else:
            print(f"\n✓ Using crystal system: {self.CRYSTAL_SYSTEMS[crystal_system_key]['name']}")
        
        # Step 3: Fit lattice parameters
        self.results = self.fit_lattice_parameters(self.pressure_data, crystal_system_key)
        
        # Step 4: Save results
        output_filename = csv_path.replace('.csv', '_lattice_results.csv')
        self.save_results_to_csv(self.results, output_filename)
        
        print("\n" + "="*60)
        print("CALCULATION COMPLETE")
        print("="*60)
        print(f"\nSummary:")
        print(f"  - Crystal system: {self.CRYSTAL_SYSTEMS[crystal_system_key]['name']}")
        print(f"  - Number of pressure points: {len(self.results)}")
        print(f"  - Results saved to: {output_filename}")
        print("\n" + "="*60 + "\n")
        
        return self.results

    def analyze(self, csv_path, original_system=None, new_system=None, auto_mode=False):
        """
        Backward compatibility method - calls calculate() for simplified workflow
        
        Parameters:
            csv_path (str): Path to input CSV file
            original_system (str, optional): Crystal system for calculation
            new_system (str, optional): Ignored in simplified version
            auto_mode (bool): If True, use provided system without prompting
            
        Returns:
            dict: Analysis results
        """
        print("\n⚠️  Note: Using simplified lattice parameter calculation")
        print("   Phase transition detection has been removed from this version")
        print("   Please separate peaks manually before using this tool\n")
        
        # Use original_system if provided, otherwise prompt
        crystal_system = original_system if auto_mode and original_system else None
        
        # Call the simplified calculate method
        results = self.calculate(csv_path, crystal_system_key=crystal_system)
        
        # Return in a format compatible with old code
        return {
            'single_phase_results': results,
            'transition_pressure': None
        }


# ==================== Backward Compatibility ====================

# Alias for backward compatibility with existing code
XRayDiffractionAnalyzer = LatticeParameterCalculator


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Example: Interactive mode
    calculator = LatticeParameterCalculator(wavelength=0.4133)
    
    # Option 1: Interactive - prompts for crystal system
    csv_path = r'D:\HEPS\ID31\dioptas_data\Al0\fit_output\all_results.csv'
    results = calculator.calculate(csv_path)
    
    # Option 2: Programmatic - specify crystal system
    # results = calculator.calculate(csv_path, crystal_system_key='cubic_FCC')