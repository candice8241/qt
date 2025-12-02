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
        self.draw_mode = 'circle'  # 'circle', 'rectangle', 'polygon', 'point', 'threshold'
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

        layout = QVBoxLayout(group)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Single row: Tools + Action
        all_row = QHBoxLayout()
        all_row.setSpacing(6)
        
        all_row.addWidget(QLabel("Tool:"))

        # Tool radio buttons
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        
        self.tool_group = QButtonGroup(group)
        
        self.circle_radio = QRadioButton("Circle")
        self.circle_radio.setChecked(True)
        self.circle_radio.setToolTip("Draw circular mask regions")
        self.circle_radio.toggled.connect(lambda: self.on_tool_changed("circle"))
        self.tool_group.addButton(self.circle_radio)
        all_row.addWidget(self.circle_radio)
        
        self.rect_radio = QRadioButton("Rectangle")
        self.rect_radio.setToolTip("Draw rectangular mask regions")
        self.rect_radio.toggled.connect(lambda: self.on_tool_changed("rectangle"))
        self.tool_group.addButton(self.rect_radio)
        all_row.addWidget(self.rect_radio)
        
        self.polygon_radio = QRadioButton("Polygon")
        self.polygon_radio.setToolTip("Draw polygon mask regions (right-click or Enter to finish)")
        self.polygon_radio.toggled.connect(lambda: self.on_tool_changed("polygon"))
        self.tool_group.addButton(self.polygon_radio)
        all_row.addWidget(self.polygon_radio)
        
        self.point_radio = QRadioButton("Point")
        self.point_radio.setToolTip("Click to mask/unmask individual points")
        self.point_radio.toggled.connect(lambda: self.on_tool_changed("point"))
        self.tool_group.addButton(self.point_radio)
        all_row.addWidget(self.point_radio)
        
        self.threshold_radio = QRadioButton("Threshold")
        self.threshold_radio.setToolTip("Mask pixels based on intensity threshold")
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

        all_row.addStretch()
        layout.addLayout(all_row)
        
        # Threshold controls row (only shown when threshold mode is active)
        threshold_row = QHBoxLayout()
        threshold_row.setSpacing(6)
        
        threshold_row.addWidget(QLabel("Threshold Value:"))
        
        self.threshold_input = QLineEdit()
        self.threshold_input.setFixedWidth(100)
        self.threshold_input.setPlaceholderText("e.g. 1000")
        self.threshold_input.setStyleSheet("""
            QLineEdit {
                padding: 4px;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
            }
        """)
        threshold_row.addWidget(self.threshold_input)
        
        self.threshold_range_label = QLabel("Range: 0 - N/A")
        self.threshold_range_label.setStyleSheet("color: #666666; font-size: 10px;")
        threshold_row.addWidget(self.threshold_range_label)
        
        apply_threshold_btn = QPushButton("Apply Threshold")
        apply_threshold_btn.setFixedWidth(120)
        apply_threshold_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 4px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #6A1B9A;
            }}
        """)
        apply_threshold_btn.clicked.connect(self.apply_threshold_mask)
        threshold_row.addWidget(apply_threshold_btn)
        
        threshold_row.addStretch()
        layout.addLayout(threshold_row)
        
        # Store threshold row widgets for show/hide
        self.threshold_controls = [self.threshold_input, self.threshold_range_label, apply_threshold_btn]
        # Initially hide threshold controls
        for widget in self.threshold_controls:
            widget.setVisible(False)

        return group

    def create_preview_group(self):
        """Create image preview group"""
        group = QGroupBox("🖼️ Mask Preview (Click/Drag to draw | Scroll to zoom)")
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
                color: {self.colors['primary']};
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Info row
        info_row = QHBoxLayout()

        self.position_label = QLabel("📍 Position: --")
        self.position_label.setFont(QFont('Arial', 10))
        self.position_label.setStyleSheet("color: #333333; padding: 3px;")
        info_row.addWidget(self.position_label)

        self.mask_status_label = QLabel("🔴 Mask: Not loaded")
        self.mask_status_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        self.mask_status_label.setStyleSheet("color: #FF5722; padding: 3px;")
        info_row.addWidget(self.mask_status_label)

        info_row.addStretch()
        layout.addLayout(info_row)

        # Main canvas layout - Image on left, Operations on right
        main_canvas_layout = QHBoxLayout()
        main_canvas_layout.setSpacing(10)
        
        # Left side: Canvas and contrast slider
        canvas_layout = QHBoxLayout()
        canvas_layout.setSpacing(5)
        
        # Matplotlib canvas - Larger size for better display
        self.figure = Figure(figsize=(10, 7))
        self.figure.subplots_adjust(left=0.07, right=0.98, top=0.97, bottom=0.07)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedSize(1000, 700)  # Larger canvas for better viewing
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
        
        main_canvas_layout.addLayout(canvas_layout)
        
        # Right side: Operations panel
        operations_panel = self.create_operations_panel()
        main_canvas_layout.addWidget(operations_panel)
        
        layout.addLayout(main_canvas_layout)

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
    
    def create_operations_panel(self):
        """Create operations panel for the right side"""
        panel = QGroupBox("Operations")
        panel.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 5px;
                font-weight: bold;
                padding-top: 8px;
                background-color: {self.colors['bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
        """)
        panel.setFixedWidth(180)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)
        
        # Title
        title = QLabel("Mask Operations")
        title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #333333;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Separator line
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("background-color: #CCCCCC;")
        layout.addWidget(separator1)
        
        # Invert button
        invert_btn = QPushButton("↕️ Invert Mask")
        invert_btn.setFixedHeight(40)
        invert_btn.setToolTip("Flip masked and unmasked regions")
        invert_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: #7E57C2;
                transform: scale(1.02);
            }}
            QPushButton:pressed {{
                background-color: #5E35B1;
            }}
        """)
        invert_btn.clicked.connect(self.invert_mask)
        layout.addWidget(invert_btn)
        
        layout.addSpacing(5)
        
        # Grow button
        grow_btn = QPushButton("➕ Grow (Dilate)")
        grow_btn.setFixedHeight(40)
        grow_btn.setToolTip("Expand mask regions by 1 pixel (morphological dilation)")
        grow_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: #45A049;
                transform: scale(1.02);
            }}
            QPushButton:pressed {{
                background-color: #388E3C;
            }}
        """)
        grow_btn.clicked.connect(self.grow_mask)
        layout.addWidget(grow_btn)
        
        # Shrink button
        shrink_btn = QPushButton("➖ Shrink (Erode)")
        shrink_btn.setFixedHeight(40)
        shrink_btn.setToolTip("Shrink mask regions by 1 pixel (morphological erosion)")
        shrink_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: #FB8C00;
                transform: scale(1.02);
            }}
            QPushButton:pressed {{
                background-color: #F57C00;
            }}
        """)
        shrink_btn.clicked.connect(self.shrink_mask)
        layout.addWidget(shrink_btn)
        
        # Fill holes button
        fill_btn = QPushButton("🔧 Fill Holes")
        fill_btn.setFixedHeight(40)
        fill_btn.setToolTip("Fill enclosed holes in masked regions")
        fill_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: #1E88E5;
                transform: scale(1.02);
            }}
            QPushButton:pressed {{
                background-color: #1976D2;
            }}
        """)
        fill_btn.clicked.connect(self.fill_holes)
        layout.addWidget(fill_btn)
        
        # Separator line
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #CCCCCC;")
        layout.addWidget(separator2)
        
        # Statistics section
        stats_title = QLabel("Mask Statistics")
        stats_title.setStyleSheet("font-size: 10pt; font-weight: bold; color: #333333;")
        stats_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stats_title)
        
        self.mask_stats_label = QLabel("No mask data")
        self.mask_stats_label.setStyleSheet("""
            color: #555555; 
            font-size: 9pt; 
            padding: 8px;
            background-color: #F5F5F5;
            border-radius: 3px;
        """)
        self.mask_stats_label.setWordWrap(True)
        self.mask_stats_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.mask_stats_label)
        
        # Help text
        layout.addStretch()
        help_text = QLabel("💡 Tip:\nUse scroll wheel\nto zoom in/out")
        help_text.setStyleSheet("color: #888888; font-size: 9pt; font-style: italic;")
        help_text.setWordWrap(True)
        help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(help_text)
        
        return panel

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
            
            # Update threshold range
            self.threshold_range_label.setText(
                f"Range: 0 - {self.image_data.max():.1f}"
            )
            
            # Update mask status
            self.mask_status_label.setText("🟢 Mask: Active (empty)")
            self.mask_status_label.setStyleSheet("color: #4CAF50; padding: 3px; font-weight: bold;")

            # Display with caching
            self.update_display(force_recalc=True)
            self.update_mask_statistics()
            
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
            self.mask_status_label.setText(f"🟢 Mask: {os.path.basename(file_path)}")
            self.mask_status_label.setStyleSheet("color: #4CAF50; padding: 3px; font-weight: bold;")
            
            self.update_display()
            self.update_mask_statistics()

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
                self.update_display()
                self.update_mask_statistics()

    def on_tool_changed(self, tool_name):
        """Handle tool selection change"""
        self.draw_mode = tool_name.lower()
        # Reset drawing state
        self.drawing = False
        self.draw_start = None
        self.draw_current = None
        self.polygon_points = []
        self.temp_shape = None
        
        # Show/hide threshold controls based on mode
        is_threshold_mode = (self.draw_mode == 'threshold')
        for widget in self.threshold_controls:
            widget.setVisible(is_threshold_mode)
        
        if self.image_data is not None:
            self.update_display()
    
    def update_mask_statistics(self):
        """Update mask statistics display"""
        if self.current_mask is None or self.image_data is None:
            self.mask_stats_label.setText("No mask data")
            return
        
        total_pixels = self.current_mask.size
        masked_pixels = np.sum(self.current_mask)
        masked_percent = (masked_pixels / total_pixels) * 100
        
        stats_text = f"""Total: {total_pixels:,} px
Masked: {masked_pixels:,} px
Percentage: {masked_percent:.2f}%
Unmasked: {total_pixels - masked_pixels:,} px"""
        
        self.mask_stats_label.setText(stats_text)
    
    def invert_mask(self):
        """Invert the mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to invert")
            return
        
        self.current_mask = ~self.current_mask
        self.update_display()
        self.update_mask_statistics()
    
    def grow_mask(self):
        """Grow (dilate) the mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to grow")
            return
        
        if not np.any(self.current_mask):
            QMessageBox.warning(self.root, "Warning", "Mask is empty. Nothing to grow.")
            return
        
        try:
            from scipy import ndimage
            old_count = np.sum(self.current_mask)
            self.current_mask = ndimage.binary_dilation(self.current_mask, iterations=1)
            new_count = np.sum(self.current_mask)
            self.update_display()
            self.update_mask_statistics()
            print(f"Mask grown: {old_count} → {new_count} pixels (+{new_count - old_count})")
        except ImportError:
            QMessageBox.warning(self.root, "Warning", 
                              "scipy not available for mask operations.\nPlease install: pip install scipy")
    
    def shrink_mask(self):
        """Shrink (erode) the mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to shrink")
            return
        
        if not np.any(self.current_mask):
            QMessageBox.warning(self.root, "Warning", "Mask is empty. Nothing to shrink.")
            return
        
        try:
            from scipy import ndimage
            old_count = np.sum(self.current_mask)
            self.current_mask = ndimage.binary_erosion(self.current_mask, iterations=1)
            new_count = np.sum(self.current_mask)
            self.update_display()
            self.update_mask_statistics()
            print(f"Mask shrunk: {old_count} → {new_count} pixels (-{old_count - new_count})")
        except ImportError:
            QMessageBox.warning(self.root, "Warning", 
                              "scipy not available for mask operations.\nPlease install: pip install scipy")
    
    def fill_holes(self):
        """Fill holes in the mask"""
        if self.current_mask is None:
            QMessageBox.warning(self.root, "Warning", "No mask to fill")
            return
        
        if not np.any(self.current_mask):
            QMessageBox.warning(self.root, "Warning", "Mask is empty. Nothing to fill.")
            return
        
        try:
            from scipy import ndimage
            old_count = np.sum(self.current_mask)
            self.current_mask = ndimage.binary_fill_holes(self.current_mask)
            new_count = np.sum(self.current_mask)
            self.update_display()
            self.update_mask_statistics()
            if new_count > old_count:
                print(f"Holes filled: {old_count} → {new_count} pixels (+{new_count - old_count})")
            else:
                print("No holes found to fill")
        except ImportError:
            QMessageBox.warning(self.root, "Warning", 
                              "scipy not available for mask operations.\nPlease install: pip install scipy")

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
        if self.current_mask is not None and np.any(self.current_mask):
            from matplotlib.colors import ListedColormap
            # Create pure red colormap #FF0000
            # Index 0 = transparent (False), Index 1 = red (True)
            pure_red = ListedColormap([(0, 0, 0, 0), (1, 0, 0, 1)])  # RGBA
            
            # Use mask directly as image data (0=False=transparent, 1=True=red)
            mask_display = self.current_mask.astype(np.uint8)
            self.mask_artist = self.ax.imshow(mask_display, cmap=pure_red, alpha=0.7, 
                                             origin='lower',
                                             extent=[0, self.image_data.shape[1],
                                                    0, self.image_data.shape[0]], 
                                             interpolation='nearest', 
                                             vmin=0, vmax=1,  # Map 0->transparent, 1->red
                                             zorder=10)

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
        pure_red = ListedColormap([(0, 0, 0, 0), (1, 0, 0, 1)])  # RGBA
        
        # Use mask directly as image data (0=False=transparent, 1=True=red)
        mask_display = self.current_mask.astype(np.uint8)
        self.mask_artist = self.ax.imshow(mask_display, cmap=pure_red, alpha=0.7, 
                                          origin='lower',
                                          extent=[0, self.image_data.shape[1],
                                                 0, self.image_data.shape[0]],
                                          interpolation='nearest',
                                          vmin=0, vmax=1,  # Map 0->transparent, 1->red
                                          zorder=10)
        
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
                self.update_mask_statistics()
            return
        
        if event.button != 1:  # Only left click for drawing
            return
        
        if self.draw_mode == 'point':
            # Immediately apply point mask
            self.apply_point_mask(x, y, radius=5)
        
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
        self.update_mask_statistics()
    
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
        self.update_mask_statistics()
    
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
            QMessageBox.warning(self.root, "Warning", "Please load an image first")
            return
        
        # Get threshold value from input
        try:
            threshold = float(self.threshold_input.text())
        except ValueError:
            QMessageBox.warning(self.root, "Warning", "Please enter a valid threshold value")
            return
        
        # Validate threshold
        if threshold < 0 or threshold > self.image_data.max():
            QMessageBox.warning(self.root, "Warning", 
                              f"Threshold must be between 0 and {self.image_data.max():.1f}")
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
        self.update_mask_statistics()
        QMessageBox.information(self.root, "Success", 
                               f"Threshold mask applied: {np.sum(threshold_region)} pixels affected")
    
    def on_key_press(self, event):
        """Handle key press events"""
        if event.key == 'enter' or event.key == 'escape':
            # Finish polygon
            if self.draw_mode == 'polygon' and len(self.polygon_points) >= 3:
                self.apply_polygon_mask()
                self.update_display()
                self.update_mask_statistics()
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