# -*- coding: utf-8 -*-
"""
Mask Editor Module - Qt Version
Comprehensive mask creation and editing for X-ray diffraction images

Features:
- Multiple mask drawing modes (Rectangle, Circle, Polygon, Point)
- Threshold-based masking
- Cosmic ray removal
- Grow/Shrink masks
- Invert masks
- Load/Save masks (EDF, NPY formats)

Created: 2025
@author: XRD Processing Suite
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QCheckBox, QComboBox, QGroupBox,
                              QFileDialog, QMessageBox, QFrame, QSlider, QSpinBox,
                              QRadioButton, QButtonGroup, QSplitter, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont
import os
import numpy as np
from gui_base import GUIBase
from theme_module import ModernButton

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle, Circle
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import fabio
    FABIO_AVAILABLE = True
except ImportError:
    FABIO_AVAILABLE = False


class MaskCanvas(FigureCanvas):
    """Canvas for mask creation and editing"""
    
    mask_changed = pyqtSignal()  # Signal emitted when mask changes
    
    def __init__(self, parent=None, width=8, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.image_data = None
        self.mask_data = None
        self.drawing = False
        self.mask_mode = 'rectangle'  # rectangle, circle, point, polygon
        self.mask_value = True  # True = mask, False = unmask
        self.start_point = None
        self.preview_patch = None
        self._last_mouse_pos = None
        
        # Polygon drawing
        self.polygon_points = []
        self.polygon_lines = []
        
        # Point drawing
        self.point_radius = 10
        
        # Zoom and contrast
        self.zoom_level = 1.0
        self.contrast_min = None
        self.contrast_max = None
        self.base_xlim = None
        self.base_ylim = None
        
        # Connect mouse events
        self.mpl_connect('button_press_event', self.on_mouse_press)
        self.mpl_connect('button_release_event', self.on_mouse_release)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.mpl_connect('scroll_event', self.on_scroll)
        self.mpl_connect('key_press_event', self.on_key_press)
    
    def load_image(self, image_path):
        """Load image for mask editing"""
        try:
            if FABIO_AVAILABLE:
                img = fabio.open(image_path)
                self.image_data = img.data
            else:
                from PIL import Image
                img = Image.open(image_path)
                self.image_data = np.array(img)
            
            # Initialize mask
            if self.mask_data is None or self.mask_data.shape != self.image_data.shape:
                self.mask_data = np.zeros(self.image_data.shape, dtype=bool)
            
            self.display_image()
            return True
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
    
    def set_image_data(self, image_data):
        """Set image data directly (from array)"""
        self.image_data = image_data
        
        # Initialize mask
        if self.mask_data is None or self.mask_data.shape != self.image_data.shape:
            self.mask_data = np.zeros(self.image_data.shape, dtype=bool)
        
        self.display_image()
    
    def display_image(self):
        """Display image with mask overlay - optimized for performance"""
        self.axes.clear()
        
        if self.image_data is None:
            return
        
        # Display image with log scale
        if self.contrast_min is not None and self.contrast_max is not None:
            display_data = np.clip(self.image_data, self.contrast_min, self.contrast_max)
            vmin, vmax = np.log10(self.contrast_min + 1), np.log10(self.contrast_max + 1)
        else:
            display_data = self.image_data
            vmin, vmax = None, None
        
        # Use faster interpolation for large images
        interp = 'nearest' if self.image_data.size > 4000000 else 'bilinear'
        self.axes.imshow(np.log10(display_data + 1), cmap='viridis', 
                        origin='lower', vmin=vmin, vmax=vmax, interpolation=interp)
        
        # Overlay mask in semi-transparent red (optimized)
        if self.mask_data is not None and np.any(self.mask_data):
            mask_rgba = np.zeros((*self.mask_data.shape, 4), dtype=np.float32)
            mask_rgba[self.mask_data, 0] = 1.0  # Red
            mask_rgba[self.mask_data, 3] = 0.5  # Semi-transparent
            self.axes.imshow(mask_rgba, origin='lower', interpolation='nearest', zorder=2)
        
        # Redraw polygon lines if in polygon mode
        if self.mask_mode == 'polygon' and self.polygon_points:
            for line in self.polygon_lines:
                try:
                    line.remove()
                except:
                    pass
            self.polygon_lines = []
            
            points = np.array(self.polygon_points)
            for i in range(len(points) - 1):
                line = self.axes.plot([points[i][0], points[i+1][0]], 
                                     [points[i][1], points[i+1][1]], 
                                     'y-', linewidth=2)[0]
                self.polygon_lines.append(line)
            
            # Draw points
            self.axes.plot(points[:, 0], points[:, 1], 'yo', markersize=6)
        
        self.axes.set_title(f'Mask Editor - Mode: {self.mask_mode.capitalize()}')
        
        # Store/restore zoom
        if self.base_xlim is None:
            self.base_xlim = self.axes.get_xlim()
            self.base_ylim = self.axes.get_ylim()
        
        self.figure.canvas.draw_idle()
    
    def on_mouse_press(self, event):
        """Handle mouse press"""
        if event.inaxes != self.axes or event.button != 1:
            return
        
        if self.mask_mode == 'polygon':
            # Add point to polygon
            x, y = int(event.xdata), int(event.ydata)
            self.polygon_points.append((x, y))
            self.display_image()
        elif self.mask_mode == 'point':
            # Draw point mask
            x, y = int(event.xdata), int(event.ydata)
            self.apply_point_mask(x, y)
            self.display_image()
            self.mask_changed.emit()
        else:
            # Start drawing rectangle/circle
            self.drawing = True
            self.start_point = (int(event.xdata), int(event.ydata))
    
    def on_mouse_release(self, event):
        """Handle mouse release"""
        if not self.drawing or self.mask_mode in ['polygon', 'point']:
            return
        
        # Remove preview
        if self.preview_patch is not None:
            try:
                self.preview_patch.remove()
            except:
                pass
            self.preview_patch = None
        
        # Get end point
        if event.inaxes != self.axes:
            if self._last_mouse_pos is None:
                self.drawing = False
                return
            end_point = self._last_mouse_pos
        else:
            end_point = (int(event.xdata), int(event.ydata))
        
        # Apply mask
        try:
            if self.mask_mode == 'rectangle':
                self.apply_rectangle_mask(self.start_point, end_point)
            elif self.mask_mode == 'circle':
                self.apply_circle_mask(self.start_point, end_point)
            
            self.mask_changed.emit()
        except Exception as e:
            print(f"Error applying mask: {e}")
        
        self.drawing = False
        self.display_image()
    
    def on_mouse_move(self, event):
        """Handle mouse move"""
        if not self.drawing or event.inaxes != self.axes:
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
        
        # Draw preview
        try:
            if self.mask_mode == 'rectangle':
                x1, y1 = self.start_point
                x2, y2 = current_point
                width = x2 - x1
                height = y2 - y1
                self.preview_patch = Rectangle((x1, y1), width, height,
                                              edgecolor='yellow', facecolor='red',
                                              alpha=0.3, linewidth=2)
                self.axes.add_patch(self.preview_patch)
            elif self.mask_mode == 'circle':
                cx, cy = self.start_point
                ex, ey = current_point
                radius = np.sqrt((ex - cx)**2 + (ey - cy)**2)
                self.preview_patch = Circle((cx, cy), radius,
                                           edgecolor='yellow', facecolor='red',
                                           alpha=0.3, linewidth=2)
                self.axes.add_patch(self.preview_patch)
        except Exception as e:
            print(f"Error drawing preview: {e}")
        
        self.figure.canvas.draw_idle()
    
    def on_key_press(self, event):
        """Handle key press for polygon mode"""
        if event.key == 'enter' and self.mask_mode == 'polygon':
            # Finish polygon
            if len(self.polygon_points) >= 3:
                self.apply_polygon_mask()
                self.polygon_points = []
                self.polygon_lines = []
                self.display_image()
                self.mask_changed.emit()
        elif event.key == 'escape' and self.mask_mode == 'polygon':
            # Cancel polygon
            self.polygon_points = []
            self.polygon_lines = []
            self.display_image()
    
    def on_scroll(self, event):
        """Handle scroll for zoom"""
        if event.inaxes != self.axes:
            return
        
        cur_xlim = self.axes.get_xlim()
        cur_ylim = self.axes.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        
        scale_factor = 0.9 if event.button == 'up' else 1.1
        
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        
        self.axes.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.axes.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        
        self.zoom_level = (self.base_xlim[1] - self.base_xlim[0]) / new_width
        self.draw_idle()
    
    def apply_rectangle_mask(self, start, end):
        """Apply rectangular mask"""
        if self.mask_data is None:
            return
        
        x1, y1 = min(start[0], end[0]), min(start[1], end[1])
        x2, y2 = max(start[0], end[0]), max(start[1], end[1])
        
        # Clamp to bounds
        height, width = self.mask_data.shape
        x1 = max(0, min(x1, width - 1))
        x2 = max(0, min(x2, width - 1))
        y1 = max(0, min(y1, height - 1))
        y2 = max(0, min(y2, height - 1))
        
        self.mask_data[y1:y2+1, x1:x2+1] = self.mask_value
    
    def apply_circle_mask(self, center, edge):
        """Apply circular mask"""
        if self.mask_data is None:
            return
        
        cx, cy = center
        ex, ey = edge
        radius = np.sqrt((ex - cx)**2 + (ey - cy)**2)
        
        height, width = self.mask_data.shape
        y, x = np.ogrid[0:height, 0:width]
        
        circle_mask = (x - cx)**2 + (y - cy)**2 <= radius**2
        self.mask_data[circle_mask] = self.mask_value
    
    def apply_polygon_mask(self):
        """Apply polygon mask"""
        if self.mask_data is None or len(self.polygon_points) < 3:
            return
        
        from matplotlib.path import Path
        
        height, width = self.mask_data.shape
        y, x = np.mgrid[:height, :width]
        points = np.vstack((x.ravel(), y.ravel())).T
        
        path = Path(self.polygon_points)
        mask = path.contains_points(points)
        mask = mask.reshape(height, width)
        
        self.mask_data[mask] = self.mask_value
    
    def apply_point_mask(self, x, y):
        """Apply point mask with radius"""
        if self.mask_data is None:
            return
        
        height, width = self.mask_data.shape
        yy, xx = np.ogrid[0:height, 0:width]
        
        circle_mask = (xx - x)**2 + (yy - y)**2 <= self.point_radius**2
        self.mask_data[circle_mask] = self.mask_value
    
    def apply_threshold_mask(self, threshold_min, threshold_max):
        """Apply intensity threshold mask"""
        if self.image_data is None or self.mask_data is None:
            return
        
        mask_threshold = (self.image_data < threshold_min) | (self.image_data > threshold_max)
        self.mask_data[mask_threshold] = self.mask_value
        self.display_image()
        self.mask_changed.emit()
    
    def clear_mask(self):
        """Clear all mask"""
        if self.mask_data is not None:
            self.mask_data = np.zeros(self.mask_data.shape, dtype=bool)
            self.display_image()
            self.mask_changed.emit()
    
    def invert_mask(self):
        """Invert mask"""
        if self.mask_data is not None:
            self.mask_data = ~self.mask_data
            self.display_image()
            self.mask_changed.emit()
    
    def grow_mask(self, pixels=1):
        """Grow mask by specified pixels"""
        if self.mask_data is None:
            return
        
        from scipy.ndimage import binary_dilation
        self.mask_data = binary_dilation(self.mask_data, iterations=pixels)
        self.display_image()
        self.mask_changed.emit()
    
    def shrink_mask(self, pixels=1):
        """Shrink mask by specified pixels"""
        if self.mask_data is None:
            return
        
        from scipy.ndimage import binary_erosion
        self.mask_data = binary_erosion(self.mask_data, iterations=pixels)
        self.display_image()
        self.mask_changed.emit()
    
    def reset_zoom(self):
        """Reset zoom"""
        if self.base_xlim is not None:
            self.axes.set_xlim(self.base_xlim)
            self.axes.set_ylim(self.base_ylim)
            self.zoom_level = 1.0
            self.draw_idle()
    
    def set_contrast(self, vmin, vmax):
        """Set contrast limits"""
        self.contrast_min = vmin
        self.contrast_max = vmax
        if self.image_data is not None:
            self.display_image()
    
    def get_mask(self):
        """Get current mask"""
        return self.mask_data
    
    def set_mask(self, mask):
        """Set mask"""
        if mask is not None:
            self.mask_data = mask.astype(bool)
            self.display_image()
            self.mask_changed.emit()


class MaskModule(QObject, GUIBase):
    """Mask editor module"""
    
    mask_updated = pyqtSignal(object)  # Signal emitted when mask is updated
    
    def __init__(self, parent, root):
        QObject.__init__(self)
        GUIBase.__init__(self)
        self.parent = parent
        self.root = root
        
        # Colors
        self.colors = {
            'bg': '#F5F5F5',
            'card_bg': '#FFFFFF',
            'primary': '#FF6B9D',  # Pink for mask module
            'primary_hover': '#FF5A8D',
            'secondary': '#FFA8C5',
            'accent': '#E67E73',
            'text_dark': '#2C3E50',
            'text_light': '#7F8C8D',
            'border': '#D1D9E6',
            'success': '#6FA86F',
            'error': '#E67E73',
        }
        
        self.current_image = None
        self.current_image_path = None
        self.mask_path = None
    
    def setup_ui(self):
        """Setup mask editor UI"""
        # Check if UI is already set up
        if hasattr(self, '_ui_initialized') and self._ui_initialized:
            return
        
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            # Clear existing items
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Display
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        if MATPLOTLIB_AVAILABLE:
            # Horizontal layout for canvas and contrast slider
            canvas_container = QWidget()
            canvas_layout = QHBoxLayout(canvas_container)
            canvas_layout.setContentsMargins(0, 0, 0, 0)
            canvas_layout.setSpacing(5)
            
            self.mask_canvas = MaskCanvas(canvas_container, width=10, height=8, dpi=100)
            self.mask_canvas.mask_changed.connect(self.on_mask_changed)
            canvas_layout.addWidget(self.mask_canvas)
            
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
            
            left_layout.addWidget(canvas_container)
        else:
            no_plot_label = QLabel("Matplotlib not available")
            no_plot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            left_layout.addWidget(no_plot_label)
        
        # Status bar
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(6, 6, 6, 6)
        
        self.mask_info_lbl = QLabel("No mask loaded")
        self.mask_info_lbl.setFont(QFont('Arial', 9))
        status_layout.addWidget(self.mask_info_lbl)
        status_layout.addStretch()
        
        left_layout.addWidget(status_frame)
        
        # Right: Controls (with scroll area to prevent overflow)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setMinimumWidth(320)
        right_scroll.setMaximumWidth(320)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(8)
        
        # File operations
        self.setup_file_operations(right_layout)
        
        # Drawing tools
        self.setup_drawing_tools(right_layout)
        
        # Mask operations
        self.setup_mask_operations(right_layout)
        
        # Display controls
        self.setup_display_controls(right_layout)
        
        right_layout.addStretch()
        
        # Log output (compact)
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(80)
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont('Courier', 7))
        right_layout.addWidget(self.log_output)
        
        # Set scroll area content
        right_scroll.setWidget(right_widget)
        
        # Add to splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_scroll)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        
        layout.addWidget(main_splitter)
        
        # Mark UI as initialized
        self._ui_initialized = True
    
    def setup_file_operations(self, parent_layout):
        """Setup file operations"""
        file_gb = QGroupBox("File Operations")
        file_gb.setStyleSheet(f"""
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
        file_layout = QVBoxLayout(file_gb)
        file_layout.setSpacing(10)
        
        # Note: Image is loaded from Calibration Module
        info_label = QLabel("Image loaded from Calibration Module")
        info_label.setStyleSheet("color: gray; font-size: 8pt; padding: 5px;")
        info_label.setWordWrap(True)
        file_layout.addWidget(info_label)
        
        # Load mask
        load_mask_btn = ModernButton("Load Mask",
                                     self.load_mask,
                                     "",
                                     bg_color=self.colors['primary'],
                                     hover_color=self.colors['primary_hover'],
                                     width=280, height=35,
                                     font_size=9,
                                     parent=file_gb)
        file_layout.addWidget(load_mask_btn)
        
        # Save mask
        save_mask_btn = ModernButton("Save Mask",
                                     self.save_mask,
                                     "",
                                     bg_color=self.colors['secondary'],
                                     hover_color=self.colors['primary'],
                                     width=280, height=35,
                                     font_size=9,
                                     parent=file_gb)
        file_layout.addWidget(save_mask_btn)
        
        parent_layout.addWidget(file_gb)
    
    def setup_drawing_tools(self, parent_layout):
        """Setup drawing tools"""
        draw_gb = QGroupBox("Drawing Tools")
        draw_gb.setStyleSheet(f"""
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
        draw_layout = QVBoxLayout(draw_gb)
        draw_layout.setSpacing(10)
        
        # Mode selection
        mode_label = QLabel("Drawing Mode:")
        mode_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        mode_label.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 4px 0px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);")
        draw_layout.addWidget(mode_label)
        
        # Radio button style for mask module
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
                image: url(point.png);
            }}
            QRadioButton::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """
        
        self.mode_group = QButtonGroup()
        
        self.rect_rb = QRadioButton("Rectangle")
        self.rect_rb.setChecked(True)
        self.rect_rb.setStyleSheet(radio_style)
        self.rect_rb.toggled.connect(lambda: self.set_mask_mode('rectangle'))
        self.mode_group.addButton(self.rect_rb)
        draw_layout.addWidget(self.rect_rb)
        
        self.circle_rb = QRadioButton("Circle")
        self.circle_rb.setStyleSheet(radio_style)
        self.circle_rb.toggled.connect(lambda: self.set_mask_mode('circle'))
        self.mode_group.addButton(self.circle_rb)
        draw_layout.addWidget(self.circle_rb)
        
        self.polygon_rb = QRadioButton("Polygon (Enter to finish)")
        self.polygon_rb.setStyleSheet(radio_style)
        self.polygon_rb.toggled.connect(lambda: self.set_mask_mode('polygon'))
        self.mode_group.addButton(self.polygon_rb)
        draw_layout.addWidget(self.polygon_rb)
        
        self.point_rb = QRadioButton("Point")
        self.point_rb.setStyleSheet(radio_style)
        self.point_rb.toggled.connect(lambda: self.set_mask_mode('point'))
        self.mode_group.addButton(self.point_rb)
        draw_layout.addWidget(self.point_rb)
        
        # Point radius (only for point mode)
        point_frame = QFrame()
        point_layout = QHBoxLayout(point_frame)
        point_layout.setContentsMargins(20, 0, 0, 0)
        point_layout.addWidget(QLabel("Radius:"))
        
        self.point_radius_sb = QSpinBox()
        self.point_radius_sb.setMinimum(1)
        self.point_radius_sb.setMaximum(100)
        self.point_radius_sb.setValue(10)
        self.point_radius_sb.valueChanged.connect(self.on_point_radius_changed)
        self.point_radius_sb.setFixedWidth(60)
        point_layout.addWidget(self.point_radius_sb)
        point_layout.addStretch()
        
        draw_layout.addWidget(point_frame)
        
        # Checkbox style for mask module
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
                image: url(check.png);
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """
        
        # Mask/Unmask toggle
        self.mask_value_cb = QCheckBox("Mask (checked) / Unmask (unchecked)")
        self.mask_value_cb.setChecked(True)
        self.mask_value_cb.setStyleSheet(checkbox_style)
        self.mask_value_cb.stateChanged.connect(self.on_mask_value_changed)
        draw_layout.addWidget(self.mask_value_cb)
        
        # Threshold masking
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; max-height: 1px; margin: 8px 0px;")
        draw_layout.addWidget(separator)
        
        thresh_label = QLabel("Threshold Masking:")
        thresh_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        thresh_label.setStyleSheet(f"color: {self.colors['text_dark']}; padding: 4px 0px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);")
        draw_layout.addWidget(thresh_label)
        
        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("Min:"))
        self.threshold_min_txt = QLineEdit("0")
        self.threshold_min_txt.setFixedWidth(70)
        thresh_row.addWidget(self.threshold_min_txt)
        
        thresh_row.addWidget(QLabel("Max:"))
        self.threshold_max_txt = QLineEdit("65535")
        self.threshold_max_txt.setFixedWidth(70)
        thresh_row.addWidget(self.threshold_max_txt)
        
        draw_layout.addLayout(thresh_row)
        
        apply_thresh_btn = QPushButton("Apply Threshold")
        apply_thresh_btn.setStyleSheet("padding: 5px;")
        apply_thresh_btn.clicked.connect(self.apply_threshold)
        draw_layout.addWidget(apply_thresh_btn)
        
        parent_layout.addWidget(draw_gb)
    
    def setup_mask_operations(self, parent_layout):
        """Setup mask operations"""
        ops_gb = QGroupBox("Mask Operations")
        ops_gb.setStyleSheet(f"""
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
        ops_layout = QVBoxLayout(ops_gb)
        ops_layout.setSpacing(10)
        
        # Clear/Invert row
        row1 = QHBoxLayout()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet("padding: 5px;")
        clear_btn.clicked.connect(self.clear_mask)
        row1.addWidget(clear_btn)
        
        invert_btn = QPushButton("Invert")
        invert_btn.setStyleSheet("padding: 5px;")
        invert_btn.clicked.connect(self.invert_mask)
        row1.addWidget(invert_btn)
        
        ops_layout.addLayout(row1)
        
        # Grow/Shrink
        gs_label = QLabel("Grow/Shrink:")
        gs_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        ops_layout.addWidget(gs_label)
        
        gs_row = QHBoxLayout()
        gs_row.addWidget(QLabel("Pixels:"))
        
        self.grow_shrink_sb = QSpinBox()
        self.grow_shrink_sb.setMinimum(1)
        self.grow_shrink_sb.setMaximum(50)
        self.grow_shrink_sb.setValue(1)
        self.grow_shrink_sb.setFixedWidth(60)
        gs_row.addWidget(self.grow_shrink_sb)
        gs_row.addStretch()
        
        ops_layout.addLayout(gs_row)
        
        row2 = QHBoxLayout()
        
        grow_btn = QPushButton("Grow")
        grow_btn.setStyleSheet("padding: 5px;")
        grow_btn.clicked.connect(self.grow_mask)
        row2.addWidget(grow_btn)
        
        shrink_btn = QPushButton("Shrink")
        shrink_btn.setStyleSheet("padding: 5px;")
        shrink_btn.clicked.connect(self.shrink_mask)
        row2.addWidget(shrink_btn)
        
        ops_layout.addLayout(row2)
        
        parent_layout.addWidget(ops_gb)
    
    def setup_display_controls(self, parent_layout):
        """Setup display controls"""
        disp_gb = QGroupBox("Display Controls")
        disp_gb.setStyleSheet(f"""
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
        disp_layout = QVBoxLayout(disp_gb)
        disp_layout.setSpacing(10)
        
        # Buttons
        btn_row = QHBoxLayout()
        
        auto_btn = QPushButton("Auto Contrast")
        auto_btn.setStyleSheet("padding: 5px;")
        auto_btn.clicked.connect(self.auto_contrast)
        btn_row.addWidget(auto_btn)
        
        reset_zoom_btn = QPushButton("Reset Zoom")
        reset_zoom_btn.setStyleSheet("padding: 5px;")
        reset_zoom_btn.clicked.connect(self.reset_zoom)
        btn_row.addWidget(reset_zoom_btn)
        
        disp_layout.addLayout(btn_row)
        
        parent_layout.addWidget(disp_gb)
    
    def load_mask(self):
        """Load mask from file"""
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
                
                if MATPLOTLIB_AVAILABLE:
                    self.mask_canvas.set_mask(mask)
                
                self.mask_path = filename
                self.log(f"Mask loaded: {os.path.basename(filename)}")
                self.update_mask_info()
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to load mask:\n{str(e)}")
                self.log(f"Error: {str(e)}")
    
    def save_mask(self):
        """Save mask to file"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        mask = self.mask_canvas.get_mask()
        if mask is None or not np.any(mask):
            QMessageBox.warning(None, "No Mask", "No mask to save")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            None, "Save Mask", "",
            "NumPy Files (*.npy);;EDF Files (*.edf);;All Files (*.*)"
        )
        
        if filename:
            try:
                if filename.endswith('.npy'):
                    np.save(filename, mask)
                elif filename.endswith('.edf') and FABIO_AVAILABLE:
                    edf = fabio.edfimage.edfimage(data=mask.astype(np.uint8))
                    edf.write(filename)
                else:
                    np.save(filename, mask)
                
                self.mask_path = filename
                self.log(f"Mask saved: {os.path.basename(filename)}")
                QMessageBox.information(None, "Success", "Mask saved successfully!")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to save mask:\n{str(e)}")
                self.log(f"Error: {str(e)}")
    
    def set_mask_mode(self, mode):
        """Set mask drawing mode"""
        if MATPLOTLIB_AVAILABLE:
            self.mask_canvas.mask_mode = mode
            self.log(f"Mask mode: {mode}")
    
    def on_point_radius_changed(self, value):
        """Handle point radius change"""
        if MATPLOTLIB_AVAILABLE:
            self.mask_canvas.point_radius = value
    
    def on_mask_value_changed(self, state):
        """Handle mask/unmask toggle"""
        if MATPLOTLIB_AVAILABLE:
            self.mask_canvas.mask_value = (state == Qt.CheckState.Checked.value)
    
    def apply_threshold(self):
        """Apply threshold mask"""
        try:
            vmin = float(self.threshold_min_txt.text())
            vmax = float(self.threshold_max_txt.text())
            
            if MATPLOTLIB_AVAILABLE:
                self.mask_canvas.apply_threshold_mask(vmin, vmax)
                self.log(f"Threshold applied: {vmin} - {vmax}")
                self.update_mask_info()
        except ValueError:
            QMessageBox.warning(None, "Invalid Input", "Please enter valid threshold values")
    
    def clear_mask(self):
        """Clear mask"""
        if MATPLOTLIB_AVAILABLE:
            self.mask_canvas.clear_mask()
            self.log("Mask cleared")
            self.update_mask_info()
    
    def invert_mask(self):
        """Invert mask"""
        if MATPLOTLIB_AVAILABLE:
            self.mask_canvas.invert_mask()
            self.log("Mask inverted")
            self.update_mask_info()
    
    def grow_mask(self):
        """Grow mask"""
        if MATPLOTLIB_AVAILABLE:
            pixels = self.grow_shrink_sb.value()
            self.mask_canvas.grow_mask(pixels)
            self.log(f"Mask grown by {pixels} pixels")
            self.update_mask_info()
    
    def shrink_mask(self):
        """Shrink mask"""
        if MATPLOTLIB_AVAILABLE:
            pixels = self.grow_shrink_sb.value()
            self.mask_canvas.shrink_mask(pixels)
            self.log(f"Mask shrunk by {pixels} pixels")
            self.update_mask_info()
    
    def on_contrast_slider_changed(self, value):
        """Handle contrast slider change (single vertical slider)"""
        if MATPLOTLIB_AVAILABLE:
            vmin = 0
            vmax = value
            self.mask_canvas.set_contrast(vmin, vmax)
    
    def auto_contrast(self):
        """Auto contrast"""
        if self.current_image is None:
            return
        
        vmin = np.percentile(self.current_image, 1)
        vmax = np.percentile(self.current_image, 99)
        
        if hasattr(self, 'contrast_slider'):
            self.contrast_slider.setValue(int(vmax))
        
        self.log(f"Auto contrast: 0 - {vmax:.0f}")
    
    def reset_zoom(self):
        """Reset zoom"""
        if MATPLOTLIB_AVAILABLE:
            self.mask_canvas.reset_zoom()
            self.log("Zoom reset")
    
    def on_mask_changed(self):
        """Handle mask change"""
        self.update_mask_info()
        
        # Emit signal with current mask (only if mask is not None)
        if MATPLOTLIB_AVAILABLE:
            mask = self.mask_canvas.get_mask()
            if mask is not None:
                self.mask_updated.emit(mask)
    
    def update_mask_info(self):
        """Update mask info label"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        mask = self.mask_canvas.get_mask()
        if mask is not None:
            masked_pixels = np.sum(mask)
            total_pixels = mask.size
            percentage = (masked_pixels / total_pixels) * 100
            self.mask_info_lbl.setText(f"Masked: {masked_pixels:,} / {total_pixels:,} pixels ({percentage:.2f}%)")
        else:
            self.mask_info_lbl.setText("No mask loaded")
    
    def log(self, message):
        """Log message"""
        if hasattr(self, 'log_output'):
            self.log_output.append(str(message))
            scrollbar = self.log_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def get_current_mask(self):
        """Get current mask for external use"""
        if MATPLOTLIB_AVAILABLE:
            return self.mask_canvas.get_mask()
        return None
    
    def set_image_for_mask(self, image_data):
        """Set image data from external source (e.g., calibration module)"""
        self.current_image = image_data
        if MATPLOTLIB_AVAILABLE:
            self.mask_canvas.set_image_data(image_data)
        self.log("Image data received from external module")
        self.update_mask_info()