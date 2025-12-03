#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bin Mode Configuration Dialog
Dialog for configuring azimuthal binning
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QSpinBox, QGroupBox,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import numpy as np


class BinConfigDialog(QDialog):
    """Bin Mode Configuration Dialog"""
    
    # Signal: configuration completed, returns bin list
    bins_configured = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bin Mode Configuration")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        # Color theme
        self.colors = {
            'primary': '#7C4DFF',
            'background': '#F5F5F5',
            'card_bg': '#FFFFFF',
            'border': '#E0E0E0',
            'text_dark': '#333333'
        }
        
        # Data storage
        self.bins = []  # List of dicts: {'start': float, 'end': float, 'name': str}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Azimuthal Bin Configuration")
        title.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['primary']};")
        layout.addWidget(title)
        
        # Quick generate group
        quick_group = self.create_quick_generate_group()
        layout.addWidget(quick_group)
        
        # Bin list group
        list_group = self.create_bin_list_group()
        layout.addWidget(list_group)
        
        # Manual add group
        manual_group = self.create_manual_add_group()
        layout.addWidget(manual_group)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedWidth(100)
        clear_btn.setFixedHeight(32)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF5252;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #FF1744;
            }}
        """)
        clear_btn.clicked.connect(self.clear_bins)
        button_layout.addWidget(clear_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setFixedHeight(32)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #BDBDBD;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #9E9E9E;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(100)
        ok_btn.setFixedHeight(32)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #6A1B9A;
            }}
        """)
        ok_btn.clicked.connect(self.accept_config)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def create_quick_generate_group(self):
        """Create quick generate group"""
        group = QGroupBox("Quick Generate")
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 8px;
                font-weight: bold;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Parameter row
        param_layout = QHBoxLayout()
        param_layout.setSpacing(8)
        
        # Start angle
        start_label = QLabel("Start:")
        start_label.setFont(QFont('Arial', 9))
        param_layout.addWidget(start_label)
        self.quick_start = QLineEdit("0")
        self.quick_start.setFixedWidth(70)
        self.quick_start.setFixedHeight(26)
        self.quick_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        param_layout.addWidget(self.quick_start)
        
        # End angle
        end_label = QLabel("End:")
        end_label.setFont(QFont('Arial', 9))
        param_layout.addWidget(end_label)
        self.quick_end = QLineEdit("360")
        self.quick_end.setFixedWidth(70)
        self.quick_end.setFixedHeight(26)
        self.quick_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        param_layout.addWidget(self.quick_end)
        
        # Number of bins
        bins_label = QLabel("Bins:")
        bins_label.setFont(QFont('Arial', 9))
        param_layout.addWidget(bins_label)
        self.quick_num_bins = QSpinBox()
        self.quick_num_bins.setRange(1, 360)
        self.quick_num_bins.setValue(36)
        self.quick_num_bins.setFixedWidth(70)
        self.quick_num_bins.setFixedHeight(26)
        param_layout.addWidget(self.quick_num_bins)
        
        # Generate button
        gen_btn = QPushButton("Generate")
        gen_btn.setFixedHeight(26)
        gen_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 4px 15px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #6A1B9A;
            }}
        """)
        gen_btn.clicked.connect(self.quick_generate)
        param_layout.addWidget(gen_btn)
        
        param_layout.addStretch()
        
        layout.addLayout(param_layout)
        
        return group
    
    def create_bin_list_group(self):
        """Create bin list group"""
        group = QGroupBox("Bin List")
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 8px;
                font-weight: bold;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Table
        self.bin_table = QTableWidget()
        self.bin_table.setColumnCount(4)
        self.bin_table.setHorizontalHeaderLabels(["Bin Name", "Start (°)", "End (°)", "Action"])
        self.bin_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.bin_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.bin_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.bin_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.bin_table.setColumnWidth(1, 100)
        self.bin_table.setColumnWidth(2, 100)
        self.bin_table.setColumnWidth(3, 80)
        self.bin_table.setMinimumHeight(180)
        
        layout.addWidget(self.bin_table)
        
        return group
    
    def create_manual_add_group(self):
        """Create manual add group"""
        group = QGroupBox("Manual Add")
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 8px;
                font-weight: bold;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        
        layout = QHBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Name
        name_label = QLabel("Name:")
        name_label.setFont(QFont('Arial', 9))
        layout.addWidget(name_label)
        self.manual_name = QLineEdit()
        self.manual_name.setPlaceholderText("e.g., Bin01")
        self.manual_name.setFixedWidth(100)
        self.manual_name.setFixedHeight(26)
        layout.addWidget(self.manual_name)
        
        # Start
        start_label = QLabel("Start:")
        start_label.setFont(QFont('Arial', 9))
        layout.addWidget(start_label)
        self.manual_start = QLineEdit("0")
        self.manual_start.setFixedWidth(70)
        self.manual_start.setFixedHeight(26)
        self.manual_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.manual_start)
        
        # End
        end_label = QLabel("End:")
        end_label.setFont(QFont('Arial', 9))
        layout.addWidget(end_label)
        self.manual_end = QLineEdit("10")
        self.manual_end.setFixedWidth(70)
        self.manual_end.setFixedHeight(26)
        self.manual_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.manual_end)
        
        # Add button
        add_btn = QPushButton("Add")
        add_btn.setFixedHeight(26)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 15px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #45A049;
            }}
        """)
        add_btn.clicked.connect(self.manual_add)
        layout.addWidget(add_btn)
        
        layout.addStretch()
        
        return group
    
    def quick_generate(self):
        """Quickly generate bins"""
        try:
            start = float(self.quick_start.text())
            end = float(self.quick_end.text())
            num_bins = self.quick_num_bins.value()
            
            if start >= end:
                QMessageBox.warning(self, "Error", "Start angle must be less than end angle")
                return
            
            if num_bins < 1:
                QMessageBox.warning(self, "Error", "Number of bins must be at least 1")
                return
            
            # Clear existing bins
            self.bins = []
            
            # Generate bins
            bin_width = (end - start) / num_bins
            for i in range(num_bins):
                bin_start = start + i * bin_width
                bin_end = start + (i + 1) * bin_width
                bin_name = f"Bin{i+1:03d}"
                
                self.bins.append({
                    'name': bin_name,
                    'start': bin_start,
                    'end': bin_end
                })
            
            self.update_table()
            
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Invalid input: {str(e)}")
    
    def manual_add(self):
        """Manually add a bin"""
        try:
            name = self.manual_name.text().strip()
            if not name:
                name = f"Bin{len(self.bins)+1:03d}"
            
            start = float(self.manual_start.text())
            end = float(self.manual_end.text())
            
            if start >= end:
                QMessageBox.warning(self, "Error", "Start angle must be less than end angle")
                return
            
            self.bins.append({
                'name': name,
                'start': start,
                'end': end
            })
            
            self.update_table()
            
            # Clear input fields
            self.manual_name.clear()
            
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Invalid input: {str(e)}")
    
    def update_table(self):
        """Update table display"""
        self.bin_table.setRowCount(len(self.bins))
        
        for i, bin_data in enumerate(self.bins):
            # Name
            name_item = QTableWidgetItem(bin_data['name'])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bin_table.setItem(i, 0, name_item)
            
            # Start
            start_item = QTableWidgetItem(f"{bin_data['start']:.2f}")
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bin_table.setItem(i, 1, start_item)
            
            # End
            end_item = QTableWidgetItem(f"{bin_data['end']:.2f}")
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bin_table.setItem(i, 2, end_item)
            
            # Delete button
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF5252;
                    color: white;
                    border: none;
                    padding: 3px 8px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #FF1744;
                }
            """)
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_bin(idx))
            self.bin_table.setCellWidget(i, 3, delete_btn)
    
    def delete_bin(self, index):
        """Delete a bin"""
        if 0 <= index < len(self.bins):
            del self.bins[index]
            self.update_table()
    
    def clear_bins(self):
        """Clear all bins"""
        reply = QMessageBox.question(
            self, 'Confirm', 'Clear all bins?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.bins = []
            self.update_table()
    
    def accept_config(self):
        """Accept configuration"""
        if not self.bins:
            QMessageBox.warning(self, "Error", "Please add at least one bin")
            return
        
        self.bins_configured.emit(self.bins)
        self.accept()
    
    def get_bins(self):
        """Get bins list"""
        return self.bins


# Test code
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    dialog = BinConfigDialog()
    
    def on_configured(bins):
        print("Configured bins:")
        for bin_data in bins:
            print(f"  {bin_data['name']}: {bin_data['start']}° - {bin_data['end']}°")
    
    dialog.bins_configured.connect(on_configured)
    
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:
        print(f"Total bins: {len(dialog.get_bins())}")
    else:
        print("Cancelled")
    
    sys.exit(0)