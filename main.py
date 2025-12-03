# -*- coding: utf-8 -*-
"""
Main GUI Application
XRD Data Post-Processing Suite - Entry point and main window
"""

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout,
                              QHBoxLayout, QFrame, QScrollArea, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
import sys
import os
from theme_module import GUIBase, ModernButton, ModernTab, CuteSheepProgressBar
from mask_module import MaskModule
from powder_module import PowderXRDModule
from radial_module import AzimuthalIntegrationModule
from single_crystal_module import SingleCrystalModule
from bcdi_cal_module import BCDICalModule
from dioptas_module import DioptasModule
from auto_fitting_module import AutoFittingModule


class XRDProcessingGUI(QMainWindow, GUIBase):
    """Main GUI application for XRD data processing"""

    def __init__(self):
        """Initialize main GUI"""
        QMainWindow.__init__(self)
        GUIBase.__init__(self)

        # Hide the window while heavy UI construction occurs to avoid visible flashes
        self.hide()

        # Set window close behavior
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        
        #self.setWindowTitle("XRD Data Post-Processing")
        self.setGeometry(100, 100, 1100, 950)

        # Try to set icon
        try:
            icon_path = r'D:\HEPS\ID31\dioptas_data\github_felicity\batch\\HP_full_package\ChatGPT Image.ico'
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")

        # Set background color
        self.setStyleSheet(f"background-color: {self.colors['bg']};")

        # Initialize modules
        self.mask_module = None
        self.powder_module = None
        self.radial_module = None
        self.single_crystal_module = None
        self.bcdi_cal_module = None
        self.dioptas_module = None
        self.auto_fitting_module = None
        self.batch_module = None

        # Containers for each module (prebuilt and stacked to avoid flicker)
        self.module_frames = {
            "mask": None,
            "powder": None,
            "single": None,
            "radial": None,
            "bcdi_cal": None,
            "dioptas": None,
            "auto_fitting": None,
            "batch": None
        }
        
        # Tool windows (embedded in right panel)
        self.interactive_fitting_window = None
        self.interactive_eos_window = None
        self.current_view = "powder"  # Track current view (module name or "curvefit", "EOSfit")

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Setup UI
        self.setup_ui(main_layout)

    def setup_ui(self, main_layout):
        """Setup main user interface with left sidebar"""
        # Header section - removed per user request
        # header_frame = QFrame()
        # header_frame.setFixedHeight(70)
        # header_frame.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        # header_layout = QVBoxLayout(header_frame)
        # header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #
        # header_content = QWidget()
        # header_content_layout = QHBoxLayout(header_content)
        # header_content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # header_content_layout.setContentsMargins(0, 0, 0, 0)
        #
        # # Emoji
        # emoji_label = QLabel("", header_content)
        # emoji_label.setFont(QFont('Segoe UI Emoji', 24))
        # emoji_label.setStyleSheet(f"background-color: {self.colors['card_bg']};")
        # header_content_layout.addWidget(emoji_label)
        #
        # # Title
        # title_label = QLabel("XRD Data Post_Processing", header_content)
        # title_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        # title_label.setStyleSheet(f"background-color: {self.colors['card_bg']}; color: {self.colors['text_dark']};")
        # header_content_layout.addWidget(title_label)
        #
        # header_layout.addWidget(header_content)
        # main_layout.addWidget(header_frame)

        # Main content area with left sidebar
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # LEFT SIDEBAR - Navigation
        sidebar_frame = QFrame()
        sidebar_frame.setFixedWidth(140)
        sidebar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card_bg']};
                border-right: 2px solid {self.colors['border']};
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Create navigation buttons (store references for state management)
        self.mask_btn = self.create_sidebar_button("🎭  Mask", lambda: self.switch_tab("mask"), is_active=False)
        sidebar_layout.addWidget(self.mask_btn)
        
        self.powder_btn = self.create_sidebar_button("⚗️  Batch Int.", lambda: self.switch_tab("powder"), is_active=True)
        sidebar_layout.addWidget(self.powder_btn)

        # Hidden buttons - SC and Radial Int
        # self.radial_btn = self.create_sidebar_button("🔄  Radial Int.", lambda: self.switch_tab("radial"), is_active=False)
        # sidebar_layout.addWidget(self.radial_btn)
        #
        # self.single_btn = self.create_sidebar_button("🔬  SC", lambda: self.switch_tab("single"), is_active=False)
        # sidebar_layout.addWidget(self.single_btn)

        self.bcdi_cal_btn = self.create_sidebar_button("🔬  BCDI Cal.", lambda: self.switch_tab("bcdi_cal"), is_active=False)
        sidebar_layout.addWidget(self.bcdi_cal_btn)

        self.dioptas_btn = self.create_sidebar_button("💎  Dioptas", lambda: self.switch_tab("dioptas"), is_active=False)
        sidebar_layout.addWidget(self.dioptas_btn)

        # Auto Fitting button
        self.auto_fitting_btn = self.create_sidebar_button("🔍  Auto Fit", lambda: self.switch_tab("auto_fitting"), is_active=False)
        sidebar_layout.addWidget(self.auto_fitting_btn)

        # Batch Fitting button (standalone)
        self.batch_btn = self.create_sidebar_button("📊  Batch", self.open_batch, is_active=False)
        sidebar_layout.addWidget(self.batch_btn)

        # Curve Fitting button (hidden)
        # self.curvefit_btn = self.create_sidebar_button("📈  curvefit", self.open_curvefit, is_active=False)
        # sidebar_layout.addWidget(self.curvefit_btn)

        # EOS Fitting button
        self.EOSfit_btn = self.create_sidebar_button("📊  eosfit", self.open_EOSfit, is_active=False)
        sidebar_layout.addWidget(self.EOSfit_btn)

        sidebar_layout.addStretch()

        # Add sidebar to content layout
        content_layout.addWidget(sidebar_frame)

        # RIGHT SIDE - Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet(f"background-color: {self.colors['bg']}; border: none;")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Disable vertical scrollbar for Interactive Fitting GUI (去掉右侧滚动条)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create scrollable widget
        self.scrollable_widget = QWidget()
        self.scrollable_layout = QVBoxLayout(self.scrollable_widget)
        self.scrollable_layout.setContentsMargins(20, 10, 20, 10)
        self.scrollable_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(self.scrollable_widget)
        content_layout.addWidget(scroll_area)

        main_layout.addWidget(content_container)
        
        # Prebuild powder module immediately (before showing window) to avoid flash
        powder_frame = self._ensure_frame("powder")
        self.powder_module = PowderXRDModule(powder_frame, self)
        self.powder_module.setup_ui()
        # Don't call show() yet - will show when main window is shown
        
        # Update UI to reflect powder as active
        self.update_sidebar_buttons("powder")
        self.current_view = "powder"

        # Prebuild other modules in background after UI is shown
        QTimer.singleShot(100, self.prebuild_modules)

        # Prebuild interactive windows in background to avoid flash on first open
        QTimer.singleShot(200, self.prebuild_interactive_windows)

        # Warm up any heavy interactive windows once the loop starts
        QTimer.singleShot(300, self._warm_interactive_windows)
    
    def closeEvent(self, event):
        """Handle window close event to ensure proper cleanup"""
        try:
            # Close all tool windows (these are QWidgets)
            if hasattr(self, 'interactive_fitting_window') and self.interactive_fitting_window is not None:
                try:
                    self.interactive_fitting_window.close()
                    self.interactive_fitting_window.deleteLater()
                except:
                    pass
            
            if hasattr(self, 'interactive_eos_window') and self.interactive_eos_window is not None:
                try:
                    self.interactive_eos_window.close()
                    self.interactive_eos_window.deleteLater()
                except:
                    pass
            
            # Clean up module frames (not the modules themselves, as they may not be QObjects)
            for frame_name, frame in self.module_frames.items():
                if frame is not None:
                    try:
                        frame.close()
                        frame.deleteLater()
                    except:
                        pass
            
            # Clear matplotlib figures to prevent memory leaks
            import matplotlib.pyplot as plt
            plt.close('all')
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        event.accept()

    def create_sidebar_button(self, text, callback, is_active=False):
        """Create a sidebar navigation button"""
        button = QPushButton(text)
        button.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        button.setFixedHeight(45)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if is_active:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['primary']};
                    color: black;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['primary_hover']};
                }}
            """)
        else:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #DBE3F9;
                    color: {self.colors['text_dark']};
                    border: 1px solid {self.colors['border']};
                    border-radius: 8px;
                    padding: 10px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['light_purple']};
                    border: 1px solid {self.colors['primary']};
                }}
            """)
        
        button.clicked.connect(callback)
        return button

    def open_batch(self):
        """Open batch processing module (same as switch_tab)"""
        self.switch_tab("batch")

    def open_curvefit(self):
        """Open curve fitting (Interactive Fitting) window"""
        # Hide all module frames
        for frame in self.module_frames.values():
            if frame is not None:
                frame.hide()
        
        # Hide other tool windows
        if self.interactive_eos_window is not None:
            self.interactive_eos_window.hide()
        
        # Show interactive fitting window (should already exist from prebuild)
        if self.interactive_fitting_window is None:
            # Fallback: create on demand if prebuild didn't happen
            from interactive_fitting_gui import InteractiveFittingGUI
            self.interactive_fitting_window = InteractiveFittingGUI(self.scrollable_widget)
            self.interactive_fitting_window.hide()
            self.scrollable_layout.addWidget(self.interactive_fitting_window)
        
        # Simply show the prebuilt window
        self.interactive_fitting_window.show()
        self.current_view = "curvefit"
        
        # Update sidebar to show curve fitting is active
        self.update_sidebar_buttons("curvefit")

    def open_EOSfit(self):
        """Open EOS fitting window"""
        # Hide all module frames
        for frame in self.module_frames.values():
            if frame is not None:
                frame.hide()
        
        # Hide other tool windows
        if self.interactive_fitting_window is not None:
            self.interactive_fitting_window.hide()
        
        # Show EOS fitting window (should already exist from prebuild)
        if self.interactive_eos_window is None:
            # Fallback: create on demand if prebuild didn't happen
            try:
                from interactive_eos_gui import InteractiveEoSGUI
                self.interactive_eos_window = InteractiveEoSGUI(self.scrollable_widget)
                self.interactive_eos_window.hide()
                self.scrollable_layout.addWidget(self.interactive_eos_window)
            except ImportError as e:
                QMessageBox.warning(self, "Warning", f"EOS Fitting GUI not available:\n{str(e)}")
                return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create EOS Fitting GUI:\n{str(e)}")
                return
        
        # Simply show the prebuilt window
        self.interactive_eos_window.show()
        self.current_view = "eosfit"
        
        # Update sidebar to show EOS fitting is active
        self.update_sidebar_buttons("eosfit")

    def update_sidebar_buttons(self, active_tab):
        """Update sidebar button styles based on active tab (None = no active module)"""
        buttons = {
            "mask": self.mask_btn,
            "powder": self.powder_btn,
            # "radial": self.radial_btn,  # Hidden
            # "single": self.single_btn,  # Hidden
            "bcdi_cal": self.bcdi_cal_btn,
            "dioptas": self.dioptas_btn,
            "auto_fitting": self.auto_fitting_btn,
            "batch": self.batch_btn,
            # "curvefit": self.curvefit_btn,  # Hidden
            "eosfit": self.EOSfit_btn
        }
        
        for tab_name, button in buttons.items():
            is_active = (active_tab is not None and tab_name == active_tab)
            if is_active:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['primary']};
                        color: white;
                        border: none;
                        border-radius: 8px;
                        padding: 10px;
                        text-align: left;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {self.colors['primary_hover']};
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #DBE3F9;
                        color: {self.colors['text_dark']};
                        border: 1px solid {self.colors['border']};
                        border-radius: 8px;
                        padding: 10px;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        background-color: {self.colors['light_purple']};
                        border: 1px solid {self.colors['primary']};
                    }}
                """)
    
    def update_tool_buttons(self, active_tool):
        """Update tool button styles based on active tool - now handled by update_sidebar_buttons"""
        # This method is kept for compatibility but functionality moved to update_sidebar_buttons
        pass

    def _warm_interactive_windows(self):
        """Ensure interactive secondary windows are prebuilt after startup."""
        try:
            if self.powder_module is not None:
                self.powder_module.prebuild_interactive_windows(force=True)
        except Exception:
            pass

    def _ensure_frame(self, name):
        """Ensure a frame exists for the given module"""
        if self.module_frames[name] is None:
            frame = QWidget(self.scrollable_widget)
            frame.setStyleSheet(f"background-color: {self.colors['bg']};")
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(0, 0, 0, 0)
            self.scrollable_layout.addWidget(frame)
            self.module_frames[name] = frame
        frame = self.module_frames[name]

        # Ensure a layout always exists in case an external caller removed it
        if frame.layout() is None:
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(0, 0, 0, 0)

        return frame

    def prebuild_modules(self):
        """Construct all module frames and their UIs ahead of first use to avoid initial flash."""
        # Prebuild mask module
        mask_frame = self._ensure_frame("mask")
        if self.mask_module is None:
            self.mask_module = MaskModule(mask_frame, self)
            self.mask_module.setup_ui()
        mask_frame.hide()  # Ensure hidden after prebuild
        
        # Only prebuild non-active modules in background
        radial_frame = self._ensure_frame("radial")
        if self.radial_module is None:
            self.radial_module = AzimuthalIntegrationModule(radial_frame, self)
            self.radial_module.setup_ui()
        radial_frame.hide()  # Ensure hidden after prebuild

        single_frame = self._ensure_frame("single")
        if self.single_crystal_module is None:
            self.single_crystal_module = SingleCrystalModule(single_frame, self)
            self.single_crystal_module.setup_ui()
        single_frame.hide()  # Ensure hidden after prebuild
        
        bcdi_cal_frame = self._ensure_frame("bcdi_cal")
        if self.bcdi_cal_module is None:
            self.bcdi_cal_module = BCDICalModule(bcdi_cal_frame, self)
            self.bcdi_cal_module.setup_ui()
        bcdi_cal_frame.hide()  # Ensure hidden after prebuild
        
        dioptas_frame = self._ensure_frame("dioptas")
        if self.dioptas_module is None:
            self.dioptas_module = DioptasModule(dioptas_frame, self)
            self.dioptas_module.setup_ui()
        dioptas_frame.hide()  # Ensure hidden after prebuild
        
        auto_fitting_frame = self._ensure_frame("auto_fitting")
        if self.auto_fitting_module is None:
            self.auto_fitting_module = AutoFittingModule()
            auto_fitting_frame.layout().addWidget(self.auto_fitting_module)
        auto_fitting_frame.hide()  # Ensure hidden after prebuild
        
        batch_frame = self._ensure_frame("batch")
        if self.batch_module is None:
            from batch_fitting_dialog import BatchFittingDialog
            self.batch_module = BatchFittingDialog(batch_frame)
            # Add generous margins to the frame layout for border visibility
            batch_frame.layout().setContentsMargins(0, 0, 15, 0)  # Extra right margin
            batch_frame.layout().addWidget(self.batch_module)
        batch_frame.hide()  # Ensure hidden after prebuild
    
    def prebuild_interactive_windows(self):
        """Prebuild interactive tool windows in background to avoid flash on first open"""
        try:
            # Prebuild curve fitting window
            if self.interactive_fitting_window is None:
                from interactive_fitting_gui import InteractiveFittingGUI
                self.interactive_fitting_window = InteractiveFittingGUI(self.scrollable_widget)
                self.interactive_fitting_window.hide()  # Keep hidden
                self.scrollable_layout.addWidget(self.interactive_fitting_window)
            
            # Prebuild EOS fitting window
            if self.interactive_eos_window is None:
                from interactive_eos_gui import InteractiveEoSGUI
                self.interactive_eos_window = InteractiveEoSGUI(self.scrollable_widget)
                self.interactive_eos_window.hide()  # Keep hidden
                self.scrollable_layout.addWidget(self.interactive_eos_window)
        except Exception as e:
            print(f"Note: Interactive windows will be created on demand: {e}")

    def switch_tab(self, tab_name):
        """
        Switch between main tabs

        Args:
            tab_name: Name of tab to switch to ('powder', 'single', 'radial', 'bcdi_cal')
        """
        # Hide tool windows
        if self.interactive_fitting_window is not None:
            self.interactive_fitting_window.hide()
        if self.interactive_eos_window is not None:
            self.interactive_eos_window.hide()
        
        # Update sidebar button styles
        self.update_sidebar_buttons(tab_name)

        # Hide all module frames
        for frame in self.module_frames.values():
            if frame is not None:
                frame.hide()

        # Show appropriate module
        target_frame = None
        if tab_name == "mask":
            target_frame = self._ensure_frame("mask")
            if self.mask_module is None:
                self.mask_module = MaskModule(target_frame, self)
                self.mask_module.setup_ui()
        
        elif tab_name == "powder":
            target_frame = self._ensure_frame("powder")
            if self.powder_module is None:
                self.powder_module = PowderXRDModule(target_frame, self)
                self.powder_module.setup_ui()
                try:
                    self.powder_module.prebuild_interactive_windows()
                except AttributeError:
                    pass

        elif tab_name == "radial":
            target_frame = self._ensure_frame("radial")
            if self.radial_module is None:
                self.radial_module = AzimuthalIntegrationModule(target_frame, self)
                self.radial_module.setup_ui()

        elif tab_name == "single":
            target_frame = self._ensure_frame("single")
            if self.single_crystal_module is None:
                self.single_crystal_module = SingleCrystalModule(target_frame, self)
                self.single_crystal_module.setup_ui()

        elif tab_name == "bcdi_cal":
            target_frame = self._ensure_frame("bcdi_cal")
            if self.bcdi_cal_module is None:
                self.bcdi_cal_module = BCDICalModule(target_frame, self)
                self.bcdi_cal_module.setup_ui()

        elif tab_name == "dioptas":
            target_frame = self._ensure_frame("dioptas")
            if self.dioptas_module is None:
                self.dioptas_module = DioptasModule(target_frame, self)
                self.dioptas_module.setup_ui()

        elif tab_name == "auto_fitting":
            target_frame = self._ensure_frame("auto_fitting")
            if self.auto_fitting_module is None:
                self.auto_fitting_module = AutoFittingModule()
                target_frame.layout().addWidget(self.auto_fitting_module)

        elif tab_name == "batch":
            target_frame = self._ensure_frame("batch")
            if self.batch_module is None:
                from batch_fitting_dialog import BatchFittingDialog
                self.batch_module = BatchFittingDialog(target_frame)
                # Add generous margins to the frame layout for border visibility
                target_frame.layout().setContentsMargins(0, 0, 15, 0)  # Extra right margin
                target_frame.layout().addWidget(self.batch_module)

        if target_frame is not None:
            target_frame.show()
        
        self.current_view = tab_name


def _ensure_app_icon(app):
    """Set the application icon if the file exists."""
    icon_path = r"D:\HEPS\ID31\dioptas_data\github_felicity\batch\\HP_full_package\ChatGPT Image.ico"
    if os.path.exists(icon_path):
        try:
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)
        except Exception as e:
            print(f"Failed to set icon: {e}")
    else:
        print("Icon file not found!")


def launch_main_app():
    """Launch the main application window, reusing an existing QApplication when possible."""
    # Always create a fresh QApplication instance to avoid state issues
    app = QApplication.instance()
    if app is not None:
        # Clean up existing instance
        app.quit()
        app = None
    
    app = QApplication(sys.argv)
    
    # Set application-wide attributes for better compatibility
    app.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    app.setQuitOnLastWindowClosed(True)

    _ensure_app_icon(app)

    # Apply shared checkbox and radio indicator styling
    GUIBase().apply_indicator_styles(app)

    # Keep a reference on the application to avoid premature garbage collection
    window = XRDProcessingGUI()
    app.main_window = window
    
    # Ensure proper cleanup on close
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    
    # Show powder frame explicitly before showing main window
    if window.module_frames["powder"] is not None:
        window.module_frames["powder"].show()
    
    # Show maximized window after complete initialization
    window.showMaximized()

    # Start event loop
    sys.exit(app.exec())


class StartupWindow(QWidget):
    """Startup splash screen with progress animation"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading...")

        # Set custom icon
        icon_path = r"D:\HEPS\ID31\dioptas_data\github_felicity\batch\HP_full_package\ChatGPT Image.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Window style
        window_width = 480
        window_height = 220

        # Center window on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2

        self.setGeometry(x, y, window_width, window_height)
        self.setStyleSheet("background-color: #fbeaff;")
        self.setFixedSize(window_width, window_height)

        # Layout
        layout = QVBoxLayout(self)

        # Title
        self.title_label = QLabel("Starting up, please wait...", self)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #ab47bc; background-color: #fbeaff;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Percentage label
        self.percent_label = QLabel("0%", self)
        self.percent_label.setFont(QFont("Arial", 10))
        self.percent_label.setStyleSheet("color: #9c27b0; background-color: #fbeaff;")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percent_label)

        # Progress bar with sheep
        self.progress_bar = CuteSheepProgressBar(width=400, height=60, parent=self)
        self.progress_bar.setStyleSheet("background-color: #fbeaff;")
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Draw track for progress bar
        self.track_widget = QWidget(self)
        self.track_widget.setFixedSize(400, 60)
        self.track_widget.setStyleSheet("""
            background-color: #f3cfe2;
            border: 2px solid #d8b4e2;
            border-radius: 15px;
        """)
        # Place track behind progress bar
        self.track_widget.lower()

        self.progress = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_progress)

    def start_animation(self):
        """Start the progress animation"""
        self.progress_bar.start()
        self.timer.start(35)  # Update every 35ms

    def animate_progress(self):
        """Animate progress bar"""
        if self.progress <= 100:
            # Update percentage
            self.percent_label.setText(f"{self.progress}%")

            # Update title with fun messages at milestones
            if self.progress == 20:
                self.title_label.setText("Loading modules... 🌸")
            elif self.progress == 40:
                self.title_label.setText("Setting up workspace... 💜")
            elif self.progress == 60:
                self.title_label.setText("Almost there, sweetheart! 💖")
            elif self.progress == 80:
                self.title_label.setText("Final touches... ✨")
            elif self.progress == 100:
                self.title_label.setText("Ready to go! 🎉")

            self.progress += 2
        else:
            # Finish animation
            self.timer.stop()
            self.progress_bar.stop()
            QTimer.singleShot(100, self.launch_main)

    def launch_main(self):
        """Close splash and launch main app"""
        self.close()
        launch_main_app()


def show_startup_window():
    """Show startup window with progress animation"""
    app = QApplication(sys.argv)
    _ensure_app_icon(app)

    splash = StartupWindow()
    splash.show()
    splash.start_animation()

    # Avoid raising SystemExit in interactive environments (e.g., notebooks).
    app.exec()


if __name__ == "__main__":
    # Ensure clean startup
    import matplotlib
    matplotlib.use('QtAgg')  # Set backend before any plotting
    launch_main_app()  # Directly launch main app without startup animation


def main():
    """Main application entry point"""
    import matplotlib
    matplotlib.use('QtAgg')  # Set backend before any plotting
    launch_main_app()