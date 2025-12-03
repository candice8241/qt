#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the full Qt6 auto_fitting_module (1:1 restoration)
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

try:
    from auto_fitting_module import AutoFittingModule
    print("✓ Successfully imported AutoFittingModule")
except ImportError as e:
    print(f"✗ Failed to import AutoFittingModule: {e}")
    sys.exit(1)

def test_module():
    """Test the auto fitting module"""
    print("\n" + "="*60)
    print("Testing Auto Fitting Module - Full Version")
    print("="*60)
    
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Auto Fitting Module - Full Qt6 Version Test")
    window.setGeometry(100, 100, 1400, 900)
    
    # Create central widget
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Create and add auto fitting module
    auto_fitting = AutoFittingModule()
    layout.addWidget(auto_fitting)
    
    window.setCentralWidget(central_widget)
    
    # Check for all UI components
    print("\nChecking UI Components:")
    print("-" * 60)
    
    components_to_check = [
        ('btn_load', 'Load File button'),
        ('btn_prev', 'Previous File button'),
        ('btn_next', 'Next File button'),
        ('btn_auto_find', 'Auto Find button'),
        ('btn_fit', 'Fit Peaks button'),
        ('btn_clear_fit', 'Clear Fit button'),
        ('btn_undo', 'Undo button'),
        ('btn_reset', 'Reset button'),
        ('btn_save', 'Save button'),
        ('btn_overlap', 'Overlap button'),
        ('btn_batch_auto', 'Batch Auto Fit button'),
        ('btn_batch_settings', 'Batch Settings button'),
        ('btn_select_bg', 'Select BG Points button'),
        ('btn_subtract_bg', 'Subtract BG button'),
        ('btn_clear_bg', 'Clear BG button'),
        ('btn_auto_bg', 'Auto Select BG button'),
        ('btn_apply_smooth', 'Apply Smoothing button'),
        ('btn_reset_smooth', 'Reset Data button'),
        ('combo_fit_method', 'Fit Method combobox'),
        ('combo_smooth_method', 'Smooth Method combobox'),
        ('overlap_threshold_input', 'Overlap Threshold input'),
        ('fitting_window_input', 'Fitting Window input'),
        ('smooth_sigma_input', 'Smooth Sigma input'),
        ('smooth_window_input', 'Smooth Window input'),
        ('chk_smooth', 'Enable Smoothing checkbox'),
        ('canvas', 'Matplotlib canvas'),
        ('results_table', 'Results table'),
        ('info_text', 'Info text area'),
        ('status_label', 'Status label'),
    ]
    
    missing = []
    present = []
    
    for attr_name, description in components_to_check:
        if hasattr(auto_fitting, attr_name):
            present.append(description)
            print(f"  ✓ {description}")
        else:
            missing.append(description)
            print(f"  ✗ {description}")
    
    print("\n" + "="*60)
    print(f"Summary: {len(present)}/{len(components_to_check)} components present")
    
    if missing:
        print(f"\nMissing components ({len(missing)}):")
        for item in missing:
            print(f"  • {item}")
    else:
        print("\n✓ All components present!")
    
    # Check for all methods
    print("\n" + "="*60)
    print("Checking Methods:")
    print("-" * 60)
    
    methods_to_check = [
        'load_file',
        'auto_find_peaks',
        'fit_peaks',
        'reset_peaks',
        'save_results',
        'clear_fit',
        'undo_action',
        'toggle_bg_selection',
        'auto_select_background',
        'subtract_background',
        'clear_background',
        'apply_smoothing_to_data',
        'reset_to_original_data',
        'toggle_overlap_mode',
        'batch_auto_fit',
        'show_batch_settings',
        'prev_file',
        'next_file',
    ]
    
    missing_methods = []
    present_methods = []
    
    for method_name in methods_to_check:
        if hasattr(auto_fitting, method_name) and callable(getattr(auto_fitting, method_name)):
            present_methods.append(method_name)
            print(f"  ✓ {method_name}()")
        else:
            missing_methods.append(method_name)
            print(f"  ✗ {method_name}()")
    
    print("\n" + "="*60)
    print(f"Summary: {len(present_methods)}/{len(methods_to_check)} methods present")
    
    if missing_methods:
        print(f"\nMissing methods ({len(missing_methods)}):")
        for method in missing_methods:
            print(f"  • {method}()")
    else:
        print("\n✓ All methods present!")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)
    print("\nThe window will now be displayed.")
    print("Try loading a data file to test all functionality.")
    print("\nFeatures to test:")
    print("  1. Load File")
    print("  2. Auto Find Peaks")
    print("  3. Manual Peak Selection (click on plot)")
    print("  4. Background Selection (Select BG Points, Auto Select BG, Subtract BG)")
    print("  5. Smoothing (Enable, Method, Apply, Reset)")
    print("  6. Overlap Mode")
    print("  7. Fit Peaks")
    print("  8. Save Results")
    print("  9. Batch Auto Fit")
    print(" 10. Batch Settings")
    print("\n")
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    test_module()
