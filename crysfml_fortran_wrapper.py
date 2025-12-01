# -*- coding: utf-8 -*-
"""
CrysFML Fortran Wrapper - Python Interface to CrysFML EoS Fortran Module

This module provides a Python wrapper for the original CrysFML CFML_EoS_Mod.f90
Fortran module, allowing Python code to call the high-performance Fortran
implementations directly.

Requirements:
- CrysFML Fortran library compiled as shared library
- numpy-f2py or ctypes for Fortran-Python interface

Author: Integration wrapper
Created: 2025-12-01
"""

import numpy as np
from typing import Optional, Tuple
import os
import sys
from dataclasses import dataclass
from enum import Enum

# Try to import compiled Fortran module
FORTRAN_AVAILABLE = False
try:
    # This will be the compiled f2py module
    # import cfml_eos_fortran
    # FORTRAN_AVAILABLE = True
    pass
except ImportError:
    FORTRAN_AVAILABLE = False
    print("Warning: CrysFML Fortran module not available. Using Python fallback.")


class CrysFMLEoSType(Enum):
    """EoS types matching CrysFML definitions"""
    MURNAGHAN = 1
    BIRCH_MURNAGHAN_3RD = 2
    BIRCH_MURNAGHAN_4TH = 3
    VINET = 4
    NATURAL_STRAIN = 5
    TAIT = 6


@dataclass
class CrysFMLEoSParams:
    """
    EoS parameters matching CrysFML EOS_Parameters_Type
    
    Corresponds to Fortran derived type:
    Type, public :: EOS_Parameters_Type
        integer :: imodel
        real(kind=cp) :: V0, K0, Kp, Kpp
        real(kind=cp) :: eV0, eK0, eKp, eKpp
        real(kind=cp) :: chi2
    End Type EOS_Parameters_Type
    """
    imodel: int = 2  # EoS model type (1-6)
    V0: float = 0.0  # Zero-pressure volume
    K0: float = 0.0  # Zero-pressure bulk modulus (B0 in GPa)
    Kp: float = 4.0  # First derivative of K0 (B0')
    Kpp: float = 0.0  # Second derivative of K0 (B0'')
    
    # Errors
    eV0: float = 0.0
    eK0: float = 0.0
    eKp: float = 0.0
    eKpp: float = 0.0
    
    # Quality metric
    chi2: float = 0.0


