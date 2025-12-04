#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: Using the Simplified Lattice Parameter Calculator

This example demonstrates how to use the new simplified interface
for calculating lattice parameters from XRD peak positions.
"""

from batch_cal_volume import LatticeParameterCalculator

def example_1_interactive():
    """Example 1: Interactive mode - prompts for crystal system"""
    print("\n" + "="*70)
    print("Example 1: Interactive Mode")
    print("="*70)
    
    # Create calculator instance
    calculator = LatticeParameterCalculator(wavelength=0.4133)
    
    # The calculate method will prompt you to select crystal system
    csv_path = 'your_peaks.csv'  # Replace with your actual CSV file
    
    # Uncomment to run:
    # results = calculator.calculate(csv_path)
    
    print("\n✓ In interactive mode, you will be prompted to select crystal system")
    print("  Results will be saved to: your_peaks_lattice_results.csv")


def example_2_programmatic():
    """Example 2: Programmatic mode - specify crystal system directly"""
    print("\n" + "="*70)
    print("Example 2: Programmatic Mode")
    print("="*70)
    
    # Create calculator instance
    calculator = LatticeParameterCalculator(wavelength=0.4133)
    
    # Specify crystal system directly
    csv_path = 'your_peaks.csv'  # Replace with your actual CSV file
    crystal_system = 'cubic_FCC'  # Options: cubic_FCC, cubic_BCC, cubic_SC, 
                                   #          Hexagonal, Tetragonal, Orthorhombic
    
    # Uncomment to run:
    # results = calculator.calculate(csv_path, crystal_system_key=crystal_system)
    
    print(f"\n✓ Crystal system: {crystal_system}")
    print("  Results will be saved to: your_peaks_lattice_results.csv")
    print("\n  Results dictionary contains:")
    print("    - Pressure (GPa)")
    print("    - Lattice parameters (a, b, c)")
    print("    - Cell volume (V_cell)")
    print("    - Atomic volume (V_atomic)")
    print("    - Number of peaks used")


def example_3_multiple_phases():
    """Example 3: Calculate parameters for multiple phases separately"""
    print("\n" + "="*70)
    print("Example 3: Multiple Phases (Manual Separation)")
    print("="*70)
    
    calculator = LatticeParameterCalculator(wavelength=0.4133)
    
    # Process original phase
    print("\n1. Original Phase:")
    original_csv = 'original_phase_peaks.csv'
    original_system = 'cubic_FCC'
    # results_original = calculator.calculate(original_csv, original_system)
    print(f"   ✓ System: {original_system}")
    print(f"   ✓ Results saved to: {original_csv.replace('.csv', '_lattice_results.csv')}")
    
    # Process new phase
    print("\n2. New Phase:")
    new_csv = 'new_phase_peaks.csv'
    new_system = 'Hexagonal'
    # results_new = calculator.calculate(new_csv, new_system)
    print(f"   ✓ System: {new_system}")
    print(f"   ✓ Results saved to: {new_csv.replace('.csv', '_lattice_results.csv')}")
    
    print("\n⚠️  Note: You must manually separate peaks before using this tool")


def example_4_csv_format():
    """Example 4: Show expected CSV format"""
    print("\n" + "="*70)
    print("Example 4: Expected CSV File Format")
    print("="*70)
    
    print("\nYour CSV file should look like this:")
    print("\n" + "-"*40)
    print("File,Center")
    print("10.0,8.5")
    print("10.0,9.2")
    print("10.0,12.3")
    print("")  # Empty row separates pressure points
    print("20.0,8.6")
    print("20.0,9.3")
    print("20.0,12.4")
    print("")
    print("30.0,8.7")
    print("30.0,9.4")
    print("-"*40)
    
    print("\nColumn descriptions:")
    print("  - 'File': Pressure value (GPa)")
    print("  - 'Center': Peak position (2theta in degrees)")
    print("  - Empty rows separate different pressure points")


def show_available_crystal_systems():
    """Show all available crystal systems"""
    print("\n" + "="*70)
    print("Available Crystal Systems")
    print("="*70)
    
    systems = {
        'cubic_FCC': 'Face-Centered Cubic (FCC) - min 1 peak',
        'cubic_BCC': 'Body-Centered Cubic (BCC) - min 1 peak',
        'cubic_SC': 'Simple Cubic (SC) - min 1 peak',
        'Hexagonal': 'Hexagonal Close-Packed (HCP) - min 2 peaks',
        'Tetragonal': 'Tetragonal - min 2 peaks',
        'Orthorhombic': 'Orthorhombic - min 3 peaks',
        'Monoclinic': 'Monoclinic - min 4 peaks',
        'Triclinic': 'Triclinic - min 6 peaks',
    }
    
    print("\nCrystal System Keys:")
    for key, description in systems.items():
        print(f"  • {key:20s} - {description}")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("Lattice Parameter Calculator - Usage Examples")
    print("="*70)
    
    # Show available crystal systems
    show_available_crystal_systems()
    
    # Show examples
    example_1_interactive()
    example_2_programmatic()
    example_3_multiple_phases()
    example_4_csv_format()
    
    print("\n" + "="*70)
    print("📚 For more details, see: BATCH_CAL_VOLUME_CHANGES.md")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
