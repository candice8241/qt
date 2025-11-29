#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for colorful curve fitting GUI
"""

import sys
from PyQt6.QtWidgets import QApplication
from interactive_fitting_gui import InteractiveFittingGUI

def main():
    """Test the colorful GUI"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show window
    window = InteractiveFittingGUI()
    window.setWindowTitle("Interactive XRD Peak Fitting Tool - Enhanced")
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
