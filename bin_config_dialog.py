#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bin Mode Configuration Dialog
用于配置方位角分bin的对话框
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QSpinBox, QGroupBox,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import numpy as np


class BinConfigDialog(QDialog):
    """Bin Mode配置对话框"""
    
    # 信号：配置完成，返回bin列表
    bins_configured = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bin Mode Configuration")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        # 颜色主题
        self.colors = {
            'primary': '#7C4DFF',
            'background': '#F5F5F5',
            'card_bg': '#FFFFFF',
            'border': '#E0E0E0',
            'text_dark': '#333333'
        }
        
        # 数据
        self.bins = []  # List of dicts: {'start': float, 'end': float, 'name': str}
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("Azimuthal Bin Configuration")
        title.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['primary']};")
        layout.addWidget(title)
        
        # 快速生成组
        quick_group = self.create_quick_generate_group()
        layout.addWidget(quick_group)
        
        # Bin列表
        list_group = self.create_bin_list_group()
        layout.addWidget(list_group)
        
        # 手动添加组
        manual_group = self.create_manual_add_group()
        layout.addWidget(manual_group)
        
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
        clear_btn.clicked.connect(self.clear_bins)
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
    
    def create_quick_generate_group(self):
        """创建快速生成组"""
        group = QGroupBox("Quick Generate")
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
        
        # 参数行
        param_layout = QHBoxLayout()
        
        # Start angle
        param_layout.addWidget(QLabel("Start:"))
        self.quick_start = QLineEdit("0")
        self.quick_start.setFixedWidth(80)
        self.quick_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        param_layout.addWidget(self.quick_start)
        
        # End angle
        param_layout.addWidget(QLabel("End:"))
        self.quick_end = QLineEdit("360")
        self.quick_end.setFixedWidth(80)
        self.quick_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        param_layout.addWidget(self.quick_end)
        
        # Number of bins
        param_layout.addWidget(QLabel("Bins:"))
        self.quick_num_bins = QSpinBox()
        self.quick_num_bins.setRange(1, 360)
        self.quick_num_bins.setValue(36)
        self.quick_num_bins.setFixedWidth(80)
        param_layout.addWidget(self.quick_num_bins)
        
        # Generate button
        gen_btn = QPushButton("Generate")
        gen_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
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
        """创建Bin列表组"""
        group = QGroupBox("Bin List")
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
        self.bin_table.setMinimumHeight(200)
        
        layout.addWidget(self.bin_table)
        
        return group
    
    def create_manual_add_group(self):
        """创建手动添加组"""
        group = QGroupBox("Manual Add")
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
        
        # Name
        layout.addWidget(QLabel("Name:"))
        self.manual_name = QLineEdit()
        self.manual_name.setPlaceholderText("e.g., Bin01")
        self.manual_name.setFixedWidth(100)
        layout.addWidget(self.manual_name)
        
        # Start
        layout.addWidget(QLabel("Start:"))
        self.manual_start = QLineEdit("0")
        self.manual_start.setFixedWidth(80)
        self.manual_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.manual_start)
        
        # End
        layout.addWidget(QLabel("End:"))
        self.manual_end = QLineEdit("10")
        self.manual_end.setFixedWidth(80)
        self.manual_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.manual_end)
        
        # Add button
        add_btn = QPushButton("Add")
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
        add_btn.clicked.connect(self.manual_add)
        layout.addWidget(add_btn)
        
        layout.addStretch()
        
        return group
    
    def quick_generate(self):
        """快速生成bins"""
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
            
            # 清空现有bins
            self.bins = []
            
            # 生成bins
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
        """手动添加bin"""
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
            
            # 清空输入框
            self.manual_name.clear()
            
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Invalid input: {str(e)}")
    
    def update_table(self):
        """更新表格"""
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
        """删除bin"""
        if 0 <= index < len(self.bins):
            del self.bins[index]
            self.update_table()
    
    def clear_bins(self):
        """清空所有bins"""
        reply = QMessageBox.question(
            self, 'Confirm', 'Clear all bins?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.bins = []
            self.update_table()
    
    def accept_config(self):
        """接受配置"""
        if not self.bins:
            QMessageBox.warning(self, "Error", "Please add at least one bin")
            return
        
        self.bins_configured.emit(self.bins)
        self.accept()
    
    def get_bins(self):
        """获取bins列表"""
        return self.bins


# 测试代码
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