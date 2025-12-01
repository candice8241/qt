# -*- coding: utf-8 -*-
"""
CrysFML Official API Wrapper for EoS
====================================

This module provides a wrapper for the official CrysFML Python API
to integrate EoS (Equation of State) functionality into the GUI.

Since the official Python API doesn't have EoS bindings yet, this wrapper
provides compatibility between the CrysFML Fortran EoS module and our GUI.

Author: Integration wrapper
Created: 2025-12-01
Source: https://code.ill.fr/scientific-software/crysfml
"""

import numpy as np
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from enum import Enum
import sys
import os

# Try to import official CrysFML Python API
CRYSFML_API_AVAILABLE = False
try:
    # Add CrysFML Python API to path
    crysfml_api_path = os.path.join(os.path.dirname(__file__), 'crysfml_python_api', 'Python_API', 'Src')
    if os.path.exists(crysfml_api_path):
        sys.path.insert(0, crysfml_api_path)
    
    # Try importing CrysFML modules
    # from API_Error_Messages import *
    # from FortranBindedClass import *
    # CRYSFML_API_AVAILABLE = True
    pass
except ImportError:
    CRYSFML_API_AVAILABLE = False

print(f"CrysFML Official API Available: {CRYSFML_API_AVAILABLE}")

# Fallback to our Python implementation
from crysfml_eos_module import (
    CrysFMLEoS, EoSType, EoSParameters,
    MultiEoSFitter, InteractiveEoSFitter
)


class CrysFMLOfficialWrapper:
    """
    Wrapper for CrysFML Official API
    
    This class provides a bridge between:
    1. Official CrysFML Fortran library (when available)
    2. Our Python implementation (as fallback)
    
    Usage:
        wrapper = CrysFMLOfficialWrapper()
        params = wrapper.fit_eos(V_data, P_data, eos_type="BM3")
    """
    
    def __init__(self, use_fortran=True):
        """
        Initialize wrapper
        
        Args:
            use_fortran: Whether to use Fortran backend if available
        """
        self.use_fortran = use_fortran and CRYSFML_API_AVAILABLE
        self.backend = "CrysFML Fortran" if self.use_fortran else "Python (NumPy/SciPy)"
        
        print(f"Initialized CrysFML wrapper with backend: {self.backend}")
        
        # Initialize Python fallback
        self.python_fitter = None
    
    def fit_eos(self, 
                V_data: np.ndarray, 
                P_data: np.ndarray,
                eos_type: str = "BM3",
                **kwargs) -> EoSParameters:
        """
        Fit EoS to P-V data
        
        Args:
            V_data: Volume data (Å³/atom)
            P_data: Pressure data (GPa)
            eos_type: EoS model type ("BM2", "BM3", "BM4", "Murnaghan", "Vinet", etc.)
            **kwargs: Additional fitting parameters
            
        Returns:
            EoSParameters: Fitted parameters
        """
        if self.use_fortran:
            return self._fit_fortran(V_data, P_data, eos_type, **kwargs)
        else:
            return self._fit_python(V_data, P_data, eos_type, **kwargs)
    
    def _fit_fortran(self, V_data, P_data, eos_type, **kwargs):
        """
        Fit using CrysFML Fortran backend
        
        TODO: Implement when CrysFML Python API EoS bindings are available
        """
        print("Warning: CrysFML Fortran EoS bindings not yet available")
        print("Falling back to Python implementation")
        return self._fit_python(V_data, P_data, eos_type, **kwargs)
    
    def _fit_python(self, V_data, P_data, eos_type, **kwargs):
        """
        Fit using Python implementation
        """
        # Map EoS type strings to enum
        eos_map = {
            "BM2": EoSType.BIRCH_MURNAGHAN_2ND,
            "BM3": EoSType.BIRCH_MURNAGHAN_3RD,
            "BM4": EoSType.BIRCH_MURNAGHAN_4TH,
            "Murnaghan": EoSType.MURNAGHAN,
            "Vinet": EoSType.VINET,
            "Natural": EoSType.NATURAL_STRAIN,
        }
        
        eos_enum = eos_map.get(eos_type, EoSType.BIRCH_MURNAGHAN_3RD)
        
        # Create fitter
        if self.python_fitter is None or self.python_fitter.eos_type != eos_enum:
            self.python_fitter = CrysFMLEoS(
                eos_type=eos_enum,
                regularization_strength=kwargs.get('regularization_strength', 1.0)
            )
        
        # Fit
        params = self.python_fitter.fit(V_data, P_data, **kwargs)
        
        return params
    
    def calculate_pressure(self,
                          V: np.ndarray,
                          params: EoSParameters) -> np.ndarray:
        """
        Calculate pressure from volume
        
        Args:
            V: Volume array
            params: EoS parameters
            
        Returns:
            P: Pressure array (GPa)
        """
        if self.python_fitter is None:
            self.python_fitter = CrysFMLEoS(eos_type=params.eos_type)
        
        return self.python_fitter.calculate_pressure(V, params)
    
    def get_info(self) -> Dict[str, str]:
        """
        Get information about the wrapper and CrysFML
        
        Returns:
            Dict with version and source information
        """
        info = {
            "Backend": self.backend,
            "CrysFML API Available": str(CRYSFML_API_AVAILABLE),
            "Source": "https://code.ill.fr/scientific-software/crysfml",
            "EoS Module": "CFML_EoS.f90",
            "Python Implementation": "crysfml_eos_module.py (based on CrysFML methods)",
        }
        
        if CRYSFML_API_AVAILABLE:
            info["API Path"] = crysfml_api_path
        
        return info
    
    def print_info(self):
        """Print wrapper information"""
        print("\n" + "="*70)
        print("CrysFML Official API Wrapper Information")
        print("="*70)
        
        info = self.get_info()
        for key, value in info.items():
            print(f"{key:25s}: {value}")
        
        print("="*70 + "\n")


