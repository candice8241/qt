#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multiple Sector Configuration Dialog
用于配置多个扇区的对话框
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QSpinBox, QGroupBox,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import numpy as np


class SectorConfigDialog(QDialog):
    """Multiple Sector配置对话框"""
    
    # 信号：配置完成，返回sector列表
    sectors_configured = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multiple Sector Configuration")
        self.setModal(True)
        self.setMinimumSize(700, 550)
        
        # 颜色主题
        self.colors = {
            'primary': '#7C4DFF',
            'background': '#F5F5F5',
            'card_bg': '#FFFFFF',
            'border': '#E0E0E0',
            'text_dark': '#333333'
        }
        
        # 数据
        self.sectors = []  # List of dicts: {'name': str, 'azim_start': float, 'azim_end': float, 'rad_min': float, 'rad_max': float}
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("Multiple Sector Configuration")
        title.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['primary']};")
        layout.addWidget(title)
        
        desc = QLabel("Define multiple azimuthal sectors for integration")
        desc.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(desc)
        
        # Sector列表
        list_group = self.create_sector_list_group()
        layout.addWidget(list_group)
        
        # 添加Sector组
        add_group = self.create_add_sector_group()
        layout.addWidget(add_group)
        
        # 快速预设
        preset_group = self.create_preset_group()
        layout.addWidget(preset_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedWidth(100)
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
        clear_btn.clicked.connect(self.clear_sectors)
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
    
    def create_sector_list_group(self):
        """创建Sector列表组"""
        group = QGroupBox("Sector List")
        group.setStyleSheet(f"""
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
        """)
        
        layout = QVBoxLayout(group)
        
        # Table
        self.sector_table = QTableWidget()
        self.sector_table.setColumnCount(6)
        self.sector_table.setHorizontalHeaderLabels([
            "Name", "Azim Start (°)", "Azim End (°)", 
            "Rad Min (px)", "Rad Max (px)", "Action"
        ])
        header = self.sector_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        
        self.sector_table.setColumnWidth(1, 100)
        self.sector_table.setColumnWidth(2, 100)
        self.sector_table.setColumnWidth(3, 80)
        self.sector_table.setColumnWidth(4, 80)
        self.sector_table.setColumnWidth(5, 80)
        self.sector_table.setMinimumHeight(200)
        
        layout.addWidget(self.sector_table)
        
        return group
    
    def create_add_sector_group(self):
        """创建添加Sector组"""
        group = QGroupBox("Add Sector")
        group.setStyleSheet(f"""
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
        """)
        
        layout = QVBoxLayout(group)
        
        # Row 1: Name and Azimuthal range
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("Name:"))
        self.sector_name = QLineEdit()
        self.sector_name.setPlaceholderText("e.g., Sector1")
        self.sector_name.setFixedWidth(100)
        row1.addWidget(self.sector_name)
        
        row1.addWidget(QLabel("Azimuthal:"))
        self.sector_azim_start = QLineEdit("0")
        self.sector_azim_start.setFixedWidth(70)
        self.sector_azim_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self.sector_azim_start)
        
        row1.addWidget(QLabel("to"))
        self.sector_azim_end = QLineEdit("90")
        self.sector_azim_end.setFixedWidth(70)
        self.sector_azim_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self.sector_azim_end)
        row1.addWidget(QLabel("°"))
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # Row 2: Radial range
        row2 = QHBoxLayout()
        
        rad_label = QLabel("Radial Range (pixels):")
        rad_label.setToolTip("径向范围，单位：像素 (0 = 自动)")
        row2.addWidget(rad_label)
        
        self.sector_rad_min = QLineEdit("0")
        self.sector_rad_min.setFixedWidth(70)
        self.sector_rad_min.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sector_rad_min.setToolTip("最小径向值（像素）")
        row2.addWidget(self.sector_rad_min)
        
        row2.addWidget(QLabel("to"))
        self.sector_rad_max = QLineEdit("0")
        self.sector_rad_max.setFixedWidth(70)
        self.sector_rad_max.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sector_rad_max.setToolTip("最大径向值（像素），0表示自动")
        row2.addWidget(self.sector_rad_max)
        
        auto_label = QLabel("(0 = auto)")
        auto_label.setStyleSheet("color: #999999; font-size: 10px;")
        row2.addWidget(auto_label)
        
        # Add button
        add_btn = QPushButton("Add Sector")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #45A049;
            }}
        """)
        add_btn.clicked.connect(self.add_sector)
        row2.addWidget(add_btn)
        
        row2.addStretch()
        layout.addLayout(row2)
        
        return group
    
    def create_preset_group(self):
        """创建预设组"""
        group = QGroupBox("Quick Presets")
        group.setStyleSheet(f"""
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
        """)
        
        layout = QHBoxLayout(group)
        
        # 4-sector preset
        btn_4 = QPushButton("4 Sectors (90° each)")
        btn_4.setStyleSheet(self._preset_btn_style())
        btn_4.clicked.connect(lambda: self.apply_preset(4))
        layout.addWidget(btn_4)
        
        # 8-sector preset
        btn_8 = QPushButton("8 Sectors (45° each)")
        btn_8.setStyleSheet(self._preset_btn_style())
        btn_8.clicked.connect(lambda: self.apply_preset(8))
        layout.addWidget(btn_8)
        
        # 12-sector preset
        btn_12 = QPushButton("12 Sectors (30° each)")
        btn_12.setStyleSheet(self._preset_btn_style())
        btn_12.clicked.connect(lambda: self.apply_preset(12))
        layout.addWidget(btn_12)
        
        layout.addStretch()
        
        return group
    
    def _preset_btn_style(self):
        """预设按钮样式"""
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
    
    def add_sector(self):
        """添加sector"""
        try:
            name = self.sector_name.text().strip()
            if not name:
                name = f"Sector{len(self.sectors)+1}"
            
            azim_start = float(self.sector_azim_start.text())
            azim_end = float(self.sector_azim_end.text())
            rad_min = float(self.sector_rad_min.text())
            rad_max = float(self.sector_rad_max.text())
            
            if azim_start >= azim_end:
                QMessageBox.warning(self, "Error", "Azimuthal start must be less than end")
                return
            
            if rad_min < 0 or (rad_max != 0 and rad_min >= rad_max):
                QMessageBox.warning(self, "Error", "Invalid radial range")
                return
            
            self.sectors.append({
                'name': name,
                'azim_start': azim_start,
                'azim_end': azim_end,
                'rad_min': rad_min,
                'rad_max': rad_max
            })
            
            self.update_table()
            
            # 清空输入框
            self.sector_name.clear()
            
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Invalid input: {str(e)}")
    
    def apply_preset(self, num_sectors):
        """应用预设"""
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
                'rad_max': 0.0
            })
        
        self.update_table()
    
    def update_table(self):
        """更新表格"""
        self.sector_table.setRowCount(len(self.sectors))
        
        for i, sector in enumerate(self.sectors):
            # Name
            name_item = QTableWidgetItem(sector['name'])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sector_table.setItem(i, 0, name_item)
            
            # Azim Start
            azim_start_item = QTableWidgetItem(f"{sector['azim_start']:.1f}")
            azim_start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sector_table.setItem(i, 1, azim_start_item)
            
            # Azim End
            azim_end_item = QTableWidgetItem(f"{sector['azim_end']:.1f}")
            azim_end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sector_table.setItem(i, 2, azim_end_item)
            
            # Rad Min
            rad_min_item = QTableWidgetItem(f"{sector['rad_min']:.2f}")
            rad_min_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sector_table.setItem(i, 3, rad_min_item)
            
            # Rad Max
            rad_max_text = "auto" if sector['rad_max'] == 0 else f"{sector['rad_max']:.2f}"
            rad_max_item = QTableWidgetItem(rad_max_text)
            rad_max_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sector_table.setItem(i, 4, rad_max_item)
            
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
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_sector(idx))
            self.sector_table.setCellWidget(i, 5, delete_btn)
    
    def delete_sector(self, index):
        """删除sector"""
        if 0 <= index < len(self.sectors):
            del self.sectors[index]
            self.update_table()
    
    def clear_sectors(self):
        """清空所有sectors"""
        reply = QMessageBox.question(
            self, 'Confirm', 'Clear all sectors?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.sectors = []
            self.update_table()
    
    def accept_config(self):
        """接受配置"""
        if not self.sectors:
            QMessageBox.warning(self, "Error", "Please add at least one sector")
            return
        
        self.sectors_configured.emit(self.sectors)
        self.accept()
    
    def get_sectors(self):
        """获取sectors列表"""
        return self.sectors


# 测试代码
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    dialog = SectorConfigDialog()
    
    def on_configured(sectors):
        print("Configured sectors:")
        for sector in sectors:
            print(f"  {sector['name']}: {sector['azim_start']}° - {sector['azim_end']}°, "
                  f"Radial: {sector['rad_min']} - {sector['rad_max']}")
    
    dialog.sectors_configured.connect(on_configured)
    
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:
        print(f"Total sectors: {len(dialog.get_sectors())}")
    else:
        print("Cancelled")
    
    sys.exit(0)