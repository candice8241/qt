# -*- coding: utf-8 -*-
"""
Calibration Canvas Classes - Visualization Components
Contains MaskCanvas and CalibrationCanvas for detector calibration

Split from calibrate_module.py for better maintainability
"""

import numpy as np

# PyQt imports
from PyQt6.QtCore import Qt

# Matplotlib imports
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = object  # Dummy class if matplotlib not available

# pyFAI imports
try:
    import pyFAI
    from pyFAI.calibrant import Calibrant, ALL_CALIBRANTS
    from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
    PYFAI_AVAILABLE = True
except ImportError:
    PYFAI_AVAILABLE = False

# fabio for image loading
try:
    import fabio
    FABIO_AVAILABLE = True
except ImportError:
    FABIO_AVAILABLE = False


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
    
    def on_mouse_press(self, event):
        """Handle mouse press for mask drawing"""
        if event.inaxes != self.axes or self.image_data is None:
            return
        
        self.drawing = True
        self.start_point = (event.xdata, event.ydata)
        
    def on_mouse_release(self, event):
        """Handle mouse release to finalize mask shape"""
        if not self.drawing or self.start_point is None:
            return
        
        self.drawing = False
        
        if event.inaxes != self.axes:
            return
        
        end_point = (event.xdata, event.ydata)
        
        # Apply mask based on mode
        if self.mask_mode == 'rectangle':
            self.apply_rectangle_mask(self.start_point, end_point)
        elif self.mask_mode == 'circle':
            self.apply_circle_mask(self.start_point, end_point)
        
        # Clear preview
        if self.preview_patch is not None:
            self.preview_patch.remove()
            self.preview_patch = None
        
        self.start_point = None
        self.display_image()
    
    def on_mouse_move(self, event):
        """Handle mouse move for mask preview"""
        if not self.drawing or self.start_point is None:
            return
        
        if event.inaxes != self.axes:
            return
        
        # Performance optimization: only update if moved significantly
        if self._last_preview_pos is not None:
            dx = abs(event.xdata - self._last_preview_pos[0])
            dy = abs(event.ydata - self._last_preview_pos[1])
            if dx < 5 and dy < 5:  # Threshold in pixels
                return
        
        self._last_preview_pos = (event.xdata, event.ydata)
        
        # Remove old preview
        if self.preview_patch is not None:
            self.preview_patch.remove()
        
        # Draw preview shape
        if self.mask_mode == 'rectangle':
            x0, y0 = self.start_point
            width = event.xdata - x0
            height = event.ydata - y0
            self.preview_patch = Rectangle((x0, y0), width, height, 
                                          fill=False, edgecolor='yellow', linewidth=2)
        elif self.mask_mode == 'circle':
            x0, y0 = self.start_point
            radius = np.sqrt((event.xdata - x0)**2 + (event.ydata - y0)**2)
            self.preview_patch = Circle((x0, y0), radius, 
                                       fill=False, edgecolor='yellow', linewidth=2)
        
        if self.preview_patch is not None:
            self.axes.add_patch(self.preview_patch)
        
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
        
        self.draw_idle()
    
    def apply_rectangle_mask(self, start, end):
        """Apply rectangular mask"""
        if self.mask_data is None:
            return
        
        x0, y0 = start
        x1, y1 = end
        
        # Ensure correct order
        x_min, x_max = sorted([int(x0), int(x1)])
        y_min, y_max = sorted([int(y0), int(y1)])
        
        # Clip to image boundaries
        x_min = max(0, x_min)
        x_max = min(self.mask_data.shape[1] - 1, x_max)
        y_min = max(0, y_min)
        y_max = min(self.mask_data.shape[0] - 1, y_max)
        
        # Apply mask
        self.mask_data[y_min:y_max+1, x_min:x_max+1] = self.mask_value
    
    def apply_circle_mask(self, center, edge):
        """Apply circular mask"""
        if self.mask_data is None:
            return
        
        cx, cy = center
        ex, ey = edge
        radius = np.sqrt((ex - cx)**2 + (ey - cy)**2)
        
        # Create coordinate arrays
        y, x = np.ogrid[:self.mask_data.shape[0], :self.mask_data.shape[1]]
        
        # Calculate distance from center
        distance = np.sqrt((x - cx)**2 + (y - cy)**2)
        
        # Apply mask
        self.mask_data[distance <= radius] = self.mask_value
    
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
        self.display_image()
    
    def clear_mask(self):
        """Clear all masks"""
        if self.mask_data is not None:
            self.mask_data.fill(False)
            self.display_image()
    
    def invert_mask(self):
        """Invert mask"""
        if self.mask_data is not None:
            self.mask_data = ~self.mask_data
            self.display_image()
    
    def save_mask(self, filename):
        """Save mask to file"""
        if self.mask_data is not None:
            np.save(filename, self.mask_data)
            return True
        return False
    
    def load_mask(self, filename):
        """Load mask from file"""
        try:
            self.mask_data = np.load(filename)
            self.display_image()
            return True
        except:
            return False


