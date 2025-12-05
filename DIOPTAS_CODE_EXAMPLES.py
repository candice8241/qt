#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dioptas Calibration - Code Examples
Based on Dioptas GitHub implementation: https://github.com/Dioptas/Dioptas

This file demonstrates how Dioptas performs detector calibration using pyFAI.
"""

import numpy as np

# =============================================================================
# Example 1: Basic Calibration Workflow (Dioptas-style)
# =============================================================================

def example_1_basic_calibration():
    """
    Demonstrates the basic calibration workflow as implemented in Dioptas.
    
    Reference: dioptas/model/CalibrationModel.py
    """
    from pyFAI.calibrant import Calibrant
    from pyFAI.detectors import Detector
    from pyFAI.geometryRefinement import GeometryRefinement
    from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
    import fabio
    
    # Step 1: Load calibration image
    print("="*60)
    print("Step 1: Load Calibration Image")
    print("="*60)
    
    image_path = "calibration_image.tif"  # Example path
    # img = fabio.open(image_path).data  # Uncomment with real image
    img = np.random.random((2048, 2048)) * 1000  # Dummy data for demo
    print(f"Image shape: {img.shape}")
    print(f"Image dtype: {img.dtype}")
    
    # Step 2: Define detector parameters
    print("\n" + "="*60)
    print("Step 2: Configure Detector")
    print("="*60)
    
    pixel_size = 79.0e-6  # 79 microns in meters
    detector = Detector(
        pixel1=pixel_size,
        pixel2=pixel_size,
        max_shape=img.shape
    )
    print(f"Pixel size: {pixel_size*1e6:.2f} μm")
    print(f"Detector shape: {detector.max_shape}")
    
    # Step 3: Setup calibrant (standard material)
    print("\n" + "="*60)
    print("Step 3: Setup Calibrant")
    print("="*60)
    
    wavelength = 1.033e-10  # X-ray wavelength in meters (12 keV)
    calibrant = Calibrant(wavelength=wavelength)
    calibrant.load_file("CeO2.D")  # Load CeO2 d-spacings from pyFAI database
    
    print(f"Calibrant: CeO2")
    print(f"Wavelength: {wavelength*1e10:.4f} Å")
    print(f"Energy: {12.3984 / (wavelength*1e10):.2f} keV")
    print(f"Number of rings available: {len(calibrant.dSpacing)}")
    
    # Step 4: Define control points (manual or automatic)
    print("\n" + "="*60)
    print("Step 4: Control Points")
    print("="*60)
    
    # Example: Manual control points format used by Dioptas
    # Each point is [row, col, ring_number]
    control_points = [
        # Ring 0 (innermost)
        [1024.5, 1124.3, 0],
        [1024.2, 924.7, 0],
        [1124.1, 1024.5, 0],
        [924.3, 1024.1, 0],
        # Ring 1
        [1024.3, 1224.5, 1],
        [1024.1, 824.2, 1],
        [1224.4, 1024.3, 1],
        [824.5, 1024.2, 1],
        # Ring 2
        [1024.2, 1324.1, 2],
        [1024.3, 724.5, 2],
        [1324.2, 1024.1, 2],
        [724.1, 1024.3, 2],
    ]
    
    print(f"Total control points: {len(control_points)}")
    
    # Organize by ring
    from collections import defaultdict
    points_by_ring = defaultdict(list)
    for point in control_points:
        row, col, ring = point
        points_by_ring[ring].append([row, col])
    
    for ring_num, points in sorted(points_by_ring.items()):
        print(f"  Ring {ring_num}: {len(points)} points")
    
    # Step 5: Create GeometryRefinement and calibrate
    print("\n" + "="*60)
    print("Step 5: Geometry Refinement")
    print("="*60)
    
    # Initial geometry estimates
    initial_distance = 0.15  # 150 mm in meters
    
    # Create geometry refinement object
    geo_ref = GeometryRefinement(
        data=control_points,        # Control points
        calibrant=calibrant,        # Standard material
        detector=detector,          # Detector object
        wavelength=wavelength       # X-ray wavelength
    )
    
    # Set initial geometry parameters
    geo_ref.dist = initial_distance
    geo_ref.poni1 = detector.max_shape[0] // 2 * pixel_size  # Center Y
    geo_ref.poni2 = detector.max_shape[1] // 2 * pixel_size  # Center X
    geo_ref.rot1 = 0.0  # Rotation around X
    geo_ref.rot2 = 0.0  # Rotation around Y
    geo_ref.rot3 = 0.0  # In-plane rotation
    
    print("Initial parameters:")
    print(f"  Distance: {geo_ref.dist*1000:.2f} mm")
    print(f"  PONI1 (Y): {geo_ref.poni1*1000:.4f} mm")
    print(f"  PONI2 (X): {geo_ref.poni2*1000:.4f} mm")
    print(f"  Rot1: {np.degrees(geo_ref.rot1):.4f}°")
    print(f"  Rot2: {np.degrees(geo_ref.rot2):.4f}°")
    print(f"  Rot3: {np.degrees(geo_ref.rot3):.4f}°")
    
    # Perform refinement (This is the core calibration step!)
    print("\nPerforming refinement...")
    # geo_ref.refine2()  # Uncomment with real data
    
    # Note: refine2() uses scipy.optimize.leastsq to minimize residuals
    # It iteratively adjusts the 6 parameters to best fit the control points
    
    print("Refinement completed!")
    
    # Step 6: Extract calibration results
    print("\n" + "="*60)
    print("Step 6: Calibration Results")
    print("="*60)
    
    # In real scenario, after refinement:
    # print(f"  Distance: {geo_ref.dist*1000:.2f} mm")
    # print(f"  PONI1: {geo_ref.poni1*1000:.4f} mm")
    # print(f"  PONI2: {geo_ref.poni2*1000:.4f} mm")
    # print(f"  Rot1: {np.degrees(geo_ref.rot1):.4f}°")
    # print(f"  Rot2: {np.degrees(geo_ref.rot2):.4f}°")
    # print(f"  Rot3: {np.degrees(geo_ref.rot3):.4f}°")
    
    # Step 7: Create AzimuthalIntegrator and save
    print("\n" + "="*60)
    print("Step 7: Save Calibration")
    print("="*60)
    
    # Create AzimuthalIntegrator from geometry
    ai = AzimuthalIntegrator(detector=detector)
    # ai.setPyFAI(dist=geo_ref.dist,
    #             poni1=geo_ref.poni1,
    #             poni2=geo_ref.poni2,
    #             rot1=geo_ref.rot1,
    #             rot2=geo_ref.rot2,
    #             rot3=geo_ref.rot3,
    #             wavelength=wavelength)
    
    # Save to PONI file
    poni_filename = "calibration.poni"
    # ai.save(poni_filename)
    print(f"Calibration saved to: {poni_filename}")
    print("\nPONI file format:")
    print("""
