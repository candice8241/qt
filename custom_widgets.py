# -*- coding: utf-8 -*-
"""
Custom Widgets for XRD Application
Contains custom spinbox and other specialized widgets

Created: 2025
@author: candicewang928@gmail.com
"""

from PyQt6.QtWidgets import QWidget, QPushButton, QLineEdit, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class CustomSpinbox(QWidget):
    """Custom spinbox widget with +/- buttons"""
    
    valueChanged = pyqtSignal(float)
    
    def __init__(self, from_=0, to=100, value=0, increment=1, width=120, 
                 is_float=False, parent=None):
        super().__init__(parent)
        self.from_value = from_
        self.to_value = to
        self.current_value = value
        self.increment = increment
        self.is_float = is_float
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        
        # Minus button
        self.minus_btn = QPushButton("<")
        self.minus_btn.setFixedSize(30, 28)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8E4F3;
                border: 1px solid #E8E4F3;
                border-radius: 3px;
                color: #2B2D42;
            }
            QPushButton:hover { background-color: #E6D9F5; }
        """)
        self.minus_btn.clicked.connect(self.decrement)
        layout.addWidget(self.minus_btn)
        
        # Value entry
        self.entry = QLineEdit(str(value))
        self.entry.setFixedWidth(width - 66)  # Account for buttons
        self.entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry.setFont(QFont('Arial', 9))
        self.entry.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: #2B2D42;
                border: 1px solid #E8E4F3;
                padding: 3px;
            }
        """)
        self.entry.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.entry)
        
        # Plus button
        self.plus_btn = QPushButton(">")
        self.plus_btn.setFixedSize(30, 28)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8E4F3;
                border: 1px solid #E8E4F3;
                border-radius: 3px;
                color: #2B2D42;
            }
            QPushButton:hover { background-color: #E6D9F5; }
        """)
        self.plus_btn.clicked.connect(self.increment_value)
        layout.addWidget(self.plus_btn)
        
        self.setFixedWidth(width)
    
    def increment_value(self):
        """Increment the value"""
        new_value = self.current_value + self.increment
        if new_value <= self.to_value:
            self.set_value(new_value)
    
    def decrement(self):
        """Decrement the value"""
        new_value = self.current_value - self.increment
        if new_value >= self.from_value:
            self.set_value(new_value)
    
    def set_value(self, value):
        """Set the spinbox value"""
        value = max(self.from_value, min(self.to_value, value))
        self.current_value = value
        if self.is_float:
            self.entry.setText(f"{value:.1f}")
        else:
            self.entry.setText(str(int(value)))
        self.valueChanged.emit(value)
    
    def on_text_changed(self, text):
        """Handle manual text entry"""
        try:
            if self.is_float:
                value = float(text)
            else:
                value = int(text)
            value = max(self.from_value, min(self.to_value, value))
            self.current_value = value
            self.valueChanged.emit(value)
        except ValueError:
            pass
    
    def value(self):
        """Get current value"""
        return self.current_value


class SpinboxStyleButton(QPushButton):
    """Button styled to match spinbox appearance"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(30, 28)
        self.setStyleSheet("""
            QPushButton {
                background-color: #E8E4F3;
                border: 1px solid #E8E4F3;
                border-radius: 3px;
                color: #2B2D42;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E6D9F5; }
            QPushButton:pressed { background-color: #C8B3E6; }
        """)