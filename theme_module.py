# -*- coding: utf-8 -*-
"""
GUI Components Module for Curve Fitting Application
Contains all UI elements, components, color schemes, and utility methods

Created on Fri Nov 14 09:31:22 2025
@author: 16961
"""

from PyQt6.QtWidgets import (QPushButton, QWidget, QLabel, QVBoxLayout,
                              QHBoxLayout, QFrame, QFileDialog, QMessageBox,
                              QDialog)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPalette
import math
import os


# ==============================================================================
# Modern UI Components
# ==============================================================================

class ModernButton(QPushButton):
    """Modern button component with rounded corners and hover effects"""

    def __init__(self, text, command=None, icon="", bg_color="#9D4EDD",
                 hover_color="#C77DFF", text_color="black", width=200, height=40,
                 font_size=11, parent=None):
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
        font = QFont('Arial', font_size)
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
    """Modern tab component with active/inactive states"""

    clicked = pyqtSignal()

    def __init__(self, text, command=None, is_active=False, parent=None):
        super().__init__(parent)
        self.command = command
        self.is_active = is_active

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
            parent_bg = self.parent().palette().color(QPalette.ColorRole.Window).name() if self.parent() else "#FFFFFF"
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

    def __init__(self, width=700, height=80, parent=None):
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
        """Draw a cute sheep emoji with bounce animation"""
        jump = -abs(math.sin(jump_phase) * 15)
        y_pos = y + jump

        # Draw sheep emoji
        font = QFont("Segoe UI Emoji", 48)
        painter.setFont(font)
        painter.drawText(int(x - 24), int(y_pos + 24), "🐰")

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

        # Update and draw all sheep
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


# ==============================================================================
# Base GUI Class with Utilities
# ==============================================================================