class CrysFMLFortranWrapper:
    """
    Python wrapper for CrysFML Fortran EoS module
    
    This class provides a Pythonic interface to the compiled CrysFML
    Fortran library, handling data type conversions and error checking.
    """
    
    def __init__(self, fortran_lib_path: Optional[str] = None):
        """
        Initialize wrapper
        
        Args:
            fortran_lib_path: Path to compiled Fortran shared library (.so/.dll)
        """
        self.fortran_available = FORTRAN_AVAILABLE
        self.lib_path = fortran_lib_path
        
        if not self.fortran_available:
            print("Warning: Fortran module not loaded. Using Python fallback.")
            # Fallback to Python implementation
            from crysfml_eos_module import CrysFMLEoS, EoSType
            self.python_fallback = CrysFMLEoS()
    
    def fit_eos_fortran(self, 
                       V_data: np.ndarray, 
                       P_data: np.ndarray,
                       eos_type: CrysFMLEoSType = CrysFMLEoSType.BIRCH_MURNAGHAN_3RD,
                       weights: Optional[np.ndarray] = None) -> CrysFMLEoSParams:
        """
        Fit EoS parameters using CrysFML Fortran routine
        
        Calls the Fortran subroutine:
        Subroutine EoS_Fit(V, P, Sig, imod, Params, chi2)
        
        Args:
            V_data: Volume data (Å³/atom or Å³)
            P_data: Pressure data (GPa)
            eos_type: EoS model type
            weights: Optional weights for data points
            
        Returns:
            CrysFMLEoSParams: Fitted parameters
        """
        if not self.fortran_available:
            return self._fit_python_fallback(V_data, P_data, eos_type)
        
        # Ensure correct array types for Fortran
        V_f = np.asfortranarray(V_data, dtype=np.float64)
        P_f = np.asfortranarray(P_data, dtype=np.float64)
        
        # Weights (if not provided, use unit weights)
        if weights is None:
            weights_f = np.ones_like(V_data, dtype=np.float64)
        else:
            weights_f = np.asfortranarray(weights, dtype=np.float64)
        
        # Call Fortran routine (example - actual interface depends on compilation)
        # params_dict = cfml_eos_fortran.eos_fit(
        #     v=V_f, 
        #     p=P_f, 
        #     sig=weights_f, 
        #     imod=eos_type.value
        # )
        
        # Convert Fortran output to Python dataclass
        # params = CrysFMLEoSParams(
        #     imodel=params_dict['imodel'],
        #     V0=params_dict['v0'],
        #     K0=params_dict['k0'],
        #     Kp=params_dict['kp'],
        #     Kpp=params_dict['kpp'],
        #     eV0=params_dict['ev0'],
        #     eK0=params_dict['ek0'],
        #     eKp=params_dict['ekp'],
        #     eKpp=params_dict['ekpp'],
        #     chi2=params_dict['chi2']
        # )
        
        # return params
        
        # Placeholder - implement after Fortran compilation
        raise NotImplementedError("Fortran interface not yet compiled. Use Python fallback.")
    
    def calculate_pressure_fortran(self,
                                   V: np.ndarray,
                                   params: CrysFMLEoSParams) -> np.ndarray:
        """
        Calculate pressure from volume using CrysFML Fortran routine
        
        Calls the Fortran function:
        Function Get_Pressure_EoS(V, Params) Result(P)
        
        Args:
            V: Volume array
            params: EoS parameters
            
        Returns:
            P: Pressure array (GPa)
        """
        if not self.fortran_available:
            return self._calculate_pressure_python_fallback(V, params)
        
        # Ensure correct array type
        V_f = np.asfortranarray(V, dtype=np.float64)
        
        # Call Fortran routine
        # P_f = cfml_eos_fortran.get_pressure_eos(
        #     v=V_f,
        #     v0=params.V0,
        #     k0=params.K0,
        #     kp=params.Kp,
        #     kpp=params.Kpp,
        #     imod=params.imodel
        # )
        
        # return P_f
        
        raise NotImplementedError("Fortran interface not yet compiled. Use Python fallback.")
    
    def _fit_python_fallback(self, V_data, P_data, eos_type):
        """Fallback to Python implementation"""
        from crysfml_eos_module import CrysFMLEoS, EoSType
        
        # Map CrysFMLEoSType to Python EoSType
        type_map = {
            CrysFMLEoSType.MURNAGHAN: EoSType.MURNAGHAN,
            CrysFMLEoSType.BIRCH_MURNAGHAN_3RD: EoSType.BIRCH_MURNAGHAN_3RD,
            CrysFMLEoSType.BIRCH_MURNAGHAN_4TH: EoSType.BIRCH_MURNAGHAN_4TH,
            CrysFMLEoSType.VINET: EoSType.VINET,
            CrysFMLEoSType.NATURAL_STRAIN: EoSType.NATURAL_STRAIN,
        }
        
        fitter = CrysFMLEoS(eos_type=type_map.get(eos_type, EoSType.BIRCH_MURNAGHAN_3RD))
        params_py = fitter.fit(V_data, P_data)
        
        # Convert to CrysFMLEoSParams
        params = CrysFMLEoSParams(
            imodel=eos_type.value,
            V0=params_py.V0,
            K0=params_py.B0,
            Kp=params_py.B0_prime,
            Kpp=getattr(params_py, 'B0_prime2', 0.0),
            eV0=params_py.V0_err,
            eK0=params_py.B0_err,
            eKp=params_py.B0_prime_err,
            eKpp=getattr(params_py, 'B0_prime2_err', 0.0),
            chi2=params_py.chi2
        )
        
        return params
    
    def _calculate_pressure_python_fallback(self, V, params):
        """Fallback pressure calculation"""
        from crysfml_eos_module import CrysFMLEoS, EoSType, EoSParameters
        
        # Determine EoS type
        if params.imodel == 1:
            eos_type = EoSType.MURNAGHAN
        elif params.imodel == 2:
            eos_type = EoSType.BIRCH_MURNAGHAN_3RD
        elif params.imodel == 4:
            eos_type = EoSType.VINET
        else:
            eos_type = EoSType.BIRCH_MURNAGHAN_3RD
        
        fitter = CrysFMLEoS(eos_type=eos_type)
        
        # Convert to Python EoSParameters
        params_py = EoSParameters(eos_type=eos_type)
        params_py.V0 = params.V0
        params_py.B0 = params.K0
        params_py.B0_prime = params.Kp
        params_py.B0_prime2 = params.Kpp
        
        return fitter.calculate_pressure(V, params_py)


