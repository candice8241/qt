#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UI Configuration for Interactive XRD Peak Fitting Tool
Defines all colors, fonts, and styles for the application
"""

# ==================== Color Palette ====================
COLORS = {
    # Background colors
    'main_bg': '#F5F5F5',
    'panel_white': '#FFFFFF',

    # Section background colors
    'bg_section_bg': '#E7F5FF',      # Light blue tint for Background section
    'smooth_section_bg': '#F3F0FF',   # Light purple tint for Smoothing section
    'results_section_bg': '#FFF9DB',  # Light yellow tint for Results section

    # Section header text colors
    'bg_header': '#9775FA',           # Purple for Background header
    'smooth_header': '#228BE6',       # Blue for Smoothing header
    'results_header': '#FF6B9D',      # Pink for Fitting Results header

    # Button colors
    'btn_load': '#9B86BD',            # Purple for Load File
    'btn_nav': '#CBA6F7',             # Lavender for navigation buttons
    'btn_fit': '#E4B4E4',             # Light pink for Fit Peaks
    'btn_reset': '#FA9999',           # Salmon pink for Reset
    'btn_save': '#51CF66',            # Green for Save Results
    'btn_clear': '#FFB366',           # Orange for Clear Fit
    'btn_undo': '#CBA6F7',            # Lavender for Undo
    'btn_auto': '#CBA6F7',            # Lavender for Auto Find
    'btn_overlap': '#AAAAAA',         # Gray for Overlap
    'btn_batch': '#74C0FC',           # Cyan for Batch Auto Fit
    'btn_settings': '#868E96',        # Gray for Settings

    # Background section buttons
    'btn_select_bg': '#9775FA',       # Purple for Select BG Points
    'btn_subtract_bg': '#51CF66',     # Green for Subtract BG
    'btn_clear_bg': '#FF6B6B',        # Red for Clear BG
    'btn_auto_bg': '#74C0FC',         # Cyan for Auto Select BG

    # Smoothing section buttons
    'btn_apply': '#51CF66',           # Green for Apply
    'btn_reset_data': '#FF6B6B',      # Red for Reset Data

    # Text colors
    'text_dark': '#212529',
    'text_light': '#868E96',
    'text_white': '#FFFFFF',

    # Border colors
    'border_dark': '#495057',
    'border_light': '#CED4DA',
    'border_table': '#DEE2E6',
}

# ==================== Font Configuration ====================
FONTS = {
    'family': 'Arial',
    'sizes': {
        'large': 14,
        'header': 10,
        'normal': 9,
        'small': 8,
        'icon': 14,
    },
    'weights': {
        'normal': 'normal',
        'bold': 'bold',
    }
}

# ==================== Button Styles ====================
BUTTON_STYLES = {
    'control_panel': {
        'font_size': '10pt',
        'border': '2px solid #495057',
        'border_radius': '4px',
        'padding': '6px 10px',
        'min_width': '70px',
    },
    'section_button': {
        'font_size': '9pt',
        'border': '2px solid #495057',
        'border_radius': '3px',
        'padding': '5px 10px',
        'min_width': '60px',
    },
    'nav_button': {
        'width': 35,
        'min_width': '25px',
    },
    'settings_button': {
        'width': 35,
        'font_size': '14pt',
    }
}

# ==================== Section Configuration ====================
SECTIONS = {
    'control_panel': {
        'height': 55,
        'bg_color': '#FFFFFF',
        'border': '2px solid #DEE2E6',
        'margin': (8, 5, 8, 5),
        'spacing': 4,
    },
    'background': {
        'height': 50,
        'bg_color': '#E7F5FF',
        'header_color': '#9775FA',
        'label_color': '#9775FA',
        'margin': (8, 5, 8, 5),
        'spacing': 4,
    },
    'smoothing': {
        'height': 50,
        'bg_color': '#F3F0FF',
        'header_color': '#228BE6',
        'label_color': '#228BE6',
        'margin': (8, 5, 8, 5),
        'spacing': 4,
    },
    'results': {
        'height': 120,
        'bg_color': '#FFF9DB',
        'header_color': '#FF6B9D',
        'margin': (8, 4, 8, 4),
        'spacing': 3,
    },
    'plot': {
        'bg_color': '#FFFFFF',
        'plot_bg': '#F8F9FA',
        'grid_color': '#ADB5BD',
        'grid_alpha': 0.3,
        'margin': (5, 5, 5, 5),
        'spacing': 2,
    },
    'info': {
        'height': 75,
        'bg_color': '#E7F5FF',
        'margin': (8, 4, 8, 4),
    }
}

# ==================== Input Widget Styles ====================
INPUT_STYLES = {
    'combo_box': {
        'padding': '3px',
        'border': '1px solid #CED4DA',
        'bg_color': '#FFFFFF',
        'text_color': '#212529',
    },
    'line_edit': {
        'padding': '3px',
        'border': '1px solid #CED4DA',
        'bg_color': '#FFFFFF',
        'text_color': '#212529',
    },
    'text_edit': {
        'border': '1px solid #DEE2E6',
        'border_radius': '3px',
        'bg_color': '#FFFFFF',
        'text_color': '#212529',
    }
}

# ==================== Table Styles ====================
TABLE_STYLES = {
    'bg_color': '#FFFFFF',
    'gridline_color': '#DEE2E6',
    'border': '1px solid #DEE2E6',
    'header_bg': '#F8F9FA',
    'header_text': '#212529',
    'header_font_size': '8pt',
    'header_padding': '3px',
    'column_widths': [45, 90, 90, 90, 90, 75, 75, 55],
}

# ==================== Plot Styles ====================
PLOT_STYLES = {
    'figure_size': (12, 6),
    'figure_bg': 'white',
    'margins': {
        'left': 0.12,
        'right': 0.98,
        'top': 0.92,
        'bottom': 0.15,
    },
    'ax_bg': '#F8F9FA',
    'grid': {
        'enabled': True,
        'alpha': 0.3,
        'linestyle': '--',
        'color': '#ADB5BD',
    },
    'labels': {
        'fontsize': 12,
        'color': '#212529',
        'fontweight': 'bold',
    },
    'title': {
        'fontsize': 10,
        'color': '#5C7CFA',
    }
}

# ==================== Control Panel Button Definitions ====================
CONTROL_BUTTONS = [
    {'text': 'Load File', 'color': 'btn_load', 'width': None, 'callback': 'load_data_file'},
    {'text': '◀', 'color': 'btn_nav', 'width': 35, 'callback': 'prev_file'},
    {'text': '▶', 'color': 'btn_nav', 'width': 35, 'callback': 'next_file'},
    {'text': 'Fit Peaks', 'color': 'btn_fit', 'width': None, 'callback': 'fit_all_peaks'},
    {'text': 'Reset', 'color': 'btn_reset', 'width': None, 'callback': 'clear_peaks'},
    {'text': 'Save Results', 'color': 'btn_save', 'width': None, 'callback': 'export_results'},
    {'text': 'Clear Fit', 'color': 'btn_clear', 'width': None, 'callback': 'clear_peaks'},
    {'text': 'Undo', 'color': 'btn_undo', 'width': None, 'callback': 'undo_action'},
    {'text': 'Auto Find', 'color': 'btn_auto', 'width': None, 'callback': 'auto_detect_peaks'},
    {'text': 'Overlap', 'color': 'btn_overlap', 'width': None, 'callback': 'toggle_overlap_mode'},
    {'text': 'Batch Auto Fit', 'color': 'btn_batch', 'width': None, 'callback': None},
    {'text': '⚙', 'color': 'btn_settings', 'width': 35, 'callback': None, 'font_size': '14pt'},
]

# ==================== Background Section Button Definitions ====================
BACKGROUND_BUTTONS = [
    {'text': 'Select BG Points', 'color': 'btn_select_bg', 'callback': 'toggle_bg_selection'},
    {'text': 'Subtract BG', 'color': 'btn_subtract_bg', 'callback': 'subtract_background'},
    {'text': 'Clear BG', 'color': 'btn_clear_bg', 'callback': 'clear_background'},
    {'text': 'Auto Select BG', 'color': 'btn_auto_bg', 'callback': 'auto_select_background'},
]

# ==================== Helper Functions ====================
def get_button_style(button_type='control_panel', bg_color=None, text_color='#FFFFFF'):
    """Generate button stylesheet"""
    style_config = BUTTON_STYLES.get(button_type, BUTTON_STYLES['control_panel'])

    style = f"""
        QPushButton {{
            font-family: {FONTS['family']};
            font-size: {style_config['font_size']};
            font-weight: bold;
            border: {style_config['border']};
            border-radius: {style_config['border_radius']};
            padding: {style_config['padding']};
            min-width: {style_config['min_width']};
            background-color: {bg_color if bg_color else 'transparent'};
            color: {text_color};
        }}
        QPushButton:hover {{
            opacity: 0.9;
        }}
        QPushButton:pressed {{
            padding: 7px 9px 5px 11px;
        }}
    """
    return style

def get_input_style(widget_type='line_edit'):
    """Generate input widget stylesheet"""
    config = INPUT_STYLES.get(widget_type, INPUT_STYLES['line_edit'])

    style = f"""
        QLineEdit {{
            padding: {config['padding']};
            color: {config['text_color']};
            background-color: {config['bg_color']};
            border: {config['border']};
        }}
    """
    return style

def get_combo_style():
    """Generate combobox stylesheet"""
    config = INPUT_STYLES['combo_box']

    style = f"""
        QComboBox {{
            padding: {config['padding']};
            color: {config['text_color']};
            background-color: {config['bg_color']};
            border: {config['border']};
        }}
        QComboBox QAbstractItemView {{
            color: {config['text_color']};
            background-color: {config['bg_color']};
        }}
    """
    return style

def get_table_style():
    """Generate table stylesheet"""
    style = f"""
        QTableWidget {{
            background-color: {TABLE_STYLES['bg_color']};
            gridline-color: {TABLE_STYLES['gridline_color']};
            border: {TABLE_STYLES['border']};
        }}
        QHeaderView::section {{
            background-color: {TABLE_STYLES['header_bg']};
            color: {TABLE_STYLES['header_text']};
            font-weight: bold;
            font-family: {FONTS['family']};
            font-size: {TABLE_STYLES['header_font_size']};
            border: {TABLE_STYLES['border']};
            padding: {TABLE_STYLES['header_padding']};
        }}
    """
    return style
