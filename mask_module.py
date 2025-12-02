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

        # Content widget with center alignment
        content_container = QWidget()
        container_layout = QHBoxLayout(content_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        container_layout.addStretch(1)  # Left spacer
        
        content_widget = QWidget()
        content_widget.setMaximumWidth(1200)  # Limit width for better centering
        content_widget.setStyleSheet(f"background-color: {self.colors['bg']};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 8, 20, 8)
        content_layout.setSpacing(6)
        
        container_layout.addWidget(content_widget)
        container_layout.addStretch(1)  # Right spacer

        # Title
        title = QLabel("🎭 Mask Creation & Management")
        title.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['primary']};")
        content_layout.addWidget(title)

        # Description - Compact
        desc = QLabel("Create and manage detector masks • Circle/Rect: drag • Polygon: points+Enter • Point: click")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {self.colors['text_dark']}; font-size: 9pt;")
        content_layout.addWidget(desc)

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
        
        # Add content container to scroll area
        scroll.setWidget(content_container)
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
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Row 1: Drawing tools - Radio buttons
        tool_row = QHBoxLayout()
        tool_row.setSpacing(10)
        
        tool_row.addWidget(QLabel("Tool:"))

        # Tool radio buttons
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        
        self.tool_group = QButtonGroup(group)
        
        self.select_radio = QRadioButton("Select")
        self.select_radio.setChecked(True)
        self.select_radio.toggled.connect(lambda: self.on_tool_changed("select"))
        self.tool_group.addButton(self.select_radio)
        tool_row.addWidget(self.select_radio)
        
        self.circle_radio = QRadioButton("Circle")
        self.circle_radio.toggled.connect(lambda: self.on_tool_changed("circle"))
        self.tool_group.addButton(self.circle_radio)
        tool_row.addWidget(self.circle_radio)
        
        self.rect_radio = QRadioButton("Rectangle")
        self.rect_radio.toggled.connect(lambda: self.on_tool_changed("rectangle"))
        self.tool_group.addButton(self.rect_radio)
        tool_row.addWidget(self.rect_radio)
        
        self.polygon_radio = QRadioButton("Polygon")
        self.polygon_radio.toggled.connect(lambda: self.on_tool_changed("polygon"))
        self.tool_group.addButton(self.polygon_radio)
        tool_row.addWidget(self.polygon_radio)
        
        self.point_radio = QRadioButton("Point")
        self.point_radio.toggled.connect(lambda: self.on_tool_changed("point"))
        self.tool_group.addButton(self.point_radio)
        tool_row.addWidget(self.point_radio)
        
        self.threshold_radio = QRadioButton("Threshold")
        self.threshold_radio.toggled.connect(lambda: self.on_tool_changed("threshold"))
        self.tool_group.addButton(self.threshold_radio)
        tool_row.addWidget(self.threshold_radio)

        tool_row.addStretch()
        layout.addLayout(tool_row)

        # Row 2: Action and Operations (combined)
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        
        action_row.addWidget(QLabel("Action:"))
        
        self.mask_radio = QRadioButton("Mask")
        self.mask_radio.setChecked(True)
        self.mask_radio.setStyleSheet(f"""
            QRadioButton {{
                color: {self.colors['text_dark']};
            }}
            QRadioButton::indicator {{
                width: 12px;
                height: 12px;
            }}
        """)
        action_row.addWidget(self.mask_radio)
        
        self.unmask_radio = QRadioButton("Unmask")
        self.unmask_radio.setStyleSheet(f"""
            QRadioButton {{
                color: {self.colors['text_dark']};
            }}
            QRadioButton::indicator {{
                width: 12px;
                height: 12px;
            }}
        """)
        action_row.addWidget(self.unmask_radio)
        
        self.action_group = QButtonGroup(group)
        self.action_group.addButton(self.mask_radio)
        self.action_group.addButton(self.unmask_radio)
        
        # Separator
        action_row.addWidget(QLabel("|"))
        
        # Operations on same row
        action_row.addWidget(QLabel("Operations:"))
        
        # Invert button
        invert_btn = QPushButton("↕️ Invert")
        invert_btn.setFixedWidth(70)
        invert_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        invert_btn.clicked.connect(self.invert_mask)
        action_row.addWidget(invert_btn)
        
        # Grow button
        grow_btn = QPushButton("➕ Grow")
        grow_btn.setFixedWidth(65)
        grow_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        grow_btn.clicked.connect(self.grow_mask)
        action_row.addWidget(grow_btn)
        
        # Shrink button
        shrink_btn = QPushButton("➖ Shrink")
        shrink_btn.setFixedWidth(65)
        shrink_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        shrink_btn.clicked.connect(self.shrink_mask)
        action_row.addWidget(shrink_btn)
        
        # Fill holes button
        fill_btn = QPushButton("🔧 Fill")
        fill_btn.setFixedWidth(65)
        fill_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
            }}
        """)
        fill_btn.clicked.connect(self.fill_holes)
        action_row.addWidget(fill_btn)

        action_row.addStretch()
        layout.addLayout(action_row)

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

        # Canvas layout (no contrast slider)
        canvas_layout = QHBoxLayout()
        canvas_layout.addStretch()  # Center the canvas
        
        # Matplotlib canvas - Compact size
        self.figure = Figure(figsize=(7, 5))
        self.figure.subplots_adjust(left=0.10, right=0.98, top=0.96, bottom=0.12)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedSize(700, 500)  # Compact size to fit in one page
        canvas_layout.addWidget(self.canvas)
        
        canvas_layout.addStretch()  # Center the canvas
        
        layout.addLayout(canvas_layout)
        
        # Contrast value (fixed, no slider)
        self.contrast_value = 50  # Default contrast

        # Connect mouse events
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('key_press_event', self.on_key_press)

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
        """Load diffraction image for mask creation"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.root,
            "Select Diffraction Image",
            "",
            "Image Files (*.tif *.tiff *.edf *.h5 *.hdf5);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Load image based on file type
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.h5', '.hdf5']:
                import h5py
                with h5py.File(file_path, 'r') as f:
                    # Try common dataset paths
                    for path in ['entry/data/data', 'data', 'image']:
                        if path in f:
                            data = f[path]
                            if len(data.shape) == 3:
                                self.image_data = np.array(data[0, :, :])
                            else:
                                self.image_data = np.array(data[:, :])
                            break
            else:
                # Try fabio for other formats
                try:
                    import fabio
                    img = fabio.open(file_path)
                    self.image_data = img.data
                except:
                    # Fallback to pillow
                    from PIL import Image
                    img = Image.open(file_path)
                    self.image_data = np.array(img)

            if self.image_data is None:
                QMessageBox.warning(self.root, "Error", "Could not load image data")
                return

            # Initialize mask if not exists
            if self.current_mask is None:
                self.current_mask = np.zeros(self.image_data.shape, dtype=bool)

            # Update info
            self.file_info_label.setText(
                f"Image: {os.path.basename(file_path)} | Shape: {self.image_data.shape}"
            )

            self.update_display()

        except Exception as e:
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
        """Handle contrast slider change"""
        self.contrast_label.setText(f"{value}%")
        if self.image_data is not None:
            self.update_display()

    def update_display(self):
        """Update image and mask display - Full redraw"""
        if self.image_data is None:
            return

        self.ax.clear()

        # Apply log scale and contrast
        img_display = np.log10(self.image_data + 1)
        contrast_factor = self.contrast_value / 100.0
        low_percentile = contrast_factor * 20
        high_percentile = 100 - (1 - contrast_factor) * 5
        vmin = np.percentile(img_display, low_percentile)
        vmax = np.percentile(img_display, high_percentile)
        
        # Display image
        self.ax.imshow(img_display, cmap='viridis', origin='lower',
                      interpolation='nearest', vmin=vmin, vmax=vmax,
                      extent=[0, self.image_data.shape[1],
                             0, self.image_data.shape[0]])

        # Overlay mask if exists
        if self.current_mask is not None:
            mask_overlay = np.ma.masked_where(~self.current_mask, self.current_mask)
            self.ax.imshow(mask_overlay, cmap='Reds', alpha=0.3, origin='lower',
                          extent=[0, self.image_data.shape[1],
                                 0, self.image_data.shape[0]])

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
    
    def update_preview_only(self):
        """Fast preview update without full redraw - for mouse move"""
        if self.image_data is None:
            return
        
        # Remove old preview artists
        for artist in self.preview_artists:
            artist.remove()
        self.preview_artists = []
        
        # Draw new preview shapes
        if self.drawing and self.draw_start and self.draw_current:
            if self.draw_mode == 'circle':
                radius = np.sqrt((self.draw_current[0] - self.draw_start[0])**2 + 
                               (self.draw_current[1] - self.draw_start[1])**2)
                circle = Circle(self.draw_start, radius, fill=False, 
                              edgecolor='yellow', linewidth=2, linestyle='--', animated=True)
                self.ax.add_patch(circle)
                self.preview_artists.append(circle)
            
            elif self.draw_mode == 'rectangle':
                x1, y1 = self.draw_start
                x2, y2 = self.draw_current
                width = x2 - x1
                height = y2 - y1
                rect = Rectangle((x1, y1), width, height, fill=False,
                               edgecolor='yellow', linewidth=2, linestyle='--', animated=True)
                self.ax.add_patch(rect)
                self.preview_artists.append(rect)
        
        # Use blit for fast update
        self.canvas.draw_idle()

    def on_mouse_move(self, event):
        """Handle mouse move event"""
        if event.inaxes != self.ax or self.image_data is None:
            self.position_label.setText("Position: --")
            return

        x, y = int(event.xdata), int(event.ydata)
        self.position_label.setText(f"Position: ({x}, {y})")
        
        # Update drawing preview - optimized
        if self.drawing and self.draw_start is not None:
            self.draw_current = (x, y)
            self.update_preview_only()

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
        """Apply mask/unmask at a point"""
        if self.current_mask is None:
            return
        
        # Create circular region around point
        Y, X = np.ogrid[:self.current_mask.shape[0], :self.current_mask.shape[1]]
        dist = np.sqrt((X - x)**2 + (Y - y)**2)
        mask_region = dist <= radius
        
        # Apply mask or unmask
        if self.mask_radio.isChecked():
            self.current_mask[mask_region] = True
        else:
            self.current_mask[mask_region] = False
        
        self.update_display()
    
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
