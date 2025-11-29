#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example: How to use ui_config.py in your application

This example shows how to integrate the UI configuration files
into the Interactive Fitting GUI.
"""

from PyQt6.QtWidgets import QPushButton, QLabel
from PyQt6.QtGui import QFont
import ui_config as cfg

# ==================== Example 1: Creating buttons with config ====================
def create_button_example():
    """Example of creating a button using configuration"""

    # Create a button
    load_btn = QPushButton("Load File")

    # Apply style from config
    btn_color = cfg.COLORS['btn_load']
    btn_style = cfg.get_button_style(
        button_type='control_panel',
        bg_color=btn_color,
        text_color=cfg.COLORS['text_white']
    )
    load_btn.setStyleSheet(btn_style)

    return load_btn


# ==================== Example 2: Creating labels with section colors ====================
def create_section_label(section_name, text):
    """Create a section label with appropriate color"""

    label = QLabel(text)
    label.setFont(QFont(
        cfg.FONTS['family'],
        cfg.FONTS['sizes']['header'],
        QFont.Weight.Bold
    ))

    # Get color based on section
    section_config = cfg.SECTIONS[section_name]
    label_color = section_config.get('header_color', cfg.COLORS['text_dark'])
    label.setStyleSheet(f"color: {label_color}; background: transparent;")

    return label


# ==================== Example 3: Using JSON config ====================
def load_json_config():
    """Example of loading and using JSON configuration"""
    import json

    with open('ui_config.json', 'r') as f:
        config = json.load(f)

    # Access colors
    bg_header_color = config['colors']['bg_header']
    smooth_header_color = config['colors']['smooth_header']

    # Access button definitions
    control_buttons = config['buttons']['control_panel']

    print(f"Background header color: {bg_header_color}")
    print(f"Number of control buttons: {len(control_buttons)}")

    return config


# ==================== Example 4: Creating styled input widgets ====================
def create_input_widgets():
    """Example of creating input widgets with config styles"""
    from PyQt6.QtWidgets import QLineEdit, QComboBox

    # Line edit
    line_edit = QLineEdit("5.0")
    line_edit.setStyleSheet(cfg.get_input_style('line_edit'))

    # Combo box
    combo_box = QComboBox()
    combo_box.addItems(['Option 1', 'Option 2'])
    combo_box.setStyleSheet(cfg.get_combo_style())

    return line_edit, combo_box


# ==================== Example 5: Programmatically change theme ====================
def apply_custom_theme():
    """Example: Apply a custom color theme"""

    # Define custom colors (override defaults)
    custom_colors = {
        'bg_header': '#E07A5F',     # Coral
        'smooth_header': '#F2CC8F',  # Warm yellow
        'results_header': '#81B29A', # Sage green
    }

    # Update config
    cfg.COLORS.update(custom_colors)

    # Now when you create widgets, they'll use the new colors
    bg_label = create_section_label('background', 'Background:')

    return bg_label


# ==================== Example 6: Dynamic button creation from config ====================
def create_all_control_buttons():
    """Create all control panel buttons from config"""

    buttons = []
    for btn_config in cfg.CONTROL_BUTTONS:
        btn = QPushButton(btn_config['text'])

        # Get color
        color_key = btn_config['color']
        bg_color = cfg.COLORS[color_key]

        # Apply style
        style = cfg.get_button_style(
            button_type='control_panel',
            bg_color=bg_color,
            text_color=cfg.COLORS['text_white']
        )
        btn.setStyleSheet(style)

        # Set width if specified
        if btn_config.get('width'):
            btn.setFixedWidth(btn_config['width'])

        buttons.append(btn)

    return buttons


# ==================== Usage in main application ====================
if __name__ == '__main__':
    """
    To use the configuration in your main application:

    1. Import the config module:
       import ui_config as cfg

    2. Use colors from cfg.COLORS:
       button.setStyleSheet(f"background-color: {cfg.COLORS['btn_load']}")

    3. Use helper functions:
       button.setStyleSheet(cfg.get_button_style('control_panel', cfg.COLORS['btn_load']))

    4. Load from JSON if you prefer:
       config = json.load(open('ui_config.json'))
       color = config['colors']['btn_load']
    """

    print("UI Configuration Examples")
    print("=" * 50)

    # Example: Print all available colors
    print("\nAvailable Colors:")
    for key, value in cfg.COLORS.items():
        print(f"  {key}: {value}")

    # Example: Print button configurations
    print("\nControl Panel Buttons:")
    for btn in cfg.CONTROL_BUTTONS:
        print(f"  {btn['text']} - Color: {btn['color']}")

    # Example: Load JSON config
    print("\nLoading JSON config...")
    json_config = load_json_config()

    print("\n✓ Configuration loaded successfully!")
    print("\nTo customize the UI:")
    print("1. Edit ui_config.json to change colors and labels")
    print("2. Or modify ui_config.py for advanced customization")
    print("3. See UI_CUSTOMIZATION_GUIDE.md for detailed instructions")