def test_crysfml_wrapper():
    """Test the CrysFML wrapper"""
    print("\n" + "="*70)
    print("Testing CrysFML Official API Wrapper")
    print("="*70 + "\n")
    
    # Create wrapper
    wrapper = CrysFMLOfficialWrapper()
    wrapper.print_info()
    
    # Test data (MgO from Angel et al. 2014)
    V_data = np.array([74.68, 74.22, 73.48, 72.90, 72.28, 71.65])
    P_data = np.array([0.0, 2.01, 5.03, 7.49, 10.10, 12.84])
    
    print("Test data: MgO (from Angel et al. 2014)")
    print(f"  V: {V_data}")
    print(f"  P: {P_data}")
    print()
    
    # Test fitting
    print("Fitting Birch-Murnaghan 3rd order...")
    params = wrapper.fit_eos(V_data, P_data, eos_type="BM3")
    
    if params is not None:
        print(f"\nFitted parameters:")
        print(f"  V₀ = {params.V0:.4f} ± {params.V0_err:.4f} Å³")
        print(f"  B₀ = {params.B0:.2f} ± {params.B0_err:.2f} GPa")
        print(f"  B₀' = {params.B0_prime:.3f} ± {params.B0_prime_err:.3f}")
        print(f"  R² = {params.R_squared:.6f}")
        print(f"  RMSE = {params.RMSE:.4f} GPa")
        print()
        
        # Test prediction
        V_test = np.array([73.0, 72.0, 71.0])
        P_test = wrapper.calculate_pressure(V_test, params)
        print(f"Pressure predictions:")
        for v, p in zip(V_test, P_test):
            print(f"  P({v:.1f} Å³) = {p:.3f} GPa")
        
        print("\n✓ Test completed successfully")
    else:
        print("✗ Fitting failed")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    test_crysfml_wrapper()
