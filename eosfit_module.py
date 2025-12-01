# -*- coding: utf-8 -*-
"""
EoSFit Module - CrysFML EoS Fitting Interface
Provides a wrapper module for the CrysFML eosfit GUI
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTextEdit, QFrame, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from gui_base import GUIBase
from theme_module import ModernButton
from interactive_eos_gui import InteractiveEoSGUI


class EoSFitModule(GUIBase):
    """EoSFit module - Wrapper for CrysFML EoS fitting GUI"""

    def __init__(self, parent, root):
        """
        Initialize EoSFit module

        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        super().__init__()
        self.parent = parent
        self.root = root
        
        # Track the eosfit window
        self.eosfit_window = None

    def setup_ui(self):
        """Setup the EoSFit module UI"""
        # Get or create layout for parent
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 0, 0, 0)

        # Create main content widget
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {self.colors['bg']};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Title section
        title_frame = QWidget()
        title_frame.setStyleSheet(f"background-color: {self.colors['bg']};")
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 20)
        
        title_label = QLabel("🔬 Equation of State (EoS) Fitting")
        title_label.setFont(QFont('Arial', 20, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['bg']};")
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("CrysFML EoS Fitting Tool - Advanced P-V Analysis")
        subtitle_label.setFont(QFont('Arial', 11))
        subtitle_label.setStyleSheet(f"color: {self.colors['text_light']}; background-color: {self.colors['bg']};")
        title_layout.addWidget(subtitle_label)
        
        content_layout.addWidget(title_frame)
        
        # Description card
        desc_card = self.create_card_frame(content_widget)
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setContentsMargins(20, 20, 20, 20)
        
        desc_title = QLabel("📊 About EoSFit")
        desc_title.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        desc_title.setStyleSheet(f"color: {self.colors['primary']}; background-color: {self.colors['card_bg']};")
        desc_layout.addWidget(desc_title)
        
        desc_text = QTextEdit()
        desc_text.setReadOnly(True)
        desc_text.setFont(QFont('Arial', 10))
        desc_text.setMaximumHeight(150)
        desc_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colors['card_bg']};
                color: {self.colors['text_dark']};
                border: none;
            }}
        """)
        
        desc_content = """
<b>EoSFit</b> is an advanced tool for fitting Equation of State (EoS) models to pressure-volume (P-V) data.

<b>Key Features:</b>
• Multiple EoS models: Birch-Murnaghan (2nd, 3rd, 4th order), Murnaghan, Vinet, Natural Strain
• Interactive parameter adjustment with real-time visualization
• Smart initial guess and automatic fitting
• Parameter locking for selective refinement
• Comprehensive quality metrics (R², RMSE, χ²)
• CrysFML linearization method for stable B₀' determination

<b>Usage:</b>
Click the button below to open the EoSFit GUI window and start fitting your P-V data.
        """
        desc_text.setHtml(desc_content)
        desc_layout.addWidget(desc_text)
        
        content_layout.addWidget(desc_card)
        
        # Features card
        features_card = self.create_card_frame(content_widget)
        features_layout = QVBoxLayout(features_card)
        features_layout.setContentsMargins(20, 20, 20, 20)
        
        features_title = QLabel("✨ Supported EoS Models")
        features_title.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        features_title.setStyleSheet(f"color: {self.colors['primary']}; background-color: {self.colors['card_bg']};")
        features_layout.addWidget(features_title)
        
        # Model list
        models_layout = QVBoxLayout()
        models_layout.setSpacing(8)
        
        models = [
            ("Birch-Murnaghan 2nd Order", "Simple 2-parameter model (V₀, B₀)"),
            ("Birch-Murnaghan 3rd Order", "Standard model with B₀' (recommended)"),
            ("Birch-Murnaghan 4th Order", "Advanced model with B₀''"),
            ("Murnaghan", "Classical empirical EoS"),
            ("Vinet", "Universal EoS for extreme compression"),
            ("Natural Strain", "3rd order natural strain EoS")
        ]
        
        for model_name, model_desc in models:
            model_frame = QWidget()
            model_frame.setStyleSheet(f"background-color: {self.colors['card_bg']};")
            model_layout = QHBoxLayout(model_frame)
            model_layout.setContentsMargins(0, 0, 0, 0)
            
            bullet = QLabel("•")
            bullet.setFont(QFont('Arial', 12, QFont.Weight.Bold))
            bullet.setStyleSheet(f"color: {self.colors['accent']}; background-color: {self.colors['card_bg']};")
            model_layout.addWidget(bullet)
            
            model_label = QLabel(f"<b>{model_name}</b>: {model_desc}")
            model_label.setFont(QFont('Arial', 9))
            model_label.setStyleSheet(f"color: {self.colors['text_dark']}; background-color: {self.colors['card_bg']};")
            model_label.setWordWrap(True)
            model_layout.addWidget(model_label, 1)
            
            models_layout.addWidget(model_frame)
        
        features_layout.addLayout(models_layout)
        content_layout.addWidget(features_card)
        
        # Action button card
        action_card = self.create_card_frame(content_widget)
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(30, 30, 30, 30)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Main action button
        open_btn = QPushButton("🚀 Open EoSFit GUI")
        open_btn.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        open_btn.setFixedSize(300, 60)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['accent']};
            }}
        """)
        open_btn.clicked.connect(self.open_eosfit_window)
        action_layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        hint_label = QLabel("Click to launch the interactive EoS fitting window")
        hint_label.setFont(QFont('Arial', 9))
        hint_label.setStyleSheet(f"color: {self.colors['text_light']}; background-color: {self.colors['card_bg']};")
        action_layout.addWidget(hint_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        content_layout.addWidget(action_card)
        
        # Add stretch to push everything to top
        content_layout.addStretch()
        
        # Add to parent layout
        layout.addWidget(content_widget)

    def open_eosfit_window(self):
        """Open the EoSFit GUI window"""
        try:
            # Check if window already exists and is visible
            if self.eosfit_window is not None:
                try:
                    if self.eosfit_window.isVisible():
                        # Window exists and is visible, just raise it
                        self.eosfit_window.raise_()
                        self.eosfit_window.activateWindow()
                        return
                    else:
                        # Window exists but is hidden, show it
                        self.eosfit_window.show()
                        self.eosfit_window.raise_()
                        self.eosfit_window.activateWindow()
                        return
                except RuntimeError:
                    # Window was deleted, need to create new one
                    pass
            
            # Create new window
            from PyQt6.QtWidgets import QMainWindow
            
            # Create a standalone window
            self.eosfit_window = QMainWindow(self.root)
            self.eosfit_window.setWindowTitle("EoSFit - CrysFML Equation of State Fitting")
            self.eosfit_window.resize(1480, 900)
            
            # Create the EoS GUI widget
            eos_widget = InteractiveEoSGUI(self.eosfit_window)
            eos_widget.setVisible(True)  # Make sure it's visible
            self.eosfit_window.setCentralWidget(eos_widget)
            
            # Show the window
            self.eosfit_window.show()
            self.eosfit_window.raise_()
            self.eosfit_window.activateWindow()
            
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Failed to open EoSFit GUI:\n{str(e)}"
            )
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """Cleanup resources when module is closed"""
        if self.eosfit_window is not None:
            try:
                self.eosfit_window.close()
                self.eosfit_window.deleteLater()
            except:
                pass
            self.eosfit_window = None