class CalibrationCanvas(FigureCanvas):
    """Canvas for displaying calibration results - OPTIMIZED VERSION"""
    
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
            
            # Ring number for peak picking (starts from 0)
            self.current_ring_num = 0
            self.auto_increment_ring = False
            self.parent_module = None
            
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
            
            # Store AzimuthalIntegrator for theoretical ring overlay (Dioptas-style)
            self.ai = None  # AzimuthalIntegrator from calibration result
            self.show_theoretical_rings = True  # Show theoretical calibration rings
            
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
        
        # Draw theoretical calibration rings if AI is available (Dioptas-style)
        if self.ai is not None and self.show_theoretical_rings:
            self.draw_theoretical_rings()
        
        # Use draw_idle() for better performance
        self.draw_idle()
    
    def draw_theoretical_rings(self):
        """
        Draw theoretical calibration rings - OPTIMIZED to prevent memory issues
        Uses parametric circle calculation instead of full twoThetaArray
        """
        if self.ai is None or self.image_data is None:
            return
        
        try:
            # Get image shape
            shape = self.image_data.shape
            
            # Get calibrant and number of rings
            if not hasattr(self.ai, 'calibrant') or self.ai.calibrant is None:
                return
            
            calibrant = self.ai.calibrant
            num_rings = min(len(calibrant.dSpacing), self.num_rings_display)
            
            # OPTIMIZED: Use parametric calculation instead of full array
            # Generate angles around the ring (360 points = 1° resolution)
            chi_angles = np.linspace(-np.pi, np.pi, 360)
            
            # Draw each theoretical ring
            for ring_idx in range(num_rings):
                try:
                    # Get 2theta value for this ring from calibrant
                    ring_2theta = calibrant.get_2th()[ring_idx]
                    
                    # Calculate pixel positions using AI
                    x_coords = []
                    y_coords = []
                    
                    for chi in chi_angles[::3]:  # Sample every 3° to reduce points
                        try:
                            # Convert (2theta, chi) to pixel coordinates
                            # This is much more memory-efficient than twoThetaArray
                            tth_chi = np.array([[ring_2theta, chi]])
                            pos = self.ai.calcfrom1d(tth_chi[:, 0], tth_chi[:, 1], shape=shape)
                            
                            if pos is not None and len(pos) == 2:
                                y, x = pos
                                # Check bounds
                                if 0 <= y < shape[0] and 0 <= x < shape[1]:
                                    y_coords.append(y)
                                    x_coords.append(x)
                        except:
                            continue
                    
                    # Plot the ring if we have enough points
                    if len(x_coords) > 10:
                        self.axes.plot(x_coords, y_coords, 'o',
                                     color=self.ring_color, 
                                     markersize=1,
                                     alpha=self.ring_alpha, 
                                     markeredgewidth=0,
                                     zorder=10)
                        
                except Exception as ring_error:
                    # Skip this ring if calculation fails
                    continue
                    
        except Exception as e:
            # If theoretical ring drawing fails, silently continue
            print(f"Warning: Could not draw theoretical rings: {e}")
            import traceback
            traceback.print_exc()
    
    def update_calibration_overlay(self, ai):
        """
        Update theoretical ring overlay with new calibration (Dioptas-style real-time update)
        
        Args:
            ai: AzimuthalIntegrator with calibration results
        """
        self.ai = ai
        
        # Redraw image with new theoretical rings
        if self.image_data is not None:
            self.display_calibration_image(self.image_data, self.calibration_points)
    
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
        # For now, just redraw the whole image
        # Could be optimized with blitting if needed
        if self.image_data is not None:
            self.display_calibration_image(self.image_data, self.calibration_points)
    
    def on_unified_click(self, event):
        """Unified click handler for both peak picking and mask editing"""
        if event.inaxes != self.axes:
            return
        
        if self.peak_picking_mode:
            self.on_peak_click(event)
        elif self.mask_editing_mode:
            self.on_mask_click(event)
    
    def on_peak_click(self, event):
        """Handle mouse click for peak picking"""
        if not self.peak_picking_mode:
            return
        
        # Get click coordinates
        x, y = event.xdata, event.ydata
        
        # Get current ring number (should be set by parent)
        ring_num = getattr(self, 'current_ring_num', 0)
        
        # Add peak
        self.manual_peaks.append((x, y, ring_num))
        
        # Draw marker
        marker = self.axes.plot(x, y, 'ro', markersize=8, markerfacecolor='red',
                               markeredgecolor='white', markeredgewidth=1)[0]
        self.peak_markers.append(marker)
        
        # Add label
        label = self.axes.text(x, y + 15, f'{ring_num}', color='red', fontsize=9,
                              horizontalalignment='center', verticalalignment='bottom',
                              fontweight='bold')
        self.peak_markers.append(label)
        
        self.draw_idle()
        
        # Auto-increment ring number if enabled
        if hasattr(self, 'auto_increment_ring') and self.auto_increment_ring:
            self.current_ring_num = ring_num + 1
            # Notify parent to update ring number input
            if hasattr(self, 'parent_module'):
                self.parent_module.update_ring_number_display(self.current_ring_num)
    
    def on_mask_click(self, event):
        """Handle mouse press for mask drawing"""
        if not self.mask_editing_mode:
            return
        
        self.drawing = True
        self.start_point = (event.xdata, event.ydata)
    
    def on_mouse_release(self, event):
        """Handle mouse release"""
        if self.mask_editing_mode and self.drawing:
            self.on_mask_release(event)
    
    def on_mask_release(self, event):
        """Handle mouse release for mask drawing"""
        if not self.drawing or self.start_point is None:
            return
        
        self.drawing = False
        
        if event.inaxes != self.axes:
            return
        
        end_point = (event.xdata, event.ydata)
        
        # Apply mask based on mode
        if self.mask_mode == 'rectangle':
            self.apply_rectangle_mask(self.start_point, end_point)
        elif self.mask_mode == 'circle':
            self.apply_circle_mask(self.start_point, end_point)
        
        # Clear preview
        if self.preview_patch is not None:
            self.preview_patch.remove()
            self.preview_patch = None
        
        self.start_point = None
        
        # Redraw
        if self.image_data is not None:
            self.display_calibration_image(self.image_data, self.calibration_points)
    
    def on_mouse_move(self, event):
        """Handle mouse move for mask preview"""
        if not self.drawing or self.start_point is None:
            return
        
        if event.inaxes != self.axes:
            return
        
        # Remove old preview
        if self.preview_patch is not None:
            self.preview_patch.remove()
        
        # Draw preview shape
        if self.mask_mode == 'rectangle':
            x0, y0 = self.start_point
            width = event.xdata - x0
            height = event.ydata - y0
            self.preview_patch = Rectangle((x0, y0), width, height,
                                          fill=False, edgecolor='yellow', linewidth=2)
        elif self.mask_mode == 'circle':
            x0, y0 = self.start_point
            radius = np.sqrt((event.xdata - x0)**2 + (event.ydata - y0)**2)
            self.preview_patch = Circle((x0, y0), radius,
                                       fill=False, edgecolor='yellow', linewidth=2)
        
        if self.preview_patch is not None:
            self.axes.add_patch(self.preview_patch)
        
        self.draw_idle()
    
    def apply_rectangle_mask(self, start, end):
        """Apply rectangular mask"""
        if self.mask_data is None:
            return
        
        x0, y0 = start
        x1, y1 = end
        
        # Ensure correct order
        x_min, x_max = sorted([int(x0), int(x1)])
        y_min, y_max = sorted([int(y0), int(y1)])
        
        # Clip to image boundaries
        x_min = max(0, x_min)
        x_max = min(self.mask_data.shape[1] - 1, x_max)
        y_min = max(0, y_min)
        y_max = min(self.mask_data.shape[0] - 1, y_max)
        
        # Apply mask
        self.mask_data[y_min:y_max+1, x_min:x_max+1] = self.mask_value
    
    def apply_circle_mask(self, center, edge):
        """Apply circular mask"""
        if self.mask_data is None:
            return
        
        cx, cy = center
        ex, ey = edge
        radius = np.sqrt((ex - cx)**2 + (ey - cy)**2)
        
        # Create coordinate arrays
        y, x = np.ogrid[:self.mask_data.shape[0], :self.mask_data.shape[1]]
        
        # Calculate distance from center
        distance = np.sqrt((x - cx)**2 + (y - cy)**2)
        
        # Apply mask
        self.mask_data[distance <= radius] = self.mask_value
    
    def clear_manual_peaks(self):
        """Clear all manually selected peaks"""
        self.manual_peaks = []
        # Remove all peak markers
        for marker in self.peak_markers:
            try:
                marker.remove()
            except:
                pass
        self.peak_markers = []
        self.draw_idle()
    
    def remove_last_peak(self):
        """Remove the last added peak"""
        if self.manual_peaks:
            self.manual_peaks.pop()
            # Remove last two markers (point and label)
            if len(self.peak_markers) >= 2:
                try:
                    self.peak_markers[-1].remove()  # Label
                    self.peak_markers[-2].remove()  # Point
                    self.peak_markers = self.peak_markers[:-2]
                except:
                    pass
            self.draw_idle()
    
    def display_integrated_pattern(self, tth, intensity):
        """Display integrated 1D pattern"""
        self.axes.clear()
        self.axes.plot(tth, intensity)
        self.axes.set_xlabel('2θ (degrees)')
        self.axes.set_ylabel('Intensity')
        self.axes.set_title('Integrated Diffraction Pattern')
        self.axes.grid(True, alpha=0.3)
