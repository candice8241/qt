# UI Customization Guide
# Interactive XRD Peak Fitting Tool - Enhanced

This guide explains how to customize the user interface appearance using configuration files.

## Configuration Files

### 1. `ui_config.json` (Recommended for quick customization)
JSON format configuration file that's easy to edit. You can modify colors, fonts, and button labels without touching Python code.

### 2. `ui_config.py` (For advanced customization)
Python module with helper functions and more detailed style definitions.

## How to Customize Colors

### Editing `ui_config.json`

Open `ui_config.json` and modify the color values:

```json
{
  "colors": {
    "bg_header": "#9775FA",        // Purple for Background section
    "smooth_header": "#228BE6",     // Blue for Smoothing section
    "results_header": "#FF6B9D",    // Pink for Results section
    ...
  }
}
```

### Color Reference

All colors use hex format (`#RRGGBB`). Here are the main color categories:

#### Section Background Colors
- `bg_section_bg`: Background section panel color
- `smooth_section_bg`: Smoothing section panel color
- `results_section_bg`: Results section panel color

#### Section Header Colors
- `bg_header`: Background section title color
- `smooth_header`: Smoothing section title color
- `results_header`: Results section title color

#### Button Colors
- `btn_load`: Load File button
- `btn_nav`: Navigation buttons (◀ ▶)
- `btn_fit`: Fit Peaks button
- `btn_reset`: Reset button
- `btn_save`: Save Results button
- `btn_clear`: Clear Fit button
- `btn_undo`: Undo button
- `btn_auto`: Auto Find button
- `btn_overlap`: Overlap button
- `btn_batch`: Batch Auto Fit button
- `btn_settings`: Settings button (⚙)

#### Background Section Buttons
- `btn_select_bg`: Select BG Points
- `btn_subtract_bg`: Subtract BG
- `btn_clear_bg`: Clear BG
- `btn_auto_bg`: Auto Select BG

#### Smoothing Section Buttons
- `btn_apply`: Apply button
- `btn_reset_data`: Reset Data button

## How to Customize Fonts

Edit the `fonts` section:

```json
{
  "fonts": {
    "family": "Arial",
    "sizes": {
      "large": 14,
      "header": 10,
      "normal": 9,
      "small": 8
    }
  }
}
```

### Available Font Families
- Arial (default)
- Helvetica
- Times New Roman
- Courier New
- Verdana
- Georgia

## How to Customize Button Text

Edit the `buttons` section to change button labels:

```json
{
  "buttons": {
    "control_panel": [
      {"text": "Load File", "color": "btn_load"},
      {"text": "Fit Peaks", "color": "btn_fit"},
      ...
    ]
  }
}
```

## How to Customize Section Heights

Edit the `sections` section:

```json
{
  "sections": {
    "control_panel": {
      "height": 55
    },
    "background": {
      "height": 50
    },
    "smoothing": {
      "height": 50
    },
    "results": {
      "height": 120
    }
  }
}
```

## Example: Creating a Dark Theme

```json
{
  "colors": {
    "main_bg": "#1E1E1E",
    "panel_white": "#2D2D2D",

    "bg_section_bg": "#1A2332",
    "smooth_section_bg": "#2A1A32",
    "results_section_bg": "#322A1A",

    "bg_header": "#BB86FC",
    "smooth_header": "#03DAC6",
    "results_header": "#CF6679",

    "text_dark": "#E1E1E1",
    "text_light": "#B0B0B0",
    ...
  }
}
```

## Example: Creating a Minimalist Theme

```json
{
  "colors": {
    "bg_section_bg": "#FAFAFA",
    "smooth_section_bg": "#FAFAFA",
    "results_section_bg": "#FAFAFA",

    "bg_header": "#333333",
    "smooth_header": "#333333",
    "results_header": "#333333",

    "btn_load": "#4A4A4A",
    "btn_fit": "#4A4A4A",
    "btn_save": "#4A4A4A",
    ...
  }
}
```

## Color Scheme Templates

### Template 1: Warm Colors
```json
{
  "bg_header": "#E07A5F",      // Coral
  "smooth_header": "#F2CC8F",   // Warm yellow
  "results_header": "#81B29A"   // Sage green
}
```

### Template 2: Cool Colors
```json
{
  "bg_header": "#5E60CE",      // Blue violet
  "smooth_header": "#4EA8DE",   // Sky blue
  "results_header": "#56CFE1"   // Cyan
}
```

### Template 3: Pastel Colors
```json
{
  "bg_header": "#FFB4A2",      // Pastel coral
  "smooth_header": "#B4D8E7",   // Pastel blue
  "results_header": "#FFCAD4"   // Pastel pink
}
```

## Applying Changes

After modifying `ui_config.json`, restart the application to see your changes.

## Troubleshooting

### Colors not changing
- Make sure hex color codes start with `#`
- Use 6-digit hex format: `#RRGGBB`
- Check for typos in color names

### Invalid JSON
- Use a JSON validator (https://jsonlint.com/)
- Check for missing commas or quotes
- Ensure proper bracket matching

### Fonts not displaying
- Make sure the font is installed on your system
- Fall back to "Arial" if custom font doesn't work

## Quick Reference: Current Color Scheme

| Component | Color Code | Description |
|-----------|-----------|-------------|
| Background Header | #9775FA | Purple |
| Smoothing Header | #228BE6 | Blue |
| Results Header | #FF6B9D | Pink |
| Load File | #9B86BD | Muted purple |
| Navigation | #CBA6F7 | Lavender |
| Fit Peaks | #E4B4E4 | Light pink |
| Reset | #FA9999 | Salmon |
| Save Results | #51CF66 | Green |
| Clear Fit | #FFB366 | Orange |
| Overlap | #AAAAAA | Gray |
| Batch Auto Fit | #74C0FC | Cyan |

## Support

For questions or issues with customization, please refer to the main README or open an issue in the repository.
