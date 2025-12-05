# -*- coding: utf-8 -*-
"""
Calibration Canvas Classes - Visualization Components
Contains MaskCanvas and CalibrationCanvas for detector calibration

Split from calibrate_module.py for better maintainability
"""

import numpy as np

# PyQt imports
from PyQt6.QtCore import Qt

# SciPy imports for auto peak finding
try:
    from scipy.ndimage import maximum_filter
    from scipy.spatial.distance import cdist
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    # Silently disable - no console output unless error

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
        """Load image for mask editing (memory-optimized)"""
        try:
            if FABIO_AVAILABLE:
                img = fabio.open(image_path)
                
                # Check image size and warn if too large
                img_size_mb = (img.data.nbytes / 1024 / 1024)
                if img_size_mb > 100:
                    print(f"WARNING: Large image ({img_size_mb:.1f} MB). Memory usage may be high.")
                
                # Store as float32 if image is large to save memory
                if img_size_mb > 50:
                    self.image_data = img.data.astype(np.float32)
                else:
                    self.image_data = img.data
                
                # Free original image data
                del img
            else:
                # Fallback to simple image loading
                from PIL import Image
                img = Image.open(image_path)
                self.image_data = np.array(img)
            
            # Initialize mask if needed
            if self.mask_data is None or self.mask_data.shape != self.image_data.shape:
                self.mask_data = np.zeros(self.image_data.shape, dtype=bool)
            
            # Force garbage collection for large images
            if self.image_data.size > 10000000:  # > 10M pixels
                import gc
                gc.collect()
            
            self.display_image()
            return True
        except Exception as e:
            print(f"ERROR loading image: {e}")  # Simplified error message
            return False
    
    def display_image(self):
        """Display the image with mask overlay (memory-optimized)"""
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
            if self.mask_data is not None and np.any(self.mask_data):
                # Create red mask overlay using float32 to save 50% memory
                mask_rgba = np.zeros((*self.mask_data.shape, 4), dtype=np.float32)
                mask_rgba[self.mask_data, 0] = 1.0  # Red channel
                mask_rgba[self.mask_data, 3] = 0.6  # Alpha (transparency)
                self.axes.imshow(mask_rgba, origin='lower', interpolation='nearest')
                
                # Free memory immediately
                del mask_rgba
            
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
        
        # Clean up memory
        if self.image_data is not None and self.image_data.size > 10000000:  # > 10M pixels
            import gc
            gc.collect()
        
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
            # Use full DPI for better visibility (removed 80 DPI limit per user request)
            actual_dpi = dpi
            
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
            
            # Real-time auto peak finding (Dioptas-style)
            self.auto_detected_peaks = []  # List of (x, y, ring_num) for auto-detected peaks
            self.auto_peak_markers = []  # List of matplotlib artists for auto peaks
            self.show_auto_peaks = True  # Enable/disable auto peak display
            
            # Ring number for peak picking (starts from 1 per user request)
            self.current_ring_num = 1
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
                print(f"ERROR: Could not connect canvas events: {e}")
                
        except Exception as e:
            print(f"ERROR creating CalibrationCanvas: {e}")
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
        
        # Display auto-detected peaks first (in cyan, smaller) - Dioptas style
        if hasattr(self, 'auto_detected_peaks') and self.auto_detected_peaks and self.show_auto_peaks:
            for x, y, ring_num in self.auto_detected_peaks:
                # Draw auto peaks as cyan circles (smaller than manual)
                marker = self.axes.plot(x, y, 'o', markersize=4, markerfacecolor='cyan', 
                                       markeredgecolor='blue', markeredgewidth=0.5, alpha=0.7)[0]
                self.auto_peak_markers.append(marker)
        
        # Restore manual peaks (displayed on top, in red, larger)
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
            # If theoretical ring drawing fails, print simplified error
            print(f"ERROR drawing theoretical rings: {e}")
    
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
            self.draw()  # Force canvas refresh
    
    def on_unified_click(self, event):
        """Unified click handler for both peak picking and mask editing"""
        if event.inaxes != self.axes:
            return
        
        if self.peak_picking_mode:
            self.on_peak_click(event)
        elif self.mask_editing_mode:
            self.on_mask_click(event)
    
    def on_peak_click(self, event):
        """Handle mouse click for peak picking (manual mode only, no auto search)"""
        if not self.peak_picking_mode:
            return
        
        # Get click coordinates
        x, y = event.xdata, event.ydata
        
        # Get current ring number (should be set by parent)
        ring_num = getattr(self, 'current_ring_num', 0)
        
        # Add manual peak
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
        
        # NO AUTO PEAK FINDING - removed per user request
        # Only manual peaks are added here
        # Auto peak finding happens only when clicking Calibrate button
        
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
    
    def get_mask(self):
        """Get current mask data"""
        return self.mask_data
    
    def get_manual_control_points(self):
        """Get manually selected control points in format for calibration
        
        Returns:
            list: Control points in format [[row, col, ring_num], ...]
            Only returns MANUAL peaks (no auto-detected peaks)
        """
        if not self.manual_peaks:
            return None
        
        # Convert from (x, y, ring_num) to [[row, col, ring_num], ...]
        control_points = []
        
        # Add manual peaks only
        for x, y, ring_num in self.manual_peaks:
            # x corresponds to col, y corresponds to row
            control_points.append([y, x, ring_num])
        
        # NO auto-detected peaks included - removed per user request
        # Auto peak finding only happens in Calibrate process
        
        return control_points
    
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
        
        # Also clear auto-detected peaks (if any from Calibrate process)
        if hasattr(self, 'clear_auto_peaks'):
            self.clear_auto_peaks()
        
        self.draw_idle()
    
    def clear_auto_peaks(self):
        """Clear all auto-detected peaks"""
        self.auto_detected_peaks = []
        for marker in self.auto_peak_markers:
            try:
                marker.remove()
            except:
                pass
        self.auto_peak_markers = []
    
    def auto_find_peaks_on_ring(self, seed_x, seed_y, ring_num):
        """
        Automatically find peaks on the same ring as the seed point (Dioptas-style)
        
        Args:
            seed_x: X coordinate of seed point (manual click)
            seed_y: Y coordinate of seed point (manual click)
            ring_num: Ring number for this peak
        
        Returns:
            list: List of (x, y, ring_num) tuples for auto-detected peaks
        """
        if self.image_data is None:
            return []
        
        # Check if scipy is available
        if not SCIPY_AVAILABLE:
            return []  # Silently skip if scipy not available
        
        try:
            # Import necessary modules
            from scipy.ndimage import maximum_filter
            
            # Calculate radius from center of image to seed point
            center_y, center_x = self.image_data.shape[0] / 2, self.image_data.shape[1] / 2
            radius = np.sqrt((seed_x - center_x)**2 + (seed_y - center_y)**2)
            
            # Define ring width (tolerance) - typically 2-5% of radius
            ring_width = max(5, radius * 0.03)  # At least 5 pixels
            
            # Create polar coordinate arrays
            y_coords, x_coords = np.ogrid[:self.image_data.shape[0], :self.image_data.shape[1]]
            distances = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
            
            # Create ring mask
            ring_mask = (distances >= radius - ring_width) & (distances <= radius + ring_width)
            
            # Get intensities in ring region
            ring_data = self.image_data.copy()
            ring_data[~ring_mask] = 0
            
            # Apply maximum filter to find local maxima
            footprint_size = 5  # Size of local region
            local_max = maximum_filter(ring_data, size=footprint_size)
            peaks_mask = (ring_data == local_max) & (ring_data > 0)
            
            # Get peak coordinates
            peak_coords = np.argwhere(peaks_mask)
            
            if len(peak_coords) == 0:
                return []
            
            # Convert to (x, y) format
            peaks = [(coord[1], coord[0]) for coord in peak_coords]
            
            # Filter peaks by intensity (top percentile)
            intensities = [self.image_data[int(y), int(x)] for x, y in peaks]
            if len(intensities) > 0:
                intensity_threshold = np.percentile(intensities, 70)  # Keep top 30%
                peaks = [(x, y) for (x, y), intensity in zip(peaks, intensities) 
                        if intensity >= intensity_threshold]
            
            # Limit number of peaks per ring (Dioptas typically shows ~36-360 points per ring)
            # We'll use fewer for clarity: ~36 points (every 10 degrees)
            max_peaks_per_ring = 36
            if len(peaks) > max_peaks_per_ring:
                # Sample evenly around the ring by angle
                angles = [np.arctan2(y - center_y, x - center_x) for x, y in peaks]
                # Sort by angle
                sorted_indices = np.argsort(angles)
                # Select evenly spaced indices
                step = len(peaks) // max_peaks_per_ring
                selected_indices = sorted_indices[::step][:max_peaks_per_ring]
                peaks = [peaks[i] for i in selected_indices]
            
            # Remove seed point from results (avoid duplication)
            peaks = [(x, y) for x, y in peaks 
                    if np.sqrt((x - seed_x)**2 + (y - seed_y)**2) > footprint_size]
            
            # Return as list of (x, y, ring_num)
            return [(x, y, ring_num) for x, y in peaks]
            
        except Exception as e:
            # Simplified error message
            print(f"ERROR in auto peak finding: {e}")
            return []
    
    def update_auto_peaks_display(self):
        """Update display with current auto-detected peaks (Dioptas-style real-time update)"""
        if not self.show_auto_peaks:
            return
        
        # Clear old auto peak markers
        for marker in self.auto_peak_markers:
            try:
                marker.remove()
            except:
                pass
        self.auto_peak_markers = []
        
        # Draw new auto peaks
        if self.auto_detected_peaks:
            for x, y, ring_num in self.auto_detected_peaks:
                # Draw auto peaks as cyan circles
                marker = self.axes.plot(x, y, 'o', markersize=4, markerfacecolor='cyan', 
                                       markeredgecolor='blue', markeredgewidth=0.5, alpha=0.7)[0]
                self.auto_peak_markers.append(marker)
        
        self.draw_idle()
    
    def refresh_auto_peaks_for_all_manual(self):
        """Re-run auto peak detection for all existing manual peaks (Dioptas-style)"""
        if not self.show_auto_peaks or not self.manual_peaks or self.image_data is None:
            return
        
        # Clear existing auto peaks
        self.clear_auto_peaks()
        
        # Re-run auto detection for each manual peak
        for x, y, ring_num in self.manual_peaks:
            auto_peaks = self.auto_find_peaks_on_ring(x, y, ring_num)
            if auto_peaks:
                self.auto_detected_peaks.extend(auto_peaks)
        
        # Update display
        if self.image_data is not None:
            self.display_calibration_image(self.image_data, self.calibration_points)
    
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