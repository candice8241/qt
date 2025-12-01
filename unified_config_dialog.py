#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unified Configuration Dialog
Unified dialog for configuring single and multiple sectors
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QSpinBox, QGroupBox,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QTabWidget, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import numpy as np


class UnifiedConfigDialog(QDialog):
    """Unified Configuration Dialog - Single and Multiple Sectors"""
    
    # Signal: configuration completed, returns bins and sectors lists
    config_completed = pyqtSignal(list, list)  # (bins, sectors)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Azimuthal Configuration")
        self.setModal(True)
        self.setMinimumSize(750, 650)
        
        # Color theme
        self.colors = {
            'primary': '#7C4DFF',
            'background': '#F5F5F5',
            'card_bg': '#FFFFFF',
            'border': '#E0E0E0',
            'text_dark': '#333333'
        }
        
        # Data storage
        self.bins = []  # List of dicts: {'name': str, 'start': float, 'end': float, 'rad_min': float, 'rad_max': float}
        self.sectors = []  # List of dicts: {'name': str, 'azim_start': float, 'azim_end': float, 'rad_min': float, 'rad_max': float}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Azimuthal Configuration")
        title.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['primary']};")
        layout.addWidget(title)
        
        desc = QLabel("Configure single or multiple sectors for azimuthal integration")
        desc.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(desc)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: #E0E0E0;
                color: {self.colors['text_dark']};
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.colors['primary']};
                color: white;
                font-weight: bold;
            }}
        """)
        
        # Single Sector tab (formerly Bins)
        bins_tab = self.create_bins_tab()
        self.tab_widget.addTab(bins_tab, "Single Sector")
        
        # Multiple Sectors tab
        sectors_tab = self.create_sectors_tab()
        self.tab_widget.addTab(sectors_tab, "Multiple Sectors")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        clear_btn = QPushButton("Clear Current Tab")
        clear_btn.setFixedWidth(130)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF5252;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FF1744;
            }}
        """)
        clear_btn.clicked.connect(self.clear_current_tab)
        button_layout.addWidget(clear_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #BDBDBD;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #9E9E9E;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(100)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #6A1B9A;
            }}
        """)
        ok_btn.clicked.connect(self.accept_config)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def create_bins_tab(self):
        """Create Single Sector tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Quick generate group
        quick_group = self.create_bins_quick_generate_group()
        layout.addWidget(quick_group)
        
        # Sector list
        list_group = self.create_bins_list_group()
        layout.addWidget(list_group)
        
        # Manual add group
        manual_group = self.create_bins_manual_add_group()
        layout.addWidget(manual_group)
        
        return tab
    
    def create_sectors_tab(self):
        """Create Multiple Sectors tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Sector list
        list_group = self.create_sectors_list_group()
        layout.addWidget(list_group)
        
        # Add sector group
        add_group = self.create_sectors_add_group()
        layout.addWidget(add_group)
        
        # Quick presets
        preset_group = self.create_sectors_preset_group()
        layout.addWidget(preset_group)
        
        return tab
    
    # ==================== Single Sector Tab Components ====================
    
    def create_bins_quick_generate_group(self):
        """Create quick generate group for single sectors"""
        group = QGroupBox("Quick Generate")
        group.setStyleSheet(self._group_style())
        
        layout = QVBoxLayout(group)
        
        # Row 1: Azimuthal parameters
        param_layout = QHBoxLayout()
        
        # Start angle
        param_layout.addWidget(QLabel("Azim Start:"))
        self.bins_quick_start = QLineEdit("0")
        self.bins_quick_start.setFixedWidth(70)
        self.bins_quick_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bins_quick_start.textChanged.connect(self.update_bins_count)
        param_layout.addWidget(self.bins_quick_start)
        
        # End angle
        param_layout.addWidget(QLabel("End:"))
        self.bins_quick_end = QLineEdit("360")
        self.bins_quick_end.setFixedWidth(70)
        self.bins_quick_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bins_quick_end.textChanged.connect(self.update_bins_count)
        param_layout.addWidget(self.bins_quick_end)
        
        # Bin size
        param_layout.addWidget(QLabel("Bin Size:"))
        self.bins_quick_size = QLineEdit("10")
        self.bins_quick_size.setFixedWidth(70)
        self.bins_quick_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bins_quick_size.textChanged.connect(self.update_bins_count)
        param_layout.addWidget(self.bins_quick_size)
        param_layout.addWidget(QLabel("°"))
        
        # Bins count display
        self.bins_count_label = QLabel("→ 36 bins")
        self.bins_count_label.setStyleSheet("color: #666666; font-weight: bold;")
        param_layout.addWidget(self.bins_count_label)
        
        param_layout.addStretch()
        layout.addLayout(param_layout)
        
        # Row 2: Radial parameters
        rad_layout = QHBoxLayout()
        
        rad_label = QLabel("Radial Range (px):")
        rad_label.setToolTip("Radial range in pixels (0 = auto)")
        rad_layout.addWidget(rad_label)
        
        self.bins_quick_rad_min = QLineEdit("0")
        self.bins_quick_rad_min.setFixedWidth(70)
        self.bins_quick_rad_min.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bins_quick_rad_min.setToolTip("Minimum radial value (pixels)")
        rad_layout.addWidget(self.bins_quick_rad_min)
        
        rad_layout.addWidget(QLabel("to"))
        self.bins_quick_rad_max = QLineEdit("0")
        self.bins_quick_rad_max.setFixedWidth(70)
        self.bins_quick_rad_max.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bins_quick_rad_max.setToolTip("Maximum radial value (0 = auto)")
        rad_layout.addWidget(self.bins_quick_rad_max)
        
        auto_label = QLabel("(0 = auto)")
        auto_label.setStyleSheet("color: #999999; font-size: 10px;")
        rad_layout.addWidget(auto_label)
        
        # Generate button
        gen_btn = QPushButton("Generate")
        gen_btn.setStyleSheet(self._action_btn_style())
        gen_btn.clicked.connect(self.bins_quick_generate)
        rad_layout.addWidget(gen_btn)
        
        rad_layout.addStretch()
        layout.addLayout(rad_layout)
        
        return group
    
    def create_bins_list_group(self):
        """Create single sector list group"""
        group = QGroupBox("Sector List")
        group.setStyleSheet(self._group_style())
        
        layout = QVBoxLayout(group)
        
        # Table
        self.bins_table = QTableWidget()
        self.bins_table.setColumnCount(6)
        self.bins_table.setHorizontalHeaderLabels([
            "Name", "Azim Start (°)", "Azim End (°)", 
            "Rad Min (px)", "Rad Max (px)", "Action"
        ])
        header = self.bins_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        
        self.bins_table.setColumnWidth(1, 110)
        self.bins_table.setColumnWidth(2, 110)
        self.bins_table.setColumnWidth(3, 100)
        self.bins_table.setColumnWidth(4, 100)
        self.bins_table.setColumnWidth(5, 80)
        self.bins_table.setMinimumHeight(180)
        
        layout.addWidget(self.bins_table)
        
        return group
    
    def create_bins_manual_add_group(self):
        """Create manual add group for single sectors"""
        group = QGroupBox("Manual Add")
        group.setStyleSheet(self._group_style())
        
        layout = QVBoxLayout(group)
        
        # Row 1: Name and Azimuthal range
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("Name:"))
        self.bins_manual_name = QLineEdit()
        self.bins_manual_name.setPlaceholderText("e.g., Sector01")
        self.bins_manual_name.setFixedWidth(100)
        row1.addWidget(self.bins_manual_name)
        
        row1.addWidget(QLabel("Azimuthal:"))
        self.bins_manual_start = QLineEdit("0")
        self.bins_manual_start.setFixedWidth(70)
        self.bins_manual_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self.bins_manual_start)
        
        row1.addWidget(QLabel("to"))
        self.bins_manual_end = QLineEdit("10")
        self.bins_manual_end.setFixedWidth(70)
        self.bins_manual_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self.bins_manual_end)
        row1.addWidget(QLabel("°"))
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # Row 2: Radial range
        row2 = QHBoxLayout()
        
        rad_label = QLabel("Radial Range (px):")
        rad_label.setToolTip("Radial range in pixels (0 = auto)")
        row2.addWidget(rad_label)
        
        self.bins_manual_rad_min = QLineEdit("0")
        self.bins_manual_rad_min.setFixedWidth(70)
        self.bins_manual_rad_min.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bins_manual_rad_min.setToolTip("Minimum radial value (pixels)")
        row2.addWidget(self.bins_manual_rad_min)
        
        row2.addWidget(QLabel("to"))
        self.bins_manual_rad_max = QLineEdit("0")
        self.bins_manual_rad_max.setFixedWidth(70)
        self.bins_manual_rad_max.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bins_manual_rad_max.setToolTip("Maximum radial value (0 = auto)")
        row2.addWidget(self.bins_manual_rad_max)
        
        auto_label = QLabel("(0 = auto)")
        auto_label.setStyleSheet("color: #999999; font-size: 10px;")
        row2.addWidget(auto_label)
        
        # Add button
        add_btn = QPushButton("Add Sector")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        add_btn.clicked.connect(self.bins_manual_add)
        row2.addWidget(add_btn)
        
        row2.addStretch()
        layout.addLayout(row2)
        
        return group
    
    # ==================== Multiple Sectors Tab Components ====================
    
    def create_sectors_list_group(self):
        """Create multiple sectors list group"""
        group = QGroupBox("Sector List")
        group.setStyleSheet(self._group_style())
        
        layout = QVBoxLayout(group)
        
        # Table
        self.sectors_table = QTableWidget()
        self.sectors_table.setColumnCount(7)
        self.sectors_table.setHorizontalHeaderLabels([
            "Name", "Azim Start (°)", "Azim End (°)", 
            "Rad Min (px)", "Rad Max (px)", "Bin Size (°)", "Action"
        ])
        header = self.sectors_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        
        self.sectors_table.setColumnWidth(1, 110)
        self.sectors_table.setColumnWidth(2, 110)
        self.sectors_table.setColumnWidth(3, 100)
        self.sectors_table.setColumnWidth(4, 100)
        self.sectors_table.setColumnWidth(5, 80)
        self.sectors_table.setColumnWidth(6, 80)
        self.sectors_table.setMinimumHeight(200)
        
        layout.addWidget(self.sectors_table)
        
        return group
    
    def create_sectors_add_group(self):
        """Create add sector group for multiple sectors"""
        group = QGroupBox("Add Sector")
        group.setStyleSheet(self._group_style())
        
        layout = QVBoxLayout(group)
        
        # Row 1: Name and Azimuthal range
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("Name:"))
        self.sectors_name = QLineEdit()
        self.sectors_name.setPlaceholderText("e.g., Sector1")
        self.sectors_name.setFixedWidth(100)
        row1.addWidget(self.sectors_name)
        
        row1.addWidget(QLabel("Azimuthal:"))
        self.sectors_azim_start = QLineEdit("0")
        self.sectors_azim_start.setFixedWidth(70)
        self.sectors_azim_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sectors_azim_start.textChanged.connect(self.update_sectors_bins_count)
        row1.addWidget(self.sectors_azim_start)
        
        row1.addWidget(QLabel("to"))
        self.sectors_azim_end = QLineEdit("90")
        self.sectors_azim_end.setFixedWidth(70)
        self.sectors_azim_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sectors_azim_end.textChanged.connect(self.update_sectors_bins_count)
        row1.addWidget(self.sectors_azim_end)
        row1.addWidget(QLabel("°"))
        
        row1.addWidget(QLabel("Bin Size:"))
        self.sectors_bin_size = QLineEdit("10")
        self.sectors_bin_size.setFixedWidth(60)
        self.sectors_bin_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sectors_bin_size.textChanged.connect(self.update_sectors_bins_count)
        row1.addWidget(self.sectors_bin_size)
        row1.addWidget(QLabel("°"))
        
        # Bins count display for sectors
        self.sectors_bins_count_label = QLabel("→ 9 bins")
        self.sectors_bins_count_label.setStyleSheet("color: #666666; font-weight: bold;")
        row1.addWidget(self.sectors_bins_count_label)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # Row 2: Radial range
        row2 = QHBoxLayout()
        
        rad_label = QLabel("Radial Range (px):")
        rad_label.setToolTip("Radial range in pixels (0 = auto)")
        row2.addWidget(rad_label)
        
        self.sectors_rad_min = QLineEdit("0")
        self.sectors_rad_min.setFixedWidth(70)
        self.sectors_rad_min.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sectors_rad_min.setToolTip("Minimum radial value (pixels)")
        row2.addWidget(self.sectors_rad_min)
        
        row2.addWidget(QLabel("to"))
        self.sectors_rad_max = QLineEdit("0")
        self.sectors_rad_max.setFixedWidth(70)
        self.sectors_rad_max.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sectors_rad_max.setToolTip("Maximum radial value (0 = auto)")
        row2.addWidget(self.sectors_rad_max)
        
        auto_label = QLabel("(0 = auto)")
        auto_label.setStyleSheet("color: #999999; font-size: 10px;")
        row2.addWidget(auto_label)
        
        # Add button
        add_btn = QPushButton("Add Sector")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        add_btn.clicked.connect(self.sectors_add)
        row2.addWidget(add_btn)
        
        row2.addStretch()
        layout.addLayout(row2)
        
        return group
    
    def create_sectors_preset_group(self):
        """Create quick presets group for multiple sectors"""
        group = QGroupBox("Quick Presets")
        group.setStyleSheet(self._group_style())
        
        layout = QHBoxLayout(group)
        
        # 4-sector preset
        btn_4 = QPushButton("4 Sectors (90° each)")
        btn_4.setStyleSheet(self._action_btn_style())
        btn_4.clicked.connect(lambda: self.sectors_apply_preset(4))
        layout.addWidget(btn_4)
        
        # 8-sector preset
        btn_8 = QPushButton("8 Sectors (45° each)")
        btn_8.setStyleSheet(self._action_btn_style())
        btn_8.clicked.connect(lambda: self.sectors_apply_preset(8))
        layout.addWidget(btn_8)
        
        # 12-sector preset
        btn_12 = QPushButton("12 Sectors (30° each)")
        btn_12.setStyleSheet(self._action_btn_style())
        btn_12.clicked.connect(lambda: self.sectors_apply_preset(12))
        layout.addWidget(btn_12)
        
        layout.addStretch()
        
        return group
    
    # ==================== Style Helpers ====================
    
    def _group_style(self):
        """Group box style"""
        return f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """
    
    def _action_btn_style(self):
        """Action button style"""
        return f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #6A1B9A;
            }}
        """
    
    # ==================== Single Sector Methods ====================
    
    def update_bins_count(self):
        """Update bins count display"""
        try:
            start = float(self.bins_quick_start.text())
            end = float(self.bins_quick_end.text())
            bin_size = float(self.bins_quick_size.text())
            
            if bin_size > 0 and end > start:
                num_bins = int((end - start) / bin_size)
                self.bins_count_label.setText(f"→ {num_bins} bins")
            else:
                self.bins_count_label.setText("→ ? bins")
        except (ValueError, ZeroDivisionError):
            self.bins_count_label.setText("→ ? bins")
    
    def bins_quick_generate(self):
        """Quick generate single sectors"""
        try:
            start = float(self.bins_quick_start.text())
            end = float(self.bins_quick_end.text())
            bin_size = float(self.bins_quick_size.text())
            rad_min = float(self.bins_quick_rad_min.text())
            rad_max = float(self.bins_quick_rad_max.text())
            
            if start >= end:
                QMessageBox.warning(self, "Error", "Start angle must be less than end angle")
                return
            
            if bin_size <= 0:
                QMessageBox.warning(self, "Error", "Bin size must be greater than 0")
                return
            
            if rad_min < 0 or (rad_max != 0 and rad_min >= rad_max):
                QMessageBox.warning(self, "Error", "Invalid radial range")
                return
            
            # Clear existing sectors
            self.bins = []
            
            # Generate sectors based on bin size
            num_bins = int((end - start) / bin_size)
            if num_bins < 1:
                QMessageBox.warning(self, "Error", "Bin size too large for the given range")
                return
            
            for i in range(num_bins):
                bin_start = start + i * bin_size
                bin_end = min(start + (i + 1) * bin_size, end)
                bin_name = f"Sector{i+1:03d}"
                
                self.bins.append({
                    'name': bin_name,
                    'start': bin_start,
                    'end': bin_end,
                    'rad_min': rad_min,
                    'rad_max': rad_max
                })
            
            self.update_bins_table()
            
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Invalid input: {str(e)}")
    
    def bins_manual_add(self):
        """Manually add single sector"""
        try:
            name = self.bins_manual_name.text().strip()
            if not name:
                name = f"Sector{len(self.bins)+1:03d}"
            
            start = float(self.bins_manual_start.text())
            end = float(self.bins_manual_end.text())
            rad_min = float(self.bins_manual_rad_min.text())
            rad_max = float(self.bins_manual_rad_max.text())
            
            if start >= end:
                QMessageBox.warning(self, "Error", "Start angle must be less than end angle")
                return
            
            if rad_min < 0 or (rad_max != 0 and rad_min >= rad_max):
                QMessageBox.warning(self, "Error", "Invalid radial range")
                return
            
            self.bins.append({
                'name': name,
                'start': start,
                'end': end,
                'rad_min': rad_min,
                'rad_max': rad_max
            })
            
            self.update_bins_table()
            
            # Clear input fields
            self.bins_manual_name.clear()
            
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Invalid input: {str(e)}")
    
    def update_bins_table(self):
        """Update single sector table"""
        self.bins_table.setRowCount(len(self.bins))
        
        for i, bin_data in enumerate(self.bins):
            # Name
            name_item = QTableWidgetItem(bin_data['name'])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bins_table.setItem(i, 0, name_item)
            
            # Azim Start
            start_item = QTableWidgetItem(f"{bin_data['start']:.2f}")
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bins_table.setItem(i, 1, start_item)
            
            # Azim End
            end_item = QTableWidgetItem(f"{bin_data['end']:.2f}")
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bins_table.setItem(i, 2, end_item)
            
            # Rad Min
            rad_min_item = QTableWidgetItem(f"{bin_data['rad_min']:.2f}")
            rad_min_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bins_table.setItem(i, 3, rad_min_item)
            
            # Rad Max
            rad_max_text = "auto" if bin_data['rad_max'] == 0 else f"{bin_data['rad_max']:.2f}"
            rad_max_item = QTableWidgetItem(rad_max_text)
            rad_max_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bins_table.setItem(i, 4, rad_max_item)
            
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
            delete_btn.clicked.connect(lambda checked, idx=i: self.bins_delete(idx))
            self.bins_table.setCellWidget(i, 5, delete_btn)
    
    def bins_delete(self, index):
        """Delete single sector"""
        if 0 <= index < len(self.bins):
            del self.bins[index]
            self.update_bins_table()
    
    # ==================== Multiple Sectors Methods ====================
    
    def update_sectors_bins_count(self):
        """Update bins count display for multiple sectors"""
        try:
            start = float(self.sectors_azim_start.text())
            end = float(self.sectors_azim_end.text())
            bin_size = float(self.sectors_bin_size.text())
            
            if bin_size > 0 and end > start:
                num_bins = int((end - start) / bin_size)
                self.sectors_bins_count_label.setText(f"→ {num_bins} bins")
            else:
                self.sectors_bins_count_label.setText("→ ? bins")
        except (ValueError, ZeroDivisionError):
            self.sectors_bins_count_label.setText("→ ? bins")
    
    def sectors_add(self):
        """Add multiple sector"""
        try:
            name = self.sectors_name.text().strip()
            if not name:
                name = f"Sector{len(self.sectors)+1}"
            
            azim_start = float(self.sectors_azim_start.text())
            azim_end = float(self.sectors_azim_end.text())
            rad_min = float(self.sectors_rad_min.text())
            rad_max = float(self.sectors_rad_max.text())
            bin_size = float(self.sectors_bin_size.text())
            
            if azim_start >= azim_end:
                QMessageBox.warning(self, "Error", "Azimuthal start must be less than end")
                return
            
            if rad_min < 0 or (rad_max != 0 and rad_min >= rad_max):
                QMessageBox.warning(self, "Error", "Invalid radial range")
                return
            
            if bin_size <= 0:
                QMessageBox.warning(self, "Error", "Bin size must be greater than 0")
                return
            
            self.sectors.append({
                'name': name,
                'azim_start': azim_start,
                'azim_end': azim_end,
                'rad_min': rad_min,
                'rad_max': rad_max,
                'bin_size': bin_size
            })
            
            self.update_sectors_table()
            
            # Clear input fields
            self.sectors_name.clear()
            
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Invalid input: {str(e)}")
    
    def sectors_apply_preset(self, num_sectors):
        """Apply preset for multiple sectors"""
        reply = QMessageBox.question(
            self, 'Confirm', 
            f'Generate {num_sectors} equal sectors? This will clear existing sectors.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.sectors = []
        
        sector_width = 360.0 / num_sectors
        for i in range(num_sectors):
            start = i * sector_width
            end = (i + 1) * sector_width
            
            self.sectors.append({
                'name': f"Sector{i+1}",
                'azim_start': start,
                'azim_end': end,
                'rad_min': 0.0,
                'rad_max': 0.0,
                'bin_size': 10.0
            })
        
        self.update_sectors_table()
    
    def update_sectors_table(self):
        """Update multiple sectors table"""
        self.sectors_table.setRowCount(len(self.sectors))
        
        for i, sector in enumerate(self.sectors):
            # Name
            name_item = QTableWidgetItem(sector['name'])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sectors_table.setItem(i, 0, name_item)
            
            # Azim Start
            azim_start_item = QTableWidgetItem(f"{sector['azim_start']:.1f}")
            azim_start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sectors_table.setItem(i, 1, azim_start_item)
            
            # Azim End
            azim_end_item = QTableWidgetItem(f"{sector['azim_end']:.1f}")
            azim_end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sectors_table.setItem(i, 2, azim_end_item)
            
            # Rad Min
            rad_min_item = QTableWidgetItem(f"{sector['rad_min']:.2f}")
            rad_min_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sectors_table.setItem(i, 3, rad_min_item)
            
            # Rad Max
            rad_max_text = "auto" if sector['rad_max'] == 0 else f"{sector['rad_max']:.2f}"
            rad_max_item = QTableWidgetItem(rad_max_text)
            rad_max_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sectors_table.setItem(i, 4, rad_max_item)
            
            # Bin Size
            bin_size_text = f"{sector.get('bin_size', 10.0):.1f}"
            bin_size_item = QTableWidgetItem(bin_size_text)
            bin_size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sectors_table.setItem(i, 5, bin_size_item)
            
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
            delete_btn.clicked.connect(lambda checked, idx=i: self.sectors_delete(idx))
            self.sectors_table.setCellWidget(i, 6, delete_btn)
    
    def sectors_delete(self, index):
        """Delete multiple sector"""
        if 0 <= index < len(self.sectors):
            del self.sectors[index]
            self.update_sectors_table()
    
    # ==================== Common Methods ====================
    
    def clear_current_tab(self):
        """Clear current tab"""
        current_index = self.tab_widget.currentIndex()
        
        if current_index == 0:  # Single Sector tab
            if self.bins:
                reply = QMessageBox.question(
                    self, 'Confirm', 'Clear all single sectors?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.bins = []
                    self.update_bins_table()
        else:  # Multiple Sectors tab
            if self.sectors:
                reply = QMessageBox.question(
                    self, 'Confirm', 'Clear all multiple sectors?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.sectors = []
                    self.update_sectors_table()
    
    def accept_config(self):
        """Accept configuration"""
        if not self.bins and not self.sectors:
            QMessageBox.warning(self, "Error", "Please add at least one sector")
            return
        
        if self.bins and self.sectors:
            QMessageBox.warning(
                self, "Warning", 
                "Both single and multiple sectors are configured.\n"
                "During integration, single sectors will be used and multiple sectors will be ignored."
            )
        
        self.config_completed.emit(self.bins, self.sectors)
        self.accept()
    
    def get_bins(self):
        """Get single sectors list"""
        return self.bins
    
    def get_sectors(self):
        """Get multiple sectors list"""
        return self.sectors


# Test code
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    dialog = UnifiedConfigDialog()
    
    def on_configured(bins, sectors):
        print("Configured single sectors:")
        for bin_data in bins:
            print(f"  {bin_data['name']}: {bin_data['start']}° - {bin_data['end']}°, "
                  f"Radial: {bin_data['rad_min']} - {bin_data['rad_max']}")
        
        print("\nConfigured multiple sectors:")
        for sector in sectors:
            print(f"  {sector['name']}: {sector['azim_start']}° - {sector['azim_end']}°, "
                  f"Radial: {sector['rad_min']} - {sector['rad_max']}")
    
    dialog.config_completed.connect(on_configured)
    
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:
        print(f"\nTotal single sectors: {len(dialog.get_bins())}")
        print(f"Total multiple sectors: {len(dialog.get_sectors())}")
    else:
        print("Cancelled")
    
    sys.exit(0)