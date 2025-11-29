# -*- coding: utf-8 -*-
"""
Created on Fri Nov 14 09:31:22 2025

@author: 16961
"""
from PyQt6.QtWidgets import QPushButton, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPalette, QBrush, QPainterPath
import math
import os
from pathlib import Path
from batch_integration import BatchIntegrator
from peak_fitting import BatchFitter
from birch_murnaghan_batch import BirchMurnaghanFitter
from batch_cal_volume import XRayDiffractionAnalyzer
import numpy as np
import pandas as pd
from scipy.optimize import least_squares, curve_fit
import re
import warnings
import random


class ModernButton(QPushButton):
    """Modern button component"""
    def __init__(self, parent, text, command, icon="", bg_color="#9D4EDD",
                 hover_color="#C77DFF", text_color="black", width=200, height=40, **kwargs):
        display_text = f"{icon}  {text}" if icon else text
        super().__init__(display_text, parent)

        self.command = command
        self.bg_color = QColor(bg_color)
        self.hover_color = QColor(hover_color)
        self.text_color = QColor(text_color)
        self.current_color = self.bg_color

        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Set font
        font = QFont('Arial', 11)
        font.setBold(True)
        self.setFont(font)

        # Apply stylesheet for rounded corners and colors
        self.update_stylesheet()

        # Connect click event
        if command:
            self.clicked.connect(command)

    def update_stylesheet(self):
        """Update button stylesheet with current colors"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color.name()};
                color: {self.text_color.name()};
                border: 1.2px solid {self.current_color.darker(105).name()};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {self.hover_color.name()};
            }}
            QPushButton:pressed {{
                background-color: {self.bg_color.darker(115).name()};
            }}
        """)

    def enterEvent(self, event):
        """Handle mouse enter event - change to hover color"""
        self.current_color = self.hover_color
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave event - restore normal color"""
        self.current_color = self.bg_color
        super().leaveEvent(event)


class ModernTab(QWidget):
    """Modern tab component"""
    clicked = pyqtSignal()

    def __init__(self, parent, text, command, is_active=False, **kwargs):
        super().__init__(parent)
        self.command = command
        self.is_active = is_active
        self.parent_widget = parent

        self.active_color = QColor("#9D4EDD")
        self.inactive_color = QColor("#8B8BA7")
        self.hover_color = QColor("#C77DFF")

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(0)

        # Create label
        self.label = QLabel(text, self)
        font = QFont('Arial', 11)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_colors()
        layout.addWidget(self.label)

        # Create underline
        self.underline = QFrame(self)
        self.underline.setFixedHeight(3)
        self.underline.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.underline)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_underline()

    def update_colors(self):
        """Update label color based on active state"""
        color = self.active_color if self.is_active else self.inactive_color
        self.label.setStyleSheet(f"color: {color.name()}; background: transparent;")

    def update_underline(self):
        """Update underline visibility based on active state"""
        if self.is_active:
            self.underline.setStyleSheet(f"background-color: {self.active_color.name()};")
        else:
            parent_bg = self.parent_widget.palette().color(QPalette.ColorRole.Window).name() if self.parent_widget else "#FFFFFF"
            self.underline.setStyleSheet(f"background-color: {parent_bg};")

    def enterEvent(self, event):
        """Handle mouse enter event"""
        if not self.is_active:
            self.label.setStyleSheet(f"color: {self.hover_color.name()}; background: transparent;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave event"""
        if not self.is_active:
            self.update_colors()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press event"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            if self.command:
                self.command()
        super().mousePressEvent(event)

    def set_active(self, active):
        """Set the active state of the tab"""
        self.is_active = active
        self.update_colors()
        self.update_underline()


