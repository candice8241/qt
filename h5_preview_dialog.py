#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
H5 Image Preview Dialog
Dialog for viewing diffraction images with azimuthal angles and radial information
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QGroupBox, QFileDialog, QMessageBox,
                              QLineEdit, QCheckBox, QSlider)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import numpy as np
import h5py
import os

# Import matplotlib for image display
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
    from matplotlib.patches import Wedge
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠ Warning: matplotlib not available. Image preview will be disabled.")


class H5PreviewDialog(QDialog):
    """H5 Image Preview Dialog with interactive sector drawing"""

    def __init__(self, parent=None, initial_file=None):
        super().__init__(parent)
        self.setWindowTitle("H5 Image Preview")
        self.setModal(False)  # Non-modal so user can interact with main window
        self.resize(1100, 1000)
        # Start maximized to ensure everything is visible
        self.showMaximized()

        # Color theme
        self.colors = {
            'primary': '#7C4DFF',
            'background': '#F5F5F5',
            'card_bg': '#FFFFFF',
            'border': '#CCCCCC',
            'text_dark': '#333333'
        }

        # Image data
        self.current_image = None
        self.center_x = None
        self.center_y = None
        self.h5_file_path = None

        # Mouse position data
        self.mouse_x = None
        self.mouse_y = None
        self.mouse_rad = None
        self.mouse_azim = None

        # Sector drawing parameters
        self.sector_azim_start = 0.0
        self.sector_azim_end = 90.0
        self.sector_rad_min = 0.0
        self.sector_rad_max = 0.0  # 0 = auto
        self.show_sector = False
        
        # Image display parameters
        self.contrast_factor = 0.5  # Default contrast (0-1)

        self.setup_ui()

        # Load initial file if provided
        if initial_file and os.path.exists(initial_file):
            self.load_h5_image(initial_file)

    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 8, 10, 8)

        # Control area
        control_group = self.create_control_group()
        layout.addWidget(control_group)

        # Image preview area
        if MATPLOTLIB_AVAILABLE:
            preview_group = self.create_preview_group()
            layout.addWidget(preview_group, stretch=1)  # Make preview area stretchable

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Use for Integration button
        use_btn = QPushButton("✓ Use for Integration")
        use_btn.setFixedWidth(160)
        use_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #45A049;
            }}
        """)
        use_btn.clicked.connect(self.use_for_integration)
        button_layout.addWidget(use_btn)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #6A1B9A;
            }}
        """)
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_control_group(self):
        """Create file control and sector drawing group"""
        group = QGroupBox("File Control & Sector Drawing Tool")
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 3px;
                font-weight: bold;
                padding-top: 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(3)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Row 1: All controls in horizontal layout
        main_row = QHBoxLayout()
        
        # Load button
        load_btn = QPushButton("📂 Load H5")
        load_btn.setFixedWidth(90)
        load_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: white;
                border: none;
                padding: 5px 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #6A1B9A;
            }}
        """)
        load_btn.clicked.connect(lambda: self.load_h5_image())
        main_row.addWidget(load_btn)
        
        # Separator
        main_row.addWidget(QLabel("|"))

        # Azimuthal range
        main_row.addWidget(QLabel("Azim:"))
        self.azim_start_input = QLineEdit("0")
        self.azim_start_input.setFixedWidth(60)
        self.azim_start_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_row.addWidget(self.azim_start_input)
        main_row.addWidget(QLabel("-"))
        self.azim_end_input = QLineEdit("90")
        self.azim_end_input.setFixedWidth(60)
        self.azim_end_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_row.addWidget(self.azim_end_input)
        main_row.addWidget(QLabel("°"))
        
        # Separator
        main_row.addWidget(QLabel("|"))

        # Radial range
        main_row.addWidget(QLabel("Radial:"))
        self.rad_min_input = QLineEdit("0")
        self.rad_min_input.setFixedWidth(60)
        self.rad_min_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_row.addWidget(self.rad_min_input)
        main_row.addWidget(QLabel("-"))
        self.rad_max_input = QLineEdit("0")
        self.rad_max_input.setFixedWidth(60)
        self.rad_max_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rad_max_input.setPlaceholderText("auto")
        main_row.addWidget(self.rad_max_input)
        main_row.addWidget(QLabel("px"))
        
        # Separator
        main_row.addWidget(QLabel("|"))

        # Draw button
        draw_btn = QPushButton("🎯 Draw")
        draw_btn.setFixedWidth(70)
        draw_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45A049;
            }}
        """)
        draw_btn.clicked.connect(self.draw_sector)
        main_row.addWidget(draw_btn)

        main_row.addStretch()
        layout.addLayout(main_row)
        
        # Row 2: File info
        self.file_info_label = QLabel("No image loaded")
        self.file_info_label.setStyleSheet("color: #666666; font-size: 9px;")
        self.file_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.file_info_label)

        return group
    
    def create_sector_drawing_group(self):
        """Deprecated - merged into create_control_group"""
        return None

    def create_preview_group(self):
        """Create image preview group"""
        group = QGroupBox("Image Preview (Use mouse wheel to zoom)")
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 3px;
                font-weight: bold;
                padding-top: 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(3)
        layout.setContentsMargins(5, 5, 5, 5)

        # Info row - Display mouse position information
        info_row = QHBoxLayout()

        self.position_label = QLabel("Position: --")
        self.position_label.setFont(QFont('Arial', 10))
        self.position_label.setStyleSheet("color: #333333;")
        info_row.addWidget(self.position_label)

        self.radial_label = QLabel("Radial: -- px")
        self.radial_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        self.radial_label.setStyleSheet("color: #FF5722;")
        info_row.addWidget(self.radial_label)

        self.azimuth_label = QLabel("Azimuth: --°")
        self.azimuth_label.setFont(QFont('Arial', 10))
        self.azimuth_label.setStyleSheet("color: #0D47A1;")
        info_row.addWidget(self.azimuth_label)

        info_row.addStretch()
        layout.addLayout(info_row)

        # Canvas and exposure slider layout
        canvas_layout = QHBoxLayout()
        
        # Matplotlib canvas
        self.figure = Figure(figsize=(10, 8))
        # Adjust subplot to reduce margins and ensure bottom is visible
        self.figure.subplots_adjust(left=0.10, right=0.98, top=0.96, bottom=0.12)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(500)
        canvas_layout.addWidget(self.canvas)
        
        # Vertical exposure slider on the right (Dioptas style)
        slider_layout = QVBoxLayout()
        slider_layout.setSpacing(2)
        slider_layout.addStretch()
        
        # Max label
        max_label = QLabel("High")
        max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_label.setStyleSheet("color: #666666; font-size: 9px;")
        slider_layout.addWidget(max_label)
        
        self.contrast_slider = QSlider(Qt.Orientation.Vertical)
        self.contrast_slider.setMinimum(1)
        self.contrast_slider.setMaximum(100)
        self.contrast_slider.setValue(50)  # 0.5 contrast
        self.contrast_slider.setTickInterval(10)
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
            QSlider::handle:vertical:pressed {
                background: #C0C0C0;
            }
        """)
        self.contrast_slider.valueChanged.connect(self.on_contrast_changed)
        slider_layout.addWidget(self.contrast_slider, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Min label
        min_label = QLabel("Low")
        min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        min_label.setStyleSheet("color: #666666; font-size: 9px;")
        slider_layout.addWidget(min_label)
        
        # Current value label
        self.contrast_label = QLabel("50%")
        self.contrast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.contrast_label.setFixedWidth(50)
        self.contrast_label.setStyleSheet("color: #333333; font-weight: bold; font-size: 11px; margin-top: 5px;")
        slider_layout.addWidget(self.contrast_label)
        
        contrast_text_label = QLabel("Contrast")
        contrast_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        contrast_text_label.setStyleSheet("color: #666666; font-size: 9px;")
        slider_layout.addWidget(contrast_text_label)
        
        slider_layout.addStretch()
        canvas_layout.addLayout(slider_layout)
        
        layout.addLayout(canvas_layout)

        # Connect mouse move event
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        # Connect scroll event for zoom
        self.canvas.mpl_connect('scroll_event', self.on_mouse_scroll)

        # Initial plot
        self.ax = self.figure.add_subplot(111)
        self.ax.text(0.5, 0.5, 'Load an H5 image to preview\nMove mouse to see radial distance\nUse mouse wheel to zoom',
                     ha='center', va='center', fontsize=14, color='gray')
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('on')
        self.canvas.draw()

        return group

    def load_h5_image(self, file_path=None):
        """Load H5 image"""
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select H5 Image File",
                "",
                "HDF5 Files (*.h5 *.hdf5);;All Files (*)"
            )

        if not file_path:
            return

        try:
            with h5py.File(file_path, 'r') as h5f:
                # Try common dataset paths
                dataset_paths = [
                    'entry/data/data',
                    'entry/instrument/detector/data',
                    'data',
                    'image'
                ]

                image_data = None
                used_path = None

                for path in dataset_paths:
                    try:
                        dataset = h5f[path]
                        if len(dataset.shape) >= 2:
                            # Handle multi-frame data (take first frame)
                            if len(dataset.shape) == 3:
                                image_data = dataset[0, :, :]
                            else:
                                image_data = dataset[:, :]
                            used_path = path
                            break
                    except KeyError:
                        continue

                if image_data is None:
                    # Try to find any 2D dataset
                    for name in h5f:
                        obj = h5f[name]
                        if isinstance(obj, h5py.Dataset) and len(obj.shape) >= 2:
                            if len(obj.shape) == 3:
                                image_data = obj[0, :, :]
                            else:
                                image_data = obj[:, :]
                            used_path = name
                            break

                if image_data is None:
                    QMessageBox.warning(self, "Error", "No valid 2D image dataset found in H5 file")
                    return

                self.current_image = np.array(image_data)
                self.h5_file_path = file_path

                # Calculate center (assume detector center is image center)
                self.center_y, self.center_x = (
                    self.current_image.shape[0] // 2,
                    self.current_image.shape[1] // 2
                )

                # Update info label
                self.file_info_label.setText(
                    f"File: {os.path.basename(file_path)} | "
                    f"Dataset: {used_path} | "
                    f"Shape: {self.current_image.shape} | "
                    f"Center: ({self.center_x}, {self.center_y})"
                )

                # Update display
                self.update_image_display()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load H5 file:\n{str(e)}")

    def update_image_display(self):
        """Update image display"""
        if self.current_image is None:
            return

        self.ax.clear()

        # Apply log scale for diffraction rings
        img_display = np.log10(self.current_image + 1)
        
        # Adjust contrast with percentile clipping based on contrast_factor
        # Higher contrast_factor = more dynamic range between background and rings
        low_percentile = self.contrast_factor * 20  # 0-20%
        high_percentile = 100 - (1 - self.contrast_factor) * 5  # 95-100%
        vmin = np.percentile(img_display, low_percentile)
        vmax = np.percentile(img_display, high_percentile)
        
        # Use extent to show full image boundaries
        self.ax.imshow(img_display, cmap='viridis', origin='lower',
                      interpolation='nearest', vmin=vmin, vmax=vmax,
                      extent=[0, self.current_image.shape[1],
                             0, self.current_image.shape[0]])

        # Add azimuthal angle markers
        self.draw_angle_markers()

        # Draw sector if enabled
        if self.show_sector:
            self.draw_sector_overlay()

        # Set axis to show full image with boundaries
        self.ax.set_xlim(0, self.current_image.shape[1])
        self.ax.set_ylim(0, self.current_image.shape[0])
        self.ax.set_xlabel('X (pixels)', fontsize=10)
        self.ax.set_ylabel('Y (pixels)', fontsize=10)

        # Enable grid to show boundaries
        self.ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        self.canvas.draw_idle()

    def draw_angle_markers(self):
        """Draw azimuthal angle markers"""
        # Function disabled - no markers drawn
        pass

    def draw_sector_overlay(self):
        """Draw sector overlay on image"""
        if self.center_x is None or self.center_y is None:
            return

        # Calculate max radius
        max_radius = min(
            self.center_x, self.center_y,
            self.current_image.shape[1] - self.center_x,
            self.current_image.shape[0] - self.center_y
        )

        # Get sector parameters
        rad_max = self.sector_rad_max if self.sector_rad_max > 0 else max_radius

        # Draw sector wedge with black outline, no fill
        wedge = Wedge((self.center_x, self.center_y), rad_max,
                     self.sector_azim_start, self.sector_azim_end,
                     width=rad_max - self.sector_rad_min,
                     facecolor='none', fill=False,
                     edgecolor='black', linewidth=1.5)
        self.ax.add_patch(wedge)

    def draw_sector(self):
        """Draw sector with current parameters"""
        try:
            # Parse input values
            self.sector_azim_start = float(self.azim_start_input.text())
            self.sector_azim_end = float(self.azim_end_input.text())
            self.sector_rad_min = float(self.rad_min_input.text())
            self.sector_rad_max = float(self.rad_max_input.text())

            # Validate
            if self.sector_azim_start >= self.sector_azim_end:
                QMessageBox.warning(self, "Error", "Azimuthal start must be less than end")
                return

            if self.sector_rad_min < 0:
                QMessageBox.warning(self, "Error", "Radial minimum must be >= 0")
                return

            if self.sector_rad_max != 0 and self.sector_rad_min >= self.sector_rad_max:
                QMessageBox.warning(self, "Error", "Invalid radial range")
                return

            # Enable display
            self.show_sector = True

            # Update display
            self.update_image_display()

        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter valid numbers")

    def on_mouse_move(self, event):
        """Handle mouse move event"""
        if event.inaxes != self.ax or self.current_image is None:
            self.position_label.setText("Position: --")
            self.radial_label.setText("Radial: -- px")
            self.azimuth_label.setText("Azimuth: --°")
            return

        # Get mouse position in data coordinates
        self.mouse_x = event.xdata
        self.mouse_y = event.ydata

        if self.mouse_x is None or self.mouse_y is None:
            return

        # Calculate radial distance from center
        if self.center_x is not None and self.center_y is not None:
            dx = self.mouse_x - self.center_x
            dy = self.mouse_y - self.center_y
            self.mouse_rad = np.sqrt(dx**2 + dy**2)

            # Calculate azimuthal angle (in degrees, 0° = right, counterclockwise)
            self.mouse_azim = np.degrees(np.arctan2(dy, dx))
            if self.mouse_azim < 0:
                self.mouse_azim += 360

            # Update labels
            self.position_label.setText(f"Position: ({int(self.mouse_x)}, {int(self.mouse_y)})")
            self.radial_label.setText(f"Radial: {self.mouse_rad:.1f} px")
            self.azimuth_label.setText(f"Azimuth: {self.mouse_azim:.1f}°")
        else:
            self.position_label.setText(f"Position: ({int(self.mouse_x)}, {int(self.mouse_y)})")
            self.radial_label.setText("Radial: -- px")
            self.azimuth_label.setText("Azimuth: --°")

    def on_mouse_scroll(self, event):
        """Handle mouse scroll event for zooming"""
        if event.inaxes != self.ax:
            return

        # Get current axis limits
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()

        xdata = event.xdata  # Mouse x position in data coordinates
        ydata = event.ydata  # Mouse y position in data coordinates

        if xdata is None or ydata is None:
            return

        # Zoom factor
        base_scale = 1.2
        if event.button == 'up':
            # Zoom in
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            # Zoom out
            scale_factor = base_scale
        else:
            return

        # Calculate new limits
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        self.ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])

        self.canvas.draw_idle()

    def on_contrast_changed(self, value):
        """Handle contrast slider change"""
        # Map slider value (1-100) to contrast factor (0.01-1.0)
        self.contrast_factor = value / 100.0
        self.contrast_label.setText(f"{value}%")
        
        # Update image display if image is loaded
        if self.current_image is not None:
            self.update_image_display()

    def use_for_integration(self):
        """Use selected sector parameters for integration"""
        if not self.show_sector:
            QMessageBox.warning(self, "Warning", "Please draw a sector first using the Draw button")
            return
        
        if self.h5_file_path is None:
            QMessageBox.warning(self, "Warning", "Please load an H5 file first")
            return
        
        # Accept dialog and return parameters
        self.accept()
    
    def get_sector_parameters(self):
        """Get current sector parameters"""
        return {
            'h5_file': self.h5_file_path,
            'azim_start': self.sector_azim_start,
            'azim_end': self.sector_azim_end,
            'rad_min': self.sector_rad_min,
            'rad_max': self.sector_rad_max,
            'center_x': self.center_x,
            'center_y': self.center_y
        }


# Test code
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    dialog = H5PreviewDialog()
    dialog.show()

    sys.exit(app.exec())