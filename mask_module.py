#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mask Creation and Management Module
Module for creating and managing diffraction masks
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QGroupBox, QFileDialog, QMessageBox,
                              QLineEdit, QCheckBox, QSlider, QComboBox, QSpinBox,
                              QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import numpy as np
import os
from gui_base import GUIBase

# Import matplotlib for image display
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle, Rectangle, Polygon
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠ Warning: matplotlib not available. Mask preview will be disabled.")


class MaskModule(GUIBase):
    """Mask Creation and Management Module"""

    def __init__(self, parent, root):
        """
        Initialize Mask module
        
        Args:
            parent: Parent widget to contain this module
            root: Root window for dialogs
        """
        super().__init__()
        self.parent = parent
        self.root = root

        # Mask data
        self.current_mask = None
        self.mask_file_path = None
        self.image_data = None
        
        # Drawing mode and state
        self.draw_mode = 'select'  # 'select', 'circle', 'rectangle', 'polygon', 'point', 'threshold'
        self.drawing = False
        self.draw_start = None
        self.draw_current = None
        self.polygon_points = []
        self.temp_shape = None  # Temporary shape being drawn
        self.preview_artists = []  # Store preview shapes for faster update
        
        # Performance optimization - cache computed image
        self.cached_image = None
        self.cached_contrast = None
        self.cached_vmin = None
        self.cached_vmax = None
        self.last_preview_update = 0  # Throttle preview updates
        self.display_downsample = 1  # Downsample factor for display
        self.mask_artist = None  # Cache mask overlay artist for fast update

    def setup_ui(self):
        """Setup UI components"""
        # Get or create layout for parent
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area - No scrollbar, fit in one page
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background-color: {self.colors['bg']}; border: none;")

        # Content widget - Full width
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {self.colors['bg']};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 5, 10, 5)
        content_layout.setSpacing(4)

        # Control area (includes Save/Clear buttons now)
        control_group = self.create_control_group()
        content_layout.addWidget(control_group)

        # Drawing tools
        tools_group = self.create_tools_group()
        content_layout.addWidget(tools_group)

        # Preview area
        if MATPLOTLIB_AVAILABLE:
            preview_group = self.create_preview_group()
            content_layout.addWidget(preview_group)
        
        # Add content widget to scroll area
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def create_control_group(self):
        """Create file control group"""
        group = QGroupBox("File Control")
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 5px;
                font-weight: bold;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
        """)

        layout = QHBoxLayout(group)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Load Image button
        load_img_btn = QPushButton("📂 Load Image")
        load_img_btn.setFixedWidth(110)
        load_img_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #6A1B9A;
            }}
        """)
        load_img_btn.clicked.connect(self.load_image)
        layout.addWidget(load_img_btn)
        
        # Separator
        layout.addWidget(QLabel("|"))

        # Load Mask button
        load_mask_btn = QPushButton("📂 Load Mask")
        load_mask_btn.setFixedWidth(110)
        load_mask_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        load_mask_btn.clicked.connect(self.load_mask)
        layout.addWidget(load_mask_btn)
        
        # Separator
        layout.addWidget(QLabel("|"))
        
        # Save Mask button
        save_btn = QPushButton("💾 Save Mask")
        save_btn.setFixedWidth(110)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45A049;
            }}
        """)
        save_btn.clicked.connect(self.save_mask)
        layout.addWidget(save_btn)
        
        # Clear All button
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.setFixedWidth(110)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF5252;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FF1744;
            }}
        """)
        clear_btn.clicked.connect(self.clear_mask)
        layout.addWidget(clear_btn)

        layout.addStretch()
        
        # File info label
        self.file_info_label = QLabel("No image loaded")
        self.file_info_label.setStyleSheet("color: #666666; font-size: 9px;")
        layout.addWidget(self.file_info_label)

        return group
    
    def create_tools_group(self):
        """Create drawing tools group"""
        group = QGroupBox("Drawing Tools & Operations")
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 5px;
                font-weight: bold;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Single row: Tools + Action + Operations all combined
        all_row = QHBoxLayout()
        all_row.setSpacing(6)
        
        all_row.addWidget(QLabel("Tool:"))

        # Tool radio buttons
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        
        self.tool_group = QButtonGroup(group)
        
        self.select_radio = QRadioButton("Select")
        self.select_radio.setChecked(True)
        self.select_radio.toggled.connect(lambda: self.on_tool_changed("select"))
        self.tool_group.addButton(self.select_radio)
        all_row.addWidget(self.select_radio)
        
        self.circle_radio = QRadioButton("Circle")
        self.circle_radio.toggled.connect(lambda: self.on_tool_changed("circle"))
        self.tool_group.addButton(self.circle_radio)
        all_row.addWidget(self.circle_radio)
        
        self.rect_radio = QRadioButton("Rectangle")
        self.rect_radio.toggled.connect(lambda: self.on_tool_changed("rectangle"))
        self.tool_group.addButton(self.rect_radio)
        all_row.addWidget(self.rect_radio)
        
        self.polygon_radio = QRadioButton("Polygon")
        self.polygon_radio.toggled.connect(lambda: self.on_tool_changed("polygon"))
        self.tool_group.addButton(self.polygon_radio)
        all_row.addWidget(self.polygon_radio)
        
        self.point_radio = QRadioButton("Point")
        self.point_radio.toggled.connect(lambda: self.on_tool_changed("point"))
        self.tool_group.addButton(self.point_radio)
        all_row.addWidget(self.point_radio)
        
        self.threshold_radio = QRadioButton("Threshold")
        self.threshold_radio.toggled.connect(lambda: self.on_tool_changed("threshold"))
        self.tool_group.addButton(self.threshold_radio)
        all_row.addWidget(self.threshold_radio)

        # Separator
        all_row.addWidget(QLabel("|"))
        
        all_row.addWidget(QLabel("Action:"))
        
        self.mask_radio = QRadioButton("Mask")
        self.mask_radio.setChecked(True)
        all_row.addWidget(self.mask_radio)
        
        self.unmask_radio = QRadioButton("Unmask")
        all_row.addWidget(self.unmask_radio)
        
        self.action_group = QButtonGroup(group)
        self.action_group.addButton(self.mask_radio)
        self.action_group.addButton(self.unmask_radio)
        
        # Separator
        all_row.addWidget(QLabel("|"))
        
        # Operations on same row
        all_row.addWidget(QLabel("Ops:"))
        
        # Invert button
        invert_btn = QPushButton("↕️")
        invert_btn.setFixedWidth(35)
        invert_btn.setToolTip("Invert mask")
        invert_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 3px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        invert_btn.clicked.connect(self.invert_mask)
        all_row.addWidget(invert_btn)
        
        # Grow button
        grow_btn = QPushButton("➕")
        grow_btn.setFixedWidth(35)
        grow_btn.setToolTip("Grow mask")
        grow_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 3px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        grow_btn.clicked.connect(self.grow_mask)
        all_row.addWidget(grow_btn)
        
        # Shrink button
        shrink_btn = QPushButton("➖")
        shrink_btn.setFixedWidth(35)
        shrink_btn.setToolTip("Shrink mask")
        shrink_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 3px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        shrink_btn.clicked.connect(self.shrink_mask)
        all_row.addWidget(shrink_btn)
        
        # Fill holes button
        fill_btn = QPushButton("🔧")
        fill_btn.setFixedWidth(35)
        fill_btn.setToolTip("Fill holes")
        fill_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 3px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        fill_btn.clicked.connect(self.fill_holes)
        all_row.addWidget(fill_btn)

        all_row.addStretch()
        layout.addLayout(all_row)

        return group

    def create_preview_group(self):
        """Create image preview group"""
        group = QGroupBox("Mask Preview (Click to draw)")
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 5px;
                font-weight: bold;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Info row
        info_row = QHBoxLayout()

        self.position_label = QLabel("Position: --")
        self.position_label.setFont(QFont('Arial', 10))
        info_row.addWidget(self.position_label)

        self.mask_status_label = QLabel("Mask: Not loaded")
        self.mask_status_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        self.mask_status_label.setStyleSheet("color: #FF5722;")
        info_row.addWidget(self.mask_status_label)

        info_row.addStretch()
        layout.addLayout(info_row)

        # Canvas and contrast slider layout - Centered
        canvas_layout = QHBoxLayout()
        canvas_layout.addStretch(1)  # Left spacer for centering
        
        # Matplotlib canvas - Large for h5 images, no horizontal scroll
        self.figure = Figure(figsize=(13, 8))
        self.figure.subplots_adjust(left=0.05, right=0.98, top=0.97, bottom=0.06)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedSize(1300, 800)  # Large canvas without horizontal scroll
        canvas_layout.addWidget(self.canvas)
        
        # Vertical contrast slider
        slider_layout = QVBoxLayout()
        slider_layout.setSpacing(2)
        slider_layout.addStretch()
        
        max_label = QLabel("High")
        max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_label.setStyleSheet("color: #666666; font-size: 9px;")
        slider_layout.addWidget(max_label)
        
        self.contrast_slider = QSlider(Qt.Orientation.Vertical)
        self.contrast_slider.setMinimum(1)
        self.contrast_slider.setMaximum(100)
        self.contrast_slider.setValue(50)
        self.contrast_slider.setFixedHeight(500)
        self.contrast_slider.setFixedWidth(30)
        self.contrast_slider.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #BBBBBB;
                width: 8px;
                background: #FFFFFF;
                margin: 0 0;
            }
            QSlider::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E0E0E0, stop:1 #F5F5F5);
                border: 1px solid #AAAAAA;
                height: 18px;
                width: 20px;
                margin: 0 -6px;
            }
            QSlider::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D0D0D0, stop:1 #E5E5E5);
                border: 1px solid #888888;
            }
        """)
        self.contrast_slider.valueChanged.connect(self.on_contrast_changed)
        slider_layout.addWidget(self.contrast_slider, alignment=Qt.AlignmentFlag.AlignCenter)
        
        min_label = QLabel("Low")
        min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        min_label.setStyleSheet("color: #666666; font-size: 9px;")
        slider_layout.addWidget(min_label)
        
        self.contrast_label = QLabel("50%")
        self.contrast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.contrast_label.setFixedWidth(50)
        self.contrast_label.setStyleSheet("color: #333333; font-weight: bold; font-size: 11px;")
        slider_layout.addWidget(self.contrast_label)
        
        contrast_text = QLabel("Contrast")
        contrast_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        contrast_text.setStyleSheet("color: #666666; font-size: 9px;")
        slider_layout.addWidget(contrast_text)
        
        slider_layout.addStretch()
        canvas_layout.addLayout(slider_layout)
        
        canvas_layout.addStretch(1)  # Right spacer for centering
        
        layout.addLayout(canvas_layout)

        # Connect mouse events
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)

        # Initial plot
        self.ax = self.figure.add_subplot(111)
        self.ax.text(0.5, 0.5, 'Load an image to create mask\nUse drawing tools to mark regions',
                     ha='center', va='center', fontsize=14, color='gray')
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('on')
        self.canvas.draw()

        return group

    def load_image(self):
        """Load diffraction image for mask creation - Optimized for h5"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.root,
            "Select Diffraction Image",
            "",
            "Image Files (*.tif *.tiff *.edf *.h5 *.hdf5);;All Files (*)"
        )

        if not file_path:
            return

        try:
            from PyQt6.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
            
            # Load image based on file type
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.h5', '.hdf5']:
                import h5py
                # Optimized h5 loading - use direct array access without copying
                with h5py.File(file_path, 'r') as f:
                    # Try common dataset paths
                    for path in ['entry/data/data', 'data', 'image']:
                        if path in f:
                            data = f[path]
                            if len(data.shape) == 3:
                                # Use slicing to reduce memory copy
                                self.image_data = data[0, :, :].astype(np.float32)
                            else:
                                self.image_data = data[:, :].astype(np.float32)
                            break
            else:
                # Try fabio for other formats
                try:
                    import fabio
                    img = fabio.open(file_path)
                    self.image_data = img.data.astype(np.float32)
                except:
                    # Fallback to pillow
                    from PIL import Image
                    img = Image.open(file_path)
                    self.image_data = np.array(img, dtype=np.float32)

            if self.image_data is None:
                QMessageBox.warning(self.root, "Error", "Could not load image data")
                QApplication.restoreOverrideCursor()
                return

            # Initialize mask if not exists
            if self.current_mask is None or self.current_mask.shape != self.image_data.shape:
                self.current_mask = np.zeros(self.image_data.shape, dtype=bool)

            # Clear cache on new image
            self.cached_image = None
            self.cached_contrast = None

            # Update info
            self.file_info_label.setText(
                f"Image: {os.path.basename(file_path)} | Shape: {self.image_data.shape}"
            )

            # Display with caching
            self.update_display(force_recalc=True)
            
            QApplication.restoreOverrideCursor()

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.root, "Error", f"Failed to load image:\n{str(e)}")

    def load_mask(self):
        """Load existing mask file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.root,
            "Select Mask File",
            "",
            "Mask Files (*.npy *.edf *.tif *.tiff);;All Files (*)"
        )

        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.npy':
                self.current_mask = np.load(file_path)
            else:
                import fabio
                mask_img = fabio.open(file_path)
                self.current_mask = mask_img.data.astype(bool)

            self.mask_file_path = file_path
            self.mask_status_label.setText(f"Mask: {os.path.basename(file_path)}")
            
            self.update_display()

        except Exception as e:
            QMessageBox.critical(self.root, "Error", f"Failed to load mask:\n{str(e)}")

    def save_mask(self):
        """Save current mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.root,
            "Save Mask",
            "",
            "NumPy Array (*.npy);;EDF File (*.edf);;TIFF File (*.tif)"
        )

        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.npy':
                np.save(file_path, self.current_mask)
            else:
                import fabio
                mask_img = fabio.edfimage.edfimage(data=self.current_mask.astype(np.uint8))
                mask_img.write(file_path)

            self.mask_file_path = file_path
            QMessageBox.information(self.root, "Success", f"Mask saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self.root, "Error", f"Failed to save mask:\n{str(e)}")

    def clear_mask(self):
        """Clear current mask"""
        reply = QMessageBox.question(
            self.root, 'Confirm', 'Clear all mask regions?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.image_data is not None:
                self.current_mask = np.zeros(self.image_data.shape, dtype=bool)
                self.mask_shapes = []
                self.update_display()

    def on_tool_changed(self, tool_name):
        """Handle tool selection change"""
        self.draw_mode = tool_name.lower()
        # Reset drawing state
        self.drawing = False
        self.draw_start = None
        self.draw_current = None
        self.polygon_points = []
        self.temp_shape = None
        
        if self.image_data is not None:
            self.update_display()
    
    def invert_mask(self):
        """Invert the mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to invert")
            return
        
        self.current_mask = ~self.current_mask
        self.update_display()
    
    def grow_mask(self):
        """Grow (dilate) the mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to grow")
            return
        
        try:
            from scipy import ndimage
            self.current_mask = ndimage.binary_dilation(self.current_mask, iterations=1)
            self.update_display()
        except ImportError:
            QMessageBox.warning(self.root, "Warning", "scipy not available for mask operations")
    
    def shrink_mask(self):
        """Shrink (erode) the mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to shrink")
            return
        
        try:
            from scipy import ndimage
            self.current_mask = ndimage.binary_erosion(self.current_mask, iterations=1)
            self.update_display()
        except ImportError:
            QMessageBox.warning(self.root, "Warning", "scipy not available for mask operations")
    
    def fill_holes(self):
        """Fill holes in the mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to fill")
            return
        
        try:
            from scipy import ndimage
            self.current_mask = ndimage.binary_fill_holes(self.current_mask)
            self.update_display()
        except ImportError:
            QMessageBox.warning(self.root, "Warning", "scipy not available for mask operations")

    def on_contrast_changed(self, value):
        """Handle contrast slider change - with forced recalc"""
        self.contrast_label.setText(f"{value}%")
        if self.image_data is not None:
            # Force recalculation since contrast changed
            self.update_display(force_recalc=True)
    
    def on_scroll(self, event):
        """Handle mouse wheel scroll for zooming - Optimized"""
        if event.inaxes != self.ax or self.image_data is None:
            return
        
        # Get current axis limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Get mouse position in data coordinates
        xdata = event.xdata
        ydata = event.ydata
        
        if xdata is None or ydata is None:
            return
        
        # Zoom factor - smaller for smoother zoom
        zoom_factor = 1.15 if event.button == 'up' else 0.85
        
        # Calculate new limits centered on mouse position
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        
        new_x_range = x_range / zoom_factor
        new_y_range = y_range / zoom_factor
        
        # Calculate new limits
        x_center_ratio = (xdata - xlim[0]) / x_range
        y_center_ratio = (ydata - ylim[0]) / y_range
        
        new_xlim = [
            xdata - new_x_range * x_center_ratio,
            xdata + new_x_range * (1 - x_center_ratio)
        ]
        new_ylim = [
            ydata - new_y_range * y_center_ratio,
            ydata + new_y_range * (1 - y_center_ratio)
        ]
        
        # Constrain to image bounds
        new_xlim[0] = max(0, new_xlim[0])
        new_xlim[1] = min(self.image_data.shape[1], new_xlim[1])
        new_ylim[0] = max(0, new_ylim[0])
        new_ylim[1] = min(self.image_data.shape[0], new_ylim[1])
        
        # Apply new limits - only update view, don't redraw everything
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        
        # Fast update
        self.canvas.draw_idle()

    def update_display(self, force_recalc=False):
        """Update image and mask display - Full redraw with caching and optimization"""
        if self.image_data is None:
            return

        self.ax.clear()
        
        current_contrast = self.contrast_slider.value()
        
        # Use cached image if contrast hasn't changed
        if (not force_recalc and self.cached_image is not None and 
            self.cached_contrast == current_contrast):
            img_display = self.cached_image
            vmin, vmax = self.cached_vmin, self.cached_vmax
        else:
            # Determine if downsampling is needed for performance
            max_size = 2048
            h, w = self.image_data.shape
            downsample = max(1, max(h // max_size, w // max_size))
            
            if downsample > 1:
                # Downsample for faster display
                img_data = self.image_data[::downsample, ::downsample]
            else:
                img_data = self.image_data
            
            # Apply log scale and contrast - improved algorithm
            img_display = np.log10(img_data + 1)
            contrast_factor = current_contrast / 100.0
            
            # Better contrast mapping for clearer images
            low_percentile = 0.5 + contrast_factor * 5
            high_percentile = 99.5 - (1 - contrast_factor) * 10
            
            # Use faster percentile calculation for large images
            if img_display.size > 1000000:
                # Sample for percentile calculation
                sample = img_display.flat[::max(1, img_display.size // 100000)]
                vmin = np.percentile(sample, low_percentile)
                vmax = np.percentile(sample, high_percentile)
            else:
                vmin = np.percentile(img_display, low_percentile)
                vmax = np.percentile(img_display, high_percentile)
            
            # Cache the result
            self.cached_image = img_display
            self.cached_contrast = current_contrast
            self.cached_vmin = vmin
            self.cached_vmax = vmax
            self.display_downsample = downsample
        
        # Display image with interpolation for smooth viewing
        self.ax.imshow(img_display, cmap='viridis', origin='lower',
                      interpolation='bilinear', vmin=vmin, vmax=vmax,
                      extent=[0, self.image_data.shape[1],
                             0, self.image_data.shape[0]])

        # Overlay mask if exists - Pure red #FF0000 for better visibility
        if self.current_mask is not None:
            from matplotlib.colors import ListedColormap
            # Create pure red colormap #FF0000 (not pink or light red)
            pure_red = ListedColormap([(0, 0, 0, 0), (1, 0, 0, 1)])  # RGBA: transparent, pure red
            mask_overlay = np.ma.masked_where(~self.current_mask, self.current_mask)
            self.mask_artist = self.ax.imshow(mask_overlay, cmap=pure_red, alpha=0.6, origin='lower',
                                             extent=[0, self.image_data.shape[1],
                                                    0, self.image_data.shape[0]], 
                                             interpolation='nearest', zorder=10)

        # Draw temporary shape being drawn
        self._draw_preview_shapes()
        
        # Draw polygon points
        if self.draw_mode == 'polygon' and len(self.polygon_points) > 0:
            points = np.array(self.polygon_points)
            self.ax.plot(points[:, 0], points[:, 1], 'yo-', linewidth=2, markersize=8)
            # Close polygon preview if more than 2 points
            if len(self.polygon_points) > 2:
                self.ax.plot([points[-1, 0], points[0, 0]], 
                           [points[-1, 1], points[0, 1]], 'y--', linewidth=2)

        self.ax.set_xlim(0, self.image_data.shape[1])
        self.ax.set_ylim(0, self.image_data.shape[0])
        self.ax.set_xlabel('X (pixels)', fontsize=10)
        self.ax.set_ylabel('Y (pixels)', fontsize=10)
        self.ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        self.canvas.draw_idle()
    
    def _draw_preview_shapes(self):
        """Draw temporary preview shapes"""
        if self.drawing and self.draw_start and self.draw_current:
            if self.draw_mode == 'circle':
                radius = np.sqrt((self.draw_current[0] - self.draw_start[0])**2 + 
                               (self.draw_current[1] - self.draw_start[1])**2)
                circle = Circle(self.draw_start, radius, fill=False, 
                              edgecolor='yellow', linewidth=2, linestyle='--')
                self.ax.add_patch(circle)
            
            elif self.draw_mode == 'rectangle':
                x1, y1 = self.draw_start
                x2, y2 = self.draw_current
                width = x2 - x1
                height = y2 - y1
                rect = Rectangle((x1, y1), width, height, fill=False,
                               edgecolor='yellow', linewidth=2, linestyle='--')
                self.ax.add_patch(rect)
    
    def update_mask_only(self):
        """Ultra-fast mask overlay update without redrawing image"""
        if self.image_data is None or self.current_mask is None:
            return
        
        # Remove old mask overlay artist if exists
        if hasattr(self, 'mask_artist') and self.mask_artist:
            try:
                self.mask_artist.remove()
            except:
                pass
        
        # Draw only mask overlay with pure red #FF0000
        from matplotlib.colors import ListedColormap
        pure_red = ListedColormap([(0, 0, 0, 0), (1, 0, 0, 1)])  # RGBA: transparent, pure red
        mask_overlay = np.ma.masked_where(~self.current_mask, self.current_mask)
        self.mask_artist = self.ax.imshow(mask_overlay, cmap=pure_red, alpha=0.6, 
                                          origin='lower',
                                          extent=[0, self.image_data.shape[1],
                                                 0, self.image_data.shape[0]],
                                          interpolation='nearest', zorder=10)
        
        # Very fast update
        self.canvas.draw_idle()
    
    def update_preview_only(self):
        """Fast preview update without full redraw - for mouse move"""
        if self.image_data is None:
            return
        
        # Remove old preview artists efficiently
        while self.preview_artists:
            artist = self.preview_artists.pop()
            artist.remove()
        
        # Draw new preview shapes
        if self.drawing and self.draw_start and self.draw_current:
            if self.draw_mode == 'circle':
                radius = np.sqrt((self.draw_current[0] - self.draw_start[0])**2 + 
                               (self.draw_current[1] - self.draw_start[1])**2)
                circle = Circle(self.draw_start, radius, fill=False, 
                              edgecolor='yellow', linewidth=1.5, linestyle='--')
                self.ax.add_patch(circle)
                self.preview_artists.append(circle)
            
            elif self.draw_mode == 'rectangle':
                x1, y1 = self.draw_start
                x2, y2 = self.draw_current
                width = x2 - x1
                height = y2 - y1
                rect = Rectangle((x1, y1), width, height, fill=False,
                               edgecolor='yellow', linewidth=1.5, linestyle='--')
                self.ax.add_patch(rect)
                self.preview_artists.append(rect)
        
        # Use draw_idle for efficient update
        self.canvas.draw_idle()

    def on_mouse_move(self, event):
        """Handle mouse move event - optimized with throttling"""
        if event.inaxes != self.ax or self.image_data is None:
            self.position_label.setText("Position: --")
            return

        x, y = int(event.xdata), int(event.ydata)
        self.position_label.setText(f"Position: ({x}, {y})")
        
        # Update drawing preview - throttled for better performance
        if self.drawing and self.draw_start is not None:
            import time
            current_time = time.time()
            # Throttle: Only update every 16ms (60 FPS)
            if current_time - self.last_preview_update > 0.016:
                self.draw_current = (x, y)
                self.update_preview_only()
                self.last_preview_update = current_time
            else:
                # Still update position for next draw
                self.draw_current = (x, y)

    def on_mouse_press(self, event):
        """Handle mouse press event for drawing"""
        if event.inaxes != self.ax or self.image_data is None:
            return
        
        x, y = int(event.xdata), int(event.ydata)
        
        # Right click to finish polygon
        if event.button == 3:  # Right click
            if self.draw_mode == 'polygon' and len(self.polygon_points) >= 3:
                self.apply_polygon_mask()
                self.update_display()
            return
        
        if event.button != 1:  # Only left click for drawing
            return
        
        if self.draw_mode == 'select':
            return
        
        elif self.draw_mode == 'point':
            # Immediately apply point mask
            self.apply_point_mask(x, y, radius=5)
        
        elif self.draw_mode == 'threshold':
            # Apply threshold masking
            self.apply_threshold_mask()
        
        elif self.draw_mode == 'polygon':
            # Add point to polygon
            self.polygon_points.append((x, y))
            self.update_display()
        
        elif self.draw_mode in ['circle', 'rectangle']:
            # Start drawing shape
            self.drawing = True
            self.draw_start = (x, y)
            self.draw_current = (x, y)
    
    def on_mouse_release(self, event):
        """Handle mouse release event"""
        if event.inaxes != self.ax or self.image_data is None:
            return
        
        if event.button != 1:  # Only left click
            return
        
        if not self.drawing:
            return
        
        x, y = int(event.xdata), int(event.ydata)
        self.draw_current = (x, y)
        
        # Apply the shape
        if self.draw_mode == 'circle':
            self.apply_circle_mask(self.draw_start, self.draw_current)
        elif self.draw_mode == 'rectangle':
            self.apply_rectangle_mask(self.draw_start, self.draw_current)
        
        # Reset drawing state
        self.drawing = False
        self.draw_start = None
        self.draw_current = None
        self.update_display()
    
    def apply_point_mask(self, x, y, radius=5):
        """Apply mask/unmask at a point - optimized"""
        if self.current_mask is None:
            return
        
        # Optimized: only check region around point
        y_min = max(0, int(y - radius - 1))
        y_max = min(self.current_mask.shape[0], int(y + radius + 2))
        x_min = max(0, int(x - radius - 1))
        x_max = min(self.current_mask.shape[1], int(x + radius + 2))
        
        # Create local grid
        yy, xx = np.ogrid[y_min:y_max, x_min:x_max]
        dist = np.sqrt((xx - x)**2 + (yy - y)**2)
        mask_region = dist <= radius
        
        # Apply mask or unmask locally
        if self.mask_radio.isChecked():
            self.current_mask[y_min:y_max, x_min:x_max][mask_region] = True
        else:
            self.current_mask[y_min:y_max, x_min:x_max][mask_region] = False
        
        # Fast mask-only update instead of full redraw
        self.update_mask_only()
    
    def apply_circle_mask(self, start, end):
        """Apply circular mask"""
        if self.current_mask is None:
            return
        
        cx, cy = start
        radius = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        
        Y, X = np.ogrid[:self.current_mask.shape[0], :self.current_mask.shape[1]]
        dist = np.sqrt((X - cx)**2 + (Y - cy)**2)
        mask_region = dist <= radius
        
        # Apply mask or unmask
        if self.mask_radio.isChecked():
            self.current_mask[mask_region] = True
        else:
            self.current_mask[mask_region] = False
    
    def apply_rectangle_mask(self, start, end):
        """Apply rectangular mask"""
        if self.current_mask is None:
            return
        
        x1, y1 = start
        x2, y2 = end
        
        # Ensure correct order
        xmin, xmax = min(x1, x2), max(x1, x2)
        ymin, ymax = min(y1, y2), max(y1, y2)
        
        # Clip to image bounds
        xmin = max(0, xmin)
        xmax = min(self.current_mask.shape[1] - 1, xmax)
        ymin = max(0, ymin)
        ymax = min(self.current_mask.shape[0] - 1, ymax)
        
        # Apply mask or unmask
        if self.mask_radio.isChecked():
            self.current_mask[ymin:ymax+1, xmin:xmax+1] = True
        else:
            self.current_mask[ymin:ymax+1, xmin:xmax+1] = False
    
    def apply_polygon_mask(self):
        """Apply polygon mask"""
        if self.current_mask is None or len(self.polygon_points) < 3:
            return
        
        from matplotlib.path import Path
        
        # Create polygon path
        path = Path(self.polygon_points)
        
        # Create grid of points
        ny, nx = self.current_mask.shape
        x, y = np.meshgrid(np.arange(nx), np.arange(ny))
        points = np.vstack((x.flatten(), y.flatten())).T
        
        # Check which points are inside polygon
        mask_region = path.contains_points(points).reshape(ny, nx)
        
        # Apply mask or unmask
        if self.mask_radio.isChecked():
            self.current_mask[mask_region] = True
        else:
            self.current_mask[mask_region] = False
        
        # Clear polygon points
        self.polygon_points = []
    
    def apply_threshold_mask(self):
        """Apply threshold-based masking"""
        if self.image_data is None:
            return
        
        # Ask user for threshold value
        from PyQt6.QtWidgets import QInputDialog
        
        threshold, ok = QInputDialog.getDouble(
            self.root,
            "Threshold Value",
            "Enter threshold value (pixels above this will be masked):",
            value=1000.0,
            min=0.0,
            max=float(self.image_data.max()),
            decimals=1
        )
        
        if not ok:
            return
        
        # Create mask based on threshold
        threshold_region = self.image_data > threshold
        
        # Initialize mask if needed
        if self.current_mask is None:
            self.current_mask = np.zeros(self.image_data.shape, dtype=bool)
        
        # Apply mask or unmask
        if self.mask_radio.isChecked():
            self.current_mask[threshold_region] = True
        else:
            self.current_mask[threshold_region] = False
        
        self.update_display()
    
    def on_key_press(self, event):
        """Handle key press events"""
        if event.key == 'enter' or event.key == 'escape':
            # Finish polygon
            if self.draw_mode == 'polygon' and len(self.polygon_points) >= 3:
                self.apply_polygon_mask()
                self.update_display()
            elif self.draw_mode == 'polygon':
                # Cancel polygon
                self.polygon_points = []
                self.update_display()


# Test code
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Create test widget
    widget = QWidget()
    
    mask_module = MaskModule(widget, widget)
    mask_module.setup_ui()
    
    widget.setWindowTitle("Mask Module Test")
    widget.resize(1200, 900)
    widget.show()

    sys.exit(app.exec())