class GUIBase:
    """Base class for GUI components with shared styles and utilities"""

    def __init__(self):
        """Initialize color scheme and styles"""
        self.colors = {
            'bg': '#FFFFFF',
            'card_bg': '#FFFFFF',
            'primary': '#B794F6',
            'primary_hover': '#D4BBFF',
            'secondary': '#E0AAFF',
            'accent': '#FF6B9D',
            'text_dark': '#2B2D42',
            'text_light': '#8B8BA7',
            'border': '#E0E0E0',
            'success': '#06D6A0',
            'error': '#EF476F',
            'light_purple': '#E6D9F5',
            'active_module': '#C8B3E6'
        }

        # Shared checkbox and radio indicator styling to match the mockup
        self.control_indicator_styles = (
            "QCheckBox::indicator {"
            " width: 16px;"
            " height: 16px;"
            " border-radius: 2px;"
            f" border: 1.2px solid {self.colors['primary']};"
            " background: #FFFFFF;"
            " image: none;"
            " }"

            " QCheckBox::indicator:hover {"
            f" border-color: {self.colors['primary_hover']};"
            " }"

            " QCheckBox::indicator:checked {"
            f" background: {self.colors['light_purple']};"
            f" border: 1.2px solid {self.colors['primary']};"
            " image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'><path fill='%23B794F6' d='M9.5 16.2 5.3 12l1.4-1.4 2.8 2.8 7.8-7.8L18.7 7z'/></svg>\");"
            " }"

            " QRadioButton::indicator {"
            " width: 16px;"
            " height: 16px;"
            " border-radius: 8px;"
            f" border: 1.2px solid {self.colors['primary']};"
            " background: #FFFFFF;"
            " image: none;"
            " }"

            " QRadioButton::indicator:hover {"
            f" border-color: {self.colors['primary_hover']};"
            " }"

            " QRadioButton::indicator:checked {"
            f" background: {self.colors['light_purple']};"
            f" border: 1.2px solid {self.colors['primary']};"
            " image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'><circle cx='12' cy='12' r='5' fill='%23B794F6'/></svg>\");"
            " }"
        )

    def apply_indicator_styles(self, app):
        """Apply shared checkbox and radio indicator styles to the Qt application."""
        existing = app.styleSheet()
        combined = f"{existing}\n{self.control_indicator_styles}" if existing else self.control_indicator_styles
        app.setStyleSheet(combined)

    def create_card_frame(self, parent, bg=None):
        """Create a styled card frame with border"""
        if bg is None:
            bg = self.colors['card_bg']

        card = QFrame(parent)
        card.setObjectName("card")
        card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {bg};
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
            }}
        """)
        return card

    def create_file_picker(self, parent, label, variable, filetypes, pattern=False):
        """Create a file picker widget with browse button"""
        from PyQt6.QtWidgets import QLineEdit

        container = QWidget(parent)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 4)

        # Label
        lbl = QLabel(label, container)
        lbl.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        font = QFont('Arial', 9)
        font.setBold(True)
        lbl.setFont(font)
        layout.addWidget(lbl)

        # Input frame
        input_frame = QWidget(container)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)

        entry = QLineEdit(input_frame)
        entry.setFont(QFont('Arial', 9))
        entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 1px solid {self.colors['border']};
                padding: 3px;
            }}
        """)

        # Bind variable (assuming StringVar-like object)
        if hasattr(variable, 'get'):
            entry.setText(variable.get())
        if hasattr(variable, 'trace_add') or hasattr(variable, 'set'):
            entry.textChanged.connect(lambda text: variable.set(text) if hasattr(variable, 'set') else None)

        input_layout.addWidget(entry)

        if pattern:
            btn = ModernButton("Browse",
                             lambda: self.browse_pattern(variable, filetypes, entry),
                             bg_color=self.colors['secondary'],
                             hover_color=self.colors['primary'],
                             width=75, height=28, parent=input_frame)
        else:
            btn = ModernButton("Browse",
                             lambda: self.browse_file(variable, filetypes, entry),
                             bg_color=self.colors['secondary'],
                             hover_color=self.colors['primary'],
                             width=75, height=28, parent=input_frame)
        input_layout.addWidget(btn)

        layout.addWidget(input_frame)
        return container

    def create_folder_picker(self, parent, label, variable):
        """Create a folder picker widget with browse button"""
        from PyQt6.QtWidgets import QLineEdit

        container = QWidget(parent)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 4)

        # Label
        lbl = QLabel(label, container)
        lbl.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        font = QFont('Arial', 9)
        font.setBold(True)
        lbl.setFont(font)
        layout.addWidget(lbl)

        # Input frame
        input_frame = QWidget(container)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)

        entry = QLineEdit(input_frame)
        entry.setFont(QFont('Arial', 9))
        entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 1px solid {self.colors['border']};
                padding: 3px;
            }}
        """)

        # Bind variable
        if hasattr(variable, 'get'):
            entry.setText(variable.get())
        if hasattr(variable, 'set'):
            entry.textChanged.connect(lambda text: variable.set(text))

        input_layout.addWidget(entry)

        btn = ModernButton("Browse",
                         lambda: self.browse_folder(variable, entry),
                         bg_color=self.colors['secondary'],
                         hover_color=self.colors['primary'],
                         width=75, height=28, parent=input_frame)
        input_layout.addWidget(btn)

        layout.addWidget(input_frame)
        return container

    def create_entry(self, parent, label, variable):
        """Create a text entry widget"""
        from PyQt6.QtWidgets import QLineEdit

        container = QWidget(parent)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 4)

        lbl = QLabel(label, container)
        lbl.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        font = QFont('Arial', 9)
        font.setBold(True)
        lbl.setFont(font)
        layout.addWidget(lbl)

        entry = QLineEdit(container)
        entry.setFont(QFont('Arial', 9))
        entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: {self.colors['text_dark']};
                border: 1px solid {self.colors['border']};
                padding: 3px;
            }}
        """)

        # Bind variable
        if hasattr(variable, 'get'):
            entry.setText(variable.get())
        if hasattr(variable, 'set'):
            entry.textChanged.connect(lambda text: variable.set(text))

        layout.addWidget(entry)
        return container

    def browse_file(self, variable, filetypes, entry=None):
        """Open file browser dialog and set the selected file path"""
        # Convert tkinter filetypes to Qt format
        # filetypes format: [("Description", "*.ext"), ...]
        qt_filter = ";;".join([f"{desc} ({pattern})" for desc, pattern in filetypes])

        filename, _ = QFileDialog.getOpenFileName(None, "Select File", "", qt_filter)
        if filename:
            if hasattr(variable, 'set'):
                variable.set(filename)
            if entry:
                entry.setText(filename)

    def browse_pattern(self, variable, filetypes, entry=None):
        """Open file browser and create pattern from selected file"""
        qt_filter = ";;".join([f"{desc} ({pattern})" for desc, pattern in filetypes])

        filename, _ = QFileDialog.getOpenFileName(None, "Select File", "", qt_filter)
        if filename:
            folder = os.path.dirname(filename)
            ext = os.path.splitext(filename)[1]
            pattern = os.path.join(folder, f"*{ext}")
            if hasattr(variable, 'set'):
                variable.set(pattern)
            if entry:
                entry.setText(pattern)

    def browse_folder(self, variable, entry=None):
        """Open folder browser dialog and set the selected folder path"""
        folder = QFileDialog.getExistingDirectory(None, "Select Folder")
        if folder:
            if hasattr(variable, 'set'):
                variable.set(folder)
            if entry:
                entry.setText(folder)

    def show_success(self, parent, message):
        """Show success dialog with cute styling"""
        dialog = QDialog(parent)
        dialog.setWindowTitle("Success")
        dialog.setFixedSize(450, 300)
        dialog.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Success emoji
        emoji_label = QLabel("✅", dialog)
        emoji_label.setFont(QFont('Segoe UI Emoji', 64))
        emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_label.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        layout.addWidget(emoji_label)

        # Message
        msg_label = QLabel(message, dialog)
        msg_label.setStyleSheet(f"color: {self.colors['primary']}; background-color: {self.colors['card_bg']};")
        font = QFont('Arial', 13)
        font.setBold(True)
        msg_label.setFont(font)
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg_label)

        # OK button
        ok_btn = ModernButton("OK", dialog.accept,
                            bg_color=self.colors['primary'],
                            hover_color=self.colors['primary_hover'],
                            width=120, height=40, parent=dialog)
        layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()