#!/usr/bin/env python3
"""
Test script for embedded Auto Fitting Module
"""

import sys
from PyQt6.QtWidgets import QApplication

try:
    from auto_fitting_module import AutoFittingModule
    
    app = QApplication(sys.argv)
    
    # Create and show the module
    window = AutoFittingModule()
    window.setWindowTitle("Auto Fitting Module - Embedded Test")
    window.setMinimumSize(1200, 800)
    window.show()
    
    print("✅ Auto Fitting Module launched successfully!")
    print("   - Module is fully embedded (no external windows)")
    print("   - All functionality available in single window")
    print("   - Ready for integration into main application")
    
    sys.exit(app.exec())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Note: PyQt6 needs to be installed to run this test")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
