# Dioptas Calibration - Quick Reference Guide

## GitHub Repository
**Official Dioptas**: https://github.com/Dioptas/Dioptas

---

## 7-Step Calibration Process

### Step 1: Load Calibration Image
- **Action**: Load a diffraction image of a standard sample
- **Supported formats**: `.tif`, `.cbf`, `.edf`, `.mar3450`, `.img`, etc.
- **File location**: `dioptas/model/CalibrationModel.py`
- **Method**: Uses `fabio` library to read images

### Step 2: Configure Detector Parameters
- **Pixel size**: Physical dimension of detector pixels (μm)
- **Initial distance**: Sample-to-detector distance (mm)
- **Detector type**: Select from pyFAI detector library
- **Beam center**: Approximate X,Y position (optional initial guess)

### Step 3: Select Calibrant (Standard Material)
- **Common choices**:
  - **CeO₂** (Cerium Oxide) - Most popular
  - **LaB₆** (Lanthanum Hexaboride)
  - **Si** (Silicon)
  - **AgBh** (Silver Behenate)
- **Input**: X-ray wavelength (Å) or energy (keV)

### Step 4: Pick Control Points
Two methods available:

#### A) Automatic Peak Detection
- Click "Auto" button
- Dioptas automatically detects diffraction rings
- Uses pyFAI's peak-picking algorithms

#### B) Manual Point Selection
- Click on diffraction rings
- Assign ring number to each point
- Format: `[[row, col, ring_number], ...]`
- **Recommended**: 8-12 points per ring

### Step 5: Geometry Refinement
- **Engine**: pyFAI's `GeometryRefinement` class
- **Optimizes 6 parameters**:
  1. `dist` - Distance (m)
  2. `poni1` - Y-coordinate of PONI (m)
  3. `poni2` - X-coordinate of PONI (m)
  4. `rot1` - Rotation around X-axis (rad)
  5. `rot2` - Rotation around Y-axis (rad)
  6. `rot3` - In-plane rotation (rad)
- **Algorithm**: Non-linear least squares optimization
- **Goal**: Minimize residuals between theoretical and observed ring positions

### Step 6: Validate Results
- **Check residual plot**: Should show random distribution
- **RMS error**:
  - < 1 pixel: Excellent
  - < 2 pixels: Good
  - \> 3 pixels: Re-calibrate needed
- **Visual overlay**: Theoretical rings should match image

### Step 7: Save Calibration
- **Output format**: `.poni` file (pyFAI standard)
- **Contains**: All 6 geometry parameters + wavelength + detector info
- **Usage**: For subsequent data integration

---

## Key Source Code Files (Dioptas GitHub)

```
dioptas/
├── model/
│   ├── CalibrationModel.py          # Core calibration logic
│   └── ...
├── controller/
│   ├── CalibrationController.py     # UI-model interaction
│   └── ...
├── widgets/
│   ├── CalibrationWidget.py         # GUI components
│   ├── integration/
│   │   └── control/
│   │       └── CalibrationControlWidget.py
│   └── ...
└── tests/
    └── test_CalibrationModel.py     # Unit tests
```

---

## Core Algorithm (Simplified)

```python
# From CalibrationModel.py (conceptual)
def calibrate(self):
    # 1. Create detector object
    detector = Detector(pixel1=pixel_size, pixel2=pixel_size)
    
    # 2. Load calibrant (standard material)
    calibrant = Calibrant(wavelength=self.wavelength)
    calibrant.load_file("CeO2.D")
    
    # 3. Create geometry refinement
    geo_ref = GeometryRefinement(
        data=control_points,      # [[row, col, ring], ...]
        calibrant=calibrant,
        detector=detector,
        wavelength=wavelength
    )
    
    # 4. Set initial geometry
    geo_ref.dist = initial_distance
    geo_ref.poni1 = center_y * pixel_size
    geo_ref.poni2 = center_x * pixel_size
    
    # 5. Refine (optimize) all parameters
    geo_ref.refine2()
    
    # 6. Extract results
    calibration_params = {
        'dist': geo_ref.dist,
        'poni1': geo_ref.poni1,
        'poni2': geo_ref.poni2,
        'rot1': geo_ref.rot1,
        'rot2': geo_ref.rot2,
        'rot3': geo_ref.rot3,
    }
    
    # 7. Create AzimuthalIntegrator for integration
    ai = AzimuthalIntegrator(detector=detector)
    ai.setPyFAI(**calibration_params)
    
    return ai
```

