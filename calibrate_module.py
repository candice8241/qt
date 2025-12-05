# -*- coding: utf-8 -*-
"""
Detector Calibration Module - Qt Version
Integrates Dioptas calibration functionality for detector orientation calibration using standard samples

Features:
- Load calibration images (standard samples)
- Detector calibration using pyFAI
- Mask creation and editing
- PONI file generation
- Real-time calibration preview

Created: 2025
@author: XRD Processing Suite
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QCheckBox, QComboBox, QGroupBox,
                              QFileDialog, QMessageBox, QFrame, QScrollArea, QSplitter,
                              QListWidget, QListWidgetItem, QSlider, QRadioButton, QButtonGroup,
                              QSpinBox, QDoubleSpinBox, QToolBox, QTabWidget, QTableWidget,
                              QTableWidgetItem, QHeaderView, QDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import os
import sys
import numpy as np
from gui_base import GUIBase
from theme_module import ModernButton
from custom_widgets import CustomSpinbox

# Import pyFAI and related libraries
try:
    import pyFAI
    from pyFAI.calibrant import Calibrant, ALL_CALIBRANTS
    from pyFAI.geometryRefinement import GeometryRefinement
    from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
    PYFAI_AVAILABLE = True
except ImportError:
    PYFAI_AVAILABLE = False
    print("Warning: pyFAI not available. Install with: pip install pyFAI")

try:
    import fabio
    FABIO_AVAILABLE = True
except ImportError:
    FABIO_AVAILABLE = False
    print("Warning: fabio not available. Install with: pip install fabio")

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False


class CalibrationWorkerThread(QThread):
    """Worker thread for calibration processing"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    calibration_result = pyqtSignal(object)  # Emits calibration result

    def __init__(self, target_func, *args, **kwargs):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Run the calibration function"""
        try:
            result = self.target_func(*self.args, **self.kwargs)
            self.calibration_result.emit(result)
            self.finished.emit("Calibration completed successfully")
        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class MaskCanvas(FigureCanvas):
    """Canvas for displaying and editing masks"""
    
    def __init__(self, parent=None, width=6, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.image_data = None
        self.mask_data = None
        self.drawing = False
        self.mask_mode = 'rectangle'  # rectangle, circle, polygon, threshold
        self.mask_value = True  # True = mask (hide), False = unmask (show)
        self.start_point = None
        self.temp_patches = []
        self.preview_patch = None  # Temporary preview shape
        
        # Zoom and contrast settings
        self.zoom_level = 1.0
        self.contrast_min = None
        self.contrast_max = None
        self.base_xlim = None
        self.base_ylim = None
        
        # Performance optimization
        self._last_preview_pos = None
        self._background = None  # Store background for blitting
        
        # Connect mouse events
        self.mpl_connect('button_press_event', self.on_mouse_press)
        self.mpl_connect('button_release_event', self.on_mouse_release)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.mpl_connect('scroll_event', self.on_scroll)
        
        # Enable blitting for better performance
        self.mpl_connect('draw_event', self.on_draw)
        
    def load_image(self, image_path):
        """Load image for mask editing"""
        try:
            if FABIO_AVAILABLE:
                img = fabio.open(image_path)
                self.image_data = img.data
            else:
                # Fallback to simple image loading
                from PIL import Image
                img = Image.open(image_path)
                self.image_data = np.array(img)
            
            # Initialize mask if needed
            if self.mask_data is None or self.mask_data.shape != self.image_data.shape:
                self.mask_data = np.zeros(self.image_data.shape, dtype=bool)
            
            self.display_image()
            return True
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
    
    def display_image(self):
        """Display the image with mask overlay"""
        self.axes.clear()
        if self.image_data is not None:
            # Apply contrast settings
            if self.contrast_min is not None and self.contrast_max is not None:
                display_data = np.clip(self.image_data, self.contrast_min, self.contrast_max)
                vmin, vmax = np.log10(self.contrast_min + 1), np.log10(self.contrast_max + 1)
            else:
                display_data = self.image_data
                vmin, vmax = None, None
            
            # Display image with log scale
            # Use lower interpolation for large images
            interp = 'nearest' if self.image_data.size > 4000000 else 'bilinear'
            im = self.axes.imshow(np.log10(display_data + 1), cmap='viridis', 
                                 origin='lower', vmin=vmin, vmax=vmax, 
                                 interpolation=interp)
            
            # Overlay mask in red with high visibility
            if self.mask_data is not None:
                # Create red mask overlay
                mask_rgba = np.zeros((*self.mask_data.shape, 4))
                mask_rgba[self.mask_data, 0] = 1.0  # Red channel
                mask_rgba[self.mask_data, 3] = 0.6  # Alpha (transparency)
                self.axes.imshow(mask_rgba, origin='lower', interpolation='nearest')
            
            self.axes.set_title('Image with Mask (red = masked regions) - Scroll to zoom')
            
            # Store base limits for zoom
            if self.base_xlim is None:
                self.base_xlim = self.axes.get_xlim()
                self.base_ylim = self.axes.get_ylim()
            else:
                # Restore zoom level
                self.axes.set_xlim(self.base_xlim)
                self.axes.set_ylim(self.base_ylim)
            
            # Don't add colorbar - removed per user request
        
        self.figure.canvas.draw_idle()
        
        # Reset background for blitting
        self._background = None
    
    def on_draw(self, event):
        """Capture background for blitting"""
        # Store background after drawing completes
        if self.image_data is not None and self.image_data.size > 4000000:
            self._background = self.copy_from_bbox(self.axes.bbox)
    
    def on_scroll(self, event):
        """Handle mouse scroll for zoom"""
        if event.inaxes != self.axes:
            return
        
        # Get current axis limits
        cur_xlim = self.axes.get_xlim()
        cur_ylim = self.axes.get_ylim()
        
        # Get mouse position
        xdata, ydata = event.xdata, event.ydata
        
        # Zoom factor
        if event.button == 'up':
            scale_factor = 0.9  # Zoom in
        elif event.button == 'down':
            scale_factor = 1.1  # Zoom out
        else:
            return
        
        # Calculate new limits
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        
        # Set new limits centered on mouse position
        self.axes.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.axes.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        
        # Update zoom level
        self.zoom_level = (self.base_xlim[1] - self.base_xlim[0]) / new_width
        
        self.draw_idle()
    
    def reset_zoom(self):
        """Reset zoom to original view"""
        if self.base_xlim is not None:
            self.axes.set_xlim(self.base_xlim)
            self.axes.set_ylim(self.base_ylim)
            self.zoom_level = 1.0
            self.draw_idle()
    
    def set_contrast(self, vmin, vmax):
        """Set contrast limits"""
        self.contrast_min = vmin
        self.contrast_max = vmax
        
        # Only update if image data exists
        if self.image_data is not None:
            # Update image without full redraw
            self.update_image_contrast()
    
    def on_mouse_press(self, event):
        """Handle mouse press events"""
        if event.inaxes != self.axes:
            return
        # Check for left mouse button (can be 1 or MouseButton.LEFT)
        if event.button not in [1, 'MouseButton.LEFT']:
            return
        self.drawing = True
        self.start_point = (int(event.xdata), int(event.ydata))
        print(f"Mouse press at: {self.start_point}")  # Debug
    
    def on_mouse_release(self, event):
        """Handle mouse release events"""
        if not self.drawing:
            return
        
        # Get end point (even if outside axes, use last valid position)
        if event.inaxes != self.axes:
            if not hasattr(self, '_last_mouse_pos'):
                self.drawing = False
                return
            end_point = self._last_mouse_pos
        else:
            end_point = (int(event.xdata), int(event.ydata))
        
        print(f"Mouse release at: {end_point}")  # Debug
        
        # Remove preview
        if self.preview_patch is not None:
            self.preview_patch.remove()
            self.preview_patch = None
        
        # Apply mask
        try:
            if self.mask_mode == 'rectangle':
                self.apply_rectangle_mask(self.start_point, end_point)
                print("Applied rectangle mask")
            elif self.mask_mode == 'circle':
                self.apply_circle_mask(self.start_point, end_point)
                print("Applied circle mask")
        except Exception as e:
            print(f"Error applying mask: {e}")
        
        self.drawing = False
        self.display_image()
    
    def on_mouse_move(self, event):
        """Handle mouse move events with real-time preview"""
        if not self.drawing:
            return
        
        if event.inaxes != self.axes:
            return
        
        if self.start_point is None:
            return
        
        # Throttle updates for large images (only update every N pixels)
        current_point = (int(event.xdata), int(event.ydata))
        self._last_mouse_pos = current_point  # Store for release event
        
        # Skip update if moved less than 5 pixels (for performance)
        if hasattr(self, '_last_preview_pos'):
            dx = abs(current_point[0] - self._last_preview_pos[0])
            dy = abs(current_point[1] - self._last_preview_pos[1])
            if dx < 5 and dy < 5:
                return
        
        self._last_preview_pos = current_point
        
        # Remove old preview
        if self.preview_patch is not None:
            try:
                self.preview_patch.remove()
            except:
                pass
            self.preview_patch = None
        
        # Draw preview shape
        try:
            if self.mask_mode == 'rectangle':
                self.preview_patch = self.draw_rectangle_preview(self.start_point, current_point)
            elif self.mask_mode == 'circle':
                self.preview_patch = self.draw_circle_preview(self.start_point, current_point)
        except Exception as e:
            print(f"Error drawing preview: {e}")
        
        # Use draw_idle for faster updates
        self.figure.canvas.draw_idle()
    
    def draw_rectangle_preview(self, start, end):
        """Draw rectangle preview"""
        from matplotlib.patches import Rectangle
        
        x1, y1 = start
        x2, y2 = end
        
        width = x2 - x1
        height = y2 - y1
        
        rect = Rectangle((x1, y1), width, height, 
                        linewidth=2, edgecolor='yellow', 
                        facecolor='red', alpha=0.3)
        self.axes.add_patch(rect)
        return rect
    
    def draw_circle_preview(self, center, edge):
        """Draw circle preview"""
        from matplotlib.patches import Circle
        
        cx, cy = center
        ex, ey = edge
        radius = np.sqrt((ex - cx)**2 + (ey - cy)**2)
        
        circle = Circle((cx, cy), radius, 
                       linewidth=2, edgecolor='yellow',
                       facecolor='red', alpha=0.3)
        self.axes.add_patch(circle)
        return circle
    
    def apply_rectangle_mask(self, start, end):
        """Apply rectangular mask"""
        if self.mask_data is None:
            print("No mask data initialized!")
            return
        
        x1, y1 = min(start[0], end[0]), min(start[1], end[1])
        x2, y2 = max(start[0], end[0]), max(start[1], end[1])
        
        print(f"Applying rectangle mask: ({x1}, {y1}) to ({x2}, {y2})")
        
        # Clamp to image bounds
        x1 = max(0, min(x1, self.mask_data.shape[1]-1))
        x2 = max(0, min(x2, self.mask_data.shape[1]-1))
        y1 = max(0, min(y1, self.mask_data.shape[0]-1))
        y2 = max(0, min(y2, self.mask_data.shape[0]-1))
        
        # Apply mask value
        self.mask_data[y1:y2+1, x1:x2+1] = self.mask_value
        
        print(f"Masked {(y2-y1+1)*(x2-x1+1)} pixels")
    
    def apply_circle_mask(self, center, edge):
        """Apply circular mask"""
        if self.mask_data is None:
            print("No mask data initialized!")
            return
        
        cx, cy = center
        ex, ey = edge
        radius = np.sqrt((ex - cx)**2 + (ey - cy)**2)
        
        print(f"Applying circle mask: center=({cx}, {cy}), radius={radius:.2f}")
        
        # Clamp center to image bounds
        cy = max(0, min(cy, self.mask_data.shape[0] - 1))
        cx = max(0, min(cx, self.mask_data.shape[1] - 1))
        
        # Create circular mask
        y, x = np.ogrid[:self.mask_data.shape[0], :self.mask_data.shape[1]]
        mask_circle = (x - cx)**2 + (y - cy)**2 <= radius**2
        
        # Apply mask value
        self.mask_data[mask_circle] = self.mask_value
        
        print(f"Masked {np.sum(mask_circle)} pixels")
    
    def apply_threshold_mask(self, threshold_min, threshold_max):
        """Apply intensity threshold mask"""
        if self.image_data is None or self.mask_data is None:
            return
        
        mask_threshold = (self.image_data < threshold_min) | (self.image_data > threshold_max)
        self.mask_data[mask_threshold] = self.mask_value
        self.display_image()
    
    def clear_mask(self):
        """Clear all mask"""
        if self.mask_data is not None:
            self.mask_data = np.zeros(self.mask_data.shape, dtype=bool)
            self.display_image()
    
    def update_image_contrast(self):
        """Update image contrast without full redraw"""
        if self.image_data is None:
            return
        
        # Find existing image artists
        for artist in self.axes.images:
            if hasattr(artist, 'set_clim'):
                if self.contrast_min is not None and self.contrast_max is not None:
                    vmin = np.log10(self.contrast_min + 1)
                    vmax = np.log10(self.contrast_max + 1)
                    artist.set_clim(vmin, vmax)
        
    
    def invert_mask(self):
        """Invert mask"""
        if self.mask_data is not None:
            self.mask_data = ~self.mask_data
            self.display_image()
    
    def get_mask(self):
        """Get current mask data"""
        return self.mask_data
    
    def set_mask(self, mask):
        """Set mask data"""
        self.mask_data = mask.astype(bool) if mask is not None else None
        self.display_image()


class CalibrationCanvas(FigureCanvas):
    """Canvas for displaying calibration results"""
    
    def __init__(self, parent=None, width=6, height=6, dpi=100):
        try:
            # Use smaller DPI to reduce memory usage
            actual_dpi = min(dpi, 80)
            
            self.fig = Figure(figsize=(width, height), dpi=actual_dpi)
            self.axes = self.fig.add_subplot(111)
            super().__init__(self.fig)
            self.setParent(parent)
            
            # Zoom and contrast settings
            self.zoom_level = 1.0
            self.contrast_min = None
            self.contrast_max = None
            self.base_xlim = None
            self.base_ylim = None
            
            # Tool modes
            self.peak_picking_mode = False
            self.mask_editing_mode = False
            self.manual_peaks = []  # List of (x, y, ring_num)
            self.peak_markers = []  # List of matplotlib artists
            
            # Mask editing state
            self.mask_data = None
            self.image_data = None
            self.mask_mode = 'rectangle'  # rectangle, circle
            self.mask_value = True  # True = mask, False = unmask
            self.drawing = False
            self.start_point = None
            self.preview_patch = None
            self._last_mouse_pos = None
            
            # Ring display properties (fixed, Dioptas style)
            self.show_rings = True  # Always show rings
            self.num_rings_display = 50  # Show all available rings (Dioptas default)
            self.ring_alpha = 1.0  # Full opacity (Dioptas default)
            self.ring_color = 'red'  # Red color (Dioptas default)
            self.calibration_points = None  # Store calibration points
            
            # Connect events with error handling
            try:
                self.mpl_connect('scroll_event', self.on_scroll)
                self.mpl_connect('button_press_event', self.on_unified_click)
                self.mpl_connect('button_release_event', self.on_mouse_release)
                self.mpl_connect('motion_notify_event', self.on_mouse_move)
            except Exception as e:
                print(f"Warning: Could not connect canvas events: {e}")
                
        except Exception as e:
            print(f"ERROR creating CalibrationCanvas: {e}")
            import traceback
            traceback.print_exc()
            raise
        
    def display_calibration_image(self, image_data, calibration_points=None):
        """Display calibration image with detected points"""
        if image_data is None:
            return
        
        # Store image data
        self.image_data = image_data
        
        # Initialize mask if needed
        if self.mask_data is None and image_data is not None:
            self.mask_data = np.zeros(image_data.shape, dtype=bool)
        
        # Store current manual peaks before clearing
        temp_manual_peaks = self.manual_peaks.copy()
        
        self.axes.clear()
        
        # Clear peak markers list
        self.peak_markers = []
        
        # Apply contrast settings
        if self.contrast_min is not None and self.contrast_max is not None:
            display_data = np.clip(image_data, self.contrast_min, self.contrast_max)
            vmin, vmax = np.log10(self.contrast_min + 1), np.log10(self.contrast_max + 1)
        else:
            display_data = image_data
            vmin, vmax = None, None
        
        self.axes.imshow(np.log10(display_data + 1), cmap='viridis', origin='lower',
                        vmin=vmin, vmax=vmax, interpolation='nearest')
        
        # Store calibration points for later updates
        if calibration_points is not None:
            self.calibration_points = calibration_points
            
            # Plot calibration rings (with display control)
            if self.show_rings:
                # Limit number of rings displayed
                rings_to_display = min(len(self.calibration_points), self.num_rings_display)
                for i, ring in enumerate(self.calibration_points[:rings_to_display]):
                    if len(ring) > 0:
                        ring = np.array(ring)
                        self.axes.plot(ring[:, 1], ring[:, 0], '.', 
                                     color=self.ring_color,
                                     markersize=2,
                                     alpha=self.ring_alpha)
        
        # Restore manual peaks
        if temp_manual_peaks:
            for x, y, ring_num in temp_manual_peaks:
                # Draw marker as red filled circle
                marker = self.axes.plot(x, y, 'ro', markersize=8, markerfacecolor='red', 
                                       markeredgecolor='white', markeredgewidth=1)[0]
                self.peak_markers.append(marker)
                
                # Add ring number label above marker
                label = self.axes.text(x, y + 15, f'{ring_num}', color='red', fontsize=9,
                                      horizontalalignment='center', verticalalignment='bottom',
                                      fontweight='bold')
                self.peak_markers.append(label)
        
        # Overlay mask if exists (semi-transparent red)
        if self.mask_data is not None and np.any(self.mask_data):
            mask_rgba = np.zeros((*self.mask_data.shape, 4), dtype=np.float32)
            mask_rgba[self.mask_data, 0] = 1.0  # Red channel
            mask_rgba[self.mask_data, 3] = 0.5  # Alpha (semi-transparent)
            self.axes.imshow(mask_rgba, origin='lower', interpolation='nearest', zorder=2)
        
        # Dynamic title based on mode
        if self.peak_picking_mode:
            title = 'Peak Selection Mode - Click on diffraction rings'
        elif self.mask_editing_mode:
            title = 'Mask Editing Mode - Draw masks on image'
        else:
            title = 'Calibration Image - Scroll to zoom'
        
        self.axes.set_title(title)
        
        # Store base limits for zoom
        if self.base_xlim is None:
            self.base_xlim = self.axes.get_xlim()
            self.base_ylim = self.axes.get_ylim()
        
        # Use draw_idle() for better performance
        self.draw_idle()
    
    def on_scroll(self, event):
        """Handle mouse scroll for zoom"""
        if event.inaxes != self.axes:
            return
        
        # Get current axis limits
        cur_xlim = self.axes.get_xlim()
        cur_ylim = self.axes.get_ylim()
        
        # Get mouse position
        xdata, ydata = event.xdata, event.ydata
        
        # Zoom factor
        if event.button == 'up':
            scale_factor = 0.9  # Zoom in
        elif event.button == 'down':
            scale_factor = 1.1  # Zoom out
        else:
            return
        
        # Calculate new limits
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        
        # Set new limits centered on mouse position
        self.axes.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.axes.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        
        # Update zoom level
        self.zoom_level = (self.base_xlim[1] - self.base_xlim[0]) / new_width
        
        self.draw_idle()
    
    def reset_zoom(self):
        """Reset zoom to original view"""
        if self.base_xlim is not None:
            self.axes.set_xlim(self.base_xlim)
            self.axes.set_ylim(self.base_ylim)
            self.zoom_level = 1.0
            self.draw_idle()
    
    def set_contrast(self, vmin, vmax):
        """Set contrast limits"""
        self.contrast_min = vmin
        self.contrast_max = vmax
        
        # Update contrast without full redraw
        if hasattr(self, '_last_image_data') and self._last_image_data is not None:
            self.update_image_contrast()
    
    def update_image_contrast(self):
        """Update image contrast without full redraw"""
        if not hasattr(self, '_last_image_data') or self._last_image_data is None:
            return
        
        # Find existing image artists and update their color limits
        for artist in self.axes.images:
            if hasattr(artist, 'set_clim'):
                if self.contrast_min is not None and self.contrast_max is not None:
                    vmin = np.log10(self.contrast_min + 1)
                    vmax = np.log10(self.contrast_max + 1)
                    artist.set_clim(vmin, vmax)
        
    
    def on_unified_click(self, event):
        """Handle mouse click for peak selection or mask editing"""
        if event.inaxes != self.axes:
            return
        
        # Peak picking mode
        if self.peak_picking_mode and event.button == 1:
            x, y = event.xdata, event.ydata
            
            # Get ring number from parent
            # Get ring number from parent (support both main UI and compact UI)
            ring_num = 1  # Default to ring 1
            if hasattr(self, 'parent_module') and self.parent_module is not None:
                # Try main UI spinbox first
                if hasattr(self.parent_module, 'ring_number_spinbox'):
                    try:
                        ring_num = self.parent_module.ring_number_spinbox.value()
                    except:
                        ring_num = 1
                # Fall back to compact UI entry
                elif hasattr(self.parent_module, 'ring_number_entry'):
                    try:
                        ring_num = int(self.parent_module.ring_number_entry.text())
                    except (ValueError, AttributeError):
                        ring_num = 1
            
            # Add peak
            self.manual_peaks.append((x, y, ring_num))
            
            # Draw marker as red filled circle
            marker = self.axes.plot(x, y, 'ro', markersize=8, markerfacecolor='red', 
                                   markeredgecolor='white', markeredgewidth=1)[0]
            self.peak_markers.append(marker)
            
            # Add ring number label above marker
            label = self.axes.text(x, y + 15, f'{ring_num}', color='red', fontsize=9,
                                  horizontalalignment='center', verticalalignment='bottom',
                                  fontweight='bold')
            self.peak_markers.append(label)
            
            # Use draw_idle() instead of immediate draw for better performance
            self.draw_idle()
            
            # Auto-increment ring number for next peak (Dioptas style)
            if hasattr(self, 'parent_module') and self.parent_module is not None:
                self.parent_module.update_peak_count()
                
                # Check if auto increment is enabled
                auto_inc = False
                if hasattr(self.parent_module, 'automatic_peak_num_inc_cb'):
                    try:
                        auto_inc = self.parent_module.automatic_peak_num_inc_cb.isChecked()
                    except:
                        auto_inc = False
                
                if auto_inc:
                    next_ring_num = ring_num + 1
                    # Update main UI spinbox
                    if hasattr(self.parent_module, 'ring_number_spinbox'):
                        try:
                            self.parent_module.ring_number_spinbox.setValue(next_ring_num)
                        except:
                            pass
                    # Update compact UI entry
                    elif hasattr(self.parent_module, 'ring_number_entry'):
                        try:
                            self.parent_module.ring_number_entry.setText(str(next_ring_num))
                        except:
                            pass
        
        # Mask editing mode
        elif self.mask_editing_mode and event.button == 1:
            # Start drawing mask
            if event.inaxes == self.axes:
                self.drawing = True
                self.start_point = (int(event.xdata), int(event.ydata))
    
    def on_mouse_release(self, event):
        """Handle mouse release for mask drawing"""
        if not self.mask_editing_mode or not self.drawing:
            return
        
        # Remove preview
        if self.preview_patch is not None:
            try:
                self.preview_patch.remove()
            except:
                pass
            self.preview_patch = None
        
        # Use last valid position if released outside axes
        if event.inaxes != self.axes:
            if self._last_mouse_pos is not None:
                end_point = self._last_mouse_pos
            else:
                self.drawing = False
                return
        else:
            end_point = (int(event.xdata), int(event.ydata))
        
        # Apply mask
        try:
            if self.mask_mode == 'rectangle':
                self.apply_rectangle_mask(self.start_point, end_point)
            elif self.mask_mode == 'circle':
                self.apply_circle_mask(self.start_point, end_point)
        except Exception as e:
            print(f"Error applying mask: {e}")
        
        self.drawing = False
        self.start_point = None
        self._last_mouse_pos = None
        self.display_calibration_image(self.image_data)
    
    def on_mouse_move(self, event):
        """Handle mouse move for mask preview"""
        if not self.mask_editing_mode or not self.drawing:
            return
        
        if event.inaxes != self.axes or self.start_point is None:
            return
        
        current_point = (int(event.xdata), int(event.ydata))
        self._last_mouse_pos = current_point
        
        # Remove old preview
        if self.preview_patch is not None:
            try:
                self.preview_patch.remove()
            except:
                pass
            self.preview_patch = None
        
        # Draw preview shape
        try:
            from matplotlib.patches import Rectangle, Circle
            
            if self.mask_mode == 'rectangle':
                x0, y0 = self.start_point
                x1, y1 = current_point
                width = x1 - x0
                height = y1 - y0
                self.preview_patch = Rectangle((x0, y0), width, height,
                                              edgecolor='yellow', facecolor='red',
                                              alpha=0.3, linewidth=2)
                self.axes.add_patch(self.preview_patch)
            elif self.mask_mode == 'circle':
                x0, y0 = self.start_point
                x1, y1 = current_point
                radius = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
                self.preview_patch = Circle((x0, y0), radius,
                                           edgecolor='yellow', facecolor='red',
                                           alpha=0.3, linewidth=2)
                self.axes.add_patch(self.preview_patch)
        except Exception as e:
            print(f"Error drawing preview: {e}")
        
    
    def apply_rectangle_mask(self, start, end):
        """Apply rectangular mask"""
        if self.mask_data is None or self.image_data is None:
            return
        
        x0, y0 = start
        x1, y1 = end
        
        # Ensure proper ordering
        x_min, x_max = min(x0, x1), max(x0, x1)
        y_min, y_max = min(y0, y1), max(y0, y1)
        
        # Clamp to image bounds
        height, width = self.mask_data.shape
        x_min = max(0, min(x_min, width - 1))
        x_max = max(0, min(x_max, width - 1))
        y_min = max(0, min(y_min, height - 1))
        y_max = max(0, min(y_max, height - 1))
        
        # Apply mask
        self.mask_data[int(y_min):int(y_max)+1, int(x_min):int(x_max)+1] = self.mask_value
    
    def apply_circle_mask(self, center, edge):
        """Apply circular mask"""
        if self.mask_data is None or self.image_data is None:
            return
        
        cx, cy = center
        ex, ey = edge
        radius = np.sqrt((ex - cx)**2 + (ey - cy)**2)
        
        height, width = self.mask_data.shape
        y, x = np.ogrid[0:height, 0:width]
        
        # Create circular mask
        circle_mask = (x - cx)**2 + (y - cy)**2 <= radius**2
        self.mask_data[circle_mask] = self.mask_value
    
    def get_mask(self):
        """Get current mask data"""
        return self.mask_data
    
    def set_mask_mode(self, mode):
        """Set mask drawing mode"""
        self.mask_mode = mode
    
    def clear_manual_peaks(self):
        """Clear all manually selected peaks"""
        self.manual_peaks = []
        for marker in self.peak_markers:
            marker.remove()
        self.peak_markers = []
    
    def get_manual_control_points(self):
        """Get manual peaks as control points array (N, 3) - Dioptas format"""
        if not self.manual_peaks:
            return None
        
        # Convert (x, y, ring) to (y, x, ring) for pyFAI
        # x=column, y=row in image coordinates
        control_points = []
        for x, y, ring_num in self.manual_peaks:
            # pyFAI expects [row, col, ring] format
            control_points.append([y, x, ring_num])
        
        control_points_array = np.array(control_points)
        
        # Debug output
        print(f"\n=== Control Points Debug ===")
        print(f"Total points: {len(control_points_array)}")
        if len(control_points_array) > 0:
            print(f"Format: [row, col, ring]")
            for i, cp in enumerate(control_points_array[:5]):  # Show first 5
                print(f"  Point {i+1}: row={cp[0]:.1f}, col={cp[1]:.1f}, ring={cp[2]}")
        print(f"===========================\n")
        
        return control_points_array
    
    def display_calibration_image(self, image_data, calibration_points=None):
        """Display calibration image with detected points"""
        # Store for contrast adjustment
        self._last_image_data = image_data
        self._last_calib_points = calibration_points
        
        # Store current manual peaks before clearing
        temp_manual_peaks = self.manual_peaks.copy()
        
        self.axes.clear()
        
        # Clear peak markers list (they're gone after axes.clear())
        self.peak_markers = []
        
        # Apply contrast settings
        if self.contrast_min is not None and self.contrast_max is not None:
            display_data = np.clip(image_data, self.contrast_min, self.contrast_max)
            vmin, vmax = np.log10(self.contrast_min + 1), np.log10(self.contrast_max + 1)
        else:
            display_data = image_data
            vmin, vmax = None, None
        
        self.axes.imshow(np.log10(display_data + 1), cmap='viridis', origin='lower',
                        vmin=vmin, vmax=vmax, interpolation='nearest')
        
        if calibration_points is not None:
            # Plot calibration rings in red
            for ring in calibration_points:
                if len(ring) > 0:
                    ring = np.array(ring)
                    self.axes.plot(ring[:, 1], ring[:, 0], 'r.', markersize=2)
        
        # Restore manual peaks
        if temp_manual_peaks:
            for x, y, ring_num in temp_manual_peaks:
                # Draw marker as red filled circle
                marker = self.axes.plot(x, y, 'ro', markersize=8, markerfacecolor='red', 
                                       markeredgecolor='white', markeredgewidth=1)[0]
                self.peak_markers.append(marker)
                
                # Add ring number label above marker
                label = self.axes.text(x, y + 15, f'{ring_num}', color='red', fontsize=9,
                                      horizontalalignment='center', verticalalignment='bottom',
                                      fontweight='bold')
                self.peak_markers.append(label)
        
        # Overlay mask if in mask editing mode
        if self.mask_data is not None:
            mask_rgba = np.zeros((*self.mask_data.shape, 4))
            mask_rgba[self.mask_data, 0] = 1.0  # Red channel
            mask_rgba[self.mask_data, 3] = 0.6  # Alpha
            self.axes.imshow(mask_rgba, origin='lower', interpolation='nearest')
        
        # Dynamic title based on mode
        if self.peak_picking_mode:
            title = 'Peak Selection Mode - Click on diffraction rings'
        elif self.mask_editing_mode:
            title = 'Mask Editing Mode - Draw masks on image'
        else:
            title = 'Calibration Image - Scroll to zoom'
        
        self.axes.set_title(title)
        
        # Store base limits for zoom
        if self.base_xlim is None:
            self.base_xlim = self.axes.get_xlim()
            self.base_ylim = self.axes.get_ylim()
        
        # Don't add colorbar - removed per user request
        self.figure.canvas.draw_idle()
    
    def display_integrated_pattern(self, tth, intensity):
        """Display integrated 1D pattern"""
        self.axes.clear()
        self.axes.plot(tth, intensity)
        self.axes.set_xlabel('2θ (degrees)')
        self.axes.set_ylabel('Intensity')
        self.axes.set_title('Integrated Diffraction Pattern')
        self.axes.grid(True, alpha=0.3)


class CalibrateModule(GUIBase):
    """Detector calibration module using Dioptas/pyFAI functionality"""

    def __init__(self, parent, root):
        """
        Initialize Calibration module

        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        super().__init__()
        self.parent = parent
        self.root = root
        
        # Override colors for calibration module - light blue palette
        self.colors = {
            'bg': '#F5F5F5',
            'card_bg': '#FFFFFF',
            'primary': '#A8D8EA',  # Light blue
            'primary_hover': '#7FC4DD',  # Slightly darker light blue
            'secondary': '#A8D8EA',  # Light blue for buttons
            'accent': '#E67E73',
            'text_dark': '#2C3E50',
            'text_light': '#7F8C8D',
            'border': '#D1D9E6',
            'success': '#6FA86F',
            'error': '#E67E73',
            'light_purple': '#B19CD9',
            'active_module': '#6C9BD2'
        }
        
        # Check dependencies
        if not PYFAI_AVAILABLE:
            QMessageBox.warning(None, "Missing Dependencies", 
                              "pyFAI is required for calibration.\nInstall with: pip install pyFAI")
        
        # Initialize variables
        self._init_variables()
        
        # Calibration objects
        self.ai = None  # AzimuthalIntegrator
        self.calibrant = None
        self.geo_ref = None  # GeometryRefinement
        self.current_image = None
        self.current_mask = None
        
        # Track threads
        self.running_threads = []
        
        # Tool mode: 'view', 'peaks', 'mask'
        self.tool_mode = 'view'
        
        # Mask from mask module
        self.imported_mask = None
        self.mask_module_reference = None

    def _init_variables(self):
        """Initialize all variables"""
        # File paths
        self.image_path = ""
        self.mask_path = ""
        self.output_poni = ""
        
        # Calibration parameters
        self.calibrant_name = "LaB6"  # Default calibrant
        self.wavelength = 0.4133  # Angstrom
        self.detector_name = "Pilatus2M"
        self.pixel_size = 172e-6  # meters
        
        # Detector parameters
        self.distance = 0.5  # meters
        self.poni1 = 0.1  # meters
        self.poni2 = 0.1  # meters
        self.rot1 = 0.0  # radians
        self.rot2 = 0.0  # radians
        self.rot3 = 0.0  # radians
        
        # Peak finding parameters
        self.npt = 2048
        self.npt_azim = 360
        self.min_peaks = 5
        
        # Mask parameters
        self.mask_mode = 'rectangle'
        
        # Contrast parameters
        self.contrast_min_val = 0
        self.contrast_max_val = 65535
    
    def log(self, message):
        """Log message to output console"""
        if hasattr(self, 'log_output'):
            self.log_output.append(message)
            # Auto-scroll to bottom
            scrollbar = self.log_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def setup_ui(self):
        """Setup the complete calibration UI - Dioptas style layout"""
        # Check if UI is already set up
        if hasattr(self, '_ui_initialized') and self._ui_initialized:
            return
        
        # Mark as initializing to prevent re-entry
        if hasattr(self, '_ui_initializing') and self._ui_initializing:
            print("WARNING: setup_ui already initializing, skipping...")
            return
        
        self._ui_initializing = True
        
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            # Clear existing items carefully
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    try:
                        item.widget().deleteLater()
                    except:
                        pass

        # Main horizontal splitter: Display (left) + Control (right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ============== LEFT PANEL: DISPLAY WIDGET ==============
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget for Image/Cake/Pattern views (Dioptas style)
        self.display_tab_widget = QTabWidget()
        
        # Image tab
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        if MATPLOTLIB_AVAILABLE:
            # Horizontal layout for canvas and contrast slider
            canvas_container = QWidget()
            canvas_layout = QHBoxLayout(canvas_container)
            canvas_layout.setContentsMargins(0, 0, 0, 0)
            canvas_layout.setSpacing(5)
            
            try:
                # Create canvas with reduced size to prevent memory issues
                # Using smaller dimensions and DPI
                self.unified_canvas = CalibrationCanvas(canvas_container, width=8, height=6, dpi=80)
                canvas_layout.addWidget(self.unified_canvas)
                print("✅ CalibrationCanvas created successfully")
            except Exception as e:
                print(f"❌ Error creating CalibrationCanvas: {e}")
                import traceback
                traceback.print_exc()
                # Create placeholder
                placeholder = QLabel("Canvas initialization error.\nPlease restart or check console.")
                placeholder.setStyleSheet("color: red; padding: 20px;")
                canvas_layout.addWidget(placeholder)
                self.unified_canvas = None
            
            # Vertical contrast slider on right side (limited height)
            contrast_widget = QWidget()
            contrast_widget.setMaximumWidth(40)
            contrast_layout = QVBoxLayout(contrast_widget)
            contrast_layout.setContentsMargins(0, 0, 0, 0)
            contrast_layout.setSpacing(2)
            
            # Add stretch at top
            contrast_layout.addStretch(1)
            
            # Max label (top)
            max_lbl = QLabel("Max")
            max_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            max_lbl.setFont(QFont('Arial', 7))
            contrast_layout.addWidget(max_lbl)
            
            # Vertical slider with fixed height
            self.contrast_slider = QSlider(Qt.Orientation.Vertical)
            self.contrast_slider.setMinimum(0)
            self.contrast_slider.setMaximum(65535)
            self.contrast_slider.setValue(65535)
            self.contrast_slider.setInvertedAppearance(True)  # Max at top
            self.contrast_slider.setFixedHeight(300)  # Limit height
            self.contrast_slider.valueChanged.connect(self.on_contrast_slider_changed)
            contrast_layout.addWidget(self.contrast_slider)
            
            # Min label (bottom)
            min_lbl = QLabel("Min")
            min_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            min_lbl.setFont(QFont('Arial', 7))
            contrast_layout.addWidget(min_lbl)
            
            # Add stretch at bottom
            contrast_layout.addStretch(1)
            
            canvas_layout.addWidget(contrast_widget)
            
            image_layout.addWidget(canvas_container)
            
            # Keep references for compatibility
            self.calibration_canvas = self.unified_canvas
            self.mask_canvas = MaskCanvas(image_tab, width=10, height=8, dpi=100)
            self.mask_canvas.hide()
        else:
            no_plot_label = QLabel("Matplotlib not available")
            no_plot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_layout.addWidget(no_plot_label)
        
        self.display_tab_widget.addTab(image_tab, "Image")
        
        # Cake tab (Dioptas-style polar transformation)
        cake_tab = QWidget()
        cake_layout = QVBoxLayout(cake_tab)
        cake_layout.setContentsMargins(0, 0, 0, 0)
        
        if MATPLOTLIB_AVAILABLE:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            
            self.cake_figure = Figure(figsize=(10, 8), dpi=100)
            self.cake_canvas = FigureCanvas(self.cake_figure)
            self.cake_axes = self.cake_figure.add_subplot(111)
            cake_layout.addWidget(self.cake_canvas)
            
            self.cake_axes.set_title("Cake View (Polar Transform)")
            self.cake_axes.set_xlabel("2θ (degrees)")
            self.cake_axes.set_ylabel("Azimuthal angle χ (degrees)")
        else:
            cake_label = QLabel("Matplotlib not available")
            cake_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cake_layout.addWidget(cake_label)
        
        self.display_tab_widget.addTab(cake_tab, "Cake")
        
        # Pattern tab (1D integration)
        pattern_tab = QWidget()
        pattern_layout = QVBoxLayout(pattern_tab)
        pattern_layout.setContentsMargins(0, 0, 0, 0)
        
        if MATPLOTLIB_AVAILABLE:
            self.pattern_figure = Figure(figsize=(10, 8), dpi=100)
            self.pattern_canvas = FigureCanvas(self.pattern_figure)
            self.pattern_axes = self.pattern_figure.add_subplot(111)
            pattern_layout.addWidget(self.pattern_canvas)
            
            self.pattern_axes.set_title("Integrated Pattern")
            self.pattern_axes.set_xlabel("2θ (degrees)")
            self.pattern_axes.set_ylabel("Intensity (a.u.)")
            self.pattern_axes.grid(True, alpha=0.3)
        else:
            pattern_label = QLabel("Matplotlib not available")
            pattern_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pattern_layout.addWidget(pattern_label)
        
        self.display_tab_widget.addTab(pattern_tab, "Pattern")
        
        left_layout.addWidget(self.display_tab_widget)
        
        # Status bar with display controls and Calibrate/Refine buttons
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(6, 0, 0, 0)
        
        # Display control buttons
        auto_contrast_btn = ModernButton("Auto Contrast",
                                        self.auto_contrast,
                                        "",
                                        bg_color=self.colors['secondary'],
                                        hover_color=self.colors['primary'],
                                        width=120, height=35,
                                        font_size=9,
                                        parent=status_frame)
        
        reset_zoom_btn = ModernButton("Reset Zoom",
                                     self.reset_zoom,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=120, height=35,
                                     font_size=9,
                                     parent=status_frame)
        
        status_layout.addWidget(auto_contrast_btn)
        status_layout.addWidget(reset_zoom_btn)
        status_layout.addStretch()
        
        self.calibrate_btn = ModernButton("Calibrate",
                                         self.run_calibration,
                                         "",
                                         bg_color=self.colors['primary'],
                                         hover_color=self.colors['primary_hover'],
                                         width=130, height=35,
                                         font_size=10,
                                         parent=status_frame)
        
        self.refine_btn = ModernButton("Refine",
                                       self.refine_calibration,
                                       "",
                                       bg_color=self.colors['secondary'],
                                       hover_color=self.colors['primary'],
                                       width=130, height=35,
                                       font_size=10,
                                       parent=status_frame)
        
        self.position_lbl = QLabel("Position: x=0, y=0")
        self.position_lbl.setFont(QFont('Arial', 9))
        
        status_layout.addWidget(self.calibrate_btn)
        status_layout.addWidget(self.refine_btn)
        status_layout.addStretch()
        status_layout.addWidget(self.position_lbl)
        
        left_layout.addWidget(status_frame)
        
        # ============== RIGHT PANEL: CONTROL WIDGET ==============
        # Use scroll area to ensure all controls are accessible
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setMinimumWidth(320)
        right_scroll.setMaximumWidth(320)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(10)
        
        # File loading section
        file_frame = QFrame()
        file_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card_bg']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        file_layout = QHBoxLayout(file_frame)
        file_layout.setContentsMargins(8, 8, 8, 8)
        file_layout.setSpacing(6)

        self.load_img_btn = ModernButton("Load Image File",
                                         self.browse_and_load_image,
                                         "",
                                         bg_color=self.colors['secondary'],
                                         hover_color=self.colors['primary'],
                                         width=185, height=32,
                                         font_size=9,
                                         parent=file_frame)

        self.load_previous_img_btn = QPushButton("<")
        self.load_previous_img_btn.setFixedWidth(45)
        self.load_previous_img_btn.setFixedHeight(32)
        self.load_previous_img_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colors['primary']};
            }}
        """)

        self.load_next_img_btn = QPushButton(">")
        self.load_next_img_btn.setFixedWidth(45)
        self.load_next_img_btn.setFixedHeight(32)
        self.load_next_img_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colors['primary']};
            }}
        """)

        file_layout.addWidget(self.load_img_btn)
        file_layout.addWidget(self.load_previous_img_btn)
        file_layout.addWidget(self.load_next_img_btn)

        right_layout.addWidget(file_frame)

        # Filename display
        self.filename_txt = QLineEdit()
        self.filename_txt.setReadOnly(True)
        self.filename_txt.setPlaceholderText("No file loaded")
        self.filename_txt.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['card_bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 6px 10px;
                color: {self.colors['text_dark']};
            }}
        """)
        right_layout.addWidget(self.filename_txt)
        
        # Toolbox for parameters (Dioptas style)
        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet(f"""
            QToolBox::tab {{
                font-weight: bold;
                background-color: {self.colors['secondary']};
                border-radius: 4px;
                padding: 8px;
            }}
            QToolBox::tab:selected {{
                background-color: {self.colors['primary']};
                color: white;
            }}
        """)

        # Calibration Parameters page
        calib_params_widget = QWidget()
        calib_params_layout = QVBoxLayout(calib_params_widget)
        calib_params_layout.setSpacing(12)
        calib_params_layout.setContentsMargins(5, 10, 5, 10)
        
        self.setup_detector_groupbox(calib_params_layout)
        self.setup_start_values_groupbox(calib_params_layout)
        self.setup_peak_selection_groupbox(calib_params_layout)
        self.setup_refinement_options_groupbox(calib_params_layout)
        
        calib_params_layout.addStretch()
        
        self.toolbox.addItem(calib_params_widget, "Calibration Parameters")
        
        # pyFAI Parameters page
        pyfai_params_widget = QWidget()
        pyfai_params_layout = QVBoxLayout(pyfai_params_widget)
        self.setup_pyfai_parameters(pyfai_params_layout)
        pyfai_params_layout.addStretch()
        self.toolbox.addItem(pyfai_params_widget, "pyFAI Parameters")
        
        # Fit2d Parameters page
        fit2d_params_widget = QWidget()
        fit2d_params_layout = QVBoxLayout(fit2d_params_widget)
        self.setup_fit2d_parameters(fit2d_params_layout)
        fit2d_params_layout.addStretch()
        self.toolbox.addItem(fit2d_params_widget, "Fit2d Parameters")
        
        right_layout.addWidget(self.toolbox)
        
        # Bottom buttons: Load/Save Calibration
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(5, 5, 5, 5)
        
        self.load_calibration_btn = ModernButton("Load Calibration",
                                                self.load_calibration,
                                                "",
                                                bg_color=self.colors['secondary'],
                                                hover_color=self.colors['primary'],
                                                width=145, height=30,
                                                font_size=9,
                                                parent=bottom_frame)
        
        self.save_calibration_btn = ModernButton("Save Calibration",
                                                self.save_poni_file,
                                                "",
                                                bg_color=self.colors['secondary'],
                                                hover_color=self.colors['primary'],
                                                width=145, height=30,
                                                font_size=9,
                                                parent=bottom_frame)
        
        bottom_layout.addWidget(self.load_calibration_btn)
        bottom_layout.addWidget(self.save_calibration_btn)
        
        right_layout.addWidget(bottom_frame)
        
        # Set scroll area content
        right_scroll.setWidget(right_widget)
        
        # Add widgets to splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_scroll)
        
        # Left panel expandable, right panel fixed
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        
        layout.addWidget(main_splitter)
        
        # Log output at bottom of entire interface (larger font)
        log_label = QLabel("📋 Log Output:")
        log_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        log_label.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 5px;")
        layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(150)  # Increased from 80
        self.log_output.setMinimumHeight(100)
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont('Consolas', 10))  # Increased from Courier 7
        self.log_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: #f8f9fa;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                padding: 5px;
                color: #2c3e50;
            }}
        """)
        layout.addWidget(self.log_output)
        
        # Mark UI as initialized
        self._ui_initialized = True
        self._ui_initializing = False
        
        print("✅ Calibrate UI initialized successfully")

    def setup_detector_groupbox(self, parent_layout):
        """Setup Detector GroupBox (Dioptas style)"""
        detector_gb = QGroupBox("Detector")
        detector_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                margin-top: 10px;
                margin-bottom: 5px;
                padding-top: 18px;
                padding-bottom: 12px;
                padding-left: 12px;
                padding-right: 12px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: {self.colors['text_dark']};
                background-color: {self.colors['card_bg']};
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
        """)
        detector_layout = QVBoxLayout(detector_gb)
        detector_layout.setSpacing(10)
        detector_layout.setContentsMargins(8, 8, 8, 8)
        
        # Detector selection combo box
        self.detector_combo = QComboBox()
        detectors = ["Pilatus2M", "Pilatus1M", "Pilatus300K", "PerkinElmer", 
                     "Eiger2M", "Eiger1M", "Eiger4M", "Mar345", "Rayonix", "Custom"]
        self.detector_combo.addItems(detectors)
        self.detector_combo.currentTextChanged.connect(self.on_detector_changed)
        detector_layout.addWidget(self.detector_combo)
        
        # Pixel size grid
        pixel_grid = QHBoxLayout()
        pixel_grid.setSpacing(8)

        width_label = QLabel("Pixel width:")
        width_label.setMinimumWidth(80)
        pixel_grid.addWidget(width_label)
        self.pixel_width_txt = QLineEdit(str(self.pixel_size * 1e6))
        self.pixel_width_txt.setFixedWidth(70)
        pixel_grid.addWidget(self.pixel_width_txt)
        pixel_grid.addWidget(QLabel("μm"))
        pixel_grid.addStretch()

        detector_layout.addLayout(pixel_grid)

        pixel_grid2 = QHBoxLayout()
        pixel_grid2.setSpacing(8)

        height_label = QLabel("Pixel height:")
        height_label.setMinimumWidth(80)
        pixel_grid2.addWidget(height_label)
        self.pixel_height_txt = QLineEdit(str(self.pixel_size * 1e6))
        self.pixel_height_txt.setFixedWidth(70)
        pixel_grid2.addWidget(self.pixel_height_txt)
        pixel_grid2.addWidget(QLabel("μm"))
        pixel_grid2.addStretch()

        detector_layout.addLayout(pixel_grid2)
        
        # Distortion/Spline file
        distortion_layout = QHBoxLayout()
        distortion_layout.setSpacing(8)

        distortion_label = QLabel("Distortion:")
        distortion_label.setMinimumWidth(80)
        distortion_layout.addWidget(distortion_label)
        self.spline_name_lbl = QLabel("None")
        self.spline_name_lbl.setStyleSheet("color: gray; font-style: italic;")
        distortion_layout.addWidget(self.spline_name_lbl)
        distortion_layout.addStretch()

        self.spline_load_btn = QPushButton("Load")
        self.spline_load_btn.setFixedWidth(55)
        self.spline_load_btn.setToolTip("Load spline correction file")
        self.spline_load_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 8px;
                border-radius: 3px;
            }
        """)
        distortion_layout.addWidget(self.spline_load_btn)

        self.spline_reset_btn = QPushButton("Reset")
        self.spline_reset_btn.setFixedWidth(55)
        self.spline_reset_btn.setEnabled(False)
        self.spline_reset_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 8px;
                border-radius: 3px;
            }
        """)
        distortion_layout.addWidget(self.spline_reset_btn)

        detector_layout.addLayout(distortion_layout)
        
        parent_layout.addWidget(detector_gb)
    
    def setup_start_values_groupbox(self, parent_layout):
        """Setup Start Values GroupBox (Dioptas style)"""
        sv_gb = QGroupBox("Start values")
        sv_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                margin-top: 10px;
                margin-bottom: 5px;
                padding-top: 18px;
                padding-bottom: 12px;
                padding-left: 12px;
                padding-right: 12px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: {self.colors['text_dark']};
                background-color: {self.colors['card_bg']};
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
        """)
        sv_layout = QVBoxLayout(sv_gb)
        sv_layout.setSpacing(10)
        sv_layout.setContentsMargins(8, 8, 8, 8)
        
        # Calibrant selection
        calib_layout = QHBoxLayout()
        calib_layout.setSpacing(8)

        calib_label = QLabel("Calibrant:")
        calib_label.setMinimumWidth(80)
        calib_layout.addWidget(calib_label)
        self.calibrant_combo = QComboBox()
        if PYFAI_AVAILABLE:
            calibrants = sorted(ALL_CALIBRANTS.keys())
            self.calibrant_combo.addItems(calibrants)
            if "LaB6" in calibrants:
                self.calibrant_combo.setCurrentText("LaB6")
        self.calibrant_combo.currentTextChanged.connect(self.on_calibrant_changed)
        calib_layout.addWidget(self.calibrant_combo)
        sv_layout.addLayout(calib_layout)

        # Distance with refinement checkbox
        dist_layout = QHBoxLayout()
        dist_layout.setSpacing(8)

        dist_label = QLabel("Distance:")
        dist_label.setMinimumWidth(80)
        dist_layout.addWidget(dist_label)
        self.distance_txt = QLineEdit(str(self.distance * 1000))  # Convert to mm
        self.distance_txt.setFixedWidth(85)
        dist_layout.addWidget(self.distance_txt)
        dist_layout.addWidget(QLabel("mm"))
        self.distance_cb = QCheckBox("refine")
        self.distance_cb.setChecked(True)
        dist_layout.addWidget(self.distance_cb)
        dist_layout.addStretch()
        sv_layout.addLayout(dist_layout)
        
        # Wavelength with refinement checkbox
        wl_layout = QHBoxLayout()
        wl_layout.setSpacing(8)

        wl_label = QLabel("Wavelength:")
        wl_label.setMinimumWidth(80)
        wl_layout.addWidget(wl_label)
        self.wavelength_txt = QLineEdit(str(self.wavelength))
        self.wavelength_txt.setFixedWidth(85)
        wl_layout.addWidget(self.wavelength_txt)
        wl_layout.addWidget(QLabel("Å"))
        self.wavelength_cb = QCheckBox("refine")
        self.wavelength_cb.setChecked(False)  # Wavelength usually fixed
        wl_layout.addWidget(self.wavelength_cb)
        wl_layout.addStretch()
        sv_layout.addLayout(wl_layout)

        # Polarization factor
        pol_layout = QHBoxLayout()
        pol_layout.setSpacing(8)

        pol_label = QLabel("Polarization:")
        pol_label.setMinimumWidth(80)
        pol_layout.addWidget(pol_label)
        self.polarization_txt = QLineEdit("0.99")
        self.polarization_txt.setFixedWidth(85)
        pol_layout.addWidget(self.polarization_txt)
        pol_layout.addStretch()
        sv_layout.addLayout(pol_layout)
        
        # Image transformation buttons
        transform_frame = QFrame()
        transform_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(240, 240, 240, 0.3);
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                padding: 10px;
                margin-top: 8px;
            }}
        """)
        transform_layout = QVBoxLayout(transform_frame)
        transform_layout.setSpacing(8)
        transform_layout.setContentsMargins(8, 8, 8, 8)

        transform_label = QLabel("Image transformations:")
        transform_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        transform_layout.addWidget(transform_label)

        # Rotation buttons
        rot_layout = QHBoxLayout()
        rot_layout.setSpacing(6)

        self.rotate_m90_btn = QPushButton("↶ -90°")
        self.rotate_m90_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        self.rotate_p90_btn = QPushButton("↷ +90°")
        self.rotate_p90_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        rot_layout.addWidget(self.rotate_m90_btn)
        rot_layout.addWidget(self.rotate_p90_btn)
        transform_layout.addLayout(rot_layout)

        # Flip buttons
        flip_layout = QHBoxLayout()
        flip_layout.setSpacing(6)

        self.flip_horizontal_btn = QPushButton("Flip H")
        self.flip_horizontal_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        self.flip_vertical_btn = QPushButton("Flip V")
        self.flip_vertical_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        flip_layout.addWidget(self.flip_horizontal_btn)
        flip_layout.addWidget(self.flip_vertical_btn)
        transform_layout.addLayout(flip_layout)

        # Reset button
        self.reset_transformations_btn = QPushButton("Reset Transformations")
        self.reset_transformations_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        transform_layout.addWidget(self.reset_transformations_btn)

        sv_layout.addWidget(transform_frame)
        
        parent_layout.addWidget(sv_gb)
    
    def setup_peak_selection_groupbox(self, parent_layout):
        """Setup Peak Selection GroupBox (Dioptas style)"""
        peak_gb = QGroupBox("Peak Selection")
        peak_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                margin-top: 10px;
                margin-bottom: 5px;
                padding-top: 18px;
                padding-bottom: 12px;
                padding-left: 12px;
                padding-right: 12px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: {self.colors['text_dark']};
                background-color: {self.colors['card_bg']};
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
        """)
        peak_layout = QVBoxLayout(peak_gb)
        peak_layout.setSpacing(10)
        peak_layout.setContentsMargins(8, 8, 8, 8)
        
        # Radio buttons for peak selection mode
        self.peak_mode_group = QButtonGroup()
        
        # Radio button style
        radio_style = f"""
            QRadioButton {{
                spacing: 8px;
                padding: 6px 0px;
                color: {self.colors['text_dark']};
            }}
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid #999999;
                border-radius: 7px;
                background-color: white;
            }}
            QRadioButton::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 2px solid {self.colors['primary']};
                border-radius: 7px;
                image: url(check.png);
            }}
            QRadioButton::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """
        
        self.automatic_peak_search_rb = QRadioButton("Automatic peak search")
        self.automatic_peak_search_rb.setChecked(True)
        self.automatic_peak_search_rb.setStyleSheet(radio_style)
        self.automatic_peak_search_rb.toggled.connect(self.on_peak_mode_changed)
        self.peak_mode_group.addButton(self.automatic_peak_search_rb, 0)
        peak_layout.addWidget(self.automatic_peak_search_rb)
        
        self.select_peak_rb = QRadioButton("Select peak manually")
        self.select_peak_rb.setStyleSheet(radio_style)
        self.select_peak_rb.toggled.connect(self.on_peak_mode_changed)
        self.peak_mode_group.addButton(self.select_peak_rb, 1)
        peak_layout.addWidget(self.select_peak_rb)
        
        # Current Ring Number (Dioptas style)
        ring_num_row = QHBoxLayout()
        ring_num_row.setSpacing(8)

        ring_label = QLabel("Current Ring #:")
        ring_label.setMinimumWidth(100)
        ring_num_row.addWidget(ring_label)
        self.ring_number_spinbox = QSpinBox()
        self.ring_number_spinbox.setMinimum(0)
        self.ring_number_spinbox.setMaximum(50)
        self.ring_number_spinbox.setValue(1)  # Default to ring 1
        self.ring_number_spinbox.setFixedWidth(70)
        self.ring_number_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #FFF8DC;
                font-weight: bold;
                padding: 5px;
                border-radius: 3px;
            }
        """)
        ring_num_row.addWidget(self.ring_number_spinbox)
        ring_num_row.addStretch()
        peak_layout.addLayout(ring_num_row)

        # Auto increment checkbox (Dioptas style)
        self.automatic_peak_num_inc_cb = QCheckBox("Automatic increase ring number")
        self.automatic_peak_num_inc_cb.setChecked(True)
        self.automatic_peak_num_inc_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {self.colors['text_dark']};
                padding: 4px 0px;
            }}
        """)
        peak_layout.addWidget(self.automatic_peak_num_inc_cb)

        # Peak search size
        search_size_row = QHBoxLayout()
        search_size_row.setSpacing(8)

        search_label = QLabel("Search Size:")
        search_label.setMinimumWidth(100)
        search_size_row.addWidget(search_label)
        self.search_size_sb = QSpinBox()
        self.search_size_sb.setMinimum(5)
        self.search_size_sb.setMaximum(100)
        self.search_size_sb.setValue(10)
        self.search_size_sb.setFixedWidth(70)
        self.search_size_sb.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border-radius: 3px;
            }
        """)
        search_size_row.addWidget(self.search_size_sb)
        search_size_row.addWidget(QLabel("pixels"))
        search_size_row.addStretch()
        peak_layout.addLayout(search_size_row)
        
        # Clear and Undo buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.clear_peaks_btn = QPushButton("Clear Peaks")
        self.clear_peaks_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        self.clear_peaks_btn.clicked.connect(self.clear_manual_peaks)
        btn_layout.addWidget(self.clear_peaks_btn)

        self.undo_peaks_btn = QPushButton("Undo Last")
        self.undo_peaks_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        self.undo_peaks_btn.clicked.connect(self.undo_last_peak)
        btn_layout.addWidget(self.undo_peaks_btn)

        peak_layout.addLayout(btn_layout)

        # Peak count label
        self.peak_count_label = QLabel("Peaks: 0")
        self.peak_count_label.setFont(QFont('Arial', 9))
        self.peak_count_label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['primary']};
                padding: 6px 10px;
                background-color: rgba(33, 150, 243, 0.1);
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        peak_layout.addWidget(self.peak_count_label)
        
        parent_layout.addWidget(peak_gb)
    
    def setup_refinement_options_groupbox(self, parent_layout):
        """Setup Refinement Options GroupBox (Dioptas style)"""
        ref_gb = QGroupBox("Refinement Options")
        ref_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                margin-top: 10px;
                margin-bottom: 5px;
                padding-top: 18px;
                padding-bottom: 12px;
                padding-left: 12px;
                padding-right: 12px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: {self.colors['text_dark']};
                background-color: {self.colors['card_bg']};
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
        """)
        ref_layout = QVBoxLayout(ref_gb)
        ref_layout.setSpacing(10)
        ref_layout.setContentsMargins(8, 8, 8, 8)
        
        # Checkbox style
        checkbox_style = f"""
            QCheckBox {{
                spacing: 8px;
                padding: 6px 0px;
                color: {self.colors['text_dark']};
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid #999999;
                border-radius: 3px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 2px solid {self.colors['primary']};
                border-radius: 3px;
                image: url(point.png);
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """
        
        # Automatic refinement checkbox
        self.automatic_refinement_cb = QCheckBox("Automatic refinement")
        self.automatic_refinement_cb.setChecked(True)
        self.automatic_refinement_cb.setStyleSheet(checkbox_style)
        ref_layout.addWidget(self.automatic_refinement_cb)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; max-height: 2px; margin: 12px 0px;")
        ref_layout.addWidget(separator)

        # Mask from Mask Module
        mask_frame = QFrame()
        mask_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(240, 240, 240, 0.3);
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                padding: 12px;
                margin: 5px 0px;
            }}
        """)
        mask_inner_layout = QVBoxLayout(mask_frame)
        mask_inner_layout.setSpacing(10)
        mask_inner_layout.setContentsMargins(8, 8, 8, 8)
        
        mask_title = QLabel("Mask from Mask Module")
        mask_title.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        mask_title.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 2px 0px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);")
        mask_inner_layout.addWidget(mask_title)
        
        self.use_mask_cb = QCheckBox("Use Mask from Mask Module")
        self.use_mask_cb.stateChanged.connect(self.on_use_mask_changed)
        self.use_mask_cb.setStyleSheet(checkbox_style)
        mask_inner_layout.addWidget(self.use_mask_cb)
        
        self.mask_transparent_cb = QCheckBox("Transparent Overlay")
        self.mask_transparent_cb.setChecked(True)
        self.mask_transparent_cb.setStyleSheet(checkbox_style)
        mask_inner_layout.addWidget(self.mask_transparent_cb)
        
        self.mask_info_label = QLabel("No mask loaded")
        self.mask_info_label.setStyleSheet("color: gray; font-size: 8pt; padding: 5px; background-color: rgba(255,255,255,0.05); border-radius: 3px;")
        mask_inner_layout.addWidget(self.mask_info_label)
        
        ref_layout.addWidget(mask_frame)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setStyleSheet(f"background-color: {self.colors['border']}; max-height: 2px; margin: 12px 0px;")
        ref_layout.addWidget(separator2)

        # Peak search settings frame
        peak_frame = QFrame()
        peak_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(240, 240, 240, 0.3);
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                padding: 12px;
                margin: 5px 0px;
            }}
        """)
        peak_layout_inner = QVBoxLayout(peak_frame)
        peak_layout_inner.setSpacing(10)
        peak_layout_inner.setContentsMargins(8, 8, 8, 8)

        # Peak search algorithm
        algo_layout = QHBoxLayout()
        algo_layout.setSpacing(8)

        algo_label = QLabel("Peak Search:")
        algo_label.setMinimumWidth(100)
        algo_layout.addWidget(algo_label)
        self.peak_search_algorithm_cb = QComboBox()
        self.peak_search_algorithm_cb.addItems(["Massif", "Blob"])
        algo_layout.addWidget(self.peak_search_algorithm_cb)
        algo_layout.addStretch()
        peak_layout_inner.addLayout(algo_layout)
        
        # Number of rings
        rings_layout = QHBoxLayout()
        rings_label = QLabel("# of rings:")
        rings_label.setFixedWidth(100)
        rings_layout.addWidget(rings_label)
        self.number_of_rings_sb = QSpinBox()
        self.number_of_rings_sb.setMinimum(1)
        self.number_of_rings_sb.setMaximum(50)
        self.number_of_rings_sb.setValue(10)
        self.number_of_rings_sb.setFixedWidth(80)
        rings_layout.addWidget(self.number_of_rings_sb)
        rings_layout.addStretch()
        peak_layout_inner.addLayout(rings_layout)
        
        # Delta 2theta
        delta_layout = QHBoxLayout()
        delta_label = QLabel("Δ2θ:")
        delta_label.setFixedWidth(100)
        delta_layout.addWidget(delta_label)
        self.delta_tth_txt = QLineEdit("0.5")
        self.delta_tth_txt.setFixedWidth(80)
        delta_layout.addWidget(self.delta_tth_txt)
        delta_layout.addWidget(QLabel("°"))
        delta_layout.addStretch()
        peak_layout_inner.addLayout(delta_layout)
        
        # Intensity mean factor
        mean_layout = QHBoxLayout()
        mean_label = QLabel("I mean factor:")
        mean_label.setFixedWidth(100)
        mean_layout.addWidget(mean_label)
        self.intensity_mean_factor_sb = QDoubleSpinBox()
        self.intensity_mean_factor_sb.setMinimum(0.1)
        self.intensity_mean_factor_sb.setMaximum(10.0)
        self.intensity_mean_factor_sb.setSingleStep(0.1)
        self.intensity_mean_factor_sb.setValue(3.0)
        self.intensity_mean_factor_sb.setFixedWidth(80)
        mean_layout.addWidget(self.intensity_mean_factor_sb)
        mean_layout.addStretch()
        peak_layout_inner.addLayout(mean_layout)
        
        # Intensity limit
        limit_layout = QHBoxLayout()
        limit_label = QLabel("I limit:")
        limit_label.setFixedWidth(100)
        limit_layout.addWidget(limit_label)
        self.intensity_limit_txt = QLineEdit("50")
        self.intensity_limit_txt.setFixedWidth(80)
        limit_layout.addWidget(self.intensity_limit_txt)
        limit_layout.addStretch()
        peak_layout_inner.addLayout(limit_layout)
        
        ref_layout.addWidget(peak_frame)
        
        parent_layout.addWidget(ref_gb)
    
    def setup_pyfai_parameters(self, parent_layout):
        """Setup pyFAI Parameters section (Dioptas style)"""
        pyfai_gb = QGroupBox("pyFAI Geometry Parameters")
        pyfai_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                margin-top: 15px;
                margin-bottom: 10px;
                padding: 15px 10px 10px 10px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['text_dark']};
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
        """)
        pyfai_layout = QVBoxLayout(pyfai_gb)
        pyfai_layout.setSpacing(8)
        
        # Distance
        self._add_param_row(pyfai_layout, "Distance:", "pyfai_dist", "0.200", "m", True)
        
        # PONI1
        self._add_param_row(pyfai_layout, "PONI1:", "pyfai_poni1", "0.100", "m", True)
        
        # PONI2
        self._add_param_row(pyfai_layout, "PONI2:", "pyfai_poni2", "0.100", "m", True)
        
        # Rot1
        self._add_param_row(pyfai_layout, "Rot1:", "pyfai_rot1", "0.000", "rad", True)
        
        # Rot2
        self._add_param_row(pyfai_layout, "PONI2:", "pyfai_rot2", "0.000", "rad", True)
        
        # Rot3
        self._add_param_row(pyfai_layout, "Rot3:", "pyfai_rot3", "0.000", "rad", True)
        
        # Wavelength
        self._add_param_row(pyfai_layout, "Wavelength:", "pyfai_wavelength", "0.4133", "Å", False)
        
        # Update from fit button
        update_btn = QPushButton("Update from fit")
        update_btn.clicked.connect(self.update_pyfai_from_fit)
        pyfai_layout.addWidget(update_btn)
        
        parent_layout.addWidget(pyfai_gb)
    
    def setup_fit2d_parameters(self, parent_layout):
        """Setup Fit2d Parameters section (Dioptas style)"""
        fit2d_gb = QGroupBox("Fit2d Geometry Parameters")
        fit2d_gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                border: 2px solid {self.colors['border']};
                border-radius: 5px;
                margin-top: 15px;
                margin-bottom: 10px;
                padding: 15px 10px 10px 10px;
                background-color: {self.colors['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['text_dark']};
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }}
        """)
        fit2d_layout = QVBoxLayout(fit2d_gb)
        fit2d_layout.setSpacing(8)
        
        # Direct beam distance
        self._add_param_row_simple(fit2d_layout, "Direct beam distance:", "fit2d_dist", "200.0", "mm")
        
        # Center X
        self._add_param_row_simple(fit2d_layout, "Center X:", "fit2d_centerx", "1024", "px")
        
        # Center Y
        self._add_param_row_simple(fit2d_layout, "Center Y:", "fit2d_centery", "1024", "px")
        
        # Tilt
        self._add_param_row_simple(fit2d_layout, "Tilt:", "fit2d_tilt", "0.00", "°")
        
        # Rotation
        self._add_param_row_simple(fit2d_layout, "Rotation:", "fit2d_rotation", "0.00", "°")
        
        # Wavelength
        self._add_param_row_simple(fit2d_layout, "Wavelength:", "fit2d_wavelength", "0.4133", "Å")
        
        # Polarization
        self._add_param_row_simple(fit2d_layout, "Polarization:", "fit2d_polarization", "0.99", "")
        
        # Update from fit button
        update_btn = QPushButton("Update from fit")
        update_btn.clicked.connect(self.update_fit2d_from_fit)
        fit2d_layout.addWidget(update_btn)
        
        parent_layout.addWidget(fit2d_gb)
    
    def _add_param_row(self, layout, label_text, var_name, default_val, unit, has_checkbox):
        """Helper to add parameter row with label, textbox, unit, and optional checkbox"""
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        
        txt = QLineEdit(default_val)
        txt.setFixedWidth(80)
        txt.setReadOnly(True)
        setattr(self, f"{var_name}_txt", txt)
        row.addWidget(txt)
        
        if unit:
            row.addWidget(QLabel(unit))
        
        if has_checkbox:
            cb = QCheckBox("refine")
            cb.setChecked(True)
            setattr(self, f"{var_name}_cb", cb)
            row.addWidget(cb)
        
        row.addStretch()
        layout.addLayout(row)
    
    def _add_param_row_simple(self, layout, label_text, var_name, default_val, unit):
        """Helper to add simple parameter row (read-only, no checkbox)"""
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        
        txt = QLineEdit(default_val)
        txt.setFixedWidth(80)
        txt.setReadOnly(True)
        setattr(self, f"{var_name}_txt", txt)
        row.addWidget(txt)
        
        if unit:
            row.addWidget(QLabel(unit))
        
        row.addStretch()
        layout.addLayout(row)
    
    def setup_file_section_compact(self, parent_layout):
        """Setup compact file input section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)
        
        title = QLabel("📁 Image")
        title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Browse button
        browse_img_btn = ModernButton("Browse & Load",
                                     self.browse_and_load_image,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=120, height=28,
                                     font_size=9,
                                     parent=card)
        card_layout.addWidget(browse_img_btn)
        
        parent_layout.addWidget(card)
    
    def setup_file_section(self, parent_layout):
        """Setup file input section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("📁 Image Files")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Image file
        img_label = QLabel("Calibration Image:")
        img_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(img_label)
        
        img_frame = QFrame()
        img_layout = QHBoxLayout(img_frame)
        img_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_entry = QLineEdit()
        self.image_entry.setPlaceholderText("Select calibration image (e.g., LaB6, CeO2)...")
        self.image_entry.setReadOnly(True)
        img_layout.addWidget(self.image_entry)
        
        browse_img_btn = ModernButton("Browse & Load",
                                     self.browse_and_load_image,
                                     "",
                                     bg_color=self.colors['accent'],
                                     hover_color=self.colors['primary'],
                                     width=120, height=28,
                                     font_size=9,
                                     parent=img_frame)
        img_layout.addWidget(browse_img_btn)
        
        card_layout.addWidget(img_frame)
        
        parent_layout.addWidget(card)

    def setup_calibrant_section_compact(self, parent_layout):
        """Setup compact calibrant selection section - Dioptas style"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)
        
        title = QLabel("🎯 Calibrant")
        title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Calibrant selection
        self.calibrant_combo = QComboBox()
        if PYFAI_AVAILABLE:
            calibrants = sorted(ALL_CALIBRANTS.keys())
            self.calibrant_combo.addItems(calibrants)
            if "LaB6" in calibrants:
                self.calibrant_combo.setCurrentText("LaB6")
        self.calibrant_combo.currentTextChanged.connect(self.on_calibrant_changed)
        card_layout.addWidget(self.calibrant_combo)
        
        # Load custom calibrant button
        load_cal_btn = ModernButton("Load Custom",
                                   self.load_custom_calibrant,
                                   "📂",
                                   bg_color=self.colors['secondary'],
                                   hover_color=self.colors['primary'],
                                   width=120, height=24,
                                   font_size=8,
                                   parent=card)
        card_layout.addWidget(load_cal_btn)
        
        # Wavelength
        wl_label = QLabel("λ (Å):")
        wl_label.setFont(QFont('Arial', 8))
        card_layout.addWidget(wl_label)
        
        self.wavelength_entry = QLineEdit(str(self.wavelength))
        self.wavelength_entry.setPlaceholderText("Wavelength")
        self.wavelength_entry.textChanged.connect(self.on_wavelength_changed)
        card_layout.addWidget(self.wavelength_entry)
        
        parent_layout.addWidget(card)
        
        # Update calibrant info for default
        if not hasattr(self, 'calibrant_info_text'):
            # For compact version, we don't show the info text, but still update the calibrant object
            self.calibrant = None
            if PYFAI_AVAILABLE:
                try:
                    calibrant_name = self.calibrant_combo.currentText()
                    if calibrant_name in ALL_CALIBRANTS:
                        self.calibrant = ALL_CALIBRANTS[calibrant_name]
                except:
                    pass
    
    def setup_calibrant_section(self, parent_layout):
        """Setup calibrant selection section - Dioptas style"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("🎯 Calibrant & Wavelength")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Calibrant selection row
        cal_row = QFrame()
        cal_row_layout = QHBoxLayout(cal_row)
        cal_row_layout.setContentsMargins(0, 5, 0, 5)
        
        cal_label = QLabel("Calibrant:")
        cal_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        cal_label.setFixedWidth(80)
        cal_row_layout.addWidget(cal_label)
        
        self.calibrant_combo = QComboBox()
        if PYFAI_AVAILABLE:
            calibrants = sorted(ALL_CALIBRANTS.keys())
            self.calibrant_combo.addItems(calibrants)
            if "LaB6" in calibrants:
                self.calibrant_combo.setCurrentText("LaB6")
        else:
            self.calibrant_combo.addItems(["LaB6", "CeO2", "Si", "Al2O3"])
        
        self.calibrant_combo.currentTextChanged.connect(self.on_calibrant_changed)
        cal_row_layout.addWidget(self.calibrant_combo)
        
        card_layout.addWidget(cal_row)
        
        # Load custom calibrant button
        load_cal_btn = ModernButton("Load Custom Calibrant",
                                   self.load_custom_calibrant,
                                   "📂",
                                   bg_color=self.colors['secondary'],
                                   hover_color=self.colors['primary'],
                                   width=180, height=28,
                                   font_size=9,
                                   parent=card)
        card_layout.addWidget(load_cal_btn)
        
        # Calibrant information display (d-spacings)
        info_label = QLabel("D-spacings (Å):")
        info_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(info_label)
        
        self.calibrant_info_text = QTextEdit()
        self.calibrant_info_text.setReadOnly(True)
        self.calibrant_info_text.setMaximumHeight(80)
        self.calibrant_info_text.setFont(QFont('Courier', 8))
        self.calibrant_info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        card_layout.addWidget(self.calibrant_info_text)
        
        # Wavelength row
        wl_row = QFrame()
        wl_row_layout = QHBoxLayout(wl_row)
        wl_row_layout.setContentsMargins(0, 5, 0, 5)
        
        wl_label = QLabel("Wavelength (Å):")
        wl_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        wl_label.setFixedWidth(120)
        wl_row_layout.addWidget(wl_label)
        
        self.wavelength_entry = QLineEdit(str(self.wavelength))
        self.wavelength_entry.setPlaceholderText("Enter wavelength")
        self.wavelength_entry.textChanged.connect(self.on_wavelength_changed)
        wl_row_layout.addWidget(self.wavelength_entry)
        
        card_layout.addWidget(wl_row)
        
        parent_layout.addWidget(card)
        
        # Update calibrant info display for default calibrant
        self.update_calibrant_info()

    def setup_detector_section_compact(self, parent_layout):
        """Setup compact detector parameters section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)
        
        title = QLabel("📷 Detector")
        title.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Detector selection
        self.detector_combo = QComboBox()
        detectors = ["Pilatus2M", "Pilatus1M", "Pilatus300K", "PerkinElmer", 
                     "Eiger2M", "Eiger1M", "Mar345", "Custom"]
        self.detector_combo.addItems(detectors)
        self.detector_combo.currentTextChanged.connect(self.on_detector_changed)
        card_layout.addWidget(self.detector_combo)
        
        # Pixel size
        pixel_label = QLabel("Pixel (μm):")
        pixel_label.setFont(QFont('Arial', 8))
        card_layout.addWidget(pixel_label)
        
        self.pixel_entry = QLineEdit(str(self.pixel_size * 1e6))
        card_layout.addWidget(self.pixel_entry)
        
        # Distance
        dist_label = QLabel("Dist (m):")
        dist_label.setFont(QFont('Arial', 8))
        card_layout.addWidget(dist_label)
        
        self.distance_entry = QLineEdit(str(self.distance))
        card_layout.addWidget(self.distance_entry)
        
        parent_layout.addWidget(card)
    
    def setup_detector_section(self, parent_layout):
        """Setup detector parameters section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("📷 Detector Parameters")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Detector selection
        det_label = QLabel("Detector:")
        det_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(det_label)
        
        self.detector_combo = QComboBox()
        detectors = ["Pilatus2M", "Pilatus1M", "Pilatus300K", "PerkinElmer", 
                     "Eiger2M", "Eiger1M", "Mar345", "Custom"]
        self.detector_combo.addItems(detectors)
        self.detector_combo.currentTextChanged.connect(self.on_detector_changed)
        card_layout.addWidget(self.detector_combo)
        
        # Pixel size
        pixel_label = QLabel("Pixel Size (μm):")
        pixel_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(pixel_label)
        
        self.pixel_entry = QLineEdit(str(self.pixel_size * 1e6))
        card_layout.addWidget(self.pixel_entry)
        
        # Distance (initial guess)
        dist_label = QLabel("Sample-Detector Distance (m):")
        dist_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(dist_label)
        
        self.distance_entry = QLineEdit(str(self.distance))
        card_layout.addWidget(self.distance_entry)
        
        parent_layout.addWidget(card)
    
    def setup_threshold_section(self, parent_layout):
        """Setup threshold mask section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("🔢 Threshold Mask")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        info_label = QLabel("Mask pixels outside the intensity range:")
        info_label.setFont(QFont('Arial', 8))
        info_label.setWordWrap(True)
        card_layout.addWidget(info_label)
        
        # Min/Max in same row
        thresh_row = QWidget()
        thresh_layout = QHBoxLayout(thresh_row)
        thresh_layout.setContentsMargins(0, 0, 0, 0)
        
        thresh_layout.addWidget(QLabel("Min:"))
        self.threshold_min_entry = QLineEdit("0")
        self.threshold_min_entry.setFixedWidth(80)
        thresh_layout.addWidget(self.threshold_min_entry)
        
        thresh_layout.addWidget(QLabel("Max:"))
        self.threshold_max_entry = QLineEdit("65535")
        self.threshold_max_entry.setFixedWidth(80)
        thresh_layout.addWidget(self.threshold_max_entry)
        
        card_layout.addWidget(thresh_row)
        
        # Apply button
        apply_thresh_btn = ModernButton("Apply Threshold",
                                       self.apply_threshold_mask,
                                       "",
                                       bg_color=self.colors['secondary'],
                                       hover_color=self.colors['primary'],
                                       width=150, height=28,
                                       font_size=9,
                                       parent=card)
        card_layout.addWidget(apply_thresh_btn)
        
        parent_layout.addWidget(card)

    def setup_mask_section(self, parent_layout):
        """Setup mask creation section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("🎭 Mask & Display Tools")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Contrast controls
        contrast_label = QLabel("Contrast Adjustment:")
        contrast_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(contrast_label)
        
        # Min contrast slider
        min_contrast_frame = QFrame()
        min_contrast_layout = QHBoxLayout(min_contrast_frame)
        min_contrast_layout.setContentsMargins(0, 0, 0, 0)
        
        min_label = QLabel("Min:")
        min_label.setFixedWidth(40)
        min_contrast_layout.addWidget(min_label)
        
        self.contrast_min_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_min_slider.setMinimum(0)
        self.contrast_min_slider.setMaximum(65535)
        self.contrast_min_slider.setValue(int(self.contrast_min_val))
        self.contrast_min_slider.valueChanged.connect(self.on_min_slider_changed)
        min_contrast_layout.addWidget(self.contrast_min_slider)
        
        self.contrast_min_entry = QLineEdit(str(self.contrast_min_val))
        self.contrast_min_entry.setFixedWidth(80)
        self.contrast_min_entry.textChanged.connect(self.on_min_entry_changed)
        min_contrast_layout.addWidget(self.contrast_min_entry)
        
        card_layout.addWidget(min_contrast_frame)
        
        # Max contrast slider
        max_contrast_frame = QFrame()
        max_contrast_layout = QHBoxLayout(max_contrast_frame)
        max_contrast_layout.setContentsMargins(0, 0, 0, 0)
        
        max_label = QLabel("Max:")
        max_label.setFixedWidth(40)
        max_contrast_layout.addWidget(max_label)
        
        self.contrast_max_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_max_slider.setMinimum(0)
        self.contrast_max_slider.setMaximum(65535)
        self.contrast_max_slider.setValue(int(self.contrast_max_val))
        self.contrast_max_slider.valueChanged.connect(self.on_max_slider_changed)
        max_contrast_layout.addWidget(self.contrast_max_slider)
        
        self.contrast_max_entry = QLineEdit(str(self.contrast_max_val))
        self.contrast_max_entry.setFixedWidth(80)
        self.contrast_max_entry.textChanged.connect(self.on_max_entry_changed)
        max_contrast_layout.addWidget(self.contrast_max_entry)
        
        card_layout.addWidget(max_contrast_frame)
        
        # Apply and Reset contrast buttons
        contrast_btn_frame = QFrame()
        contrast_btn_layout = QHBoxLayout(contrast_btn_frame)
        
        apply_contrast_btn = ModernButton("Apply",
                                         self.apply_contrast,
                                         "",
                                         bg_color=self.colors['primary'],
                                         hover_color=self.colors['primary_hover'],
                                         width=80, height=28,
                                         font_size=9,
                                         parent=contrast_btn_frame)
        
        reset_contrast_btn = ModernButton("Auto",
                                         self.auto_contrast,
                                         "",
                                         bg_color=self.colors['secondary'],
                                         hover_color=self.colors['primary'],
                                         width=80, height=28,
                                         font_size=9,
                                         parent=contrast_btn_frame)
        
        reset_zoom_btn = ModernButton("Reset Zoom",
                                     self.reset_zoom,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=90, height=28,
                                     font_size=9,
                                     parent=contrast_btn_frame)
        
        contrast_btn_layout.addWidget(apply_contrast_btn)
        contrast_btn_layout.addWidget(reset_contrast_btn)
        contrast_btn_layout.addWidget(reset_zoom_btn)
        card_layout.addWidget(contrast_btn_frame)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {self.colors['border']};")
        separator.setFixedHeight(2)
        card_layout.addWidget(separator)
        
        # Mask mode selection
        mode_label = QLabel("Drawing Mode:")
        mode_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(mode_label)
        
        self.mask_mode_combo = QComboBox()
        self.mask_mode_combo.addItems(["Rectangle", "Circle", "Threshold"])
        self.mask_mode_combo.currentTextChanged.connect(self.on_mask_mode_changed)
        card_layout.addWidget(self.mask_mode_combo)
        
        # Mask/Unmask toggle
        self.mask_value_checkbox = QCheckBox("Mask (checked) / Unmask (unchecked)")
        self.mask_value_checkbox.setChecked(True)
        self.mask_value_checkbox.stateChanged.connect(self.on_mask_value_changed)
        card_layout.addWidget(self.mask_value_checkbox)
        
        # Mask control buttons
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        
        clear_mask_btn = ModernButton("Clear Mask",
                                     self.clear_mask,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=100, height=30,
                                     font_size=9,
                                     parent=btn_frame)
        
        invert_mask_btn = ModernButton("Invert",
                                      self.invert_mask,
                                      "",
                                      bg_color=self.colors['secondary'],
                                      hover_color=self.colors['primary'],
                                      width=80, height=30,
                                      font_size=9,
                                      parent=btn_frame)
        
        save_mask_btn = ModernButton("Save Mask",
                                    self.save_mask,
                                    "",
                                    bg_color=self.colors['secondary'],
                                    hover_color=self.colors['primary'],
                                    width=100, height=30,
                                    font_size=9,
                                    parent=btn_frame)
        
        btn_layout.addWidget(clear_mask_btn)
        btn_layout.addWidget(invert_mask_btn)
        btn_layout.addWidget(save_mask_btn)
        
        card_layout.addWidget(btn_frame)
        
        parent_layout.addWidget(card)

    def setup_calibration_section(self, parent_layout):
        """Setup calibration execution section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("⚙️ Calibration")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # Manual peak selection button
        pick_peaks_btn = ModernButton("📍 Manual Peak Selection",
                                     self.toggle_peak_picking,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=180, height=35,
                                     font_size=9,
                                     parent=card)
        card_layout.addWidget(pick_peaks_btn)
        self.pick_peaks_btn = pick_peaks_btn
        
        # Peak selection info
        peak_info_frame = QFrame()
        peak_info_layout = QHBoxLayout(peak_info_frame)
        peak_info_layout.setContentsMargins(0, 0, 0, 0)
        
        self.peak_count_label = QLabel("Peaks: 0")
        self.peak_count_label.setFont(QFont('Arial', 8))
        peak_info_layout.addWidget(self.peak_count_label)
        
        # Edit Points button (new)
        edit_peaks_btn = ModernButton("Edit",
                                     self.edit_manual_peaks,
                                     "",
                                     bg_color='#4CAF50',
                                     hover_color='#45a049',
                                     width=50, height=25,
                                     font_size=8,
                                     parent=peak_info_frame)
        peak_info_layout.addWidget(edit_peaks_btn)
        
        clear_peaks_btn = ModernButton("Clear",
                                      self.clear_manual_peaks,
                                      "",
                                      bg_color='#FF6B6B',
                                      hover_color='#FF5252',
                                      width=60, height=25,
                                      font_size=8,
                                      parent=peak_info_frame)
        peak_info_layout.addWidget(clear_peaks_btn)
        peak_info_layout.addStretch()
        
        card_layout.addWidget(peak_info_frame)
        
        # Ring number for next peak (Dioptas-style)
        ring_frame = QFrame()
        ring_layout = QHBoxLayout(ring_frame)
        ring_layout.setContentsMargins(0, 0, 0, 0)
        
        ring_label = QLabel("Current Ring #:")
        ring_label.setFixedWidth(90)
        ring_label.setStyleSheet(f"color: {self.colors['text_dark']}; font-weight: bold;")
        ring_layout.addWidget(ring_label)
        
        self.ring_number_entry = QLineEdit("1")
        self.ring_number_entry.setFixedWidth(50)
        self.ring_number_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: #FFF8DC;
                color: {self.colors['text_dark']};
                border: 2px solid {self.colors['primary']};
                padding: 3px;
                font-weight: bold;
            }}
        """)
        ring_layout.addWidget(self.ring_number_entry)
        
        ring_layout.addStretch()
        card_layout.addWidget(ring_frame)
        
        # Auto increment checkbox (Dioptas style)
        self.automatic_peak_num_inc_cb = QCheckBox("Automatic increase ring number")
        self.automatic_peak_num_inc_cb.setChecked(True)
        self.automatic_peak_num_inc_cb.setStyleSheet(f"color: {self.colors['text_dark']}; font-size: 9pt;")
        card_layout.addWidget(self.automatic_peak_num_inc_cb)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {self.colors['border']};")
        separator.setFixedHeight(2)
        card_layout.addWidget(separator)
        
        # Number of points
        npt_label = QLabel("Integration Points:")
        npt_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(npt_label)
        
        self.npt_entry = QLineEdit(str(self.npt))
        card_layout.addWidget(self.npt_entry)
        
        # Run calibration button
        calibrate_btn = ModernButton("🎯 Run Calibration",
                                    self.run_calibration,
                                    "",
                                    bg_color=self.colors['primary'],
                                    hover_color=self.colors['primary'],
                                    width=180, height=40,
                                    font_size=9,
                                    parent=card)
        card_layout.addWidget(calibrate_btn)
        
        parent_layout.addWidget(card)

    def setup_output_section(self, parent_layout):
        """Setup output section"""
        card = self.create_card_frame(self.parent)
        card_layout = QVBoxLayout(card)
        
        title = QLabel("💾 Output")
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['text_dark']}; background: {self.colors['card_bg']};")
        card_layout.addWidget(title)
        
        # PONI output
        poni_label = QLabel("Output PONI File:")
        poni_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        card_layout.addWidget(poni_label)
        
        poni_frame = QFrame()
        poni_layout = QHBoxLayout(poni_frame)
        poni_layout.setContentsMargins(0, 0, 0, 0)
        
        self.poni_entry = QLineEdit()
        self.poni_entry.setPlaceholderText("calibration.poni")
        poni_layout.addWidget(self.poni_entry)
        
        browse_poni_btn = ModernButton("Browse",
                                      self.browse_poni_output,
                                      "",
                                      bg_color=self.colors['secondary'],
                                      hover_color=self.colors['primary'],
                                      width=80, height=28,
                                      font_size=9,
                                      parent=poni_frame)
        poni_layout.addWidget(browse_poni_btn)
        
        card_layout.addWidget(poni_frame)
        
        # Save PONI button
        save_poni_btn = ModernButton("💾 Save PONI",
                                    self.save_poni_file,
                                    "",
                                    bg_color=self.colors['secondary'],
                                    hover_color=self.colors['primary'],
                                    width=150, height=35,
                                    font_size=9,
                                    parent=card)
        card_layout.addWidget(save_poni_btn)
        
        parent_layout.addWidget(card)

    def set_tool_mode(self, mode):
        """Set current tool mode"""
        self.tool_mode = mode
        
        # Update button styles
        self.view_mode_btn.setStyleSheet(f"""
            background-color: {self.colors['primary'] if mode == 'view' else self.colors['secondary']};
            color: white; border: none; border-radius: 4px; padding: 6px;
        """)
        self.pick_peaks_tool_btn.setStyleSheet(f"""
            background-color: {self.colors['success'] if mode == 'peaks' else self.colors['secondary']};
            color: white; border: {'2px solid #00ff00' if mode == 'peaks' else 'none'};
            border-radius: 4px; padding: 6px; font-weight: {'bold' if mode == 'peaks' else 'normal'};
        """)
        self.mask_tool_btn.setStyleSheet(f"""
            background-color: {self.colors['accent'] if mode == 'mask' else self.colors['secondary']};
            color: white; border: {'2px solid #ff6b6b' if mode == 'mask' else 'none'};
            border-radius: 4px; padding: 6px; font-weight: {'bold' if mode == 'mask' else 'normal'};
        """)
        
        # Update canvas modes
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
            self.unified_canvas.peak_picking_mode = (mode == 'peaks')
            self.unified_canvas.mask_editing_mode = (mode == 'mask')
            
            # Update title
            if mode == 'view':
                title = 'Calibration Image - Scroll to zoom'
            elif mode == 'peaks':
                title = 'Peak Selection Mode - Click on diffraction rings'
            elif mode == 'mask':
                title = 'Mask Editing Mode - Draw masks on image'
            
            self.unified_canvas.axes.set_title(title)
            self.unified_canvas.draw_idle()
        
        self.log(f"Tool mode: {mode.upper()}")
    
    def switch_display_tab(self, tab_name):
        """Legacy method for compatibility"""
        self.current_display = tab_name

    def browse_and_load_image(self):
        """Browse for calibration image and load it immediately"""
        filename, _ = QFileDialog.getOpenFileName(
            None, "Select Calibration Image", "",
            "Image Files (*.tif *.tiff *.edf *.cbf *.mar3450 *.img *.h5 *.hdf5);;HDF5 Files (*.h5 *.hdf5);;TIFF Files (*.tif *.tiff);;EDF Files (*.edf);;All Files (*.*)"
        )
        if filename:
            self.image_path = filename
            # Update filename display
            if hasattr(self, 'filename_txt'):
                self.filename_txt.setText(os.path.basename(filename))
            if hasattr(self, 'image_entry'):
                self.image_entry.setText(filename)
            # Automatically load the image
            self.load_image_file()

    def browse_poni_output(self):
        """Browse for PONI output location"""
        filename, _ = QFileDialog.getSaveFileName(
            None, "Save PONI File", "",
            "PONI Files (*.poni);;All Files (*.*)"
        )
        if filename:
            self.output_poni = filename
            self.poni_entry.setText(filename)

    def load_image_file(self):
        """Load calibration image"""
        # Try to get image path from either entry field
        image_path = None
        if hasattr(self, 'image_entry') and self.image_entry.text():
            image_path = self.image_entry.text()
        elif hasattr(self, 'filename_txt') and self.filename_txt.text():
            image_path = self.image_path  # Use stored path
        
        if not image_path:
            QMessageBox.warning(None, "No Image", "Please select a calibration image first.")
            return
        
        try:
            # Check if HDF5 file
            if image_path.lower().endswith(('.h5', '.hdf5')):
                try:
                    import h5py
                    # Use 'r' mode with swmr=True for better performance if available
                    with h5py.File(image_path, 'r', swmr=False, rdcc_nbytes=1024**3) as f:
                        # Try common HDF5 dataset paths
                        dataset_paths = [
                            'entry/data/data',
                            'entry/instrument/detector/data',
                            'data',
                            'image',
                        ]
                        
                        # Find first available dataset
                        for path in dataset_paths:
                            try:
                                data = f[path]
                                if len(data.shape) >= 2:
                                    # Get first image if 3D stack, use direct array read for speed
                                    if len(data.shape) == 3:
                                        # Read only the first frame directly into numpy array
                                        self.current_image = np.array(data[0, :, :], dtype=np.float32)
                                    else:
                                        # Read entire 2D array at once
                                        self.current_image = np.array(data[:], dtype=np.float32)
                                    self.log(f"Loaded HDF5 dataset: {path} (shape: {self.current_image.shape})")
                                    break
                            except KeyError:
                                continue
                        else:
                            # If no standard path found, list available datasets
                            self.log("Standard dataset paths not found. Available datasets:")
                            def print_structure(name, obj):
                                if isinstance(obj, h5py.Dataset):
                                    self.log(f"  {name}: {obj.shape}")
                            f.visititems(print_structure)
                            
                            QMessageBox.warning(None, "HDF5 Structure", 
                                              "Could not find standard dataset path.\nCheck log for available datasets.")
                            return
                except ImportError:
                    QMessageBox.warning(None, "h5py Required", 
                                      "h5py is required to read HDF5 files.\nInstall with: pip install h5py")
                    return
            elif FABIO_AVAILABLE:
                img = fabio.open(image_path)
                self.current_image = img.data
            else:
                from PIL import Image
                img = Image.open(image_path)
                self.current_image = np.array(img)
            
            self.log("Image loaded successfully")
            self.log(f"Image shape: {self.current_image.shape}")
            
            # Display image on unified canvas (optimized for immediate display)
            if MATPLOTLIB_AVAILABLE:
                from PyQt6.QtCore import QTimer
                from PyQt6.QtWidgets import QApplication
                
                # Ensure image_data is set on unified canvas
                self.unified_canvas.image_data = self.current_image
                if self.unified_canvas.mask_data is None:
                    self.unified_canvas.mask_data = np.zeros(self.current_image.shape, dtype=bool)
                
                # Link canvas to module before display
                self.unified_canvas.parent_module = self
                
                # Display image immediately with forced update
                self.unified_canvas.display_calibration_image(self.current_image)
                
                # Force immediate canvas draw and GUI update
                self.unified_canvas.draw()  # Use immediate draw for initial load
                QApplication.processEvents()  # Process GUI events immediately
                
                # Also load to mask canvas for legacy mask operations (async)
                QTimer.singleShot(10, lambda: self.mask_canvas.load_image(image_path))
            
            # Sync image to mask module
            if self.mask_module_reference is not None:
                self.mask_module_reference.set_image_for_mask(self.current_image)
                self.log(f"Image synced to Mask Module")
            
        except Exception as e:
            self.log(f"Error loading image: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to load image:\n{str(e)}")

    def on_calibrant_changed(self, calibrant_name):
        """Handle calibrant selection change"""
        self.calibrant_name = calibrant_name
        self.log(f"Calibrant changed to: {calibrant_name}")
        self.update_calibrant_info()
    
    def on_wavelength_changed(self, text):
        """Handle wavelength change"""
        try:
            self.wavelength = float(text)
            self.log(f"Wavelength set to: {self.wavelength} Å")
        except ValueError:
            pass
    
    def load_custom_calibrant(self):
        """Load custom calibrant from .D file (Dioptas style)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Custom Calibrant",
            "",
            "Calibrant Files (*.D *.d);;All Files (*.*)"
        )
        
        if file_path and PYFAI_AVAILABLE:
            try:
                # Load calibrant from file
                calibrant = Calibrant(filename=file_path)
                
                # Add to combo box if not already there
                calibrant_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # Check if already in list
                index = self.calibrant_combo.findText(calibrant_name)
                if index == -1:
                    self.calibrant_combo.addItem(calibrant_name)
                    self.calibrant_combo.setCurrentText(calibrant_name)
                else:
                    self.calibrant_combo.setCurrentIndex(index)
                
                # Store custom calibrant
                self.calibrant = calibrant
                self.calibrant_name = calibrant_name
                
                self.log(f"✅ Loaded custom calibrant: {calibrant_name}")
                self.update_calibrant_info()
                
            except Exception as e:
                QMessageBox.critical(
                    self.parent,
                    "Error Loading Calibrant",
                    f"Failed to load calibrant file:\n{str(e)}"
                )
                self.log(f"❌ Error loading calibrant: {str(e)}")
    
    def update_calibrant_info(self):
        """Update calibrant information display with d-spacings"""
        if not PYFAI_AVAILABLE:
            return
        
        try:
            # Get current calibrant
            if self.calibrant is None:
                calibrant_name = self.calibrant_combo.currentText()
                if calibrant_name in ALL_CALIBRANTS:
                    self.calibrant = ALL_CALIBRANTS[calibrant_name]
                else:
                    return
            
            # Get d-spacings
            dspacing = self.calibrant.get_dSpacing()
            
            if dspacing is not None and len(dspacing) > 0:
                # Display first 10 d-spacings
                info_text = ", ".join([f"{d:.4f}" for d in dspacing[:10]])
                if len(dspacing) > 10:
                    info_text += f"... ({len(dspacing)} total rings)"
                
                self.calibrant_info_text.setText(info_text)
            else:
                self.calibrant_info_text.setText("No d-spacing data available")
                
        except Exception as e:
            self.calibrant_info_text.setText(f"Error: {str(e)}")
            self.log(f"Warning: Could not load calibrant info: {str(e)}")

    def on_detector_changed(self, detector_name):
        """Handle detector selection change"""
        self.detector_name = detector_name
        
        # Update pixel size based on detector
        detector_specs = {
            "Pilatus2M": 172e-6,
            "Pilatus1M": 172e-6,
            "Pilatus300K": 172e-6,
            "PerkinElmer": 200e-6,
            "Eiger2M": 75e-6,
            "Eiger1M": 75e-6,
            "Eiger4M": 75e-6,
            "Mar345": 100e-6,
            "Rayonix": 88e-6,
        }
        
        if detector_name in detector_specs:
            pixel_size = detector_specs[detector_name]
            self.pixel_size = pixel_size
            
            # Update both pixel width and height fields if they exist
            if hasattr(self, 'pixel_width_txt'):
                self.pixel_width_txt.setText(str(pixel_size * 1e6))
            if hasattr(self, 'pixel_height_txt'):
                self.pixel_height_txt.setText(str(pixel_size * 1e6))
            
            # Legacy support for old UI
            if hasattr(self, 'pixel_entry'):
                self.pixel_entry.setText(str(pixel_size * 1e6))
            
            self.log(f"Detector: {detector_name}, Pixel size: {pixel_size*1e6:.1f} μm")

    def on_use_mask_changed(self, state):
        """Handle use mask checkbox change"""
        if state == Qt.CheckState.Checked.value:
            # Automatically fetch mask from mask module
            if self.mask_module_reference is not None:
                mask = self.mask_module_reference.get_current_mask()
                if mask is not None:
                    self.imported_mask = mask
                    shape_str = f"{mask.shape[0]}×{mask.shape[1]}"
                    masked_pixels = np.sum(mask)
                    total_pixels = mask.size
                    percentage = (masked_pixels / total_pixels) * 100
                    self.mask_info_label.setText(f"Mask active: {masked_pixels:,} pixels ({percentage:.2f}%)")
                    self.mask_info_label.setStyleSheet("color: green; font-size: 8pt; padding: 5px; background-color: rgba(0,255,0,0.1); border-radius: 3px;")
                    self.log(f"Using mask from Mask Module: {shape_str}, {masked_pixels:,} pixels masked")
                    
                    # Apply mask to calibration canvas
                    if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas') and self.current_image is not None:
                        self.unified_canvas.mask_data = mask
                        self.unified_canvas.display_calibration_image(self.current_image)
                        self.log("Mask overlay applied to calibration image")
                else:
                    self.mask_info_label.setText("No mask available in Mask Module")
                    self.mask_info_label.setStyleSheet("color: orange; font-size: 8pt; padding: 5px; background-color: rgba(255,165,0,0.1); border-radius: 3px;")
                    self.use_mask_cb.setChecked(False)
                    self.log("Warning: No mask available in Mask Module")
                    QMessageBox.information(None, "No Mask Available", 
                                          "No mask is currently available in the Mask Module.\n\n"
                                          "Please switch to the Mask Module and create a mask first:\n"
                                          "1. Use drawing tools (Rectangle, Circle, Polygon, Point)\n"
                                          "2. Or apply threshold masking\n"
                                          "3. Then return here and check 'Use Mask from Mask Module' again")
            else:
                self.use_mask_cb.setChecked(False)
                self.log("Warning: Mask Module not available")
                QMessageBox.warning(None, "Mask Module Not Available", 
                                  "The Mask Module is not initialized.\n"
                                  "Please restart the application.")
        else:
            self.imported_mask = None
            self.mask_info_label.setText("No mask loaded")
            self.mask_info_label.setStyleSheet("color: gray; font-size: 8pt; padding: 5px; background-color: rgba(255,255,255,0.05); border-radius: 3px;")
            
            # Remove mask overlay from calibration canvas
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                if self.unified_canvas.mask_data is not None:
                    self.unified_canvas.mask_data = np.zeros_like(self.unified_canvas.mask_data, dtype=bool)
                    if self.current_image is not None:
                        self.unified_canvas.display_calibration_image(self.current_image)
                        self.log("Mask overlay removed from calibration image")
            
            self.log("Mask will not be used in calibration")
    
    def import_mask_from_module(self):
        """Import mask from mask module"""
        # Try to get mask from mask module reference
        if self.mask_module_reference is not None:
            mask = self.mask_module_reference.get_current_mask()
            if mask is not None:
                self.imported_mask = mask
                masked_pixels = np.sum(mask)
                total_pixels = mask.size
                percentage = (masked_pixels / total_pixels) * 100
                
                self.mask_info_label.setText(f"Mask imported: {masked_pixels:,} pixels ({percentage:.2f}%)")
                self.mask_info_label.setStyleSheet("color: green; padding: 3px;")
                self.use_mask_cb.setChecked(True)
                
                self.log(f"Mask imported from Mask Module: {masked_pixels:,} / {total_pixels:,} pixels")
            else:
                QMessageBox.warning(None, "No Mask", 
                                  "No mask found in Mask Module. Please create a mask first.")
        else:
            QMessageBox.warning(None, "Mask Module Not Found", 
                              "Mask Module is not available. Please open Mask Module first.")
            self.log("Mask module reference not set. Fallback to file loading.")
            self.load_mask_from_file()
    
    def load_mask_from_file(self):
        """Load mask from file as fallback"""
        filename, _ = QFileDialog.getOpenFileName(
            None, "Load Mask", "",
            "Mask Files (*.edf *.npy);;All Files (*.*)"
        )
        
        if filename:
            try:
                if filename.endswith('.npy'):
                    mask = np.load(filename)
                elif filename.endswith('.edf') and FABIO_AVAILABLE:
                    mask_img = fabio.open(filename)
                    mask = mask_img.data.astype(bool)
                else:
                    QMessageBox.warning(None, "Error", "Unsupported mask format")
                    return
                
                self.imported_mask = mask
                masked_pixels = np.sum(mask)
                total_pixels = mask.size
                percentage = (masked_pixels / total_pixels) * 100
                
                self.mask_info_label.setText(f"Mask loaded: {masked_pixels:,} pixels ({percentage:.2f}%)")
                self.mask_info_label.setStyleSheet("color: green; padding: 3px;")
                self.use_mask_cb.setChecked(True)
                
                self.log(f"Mask loaded from file: {os.path.basename(filename)}")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to load mask:\n{str(e)}")
                self.log(f"Error loading mask: {str(e)}")
    
    def set_mask_module_reference(self, mask_module):
        """Set reference to mask module (called from main app)"""
        self.mask_module_reference = mask_module
        self.log("Mask module reference set")

    def on_peak_mode_changed(self):
        """Handle peak selection mode change"""
        if hasattr(self, 'select_peak_rb') and self.select_peak_rb.isChecked():
            # Enable manual peak picking mode
            self.peak_picking_mode = True
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                self.unified_canvas.peak_picking_mode = True
                # Update canvas title
                if self.current_image is not None:
                    self.unified_canvas.display_calibration_image(self.current_image)
            self.log("Manual peak selection mode: ENABLED - Click on diffraction rings")
        else:
            # Disable manual peak picking mode
            self.peak_picking_mode = False
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                self.unified_canvas.peak_picking_mode = False
                # Update canvas title
                if self.current_image is not None:
                    self.unified_canvas.display_calibration_image(self.current_image)
            self.log("Automatic peak search mode: ENABLED")
    
    def toggle_peak_picking(self):
        """Toggle manual peak picking mode"""
        self.peak_picking_mode = not self.peak_picking_mode
        
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'calibration_canvas'):
            self.calibration_canvas.peak_picking_mode = self.peak_picking_mode
        
        # Update button appearance
        if hasattr(self, 'pick_peaks_btn'):
            if self.peak_picking_mode:
                self.pick_peaks_btn.setStyleSheet(f"""
                    background-color: {self.colors['success']};
                    color: white; border: 2px solid #00ff00;
                    border-radius: 4px; padding: 8px;
                    font-weight: bold;
                """)
                self.log("Peak picking mode: ENABLED - Click on diffraction rings to add peaks")
            else:
                self.pick_peaks_btn.setStyleSheet(f"""
                    background-color: {self.colors['secondary']};
                    color: white; border: none;
                    border-radius: 4px; padding: 8px;
                """)
                self.log("Peak picking mode: DISABLED")
    
    def undo_last_peak(self):
        """Undo the last manually selected peak"""
        if not hasattr(self, 'unified_canvas') or self.unified_canvas is None:
            return
        
        if len(self.unified_canvas.manual_peaks) == 0:
            self.log("No peaks to undo")
            return
        
        # Remove the last peak
        removed_peak = self.unified_canvas.manual_peaks.pop()
        self.log(f"Removed peak at ({removed_peak[0]:.1f}, {removed_peak[1]:.1f}), Ring #{removed_peak[2]}")
        
        # Update peak count
        if hasattr(self, 'peak_count_label'):
            self.peak_count_label.setText(f"Peaks: {len(self.unified_canvas.manual_peaks)}")
        
        # Redraw image
        if self.current_image is not None:
            self.unified_canvas.display_calibration_image(self.current_image)
    
    
    def clear_manual_peaks(self):
        """Clear manually selected peaks"""
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'calibration_canvas'):
            self.calibration_canvas.clear_manual_peaks()
            self.update_peak_count()
            self.log("Cleared all manual peaks")
    
    def update_peak_count(self):
        """Update peak count display"""
        if hasattr(self, 'peak_count_label') and hasattr(self, 'unified_canvas'):
            count = len(self.unified_canvas.manual_peaks)
            self.peak_count_label.setText(f"Peaks: {count}")
    

    
    def run_calibration(self):
        """Run detector calibration"""
        if not PYFAI_AVAILABLE:
            QMessageBox.warning(None, "pyFAI Required", 
                              "pyFAI is required for calibration.\nInstall with: pip install pyFAI")
            return
        
        if self.current_image is None:
            QMessageBox.warning(None, "No Image", "Please load a calibration image first.")
            return
        
        try:
            # Get calibrant name from combo box
            if hasattr(self, 'calibrant_combo'):
                calibrant_name = self.calibrant_combo.currentText()
            else:
                calibrant_name = self.calibrant_name
            
            if not calibrant_name or calibrant_name not in ALL_CALIBRANTS:
                QMessageBox.warning(None, "Invalid Calibrant", 
                                  f"Please select a valid calibrant. Current: {calibrant_name}")
                return
            
            # Get parameters with validation
            try:
                # Try new UI or old UI
                if hasattr(self, 'wavelength_txt'):
                    wavelength = float(self.wavelength_txt.text()) * 1e-10  # Convert Å to meters
                elif hasattr(self, 'wavelength_entry'):
                    wavelength = float(self.wavelength_entry.text()) * 1e-10  # Convert Å to meters
                else:
                    wavelength = self.wavelength * 1e-10
            except (ValueError, AttributeError):
                QMessageBox.warning(None, "Invalid Input", "Please enter a valid wavelength.")
                return
                
            try:
                # Try new UI (distance in mm) or old UI (distance in m)
                if hasattr(self, 'distance_txt'):
                    distance = float(self.distance_txt.text()) / 1000.0  # Convert mm to meters
                elif hasattr(self, 'distance_entry'):
                    distance = float(self.distance_entry.text())
                else:
                    distance = self.distance
            except (ValueError, AttributeError):
                QMessageBox.warning(None, "Invalid Input", "Please enter a valid distance.")
                return
                
            try:
                # Try to get pixel size from new UI first, then fall back to old UI
                if hasattr(self, 'pixel_width_txt'):
                    pixel_size = float(self.pixel_width_txt.text()) * 1e-6  # Convert to meters
                elif hasattr(self, 'pixel_entry'):
                    pixel_size = float(self.pixel_entry.text()) * 1e-6  # Convert to meters
                else:
                    pixel_size = self.pixel_size
            except (ValueError, AttributeError):
                QMessageBox.warning(None, "Invalid Input", "Please enter a valid pixel size.")
                return
            
            self.log("Starting calibration...")
            self.log(f"Calibrant: {calibrant_name}")
            self.log(f"Wavelength: {wavelength*1e10:.4f} Å")
            self.log(f"Distance: {distance:.3f} m")
            self.log(f"Pixel size: {pixel_size*1e6:.1f} μm")
            
            # Create calibrant
            calibrant = ALL_CALIBRANTS[calibrant_name]
            calibrant.wavelength = wavelength
            
            # Get mask - use imported mask if "use mask" is checked
            mask = None
            if self.use_mask_cb.isChecked() and self.imported_mask is not None:
                mask = self.imported_mask
                self.log(f"Using imported mask with {np.sum(mask)} masked pixels")
            elif MATPLOTLIB_AVAILABLE and hasattr(self, 'unified_canvas'):
                mask = self.unified_canvas.get_mask()
                if mask is not None and np.any(mask):
                    self.log(f"Using canvas mask with {np.sum(mask)} masked pixels")
            
            # Get manual control points if available
            manual_cp = None
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'calibration_canvas'):
                manual_cp = self.calibration_canvas.get_manual_control_points()
                if manual_cp is not None:
                    self.log(f"Using {len(manual_cp)} manually selected peaks")
            
            # Run calibration in worker thread
            worker = CalibrationWorkerThread(
                self.perform_calibration,
                self.current_image, calibrant, distance, pixel_size, mask, manual_cp
            )
            worker.finished.connect(self.on_calibration_finished)
            worker.error.connect(self.on_calibration_error)
            worker.calibration_result.connect(self.on_calibration_result)
            
            self.running_threads.append(worker)
            worker.start()
            
        except KeyError as e:
            import traceback
            error_msg = f"Calibrant not found: {e}\n{traceback.format_exc()}"
            self.log(error_msg)
            QMessageBox.critical(None, "Error", f"Calibrant not found:\n{e}")
        except Exception as e:
            import traceback
            error_msg = f"Error starting calibration: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            QMessageBox.critical(None, "Error", f"Failed to start calibration:\n{str(e)}")

    def perform_calibration(self, image, calibrant, distance, pixel_size, mask, manual_control_points=None):
        """Perform calibration (runs in worker thread) - Based on Dioptas implementation"""
        from pyFAI.detectors import Detector
        
        # Create detector object
        shape = image.shape
        detector = Detector(pixel1=pixel_size, pixel2=pixel_size, max_shape=shape)
        
        # Create geometry refinement object
        if manual_control_points is not None and len(manual_control_points) > 0:
            # Use manual control points with ring numbers (Dioptas-style)
            # manual_control_points format: [[row, col, ring_num], ...]
            self.log(f"\n{'='*50}")
            self.log(f"Using {len(manual_control_points)} manual control points")
            self.log(f"{'='*50}")
            
            # Group points by ring number and show details
            from collections import defaultdict
            points_by_ring = defaultdict(list)
            for idx, point in enumerate(manual_control_points):
                row, col, ring_num = point
                points_by_ring[ring_num].append([row, col])
                self.log(f"  Point {idx+1}: (row={row:.1f}, col={col:.1f}) → Ring #{ring_num}")
            
            self.log(f"\n{'='*50}")
            self.log(f"Summary: {len(points_by_ring)} different rings")
            self.log(f"{'='*50}")
            for ring_num, points in sorted(points_by_ring.items()):
                self.log(f"  Ring {ring_num}: {len(points)} points")
            self.log(f"{'='*50}\n")
            
            # Create geometry refinement with ring-based control points
            geo_ref = GeometryRefinement(
                data=manual_control_points,
                calibrant=calibrant,
                detector=detector,
                wavelength=calibrant.wavelength
            )
        else:
            # Automatic peak detection
            geo_ref = GeometryRefinement(
                calibrant=calibrant,
                detector=detector,
                wavelength=calibrant.wavelength
            )
            
            # Set the image data
            geo_ref.img = image
        
        # Set initial geometry (important for convergence)
        geo_ref.dist = distance
        geo_ref.poni1 = shape[0] * pixel_size / 2  # Center Y in meters
        geo_ref.poni2 = shape[1] * pixel_size / 2  # Center X in meters
        geo_ref.pixel1 = pixel_size
        geo_ref.pixel2 = pixel_size
        geo_ref.rot1 = 0.0  # Initial rotation
        geo_ref.rot2 = 0.0
        geo_ref.rot3 = 0.0
        
        self.log(f"Initial geometry:")
        self.log(f"  Distance: {geo_ref.dist*1000:.2f} mm")
        self.log(f"  PONI1 (Y): {geo_ref.poni1*1000:.2f} mm")
        self.log(f"  PONI2 (X): {geo_ref.poni2*1000:.2f} mm")
        self.log(f"  Rotations: [{geo_ref.rot1:.3f}, {geo_ref.rot2:.3f}, {geo_ref.rot3:.3f}]")
        
        # Apply mask if provided
        if mask is not None:
            geo_ref.mask = mask
        
        # Extract control points (only if not using manual peaks)
        if manual_control_points is None or len(manual_control_points) == 0:
            try:
                geo_ref.extract_cp(max_rings=10, pts_per_deg=1.0)
            except Exception as e:
                raise ValueError(f"Failed to extract control points: {str(e)}. "
                               "Please check image quality or use Manual Peak Selection.")
        
        # Check if we have control points (removed minimum 10 requirement)
        if not hasattr(geo_ref, 'data') or geo_ref.data is None or len(geo_ref.data) < 3:
            raise ValueError(f"Not enough control points: {len(geo_ref.data) if hasattr(geo_ref, 'data') and geo_ref.data is not None else 0}. "
                           "Need at least 3 points. Use Manual Peak Selection to add more peaks.")
        
        # Refine geometry (Conservative approach: NO rotation refinement by default)
        # This avoids unrealistic tilt angles that can occur with limited data
        try:
            self.log("\nStarting geometry refinement...")
            self.log(f"Number of control points: {len(geo_ref.data)}")
            
            # Count rings
            ring_nums = set()
            for point in geo_ref.data:
                if len(point) > 0:
                    ring_nums.add(point[0])
            self.log(f"Number of rings: {len(ring_nums)}")
            
            # Stage 1: Refine distance only (most sensitive parameter)
            # Fix everything else for initial convergence
            self.log("\n  Stage 1: Refining distance only...")
            geo_ref.refine2(fix=["wavelength", "poni1", "poni2", "rot1", "rot2", "rot3"])
            stage1_distance = geo_ref.dist
            self.log(f"    Distance: {stage1_distance*1000:.2f} mm")
            
            # Stage 2: Refine beam center ONLY (keep distance from Stage 1)
            # Distance is already correct from Stage 1, only optimize beam center
            self.log("\n  Stage 2: Refining beam center only (keeping Stage 1 distance)...")
            geo_ref.refine2(fix=["wavelength", "dist", "rot1", "rot2", "rot3"])
            self.log(f"    Distance: {geo_ref.dist*1000:.2f} mm (unchanged)")
            self.log(f"    Beam center: ({geo_ref.poni2*1000:.2f}, {geo_ref.poni1*1000:.2f}) mm")
            
            # Stage 3: SKIP rotation refinement by default
            # Rotation refinement is DISABLED to avoid unrealistic angles
            # In most cases, detector is nearly perpendicular to beam (rot1≈0, rot2≈0, rot3≈0)
            self.log("\n  Stage 3: Rotation refinement DISABLED")
            self.log(f"    Detector assumed perpendicular to beam (rot1=0°, rot2=0°, rot3=0°)")
            self.log(f"    This is the safest and most common configuration.")
            
            # Optional: Only refine rotations if EXCELLENT data (strict criteria)
            # Uncomment the block below if you want to enable rotation refinement for very high quality data
            """
            if len(ring_nums) >= 8 and len(geo_ref.data) >= 100:
                self.log("\n  [OPTIONAL] Stage 3b: High-quality data detected, attempting rotation refinement...")
                try:
                    # Save current state
                    dist_backup = geo_ref.dist
                    poni1_backup = geo_ref.poni1
                    poni2_backup = geo_ref.poni2
                    
                    # Try rotation refinement
                    geo_ref.refine2(fix=["wavelength"])
                    
                    rot1_deg = np.degrees(geo_ref.rot1)
                    rot2_deg = np.degrees(geo_ref.rot2)
                    rot3_deg = np.degrees(geo_ref.rot3)
                    
                    # Check if result is reasonable
                    if abs(rot1_deg) > 5 or abs(rot2_deg) > 5 or abs(rot3_deg) > 5:
                        self.log(f"    Warning: Unrealistic rotations detected!")
                        self.log(f"    rot1={rot1_deg:.3f}°, rot2={rot2_deg:.3f}°, rot3={rot3_deg:.3f}°")
                        self.log(f"    Reverting to zero rotations (perpendicular detector)")
                        # Revert
                        geo_ref.rot1 = 0.0
                        geo_ref.rot2 = 0.0
                        geo_ref.rot3 = 0.0
                        geo_ref.dist = dist_backup
                        geo_ref.poni1 = poni1_backup
                        geo_ref.poni2 = poni2_backup
                    else:
                        self.log(f"    Rotations accepted: rot1={rot1_deg:.4f}°, rot2={rot2_deg:.4f}°, rot3={rot3_deg:.4f}°")
                except Exception as rot_error:
                    self.log(f"    Rotation refinement failed: {rot_error}")
                    self.log(f"    Keeping rotations at zero")
                    geo_ref.rot1 = 0.0
                    geo_ref.rot2 = 0.0
                    geo_ref.rot3 = 0.0
            """
            
            self.log("\n  Refinement completed successfully!")
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.log(f"Refinement error details:\n{error_detail}")
            raise ValueError(f"Geometry refinement failed: {str(e)}")
        
        # Create AzimuthalIntegrator from refined parameters
        ai = AzimuthalIntegrator(
            dist=geo_ref.dist,
            poni1=geo_ref.poni1,
            poni2=geo_ref.poni2,
            rot1=geo_ref.rot1,
            rot2=geo_ref.rot2,
            rot3=geo_ref.rot3,
            pixel1=geo_ref.pixel1,
            pixel2=geo_ref.pixel2,
            detector=detector,
            wavelength=geo_ref.wavelength
        )
        
        # Get refined parameters
        result = {
            'ai': ai,
            'geo_ref': geo_ref,
            'poni1': geo_ref.poni1,
            'poni2': geo_ref.poni2,
            'dist': geo_ref.dist,
            'rot1': geo_ref.rot1,
            'rot2': geo_ref.rot2,
            'rot3': geo_ref.rot3,
            'wavelength': geo_ref.wavelength,
        }
        
        return result

    def on_calibration_result(self, result):
        """Handle calibration result"""
        try:
            # Store results first
            self.ai = result['ai']
            self.geo_ref = result['geo_ref']
            
            # Log results
            self.log("\n=== Calibration Results ===")
            self.log(f"Distance: {result['dist']*1000:.2f} mm")
            self.log(f"PONI1: {result['poni1']*1000:.2f} mm")
            self.log(f"PONI2: {result['poni2']*1000:.2f} mm")
            self.log(f"Rot1: {np.degrees(result['rot1']):.3f}°")
            self.log(f"Rot2: {np.degrees(result['rot2']):.3f}°")
            self.log(f"Rot3: {np.degrees(result['rot3']):.3f}°")
            self.log(f"Wavelength: {result['wavelength']*1e10:.4f} Å")
            self.log("=" * 30)
            
            # Update UI with calibration results
            self.update_ui_from_calibration()
            
            # Display calibration result
            if MATPLOTLIB_AVAILABLE:
                # Get control points for visualization from geo_ref.data
                try:
                    # geo_ref.data contains the control points in pyFAI format
                    # Convert to format expected by display_calibration_image
                    if hasattr(self.geo_ref, 'data') and self.geo_ref.data is not None:
                        rings = self.geo_ref.data
                        self.calibration_canvas.display_calibration_image(self.current_image, rings)
                    else:
                        self.calibration_canvas.display_calibration_image(self.current_image)
                    self.switch_display_tab("result")
                except Exception as viz_error:
                    self.log(f"Warning: Could not display rings: {viz_error}")
                    self.calibration_canvas.display_calibration_image(self.current_image)
                    self.switch_display_tab("result")
                
                # Update Cake and Pattern views (Dioptas-style)
                try:
                    self.update_cake_view()
                    self.update_pattern_view()
                except Exception as view_error:
                    self.log(f"Warning: Could not update Cake/Pattern views: {view_error}")
                    
        except Exception as e:
            import traceback
            error_msg = f"Error processing results: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            QMessageBox.critical(None, "Error", f"Error processing results:\n{str(e)}")

    def on_calibration_finished(self, message):
        """Handle calibration completion"""
        self.log(message)

    def on_calibration_error(self, error_msg):
        """Handle calibration error"""
        self.log(f"Calibration failed:\n{error_msg}")
        QMessageBox.critical(None, "Calibration Error", 
                           f"Calibration failed:\n{error_msg}")

    def save_poni_file(self):
        """Save PONI file"""
        if self.ai is None:
            QMessageBox.warning(None, "No Calibration", 
                              "Please run calibration first before saving PONI file.")
            return
        
        poni_path = self.poni_entry.text()
        if not poni_path:
            poni_path, _ = QFileDialog.getSaveFileName(
                None, "Save PONI File", "calibration.poni",
                "PONI Files (*.poni);;All Files (*.*)"
            )
        
        if poni_path:
            try:
                self.ai.save(poni_path)
                self.log(f"PONI file saved to: {poni_path}")
                QMessageBox.information(None, "Success", 
                                      f"PONI file saved successfully!\n{poni_path}")
            except Exception as e:
                self.log(f"Error saving PONI: {str(e)}")
                QMessageBox.critical(None, "Error", f"Failed to save PONI file:\n{str(e)}")

    def on_contrast_slider_changed(self, value):
        """Handle contrast slider change (single vertical slider controls max)"""
        # Use timer to debounce slider changes
        if hasattr(self, '_contrast_timer') and self._contrast_timer is not None:
            self._contrast_timer.stop()
        
        from PyQt6.QtCore import QTimer
        self._contrast_timer = QTimer()
        self._contrast_timer.setSingleShot(True)
        self._contrast_timer.timeout.connect(lambda: self.apply_contrast_from_slider(value))
        self._contrast_timer.start(50)  # 50ms delay
    
    def apply_contrast_from_slider(self, vmax):
        """Apply contrast from single slider"""
        vmin = 0  # Always use 0 as minimum
        
        # Apply to canvases
        if MATPLOTLIB_AVAILABLE:
            if hasattr(self, 'calibration_canvas'):
                self.calibration_canvas.set_contrast(vmin, vmax)
            if hasattr(self, 'mask_canvas'):
                self.mask_canvas.set_contrast(vmin, vmax)
    
    def auto_contrast(self):
        """Auto-adjust contrast based on image statistics"""
        if self.current_image is None:
            return
        
        try:
            # Calculate percentiles for auto-contrast
            vmin = np.percentile(self.current_image, 1)
            vmax = np.percentile(self.current_image, 99)
            
            # Update slider
            if hasattr(self, 'contrast_slider'):
                self.contrast_slider.setValue(int(vmax))
            
            # Apply
            self.apply_contrast_from_slider(int(vmax))
            self.log(f"Auto-contrast applied: 0 - {vmax:.0f}")
        except Exception as e:
            self.log(f"Auto-contrast failed: {str(e)}")
    
    def reset_zoom(self):
        """Reset zoom to original view"""
        if MATPLOTLIB_AVAILABLE:
            if hasattr(self, 'mask_canvas'):
                self.mask_canvas.reset_zoom()
            if hasattr(self, 'calibration_canvas'):
                self.calibration_canvas.reset_zoom()
        self.log("Zoom reset")
    
    def log(self, message):
        """Add message to log output"""
        if hasattr(self, 'log_output'):
            self.log_output.append(str(message))
    
    def refine_calibration(self):
        """Refine calibration (similar to run_calibration but with current parameters)"""
        if not PYFAI_AVAILABLE:
            QMessageBox.warning(None, "pyFAI Required", 
                              "pyFAI is required for calibration.\nInstall with: pip install pyFAI")
            return
        
        if self.ai is None:
            QMessageBox.warning(None, "No Calibration", 
                              "Please run initial calibration first.")
            return
        
        self.log("Refining calibration with current parameters...")
        # Re-run calibration with refined starting values
        self.run_calibration()
    
    def load_calibration(self):
        """Load calibration from PONI file"""
        if not PYFAI_AVAILABLE:
            QMessageBox.warning(None, "pyFAI Required", 
                              "pyFAI is required.\nInstall with: pip install pyFAI")
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            None, "Load PONI File", "",
            "PONI Files (*.poni);;All Files (*.*)"
        )
        
        if filename:
            try:
                # Load AzimuthalIntegrator from PONI file
                from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
                self.ai = AzimuthalIntegrator.sload(filename)
                
                # Update UI with loaded parameters
                self.update_ui_from_calibration()
                
                self.log(f"Calibration loaded from: {filename}")
                QMessageBox.information(None, "Success", 
                                      f"Calibration loaded successfully!\n{filename}")
            except Exception as e:
                self.log(f"Error loading calibration: {str(e)}")
                QMessageBox.critical(None, "Error", f"Failed to load calibration:\n{str(e)}")
    
    def update_ui_from_calibration(self):
        """Update UI widgets from loaded calibration"""
        if self.ai is None:
            return
        
        try:
            # Update pyFAI parameters
            if hasattr(self, 'pyfai_dist_txt'):
                self.pyfai_dist_txt.setText(f"{self.ai.dist:.6f}")
            if hasattr(self, 'pyfai_poni1_txt'):
                self.pyfai_poni1_txt.setText(f"{self.ai.poni1:.6f}")
            if hasattr(self, 'pyfai_poni2_txt'):
                self.pyfai_poni2_txt.setText(f"{self.ai.poni2:.6f}")
            if hasattr(self, 'pyfai_rot1_txt'):
                self.pyfai_rot1_txt.setText(f"{self.ai.rot1:.6f}")
            if hasattr(self, 'pyfai_rot2_txt'):
                self.pyfai_rot2_txt.setText(f"{self.ai.rot2:.6f}")
            if hasattr(self, 'pyfai_rot3_txt'):
                self.pyfai_rot3_txt.setText(f"{self.ai.rot3:.6f}")
            if hasattr(self, 'pyfai_wavelength_txt'):
                self.pyfai_wavelength_txt.setText(f"{self.ai.wavelength * 1e10:.6f}")
            
            # Update start values
            if hasattr(self, 'distance_txt'):
                self.distance_txt.setText(f"{self.ai.dist * 1000:.3f}")  # Convert to mm
            if hasattr(self, 'wavelength_txt'):
                self.wavelength_txt.setText(f"{self.ai.wavelength * 1e10:.6f}")  # Convert to Å
            
            # Update fit2d parameters if available
            if hasattr(self.ai, 'getFit2D'):
                try:
                    fit2d_params = self.ai.getFit2D()
                    if hasattr(self, 'fit2d_dist_txt'):
                        self.fit2d_dist_txt.setText(f"{fit2d_params['directDist']:.3f}")
                    if hasattr(self, 'fit2d_centerx_txt'):
                        self.fit2d_centerx_txt.setText(f"{fit2d_params['centerX']:.1f}")
                    if hasattr(self, 'fit2d_centery_txt'):
                        self.fit2d_centery_txt.setText(f"{fit2d_params['centerY']:.1f}")
                    if hasattr(self, 'fit2d_tilt_txt'):
                        self.fit2d_tilt_txt.setText(f"{fit2d_params['tilt']:.3f}")
                    if hasattr(self, 'fit2d_rotation_txt'):
                        self.fit2d_rotation_txt.setText(f"{fit2d_params['tiltPlanRotation']:.3f}")
                except:
                    pass
            
            self.log("UI updated with loaded calibration parameters")
        except Exception as e:
            self.log(f"Error updating UI: {str(e)}")
    
    def update_pyfai_from_fit(self):
        """Update pyFAI parameters from current fit results"""
        if self.ai is None:
            QMessageBox.warning(None, "No Calibration", 
                              "Please run calibration first.")
            return
        
        self.update_ui_from_calibration()
        self.log("pyFAI parameters updated from fit")
    
    def update_fit2d_from_fit(self):
        """Update Fit2d parameters from current fit results"""
        if self.ai is None:
            QMessageBox.warning(None, "No Calibration", 
                              "Please run calibration first.")
            return
        
        if not hasattr(self.ai, 'getFit2D'):
            QMessageBox.warning(None, "Not Available", 
                              "Fit2d parameters not available for this calibration.")
            return
        
        try:
            fit2d_params = self.ai.getFit2D()
            
            if hasattr(self, 'fit2d_dist_txt'):
                self.fit2d_dist_txt.setText(f"{fit2d_params['directDist']:.3f}")
            if hasattr(self, 'fit2d_centerx_txt'):
                self.fit2d_centerx_txt.setText(f"{fit2d_params['centerX']:.1f}")
            if hasattr(self, 'fit2d_centery_txt'):
                self.fit2d_centery_txt.setText(f"{fit2d_params['centerY']:.1f}")
            if hasattr(self, 'fit2d_tilt_txt'):
                self.fit2d_tilt_txt.setText(f"{fit2d_params['tilt']:.3f}")
            if hasattr(self, 'fit2d_rotation_txt'):
                self.fit2d_rotation_txt.setText(f"{fit2d_params['tiltPlanRotation']:.3f}")
            if hasattr(self, 'fit2d_wavelength_txt'):
                self.fit2d_wavelength_txt.setText(f"{fit2d_params['wavelength'] * 1e10:.6f}")
            
            self.log("Fit2d parameters updated from fit")
        except Exception as e:
            self.log(f"Error updating Fit2d parameters: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to update Fit2d parameters:\n{str(e)}")


    def update_cake_view(self):
        """Update Cake view after calibration - Dioptas style"""
        if not hasattr(self, 'cake_axes') or self.ai is None or self.current_image is None:
            return
        
        try:
            self.log("Generating Cake view (polar transformation)...")
            
            # Use pyFAI's integrate2d for cake/polar transformation
            # num_chi: number of azimuthal bins (360 for 1 degree resolution)
            # num_2theta: number of radial bins
            result = self.ai.integrate2d(
                self.current_image,
                npt_rad=500,      # Number of radial bins (2theta)
                npt_azim=360,     # Number of azimuthal bins (chi/azimuth)
                unit="2th_deg",   # Use 2theta in degrees
                method="splitpixel"
            )
            
            # Result is (cake_image, 2theta_array, chi_array)
            cake = result[0]
            tth_rad = result[1]  # Radial axis (2theta)
            chi_azim = result[2]  # Azimuthal axis (chi)
            
            # Clear and plot
            self.cake_axes.clear()
            
            # Display cake image with proper extent
            # extent: [left, right, bottom, top]
            extent = [tth_rad.min(), tth_rad.max(), chi_azim.min(), chi_azim.max()]
            
            im = self.cake_axes.imshow(
                cake,
                aspect='auto',
                origin='lower',
                extent=extent,
                cmap='viridis',
                interpolation='nearest'
            )
            
            self.cake_axes.set_xlabel('2θ (degrees)', fontsize=10)
            self.cake_axes.set_ylabel('χ (degrees)', fontsize=10)
            self.cake_axes.set_title('Cake/Polar View', fontsize=11, fontweight='bold')
            
            # Add colorbar if not exists
            if not hasattr(self, 'cake_colorbar') or self.cake_colorbar is None:
                self.cake_colorbar = self.cake_canvas.figure.colorbar(im, ax=self.cake_axes)
            else:
                self.cake_colorbar.update_normal(im)
            
            self.cake_canvas.draw()
            self.log(f"Cake view updated: {cake.shape[1]}x{cake.shape[0]} (2θ × χ)")
                
        except Exception as e:
            import traceback
            self.log(f"Error updating Cake view: {str(e)}")
            self.log(traceback.format_exc())
    
    def update_pattern_view(self):
        """Update Pattern view after calibration - Dioptas style"""
        if not hasattr(self, 'pattern_axes') or self.ai is None or self.current_image is None:
            return
        
        try:
            self.log("Generating 1D integrated pattern...")
            
            # Use pyFAI's integrate1d for azimuthal integration
            result = self.ai.integrate1d(
                self.current_image,
                npt=2048,         # Number of points in output
                unit="2th_deg",   # Use 2theta in degrees
                method="splitpixel"
            )
            
            # Result is (2theta_array, intensity_array)
            tth = result[0]      # 2theta values
            intensity = result[1] # Integrated intensity
            
            # Clear and plot
            self.pattern_axes.clear()
            
            # Plot 1D pattern
            self.pattern_axes.plot(tth, intensity, 'b-', linewidth=1)
            self.pattern_axes.set_xlabel('2θ (degrees)', fontsize=10)
            self.pattern_axes.set_ylabel('Intensity (a.u.)', fontsize=10)
            self.pattern_axes.set_title('1D Integrated Pattern', fontsize=11, fontweight='bold')
            self.pattern_axes.grid(True, alpha=0.3)
            
            # Add calibrant peak positions if available
            if hasattr(self, 'calibrant_name') and self.calibrant_name:
                try:
                    calibrant = ALL_CALIBRANTS[self.calibrant_name]
                    calibrant.wavelength = self.ai.wavelength
                    
                    # Get expected 2theta positions for calibrant peaks
                    tth_calibrant = calibrant.get_2th()
                    tth_calibrant_deg = np.degrees(tth_calibrant)
                    
                    # Filter to visible range
                    tth_min, tth_max = tth.min(), tth.max()
                    visible_peaks = tth_calibrant_deg[(tth_calibrant_deg >= tth_min) & 
                                                       (tth_calibrant_deg <= tth_max)]
                    
                    # Draw vertical lines for calibrant peaks
                    y_max = intensity.max()
                    for peak_pos in visible_peaks[:20]:  # Limit to first 20 peaks
                        self.pattern_axes.axvline(peak_pos, color='red', linestyle='--', 
                                                 alpha=0.5, linewidth=0.8)
                    
                    self.log(f"Added {len(visible_peaks)} calibrant peak positions")
                except Exception as cal_error:
                    self.log(f"Could not add calibrant peaks: {cal_error}")
            
            self.pattern_canvas.draw()
            self.log(f"Pattern view updated: {len(tth)} points from {tth.min():.2f}° to {tth.max():.2f}°")
                
        except Exception as e:
            import traceback
            self.log(f"Error updating Pattern view: {str(e)}")
            self.log(traceback.format_exc())