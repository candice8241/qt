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
        
        # Drawing mode
        self.draw_mode = 'none'  # 'circle', 'rectangle', 'polygon', 'none'
        self.mask_shapes = []  # Store drawn shapes

    def setup_ui(self):
        """Setup UI components"""
        # Get or create layout for parent
        layout = self.parent.layout()
        if layout is None:
            layout = QVBoxLayout(self.parent)
            layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background-color: {self.colors['bg']}; border: none;")

        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {self.colors['bg']};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 10, 20, 10)
        content_layout.setSpacing(10)

        # Title
        title = QLabel("🎭 Mask Creation & Management")
        title.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.colors['primary']};")
        content_layout.addWidget(title)

        # Description
        desc = QLabel("Create, edit, and manage detector masks for diffraction data")
        desc.setStyleSheet(f"color: {self.colors['text_dark']}; font-size: 10pt;")
        content_layout.addWidget(desc)

        # Control area
        control_group = self.create_control_group()
        content_layout.addWidget(control_group)

        # Drawing tools
        tools_group = self.create_tools_group()
        content_layout.addWidget(tools_group)

        # Preview area
        if MATPLOTLIB_AVAILABLE:
            preview_group = self.create_preview_group()
            content_layout.addWidget(preview_group, stretch=1)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("💾 Save Mask")
        save_btn.setFixedWidth(120)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45A049;
            }}
        """)
        save_btn.clicked.connect(self.save_mask)
        button_layout.addWidget(save_btn)

        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.setFixedWidth(120)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF5252;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FF1744;
            }}
        """)
        clear_btn.clicked.connect(self.clear_mask)
        button_layout.addWidget(clear_btn)

        content_layout.addLayout(button_layout)
        
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

        layout.addStretch()
        
        # File info label
        self.file_info_label = QLabel("No image loaded")
        self.file_info_label.setStyleSheet("color: #666666; font-size: 9px;")
        layout.addWidget(self.file_info_label)

        return group
    
    def create_tools_group(self):
        """Create drawing tools group"""
        group = QGroupBox("Drawing Tools")
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
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Tool selector
        layout.addWidget(QLabel("Tool:"))
        
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(["Select", "Circle", "Rectangle", "Polygon", "Threshold"])
        self.tool_combo.setFixedWidth(120)
        self.tool_combo.currentTextChanged.connect(self.on_tool_changed)
        layout.addWidget(self.tool_combo)

        # Separator
        layout.addWidget(QLabel("|"))

        # Mask/Unmask radio
        layout.addWidget(QLabel("Action:"))
        
        self.action_combo = QComboBox()
        self.action_combo.addItems(["Mask Pixels", "Unmask Pixels"])
        self.action_combo.setFixedWidth(120)
        layout.addWidget(self.action_combo)

        layout.addStretch()

        # Apply button
        apply_btn = QPushButton("✓ Apply")
        apply_btn.setFixedWidth(90)
        apply_btn.setStyleSheet(f"""
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
        apply_btn.clicked.connect(self.apply_current_tool)
        layout.addWidget(apply_btn)

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

        # Canvas and contrast slider layout
        canvas_layout = QHBoxLayout()
        
        # Matplotlib canvas
        self.figure = Figure(figsize=(10, 8))
        self.figure.subplots_adjust(left=0.10, right=0.98, top=0.96, bottom=0.12)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(500)
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
        self.contrast_slider.setFixedHeight(350)
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
        
        layout.addLayout(canvas_layout)

        # Connect mouse events
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click)

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
            self,
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
                QMessageBox.warning(self, "Error", "Could not load image data")
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
            QMessageBox.critical(self, "Error", f"Failed to load image:\n{str(e)}")

    def load_mask(self):
        """Load existing mask file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
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
            QMessageBox.critical(self, "Error", f"Failed to load mask:\n{str(e)}")

    def save_mask(self):
        """Save current mask"""
        if self.current_mask is None:
            QMessageBox.warning(self, "Warning", "No mask to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
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
            QMessageBox.information(self, "Success", f"Mask saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save mask:\n{str(e)}")

    def clear_mask(self):
        """Clear current mask"""
        reply = QMessageBox.question(
            self, 'Confirm', 'Clear all mask regions?',
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

    def apply_current_tool(self):
        """Apply current drawing tool"""
        QMessageBox.information(self, "Info", f"Tool '{self.tool_combo.currentText()}' applied")

    def on_contrast_changed(self, value):
        """Handle contrast slider change"""
        self.contrast_label.setText(f"{value}%")
        if self.image_data is not None:
            self.update_display()

    def update_display(self):
        """Update image and mask display"""
        if self.image_data is None:
            return

        self.ax.clear()

        # Apply log scale and contrast
        img_display = np.log10(self.image_data + 1)
        contrast_factor = self.contrast_slider.value() / 100.0
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

        self.ax.set_xlim(0, self.image_data.shape[1])
        self.ax.set_ylim(0, self.image_data.shape[0])
        self.ax.set_xlabel('X (pixels)', fontsize=10)
        self.ax.set_ylabel('Y (pixels)', fontsize=10)
        self.ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        self.canvas.draw_idle()

    def on_mouse_move(self, event):
        """Handle mouse move event"""
        if event.inaxes != self.ax or self.image_data is None:
            self.position_label.setText("Position: --")
            return

        x, y = int(event.xdata), int(event.ydata)
        self.position_label.setText(f"Position: ({x}, {y})")

    def on_mouse_click(self, event):
        """Handle mouse click event for drawing"""
        if event.inaxes != self.ax or self.image_data is None:
            return

        # Implement drawing logic based on self.draw_mode
        # This is a placeholder for drawing functionality
        pass


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