---

## PONI Coordinate System

**PONI** = Point of Normal Incidence

```
    X-ray source
         │
         ▼
    ═════●═════  ← Sample
         │
         │ dist
         │
    ┌────┼────┐
    │    ●    │  ← Detector plane
    │  PONI   │     (poni1, poni2) = coordinates of PONI
    │         │
    └─────────┘

    PONI = where the direct beam would hit the detector
           if the detector were perpendicular to the beam
```

---

## Dioptas Workflow Diagram

```
Start
  │
  ├──> Load Image (.tif, .cbf, etc.)
  │
  ├──> Set Detector (pixel size, type)
  │
  ├──> Choose Calibrant (CeO₂, LaB₆, Si)
  │
  ├──> Input Wavelength/Energy
  │
  ├──> Pick Control Points
  │      ├─> Auto: Automatic peak detection
  │      └─> Manual: Click on rings
  │
  ├──> Run Refinement (pyFAI GeometryRefinement)
  │      ├─> Optimize 6 parameters
  │      └─> Minimize residuals
  │
  ├──> Check Results
  │      ├─> View residual plot
  │      ├─> Check RMS < 2 pixels
  │      └─> Visual ring overlay
  │
  ├──> Save .poni File
  │
End (Ready for integration)
```

---

## Key Dependencies

- **pyFAI**: Core calibration engine
- **fabio**: Image I/O for diffraction formats
- **numpy**: Array operations
- **scipy**: Optimization algorithms
- **matplotlib**: Visualization
- **PyQt5/PyQt6**: GUI framework

Install:
```bash
pip install dioptas
# or
pip install pyFAI fabio numpy scipy matplotlib PyQt5
```

---

## Comparison: Dioptas vs pyFAI-calib2

| Feature | Dioptas | pyFAI-calib2 |
|---------|---------|--------------|
| UI | Modern Qt | Basic matplotlib |
| Live preview | ✅ Yes | ❌ No |
| Integration | ✅ Built-in | ❌ Separate |
| Mask editing | ✅ Interactive | ⚠️ Limited |
| Ease of use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Underlying engine | pyFAI | pyFAI |

---

## Best Practices

### Image Quality
- Use images with 3-5 complete diffraction rings
- Ensure good signal-to-noise ratio
- Avoid saturated pixels
- Use well-known calibrants

### Control Points
- **Auto mode**: Best for high-quality images
- **Manual mode**: Better control for noisy images
- Use 8-12 points per ring for best results
- Distribute points evenly around rings

### Initial Parameters
- Accurate initial distance improves convergence
- Rough estimate of beam center is sufficient
- Rotation angles typically near zero

### Validation
- RMS should be < 2 pixels
- Residuals should be randomly distributed
- Test calibration on different datasets

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| High RMS error | Re-pick control points, check initial distance |
| Calibration fails | Verify wavelength, check calibrant selection |
| No peaks detected | Adjust threshold, use manual mode |
| Rings don't match | Confirm correct calibrant and wavelength |

---

## References

1. **Paper**: Prescher, C., & Prakapenka, V. B. (2015). DIOPTAS: a program for reduction of two-dimensional X-ray diffraction data and data exploration. *High Pressure Research*, 35(3), 223-230.
2. **Dioptas Docs**: https://dioptas.readthedocs.io
3. **pyFAI Docs**: https://pyfai.readthedocs.io
4. **GitHub**: https://github.com/Dioptas/Dioptas

---

## Implementation in This Project

The `calibrate_module.py` in this workspace implements Dioptas-style calibration with:

- ✅ pyFAI integration
- ✅ Automatic and manual peak picking
- ✅ Interactive mask editing
- ✅ Real-time visualization
- ✅ PONI file export
- ✅ Control point management

Key class: `CalibrateModule.perform_calibration()`

---

*Quick reference guide - December 5, 2025*