def compile_fortran_module():
    """
    Helper function to compile CrysFML Fortran module using f2py
    
    This function generates the compilation command for f2py.
    Run this after obtaining the CFML_EoS_Mod.f90 file.
    
    Steps:
    1. Download CFML_EoS_Mod.f90 from CrysFML repository
    2. Run this function to get compilation command
    3. Execute the command in terminal
    4. Import the compiled module
    """
    
    print("="*70)
    print("CrysFML Fortran Module Compilation Guide")
    print("="*70)
    print()
    print("Step 1: Obtain CrysFML source code")
    print("---------------------------------------")
    print("Download from:")
    print("  https://gitlab.com/CrysFML/CrysFML2008")
    print("or")
    print("  https://www.ill.eu/sites/crystallography/crysfml/")
    print()
    print("File needed: Src/CFML_EoS_Mod.f90")
    print()
    
    print("Step 2: Compile with f2py")
    print("---------------------------------------")
    print("Basic compilation command:")
    print()
    print("  python3 -m numpy.f2py -c CFML_EoS_Mod.f90 -m cfml_eos_fortran")
    print()
    print("With optimization:")
    print()
    print("  python3 -m numpy.f2py -c CFML_EoS_Mod.f90 -m cfml_eos_fortran \\")
    print("    --f90flags='-O3 -march=native'")
    print()
    
    print("Step 3: Test the compiled module")
    print("---------------------------------------")
    print("  python3 -c 'import cfml_eos_fortran; print(cfml_eos_fortran.__doc__)'")
    print()
    
    print("Step 4: Verify integration")
    print("---------------------------------------")
    print("  python3 test_crysfml_fortran.py")
    print()
    print("="*70)
    print()
    print("Note: If compilation fails, you may need to:")
    print("  - Install gfortran: sudo apt install gfortran")
    print("  - Install numpy with f2py: pip install numpy")
    print("  - Resolve Fortran dependencies in CFML_EoS_Mod.f90")
    print()


if __name__ == "__main__":
    print("CrysFML Fortran Wrapper")
    print("="*70)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "compile":
        compile_fortran_module()
    else:
        print("This module provides Python interface to CrysFML Fortran EoS routines.")
        print()
        print("Usage:")
        print("  1. Get compilation instructions:")
        print("     python3 crysfml_fortran_wrapper.py compile")
        print()
        print("  2. Use in Python code:")
        print("     from crysfml_fortran_wrapper import CrysFMLFortranWrapper")
        print("     wrapper = CrysFMLFortranWrapper()")
        print("     params = wrapper.fit_eos_fortran(V_data, P_data)")
        print()
        print("Current status:")
        print(f"  Fortran module available: {FORTRAN_AVAILABLE}")
        print(f"  Python fallback available: True")
        print()
        
        if not FORTRAN_AVAILABLE:
            print("⚠️  Fortran module not compiled. Using Python fallback.")
            print("   Run 'python3 crysfml_fortran_wrapper.py compile' for instructions.")
