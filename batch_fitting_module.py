#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch Fitting Module - Standalone Module for Batch Peak Fitting
Extracted from interactive_fitting_gui.py batch functionality
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from batch_fitting_dialog import BatchFittingDialog


class BatchFittingModule(QWidget):
    """Batch Fitting Module - Direct embedding of batch fitting dialog"""
    
    def __init__(self, parent_frame=None, main_window=None):
        super().__init__(parent_frame)
        self.main_window = main_window
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create and embed the batch fitting dialog as a widget (not as modal dialog)
        self.batch_dialog = BatchFittingDialog(parent=None)
        
        # Remove dialog window flags to make it embeddable
        self.batch_dialog.setWindowFlags(self.batch_dialog.windowFlags() & ~Qt.WindowType.Dialog)
        
        # Add to layout
        layout.addWidget(self.batch_dialog)
    
    def setup_ui(self):
        """Setup UI - required by main.py module pattern"""
        # UI is already setup in __init__
        pass
