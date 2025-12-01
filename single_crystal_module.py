# -*- coding: utf-8 -*-
"""
Single Crystal Module
Placeholder for future single crystal XRD functionality
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from gui_base import GUIBase


class SingleCrystalModule(GUIBase):
    """Single crystal XRD module (placeholder)"""

    def __init__(self, parent, root):
        """
        Initialize Single Crystal module

        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        super().__init__()
        self.parent = parent
        self.root = root

    def setup_ui(self):
        """Setup placeholder UI for single crystal module"""
        # Get or create layout for parent
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 50, 0, 50)

        # Create main frame
        main_frame = QWidget(self.parent)
        main_frame.setStyleSheet(f"background-color: {self.colors['bg']};")
        main_layout = QVBoxLayout(main_frame)

        # Create card
        card = self.create_card_frame(main_frame)
        content = QWidget(card)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(50, 50, 50, 50)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content.setStyleSheet(f"background-color: {self.colors['card_bg']};")

        # Emoji
        emoji_label = QLabel("🔬", content)
        emoji_label.setFont(QFont('Segoe UI Emoji', 48))
        emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_label.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        content_layout.addWidget(emoji_label)

        # Title
        title_label = QLabel("Single Crystal", content)
        title_label.setFont(QFont('Comic Sans MS', 20, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Coming soon...", content)
        subtitle_label.setFont(QFont('Comic Sans MS', 12))
        subtitle_label.setStyleSheet(f"color: {self.colors['text_light']}; background-color: {self.colors['card_bg']};")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(subtitle_label)

        # Set layout for card
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(content)

        main_layout.addWidget(card)
        layout.addWidget(main_frame)