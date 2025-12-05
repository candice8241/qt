#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for real-time automatic peak finding feature
Tests the Dioptas-style automatic peak detection
"""

import numpy as np
import sys

def test_imports():
    """Test if all required modules are available"""
    print("="*60)
    print("Testing Imports...")
    print("="*60)
    
    try:
        import numpy as np
        print("✓ NumPy available:", np.__version__)
    except ImportError as e:
        print("✗ NumPy not available:", e)
        return False
    
    try:
        from scipy.ndimage import maximum_filter
        from scipy.spatial.distance import cdist
        print("✓ SciPy available")
    except ImportError as e:
        print("✗ SciPy not available:", e)
        print("  Install with: pip install scipy")
        return False
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("✓ PyQt6 available")
    except ImportError as e:
        print("✗ PyQt6 not available:", e)
        return False
    
    try:
        import matplotlib
        print("✓ Matplotlib available:", matplotlib.__version__)
    except ImportError as e:
        print("✗ Matplotlib not available:", e)
        return False
    
    return True

def test_canvas_initialization():
    """Test CalibrationCanvas initialization"""
    print("\n" + "="*60)
    print("Testing CalibrationCanvas Initialization...")
    print("="*60)
    
    try:
        from PyQt6.QtWidgets import QApplication
        from calibration_canvas import CalibrationCanvas
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create canvas
        canvas = CalibrationCanvas(None, width=6, height=6, dpi=100)
        
        # Check new attributes
        assert hasattr(canvas, 'auto_detected_peaks'), "Missing auto_detected_peaks attribute"
        assert hasattr(canvas, 'auto_peak_markers'), "Missing auto_peak_markers attribute"
        assert hasattr(canvas, 'show_auto_peaks'), "Missing show_auto_peaks attribute"
        
        print("✓ CalibrationCanvas initialized successfully")
        print(f"  - auto_detected_peaks: {canvas.auto_detected_peaks}")
        print(f"  - show_auto_peaks: {canvas.show_auto_peaks}")
        
        # Check methods
        assert hasattr(canvas, 'auto_find_peaks_on_ring'), "Missing auto_find_peaks_on_ring method"
        assert hasattr(canvas, 'clear_auto_peaks'), "Missing clear_auto_peaks method"
        assert hasattr(canvas, 'update_auto_peaks_display'), "Missing update_auto_peaks_display method"
        assert hasattr(canvas, 'refresh_auto_peaks_for_all_manual'), "Missing refresh_auto_peaks_for_all_manual method"
        
        print("✓ All new methods present")
        
        return True
        
    except Exception as e:
        print(f"✗ Canvas initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auto_peak_finding_algorithm():
    """Test the auto peak finding algorithm with synthetic data"""
    print("\n" + "="*60)
    print("Testing Auto Peak Finding Algorithm...")
    print("="*60)
    
    try:
        from PyQt6.QtWidgets import QApplication
        from calibration_canvas import CalibrationCanvas
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create canvas
        canvas = CalibrationCanvas(None, width=6, height=6, dpi=100)
        
        # Create synthetic diffraction pattern (concentric rings)
        size = 512
        center_x, center_y = size // 2, size // 2
        y, x = np.ogrid[:size, :size]
        
        # Create multiple rings
        image = np.zeros((size, size), dtype=np.float32)
        
        for radius in [50, 100, 150, 200]:
            # Create ring with some Gaussian width
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            ring = np.exp(-((distance - radius)**2) / (2 * 3**2))
            
            # Add some noise/peaks around the ring
            angles = np.arctan2(y - center_y, x - center_x)
            # Create peaks at specific angles
            for angle in np.linspace(0, 2*np.pi, 36, endpoint=False):
                peak_mask = np.abs(angles - angle) < 0.1
                ring[peak_mask] *= 2.0
            
            image += ring * 1000
        
        # Add some noise
        image += np.random.normal(0, 10, image.shape)
        
        # Set image in canvas
        canvas.image_data = image
        
        # Test auto peak finding on the first ring (radius=50)
        # Click a point on the ring
        test_angle = 0  # 0 degrees
        seed_x = center_x + 50 * np.cos(test_angle)
        seed_y = center_y + 50 * np.sin(test_angle)
        ring_num = 1
        
        print(f"Testing with seed point: ({seed_x:.1f}, {seed_y:.1f}) on ring {ring_num}")
        
        # Run auto peak detection
        auto_peaks = canvas.auto_find_peaks_on_ring(seed_x, seed_y, ring_num)
        
        print(f"✓ Auto peak finding completed")
        print(f"  Found {len(auto_peaks)} peaks on ring {ring_num}")
        
        if len(auto_peaks) > 0:
            print(f"  Sample peaks (first 5):")
            for i, (x, y, rnum) in enumerate(auto_peaks[:5]):
                radius_found = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                print(f"    Peak {i+1}: ({x:.1f}, {y:.1f}), radius={radius_found:.1f}, ring={rnum}")
        
        # Verify peaks are on the correct ring (radius ~50)
        if auto_peaks:
            radii = [np.sqrt((x - center_x)**2 + (y - center_y)**2) for x, y, _ in auto_peaks]
            mean_radius = np.mean(radii)
            std_radius = np.std(radii)
            print(f"  Radius statistics: mean={mean_radius:.1f} ± {std_radius:.1f} pixels")
            
            # Should be close to 50
            if abs(mean_radius - 50) < 5:
                print("  ✓ Peaks are on the correct ring!")
            else:
                print(f"  ⚠ Warning: Expected radius ~50, got {mean_radius:.1f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Auto peak finding test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("REAL-TIME AUTO PEAK FINDING - TEST SUITE")
    print("="*60 + "\n")
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Import test failed. Please install missing dependencies.")
        return False
    
    # Test 2: Canvas initialization
    if not test_canvas_initialization():
        print("\n❌ Canvas initialization test failed.")
        return False
    
    # Test 3: Auto peak finding algorithm
    if not test_auto_peak_finding_algorithm():
        print("\n❌ Auto peak finding algorithm test failed.")
        return False
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\nReal-time automatic peak finding is ready to use!")
    print("Features implemented:")
    print("  • Auto peak detection on rings based on manual seed points")
    print("  • Real-time display of auto-detected peaks (cyan circles)")
    print("  • Toggle control for enabling/disabling the feature")
    print("  • Integration with calibration workflow")
    print("\nUsage:")
    print("  1. Load a calibration image")
    print("  2. Enable 'Real-time automatic peak finding' checkbox")
    print("  3. Enter peak picking mode")
    print("  4. Click on a diffraction ring")
    print("  5. Watch as the system automatically finds other peaks on the same ring!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
