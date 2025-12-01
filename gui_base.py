# -*- coding: utf-8 -*-
"""
Base GUI Components and Styles
Contains shared UI elements, color schemes, and utility methods
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QLineEdit, QVBoxLayout,
                              QHBoxLayout, QFrame, QFileDialog, QDialog, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from batch_appearance import ModernButton


class GUIBase:
    """Base class for GUI components with shared styles and utilities"""

    def __init__(self):
        """Initialize color scheme and styles"""
        self.colors = {
            'bg': '#F8F7FF',
            'card_bg': '#FFFFFF',
            'primary': '#E8D5F0',
            'primary_hover': '#D4BBFF',
            'secondary': '#E8D5F0',
            'accent': '#FF6B9D',
            'text_dark': '#2B2D42',
            'text_light': '#8B8BA7',
            'border': '#E8E4F3',
            'success': '#06D6A0',
            'error': '#EF476F',
            'light_purple': '#FF9FB5',
            'active_module': '#C8B3E6'
        }

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
            " image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'><path fill='%23B488D9' d='M9.5 16.2 5.3 12l1.4-1.4 2.8 2.8 7.8-7.8L18.7 7z'/></svg>\");"
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
            " image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'><circle cx='12' cy='12' r='5' fill='%23B488D9'/></svg>\");"
            " }"
        )

    def apply_indicator_styles(self, app):
        """Apply shared checkbox and radio indicator styles to the Qt application."""
        existing = app.styleSheet()
        combined = f"{existing}\n{self.control_indicator_styles}" if existing else self.control_indicator_styles
        app.setStyleSheet(combined)

    def create_card_frame(self, parent, bg=None, **kwargs):
        """Create a styled card frame"""
        if bg is None:
            bg = self.colors['card_bg']

        card = QFrame(parent)
        card.setObjectName("card")
        card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {bg};
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
            }}
        """)
        return card

    def create_group_box(self, title):
        """Create a styled group box with title"""
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                margin-top: 15px;
                margin-bottom: 10px;
                padding: 15px 10px 10px 10px;
                background-color: {self.colors['card_bg']};
                color: {self.colors['text_dark']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['primary']};
            }}
        """)
        return group

    def create_file_picker(self, parent, label, variable, filetypes, pattern=False):
        """Create a file picker widget with browse button"""
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
        if hasattr(variable, 'set'):
            entry.textChanged.connect(lambda text: variable.set(text))

        input_layout.addWidget(entry)

        if pattern:
            btn = ModernButton(input_frame, "Browse",
                             lambda: self.browse_pattern(variable, filetypes, entry),
                             bg_color=self.colors['secondary'],
                             hover_color=self.colors['primary'],
                             width=75, height=28)
        else:
            btn = ModernButton(input_frame, "Browse",
                             lambda: self.browse_file(variable, filetypes, entry),
                             bg_color=self.colors['secondary'],
                             hover_color=self.colors['primary'],
                             width=75, height=28)
        input_layout.addWidget(btn)

        layout.addWidget(input_frame)
        return container

    def create_folder_picker(self, parent, label, variable):
        """Create a folder picker widget with browse button"""
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

        btn = ModernButton(input_frame, "Browse",
                         lambda: self.browse_folder(variable, entry),
                         bg_color=self.colors['secondary'],
                         hover_color=self.colors['primary'],
                         width=75, height=28)
        input_layout.addWidget(btn)

        layout.addWidget(input_frame)
        return container

    def create_entry(self, parent, label, variable):
        """Create a text entry widget"""
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
        """Open file browser dialog"""
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
        import os
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
        """Open folder browser dialog"""
        folder = QFileDialog.getExistingDirectory(None, "Select Folder")
        if folder:
            if hasattr(variable, 'set'):
                variable.set(folder)
            if entry:
                entry.setText(folder)

    def show_success(self, root, message):
        """Show success dialog"""
        dialog = QDialog(root)
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
        ok_btn = ModernButton(dialog, "OK", dialog.accept,
                            bg_color=self.colors['primary'],
                            hover_color=self.colors['primary_hover'],
                            width=120, height=40)
        layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()