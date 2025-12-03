#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone Batch Peak Fitting Module

This module provides a standalone interface for batch peak fitting without 
requiring the curvefit (interactive_fitting_gui.py) interface.

@author: candicewang928@gmail.com
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from batch_fitting_dialog import BatchFittingDialog


class BatchFittingModule(QMainWindow):
    """Standalone Batch Fitting Module"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Batch Peak Fitting Module")
        self.setMinimumWidth(1600)
        self.setMinimumHeight(900)
        
        # Set window to center of screen
        self.center_window()
        
        # Create and show batch fitting dialog
        self.batch_dialog = BatchFittingDialog(self)
        
        # Set the dialog as the central widget
        self.setCentralWidget(self.batch_dialog)
        
    def center_window(self):
        """Center the window on screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)


def main():
    """Main function to run the standalone batch fitting module"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Set application font
    font = QFont('Arial', 10)
    app.setFont(font)
    
    # Create and show the main window
    window = BatchFittingModule()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
