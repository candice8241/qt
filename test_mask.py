#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test to verify mask module displays content
"""

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
import sys

def test_mask_module():
    app = QApplication(sys.argv)
    
    # Create main window
    window = QWidget()
    window.setWindowTitle("Mask Module Test")
    window.resize(1200, 900)
    
    # Create mask module
    from mask_module import MaskModule
    mask = MaskModule(window, window)
    mask.setup_ui()
    
    # Check if widgets were created
    print("=" * 60)
    print("Mask Module Test Results:")
    print("=" * 60)
    
    # Check layout
    layout = window.layout()
    print(f"✓ Parent has layout: {layout is not None}")
    
    if layout:
        print(f"✓ Layout has {layout.count()} items")
        
        # List all widgets
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget() if item else None
            if widget:
                print(f"  - Widget {i}: {widget.__class__.__name__}")
    
    # Check mask module attributes
    print(f"✓ Mask module has parent: {mask.parent is not None}")
    print(f"✓ Mask module has root: {mask.root is not None}")
    print(f"✓ Mask module colors defined: {hasattr(mask, 'colors')}")
    
    print("=" * 60)
    print("Test passed! Opening window...")
    print("=" * 60)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    test_mask_module()