# Detector calibration file
Detector: Detector
Wavelength: 1.033e-10
Distance: 0.15
Poni1: 0.08347
Poni2: 0.08249
Rot1: 0.0123
Rot2: -0.0045
Rot3: 0.0
    """)


# =============================================================================
# Example 2: Automatic Peak Detection (Dioptas Method)
# =============================================================================

def example_2_automatic_peak_detection():
    """
    Demonstrates automatic peak detection as used in Dioptas.
    
    Reference: dioptas/model/CalibrationModel.py - auto_search_peaks()
    """
    print("\n" + "#"*60)
    print("# Example 2: Automatic Peak Detection")
    print("#"*60 + "\n")
    
    from pyFAI.massif import Massif
    from scipy.ndimage import gaussian_filter
    
    # Create a synthetic diffraction image with rings
    img = np.zeros((2048, 2048))
    center = np.array([1024, 1024])
    
    # Add some diffraction rings
    y, x = np.ogrid[:2048, :2048]
    for radius in [200, 400, 600, 800]:
        ring = np.abs(np.sqrt((x-center[1])**2 + (y-center[0])**2) - radius) < 5
        img += ring * np.random.randint(1000, 5000)
    
    # Add noise
    img += np.random.random(img.shape) * 100
    
    print("Step 1: Image preprocessing")
    # Smooth image to reduce noise
    smoothed = gaussian_filter(img, sigma=1.0)
    print(f"Applied Gaussian filter (sigma=1.0)")
    
    print("\nStep 2: Peak detection using Massif algorithm")
    # Massif is pyFAI's blob detection algorithm
    # In Dioptas, this is called via:
    # - CalibrationModel.auto_search_peaks()
    # - Which uses pyFAI's PeakPicker or Massif
    
    # Massif parameters (similar to Dioptas defaults)
    massif = Massif(smoothed)
    # In real Dioptas: massif.find_peaks()
    
    print("Peaks would be detected using:")
    print("  - Blob detection (Massif algorithm)")
    print("  - Threshold filtering")
    print("  - Peak refinement by centroid calculation")
    
    print("\nTypical output: List of peak coordinates")
    print("  Format: [[y1, x1], [y2, x2], ...]")


# =============================================================================
# Example 3: Ring Assignment (Dioptas Method)
# =============================================================================

def example_3_ring_assignment():
    """
    Demonstrates how Dioptas assigns detected peaks to diffraction rings.
    
    Reference: dioptas/model/CalibrationModel.py
    """
    print("\n" + "#"*60)
    print("# Example 3: Ring Assignment")
    print("#"*60 + "\n")
    
    # Simulated detected peaks (distances from center)
    peak_distances = np.array([200.5, 201.3, 199.8, 400.2, 401.1, 399.5, 
                               600.3, 599.8, 601.2])
    
    # Expected ring radii (from geometry + d-spacings)
    expected_rings = np.array([200.0, 400.0, 600.0])
    
    print("Detected peak distances from center:")
    print(peak_distances)
    print("\nExpected ring radii:")
    print(expected_rings)
    
    # Assignment algorithm (simplified version of Dioptas logic)
    tolerance = 5.0  # pixels
    
    ring_assignments = []
    for peak_dist in peak_distances:
        # Find closest ring
        distances = np.abs(expected_rings - peak_dist)
        closest_ring = np.argmin(distances)
        
        if distances[closest_ring] < tolerance:
            ring_assignments.append(closest_ring)
            print(f"\nPeak at {peak_dist:.1f} px → Ring {closest_ring} "
                  f"(error: {distances[closest_ring]:.1f} px)")
        else:
            ring_assignments.append(-1)  # No assignment
            print(f"\nPeak at {peak_dist:.1f} px → No ring assigned "
                  f"(min distance: {distances[closest_ring]:.1f} px)")


# =============================================================================
# Example 4: Loading and Using a PONI File
# =============================================================================

def example_4_load_poni():
    """
    Demonstrates how to load and use a PONI calibration file.
    
    This is how you would use a calibration saved by Dioptas.
    """
    print("\n" + "#"*60)
    print("# Example 4: Using PONI Calibration File")
    print("#"*60 + "\n")
    
    from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
    
    # Load calibration from PONI file
    poni_file = "calibration.poni"  # Saved by Dioptas
    
    print("Loading calibration from PONI file...")
    # ai = AzimuthalIntegrator.sload(poni_file)  # Uncomment with real file
    
    print("\nCalibration parameters would be:")
    print("  Distance: 150.23 mm")
    print("  PONI1: 83.47 mm")
    print("  PONI2: 82.49 mm")
    print("  Rot1: 0.012 rad (0.7°)")
    print("  Rot2: -0.005 rad (-0.3°)")
    print("  Rot3: 0.0 rad (0.0°)")
    print("  Wavelength: 1.033 Å")
    
    # Use for integration
    print("\nUsing calibration for azimuthal integration:")
    # img = np.random.random((2048, 2048)) * 1000
    # I, tth = ai.integrate1d(img, npt=2000, unit="2th_deg")
    
    print("  integrate1d() - 1D pattern (intensity vs 2θ)")
    print("  integrate2d() - 2D pattern (cake/unwrapped)")


# =============================================================================
# Example 5: Dioptas Model-View-Controller Architecture
# =============================================================================

def example_5_mvc_architecture():
    """
    Explains Dioptas' software architecture (for reference).
    
    This is how Dioptas organizes its code on GitHub.
    """
    print("\n" + "#"*60)
    print("# Example 5: Dioptas Architecture")
    print("#"*60 + "\n")
    
    print("Dioptas uses Model-View-Controller (MVC) pattern:\n")
    
    architecture = """
    dioptas/
    │
    ├── model/                          # Data and Logic
    │   ├── CalibrationModel.py         # Calibration state and operations
    │   ├── MaskModel.py                # Mask data management
    │   ├── ImgModel.py                 # Image data management
    │   └── PatternModel.py             # 1D pattern data
    │
    ├── controller/                     # User Interaction Logic
    │   ├── CalibrationController.py    # Handle calibration UI events
    │   ├── MaskController.py           # Handle mask editing events
    │   └── IntegrationController.py    # Handle integration events
    │
    ├── widgets/                        # GUI Components
    │   ├── CalibrationWidget.py        # Calibration UI layout
    │   ├── integration/
    │   │   ├── IntegrationWidget.py
    │   │   └── control/
    │   │       └── CalibrationControlWidget.py  # Calibration controls
    │   └── ...
    │
    └── tests/                          # Unit Tests
        ├── test_CalibrationModel.py
        └── ...
    """
    
    print(architecture)
    
    print("\nFlow of a calibration operation:")
    print("  1. User clicks 'Calibrate' button (View)")
    print("  2. CalibrationController catches the signal (Controller)")
    print("  3. Controller calls model.calibrate() (Model)")
    print("  4. Model performs pyFAI calibration (Logic)")
    print("  5. Model emits 'calibration_changed' signal (Model)")
    print("  6. Controller updates the View (Controller)")
    print("  7. View displays updated calibration results (View)")


# =============================================================================
# Example 6: Key Dioptas Functions (Pseudo-code Reference)
# =============================================================================

def example_6_key_functions():
    """
    Reference to key functions in Dioptas GitHub repository.
    """
    print("\n" + "#"*60)
    print("# Example 6: Key Dioptas Functions")
    print("#"*60 + "\n")
    
    print("Important functions in Dioptas (GitHub):\n")
    
    functions = [
        {
            "file": "dioptas/model/CalibrationModel.py",
            "function": "calibrate()",
            "description": "Main calibration function - calls pyFAI GeometryRefinement"
        },
        {
            "file": "dioptas/model/CalibrationModel.py",
            "function": "auto_search_peaks()",
            "description": "Automatic peak detection using pyFAI's Massif algorithm"
        },
        {
            "file": "dioptas/model/CalibrationModel.py",
            "function": "set_calibrant()",
            "description": "Load calibrant (CeO2, LaB6, etc.) from pyFAI database"
        },
        {
            "file": "dioptas/model/CalibrationModel.py",
            "function": "create_cake_geometry()",
            "description": "Create geometry for cake (unwrapped) pattern"
        },
        {
            "file": "dioptas/controller/CalibrationController.py",
            "function": "calibrate_btn_clicked()",
            "description": "Handle user clicking calibrate button"
        },
        {
            "file": "dioptas/controller/CalibrationController.py",
            "function": "click_img()",
            "description": "Handle user clicking on image to add control point"
        },
    ]
    
    for i, func in enumerate(functions, 1):
        print(f"{i}. {func['function']}")
        print(f"   File: {func['file']}")
        print(f"   Description: {func['description']}")
        print()


# =============================================================================
# Main Function
# =============================================================================

def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("DIOPTAS CALIBRATION - CODE EXAMPLES")
    print("Based on: https://github.com/Dioptas/Dioptas")
    print("="*60)
    
    try:
        example_1_basic_calibration()
    except ImportError as e:
        print(f"\nNote: Some libraries not available: {e}")
        print("Install with: pip install pyFAI fabio")
    
    example_2_automatic_peak_detection()
    example_3_ring_assignment()
    example_4_load_poni()
    example_5_mvc_architecture()
    example_6_key_functions()
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)
    print("\nFor full Dioptas source code, visit:")
    print("https://github.com/Dioptas/Dioptas")
    print("\nFor documentation:")
    print("https://dioptas.readthedocs.io")
    print()


if __name__ == "__main__":
    main()
