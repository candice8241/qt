# Batch Peak Fitting Module

## Overview
The Batch Peak Fitting Module provides a standalone interface for batch processing multiple XRD data files (.xy format) with interactive peak and background adjustment capabilities.

## Features
- **Standalone Operation**: Can be run independently without launching the full curvefit interface
- **Batch Processing**: Process multiple .xy files in one session
- **Interactive Adjustment**: Manually add/remove peaks and background points
- **Auto-Fitting**: Automatic peak detection and fitting
- **Multiple Fitting Methods**: Support for Pseudo-Voigt and Voigt profiles
- **Overlap Mode**: Compare multiple files simultaneously
- **Export Results**: Save fitting results to CSV format

## Usage

### Method 1: Standalone Launch
Run the batch module directly as a standalone application:

```bash
python batch_module.py
```

This will open the Batch Peak Fitting interface directly without the main GUI.

### Method 2: From Main Application
Launch from the main application sidebar:

1. Start the main application: `python main.py`
2. Click the "📊 Batch" button in the left sidebar
3. The batch processing interface will open

### Method 3: From Curvefit (Legacy)
The batch module can still be accessed from within the curvefit interface:

1. Click "📈 curvefit" in the main application sidebar
2. Click the "Batch" button in the curvefit control panel

## Interface Components

### File Management
- **Load Folder**: Select a folder containing .xy files for batch processing
- **File List**: View and navigate through loaded files
- **Navigation**: Use Previous/Next buttons or arrow keys to move between files

### Peak Adjustment
- **Add Mode**: Switch between Peak mode (🔴) and Background mode (🔵)
- **Auto Detect**: Automatically detect peaks in the current file
- **Manual Addition**: Left-click to add peaks/background points
- **Manual Removal**: Right-click to remove peaks/background points
- **Clear All**: Remove all peaks and background points

### Fitting Options
- **Fit Method**: Choose between Pseudo-Voigt and Voigt profiles
- **Fit Current**: Fit the current file with selected peaks
- **Auto Fit**: Automatically fit all remaining files (Enter key)
- **Overlap Mode**: Compare multiple files simultaneously

### View Controls
- **Zoom**: Scroll to zoom in/out on the plot
- **Reset Zoom**: Return to original view (R key)

### Keyboard Shortcuts
- **Enter**: Start auto-fitting mode
- **Left Arrow**: Previous file
- **Right Arrow**: Next file
- **Space**: Fit current file
- **A**: Auto-detect peaks
- **C**: Clear all peaks and background
- **P**: Switch to peak mode
- **B**: Switch to background mode
- **R**: Reset zoom
- **O**: Toggle overlap mode

## Output

Results are saved to a CSV file in the `fit_output` subfolder within the selected data folder.

Output format:
- **File**: Filename (without extension)
- **Peak**: Peak identifier (Peak 1, Peak 2, etc.)
- **Center**: Peak center position
- **FWHM**: Full width at half maximum
- **Area**: Integrated peak area
- **Intensity**: Peak intensity
- **R_squared**: Goodness of fit (R² value)

## Workflow Example

1. Click "Load Folder" and select your data folder
2. The first file will load automatically with auto-detected peaks
3. Adjust peaks and background points as needed:
   - Click to add peaks (in Peak mode) or background points (in Background mode)
   - Right-click to remove peaks/background points
4. Press "Fit Current" or Space to fit the current file
5. Use arrow keys or click "Next" to move to the next file
6. Press Enter to enable Auto-Fit mode for batch processing
7. Click "Save All Results" when complete

## Technical Details

### File Structure
- `batch_module.py`: Standalone launcher for the batch module
- `batch_fitting_dialog.py`: Core batch fitting functionality
- Main integration in `main.py` via the sidebar "Batch" button

### Dependencies
- PyQt6
- NumPy
- Pandas
- Matplotlib
- SciPy

### Peak Fitting
The module uses sophisticated peak fitting algorithms:
- **Single Peaks**: Fitted independently with automatic background subtraction
- **Overlapping Peaks**: Detected and fitted together as a group
- **Background**: Linear interpolation between user-defined points
- **Quality Metrics**: R² values to assess fit quality

## Notes

- The batch module is now independent from the curvefit interface
- All fitting functionality from curvefit is preserved in the batch module
- Files must be in .xy format with two columns (2θ and Intensity)
- Auto-fitting pauses if fit quality (R²) drops below threshold (default: 0.92)
