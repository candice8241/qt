# Interactive XRD Peak Fitting Tool - Enhanced Colorful UI

## Overview

This is an enhanced version of the Interactive XRD Peak Fitting Tool with a vibrant, colorful user interface. The UI has been completely redesigned to match a modern, visually appealing aesthetic with pastel colors and improved visual hierarchy.

## Features

### Core Functionality (Unchanged)
- Load XRD data files (.xy, .dat, .chi, .txt)
- Automatic peak detection with adjustable parameters
- Manual peak selection by clicking on the plot
- Interactive peak parameter adjustment
- Voigt and Pseudo-Voigt profile fitting
- Background subtraction with multiple methods
- Data smoothing (Gaussian, Savitzky-Golay, Moving Average)
- Export fitted results to CSV
- File navigation (previous/next in folder)
- Undo functionality

### UI Enhancements (New)
- **Colorful Panel Backgrounds**: Each section has a distinct pastel background color
  - Control Panel: Light purple (#C7BFFF)
  - Background Panel: Light blue (#E3F2FF)
  - Smoothing Panel: Light purple tint (#F3E5FF)
  - Results Panel: Light yellow (#FFF9DB)
  - Plot Area: Light purple (#E8E4FF)
  - Info Panel: Light blue (#E3F2FF)

- **Vibrant Button Colors**: Each button has a unique pastel color for easy identification
  - Purple, blue, green, pink, orange, and more!
  
- **Color-Coded Labels**: Important labels use different colors (cyan, pink, red, orange, purple)

- **Improved Visual Hierarchy**: Colored borders and backgrounds help organize the interface

## Installation

### Requirements

```bash
pip install numpy pandas matplotlib scipy scikit-learn PyQt6
```

### Required Packages
- `numpy` - Numerical computations
- `pandas` - Data handling and CSV export
- `matplotlib` - Plotting and visualization
- `scipy` - Scientific computing (peak finding, curve fitting)
- `scikit-learn` - Clustering algorithms (DBSCAN for peak grouping)
- `PyQt6` - GUI framework

## Usage

### Running the Application

```bash
python3 interactive_fitting_gui.py
```

Or use the test script:

```bash
python3 test_colorful_gui.py
```

### Basic Workflow

1. **Load Data**
   - Click "Load File" button (purple)
   - Select your XRD data file (.xy, .dat, .chi, .txt)
   - The data will be displayed in the plot area

2. **Detect Peaks**
   - Click "Auto Find" button (sky blue) to automatically detect peaks
   - Or manually click on peaks in the plot to add them
   - Click on an existing peak to remove it

3. **Adjust Parameters**
   - Select fitting method: "pseudo_voigt" or "voigt"
   - Adjust "Overlap FWHM×" for peak overlap detection
   - Adjust "Fit Window×" to control fitting window size

4. **Fit Peaks**
   - Click "Fit Peaks" button (pale purple)
   - The fitted curves will be displayed on the plot
   - Results appear in the table below

5. **Background Subtraction** (Optional)
   - Click "Select BG Points" to enter background selection mode
   - Click on the plot to add background points
   - Click "Subtract BG" to remove background
   - Or use "Auto Select BG" for automatic background point selection

6. **Smoothing** (Optional)
   - Check "Enable" checkbox in the Smoothing panel
   - Select method (gaussian or savgol)
   - Adjust Sigma or Window parameters
   - Click "Apply" to smooth the data
   - Click "Reset Data" to restore original data

7. **Export Results**
   - Click "Save Results" button (mint green)
   - Choose a location to save the CSV file
   - Results include peak positions, FWHM, areas, and fit parameters

### Keyboard Shortcuts & Tips

- Use the matplotlib toolbar at the bottom to:
  - Pan: Click the pan tool and drag
  - Zoom: Click the zoom tool and select a region
  - Reset view: Click the home icon
  - Save plot: Click the save icon

- Navigation between files:
  - Click "◀" (left arrow) for previous file
  - Click "▶" (right arrow) for next file

- Click "Undo" to undo the last action

- Mouse coordinates are displayed in real-time in the Background panel (right side)

## UI Color Guide

### Button Colors and Functions

| Button | Color | Function |
|--------|-------|----------|
| Load File | Light Purple | Open file dialog to load XRD data |
| ◀ / ▶ | Light Blue | Navigate to previous/next file |
| Fit Peaks | Pale Purple | Fit all detected peaks |
| Reset | Peach | Clear all peaks and reset |
| Save Results | Mint Green | Export results to CSV |
| Clear Fit | Light Pink | Clear fitted curves |
| Undo | Very Light Purple | Undo last action |
| Auto Find | Sky Blue | Automatically detect peaks |
| Overlap | Light Cyan | Detect overlapping peaks |
| Batch Auto Fit | Pale Lavender | Batch processing (future feature) |

### Panel Sections

1. **Control Panel** (Top, Light Purple Background)
   - Main action buttons for file operations and peak fitting

2. **Background Panel** (Light Blue Background)
   - Background subtraction controls
   - Fitting method selection
   - Parameter adjustments

3. **Smoothing Panel** (Light Purple Background)
   - Data smoothing options
   - Method selection and parameter controls

4. **Results Panel** (Light Yellow Background)
   - Table displaying fitted peak parameters
   - Columns: Peak #, 2theta, FWHM, Area, Amplitude, Sigma, Gamma, Eta

5. **Plot Area** (Light Purple Background, White Plot)
   - Main visualization area
   - Interactive peak selection
   - Fitted curve display

6. **Info Panel** (Bottom, Light Blue Background)
   - Status messages and help text
   - Coordinate display

## File Format

### Input Data Format

The application supports text-based XRD data files with two columns:
```
# Optional comment lines starting with #
2theta_1  intensity_1
2theta_2  intensity_2
2theta_3  intensity_3
...
```

Supported file extensions: `.xy`, `.dat`, `.chi`, `.txt`

### Output CSV Format

The exported CSV file contains the following columns:
- Peak #: Sequential peak number
- Center (2θ): Peak center position in degrees
- Amplitude: Peak amplitude
- Sigma: Gaussian width parameter
- Gamma: Lorentzian width parameter
- Eta: Mixing parameter (only for pseudo-Voigt)

## Advanced Features

### Peak Clustering (Overlap Detection)

The "Overlap" button uses DBSCAN clustering to group nearby peaks:
1. Click "Overlap" button
2. The algorithm calculates distances between peaks
3. Groups peaks based on the "Overlap FWHM×" threshold
4. Displays the number of peak groups found

### Batch Processing

The "Batch Auto Fit" button is available for future batch processing functionality.

### Undo System

The application maintains an undo stack (up to 20 steps) that tracks:
- Peak additions/removals
- Background point changes
- Data modifications (smoothing, background subtraction)

## Troubleshooting

### Common Issues

1. **"No peaks detected"**
   - Try adjusting the auto-detection sensitivity
   - Manually click on peaks to add them
   - Check if data is properly loaded

2. **Fitting fails**
   - Peak might be too close to data edge
   - Try adjusting "Fit Window×" parameter
   - Ensure background subtraction is appropriate

3. **Background subtraction doesn't look right**
   - Add more background points manually
   - Try "Auto Select BG" for automatic points
   - Clear background and try again

4. **Colors are too bright**
   - The colorful design is intentional for better visual hierarchy
   - Reduces eye strain with pastel colors
   - Each section is visually distinct

## Code Structure

### Main Classes

- `DataProcessor`: Handles data smoothing and preprocessing
- `PeakClusterer`: Peak grouping using DBSCAN
- `BackgroundFitter`: Background estimation and subtraction
- `PeakProfile`: Peak shape functions (Voigt, Pseudo-Voigt)
- `PeakDetector`: Automatic peak detection
- `InteractiveFittingGUI`: Main GUI class

### Key Methods

- `load_data_file()`: Load XRD data from file
- `auto_detect_peaks()`: Automatic peak detection
- `fit_all_peaks()`: Fit all detected peaks
- `subtract_background()`: Background subtraction
- `apply_smoothing_to_data()`: Apply data smoothing
- `export_results()`: Export fitted results to CSV

## Development

### Modifying Colors

All colors are defined in the `self.palette` dictionary in the `__init__` method of `InteractiveFittingGUI`. To change colors:

```python
self.palette = {
    'background': '#D4CCFF',  # Main background
    'primary': '#B794F6',      # Primary accent
    'success': '#7FD857',      # Success actions
    'warning': '#FFB84D',      # Warning actions
    'danger': '#FF8A80',       # Danger actions
    # ... add more colors as needed
}
```

### Adding New Features

To add new buttons or panels:
1. Create widgets in the appropriate `setup_*_panel()` method
2. Apply consistent styling using the color palette
3. Connect signals to appropriate handler methods

## License

[Add your license information here]

## Credits

- Original Author: candicewang928@gmail.com
- UI Enhancement: [Your name/team]
- Color Scheme: Inspired by modern pastel UI design trends

## Support

For issues or questions:
- Check the troubleshooting section above
- Review the code comments for implementation details
- Consult the scipy and matplotlib documentation for advanced features