class CuteSheepProgressBar(QWidget):
    """Cute sheep progress bar animation"""
    def __init__(self, parent, width=700, height=80, **kwargs):
        super().__init__(parent)
        self.setFixedSize(width, height)

        self.width = width
        self.height = height
        self.sheep = []
        self.is_animating = False
        self.frame_count = 0

        # Timer for animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)

    def paintEvent(self, event):
        """Paint the sheep on the canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw sheep
        for sheep_data in self.sheep:
            self.draw_adorable_sheep(painter, sheep_data['x'],
                                    self.height // 2, sheep_data['phase'])

    def draw_adorable_sheep(self, painter, x, y, jump_phase):
        """Draw a cute detailed sheep with bounce animation"""
        jump = -abs(math.sin(jump_phase) * 20)
        y = y + jump

        # Shadow
        painter.setBrush(QBrush(QColor("#E8E4F3")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x-15), int(y+25), 30, 3)

        # Body
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(QPen(QColor("#FFB6D9"), 3))
        painter.drawEllipse(int(x-20), int(y-15), 40, 30)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x-18), int(y-10), 8, 8)
        painter.drawEllipse(int(x+10), int(y-8), 8, 8)
        painter.drawEllipse(int(x-5), int(y+8), 10, 7)

        # Head
        painter.setBrush(QBrush(QColor("#FFE4F0")))
        painter.setPen(QPen(QColor("#FFB6D9"), 3))
        painter.drawEllipse(int(x+15), int(y-12), 20, 20)

        # Ears (using polygon/path)
        painter.setBrush(QBrush(QColor("#FFB6D9")))
        painter.setPen(QPen(QColor("#FF6B9D"), 2))

        # Left ear
        path1 = QPainterPath()
        path1.moveTo(x+17, y-10)
        path1.lineTo(x+20, y-18)
        path1.lineTo(x+23, y-10)
        path1.closeSubpath()
        painter.drawPath(path1)

        # Right ear
        path2 = QPainterPath()
        path2.moveTo(x+27, y-10)
        path2.lineTo(x+30, y-18)
        path2.lineTo(x+33, y-10)
        path2.closeSubpath()
        painter.drawPath(path2)

        # Eyes
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x+19), int(y-6), 5, 5)
        painter.setBrush(QBrush(QColor("#2B2D42")))
        painter.drawEllipse(int(x+20), int(y-5), 3, 3)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(int(x+21), int(y-4), 1, 1)

        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(int(x+26), int(y-6), 5, 5)
        painter.setBrush(QBrush(QColor("#2B2D42")))
        painter.drawEllipse(int(x+27), int(y-5), 3, 3)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(int(x+28), int(y-4), 1, 1)

        # Nose
        painter.setBrush(QBrush(QColor("#FFB6D9")))
        painter.setPen(QPen(QColor("#FF6B9D"), 2))
        painter.drawEllipse(int(x+23), int(y+2), 4, 4)

        # Cheeks
        painter.setBrush(QBrush(QColor("#FFD4E5")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x+16), int(y+1), 3, 3)
        painter.drawEllipse(int(x+31), int(y+1), 3, 3)

        # Legs with animation
        leg_offset = abs(math.sin(jump_phase) * 3)
        painter.setPen(QPen(QColor("#FFB6D9"), 5, cap=Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x-12), int(y+15), int(x-12), int(y+24-leg_offset))
        painter.drawLine(int(x-4), int(y+15), int(x-4), int(y+24+leg_offset))
        painter.drawLine(int(x+6), int(y+15), int(x+6), int(y+24-leg_offset))
        painter.drawLine(int(x+14), int(y+15), int(x+14), int(y+24+leg_offset))

        # Hooves
        painter.setBrush(QBrush(QColor("#D4BBFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x-14), int(y+22-leg_offset), 4, 3)
        painter.drawEllipse(int(x-6), int(y+22+leg_offset), 4, 3)
        painter.drawEllipse(int(x+4), int(y+22-leg_offset), 4, 3)
        painter.drawEllipse(int(x+12), int(y+22+leg_offset), 4, 3)

        # Tail
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(QPen(QColor("#FFB6D9"), 2))
        painter.drawEllipse(int(x-22), int(y+5), 6, 6)

    def start(self):
        """Start the animation"""
        self.is_animating = True
        self.frame_count = 0
        self.sheep = []
        self.timer.start(35)  # 35ms interval

    def stop(self):
        """Stop the animation and clear the canvas"""
        self.is_animating = False
        self.timer.stop()
        self.sheep = []
        self.frame_count = 0
        self.update()

    def _animate(self):
        """Internal animation loop"""
        if not self.is_animating:
            return

        # Spawn new sheep periodically
        if self.frame_count % 35 == 0:
            self.sheep.append({'x': -40, 'phase': 0})

        # Update sheep positions
        new_sheep = []
        for sheep_data in self.sheep:
            sheep_data['x'] += 3.5
            sheep_data['phase'] += 0.25

            if sheep_data['x'] < self.width + 50:
                new_sheep.append(sheep_data)

        self.sheep = new_sheep
        self.frame_count += 1

        # Trigger repaint
        self.update()