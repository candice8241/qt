#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Half-Auto Peak Fitting GUI - Qt Version

This module provides backward compatibility by importing the new InteractiveFittingGUI.
The original PeakFittingGUI class is maintained for compatibility.

@author: candicewang928@gmail.com
"""

from interactive_fitting_gui import InteractiveFittingGUI


# Maintain backward compatibility
class PeakFittingGUI(InteractiveFittingGUI):
    """Peak fitting GUI - Qt version (alias for InteractiveFittingGUI)"""
    
    def __init__(self, parent=None):
        """Initialize peak fitting GUI"""
        super().__init__(parent)
        self.setWindowTitle("Half-Auto Peak Fitting GUI")


# Placeholder for DataProcessor class
class DataProcessor:
    """Placeholder for data processing functionality"""

    def __init__(self, *args, **kwargs):
        pass

    def process(self, *args, **kwargs):
        raise NotImplementedError("DataProcessor not yet implemented in Qt version")