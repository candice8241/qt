# Bin Configuration Integration Flow

## Overall Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Powder XRD Module                          │
│                     (powder_module.py)                          │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │         Integration Settings Section                   │   │
│  │                                                         │   │
│  │  PONI File:        [________________] [Browse]         │   │
│  │  Mask File:        [________________] [Browse]         │   │
│  │  Input Pattern:    [________________] [Browse]         │   │
│  │  Output Directory: [________________] [Browse]         │   │
│  │  Dataset Path:     [________________] [Browse]         │   │
│  │                                                         │   │
│  │  Sector Integration (Optional):                        │   │
│  │  [🔍 H5 Preview & Select Region]                       │   │
│  │  No sector selected (full integration)                 │   │
│  │                                                         │   │
│  │  Azimuthal Binning (Optional):                         │   │
│  │  [⚙️ Configure Bins] ◄── Click to open dialog         │   │
│  │                                                         │   │
│  │  ✓ 36 bins configured (Bin001: 0.0°-10.0°, ...)       │   │
│  │     (Shows bin configuration status)                   │   │
│  │                                                         │   │
│  │              [Run Integration]                         │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Click "Configure Bins"
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Bin Configuration Dialog                      │
│                  (bin_config_dialog.py)                         │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Quick Generate                                          │   │
│  │ Start: [0] End: [360] Bins: [36] [Generate]           │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Bin List                                                │   │
│  │ ┌──────────┬───────┬───────┬────────┐                 │   │
│  │ │ Bin Name │ Start │  End  │ Action │                 │   │
│  │ ├──────────┼───────┼───────┼────────┤                 │   │
│  │ │ Bin001   │  0.00 │ 10.00 │[Delete]│                 │   │
│  │ │ Bin002   │ 10.00 │ 20.00 │[Delete]│                 │   │
│  │ │ Bin003   │ 20.00 │ 30.00 │[Delete]│                 │   │
│  │ │   ...    │  ...  │  ...  │  ...   │                 │   │
│  │ └──────────┴───────┴───────┴────────┘                 │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Manual Add                                              │   │
│  │ Name: [Bin01] Start: [0] End: [10] [Add]              │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│          [Clear All]  [Cancel]  [OK]                           │
│                                        │                        │
└────────────────────────────────────────┼────────────────────────┘
                                         │ Click OK
                                         ▼
              Returns bin configuration to Powder Module
                [
                  {'name': 'Bin001', 'start': 0.0, 'end': 10.0},
                  {'name': 'Bin002', 'start': 10.0, 'end': 20.0},
                  ...
                ]
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Powder Module Processing                       │
│                                                                 │
│  1. Store bins to self.bin_config                              │
│  2. Update UI to show bin configuration                        │
│  3. Log bin details to console                                 │
└─────────────────────────────────────────────────────────────────┘
                                         │
                                         │ User clicks "Run Integration"
                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Integration Mode Selection                          │
│                                                                 │
│  Priority check:                                               │
│  1. Bins configured? ───YES──→ Use Bin Mode                   │
│         │                                                       │
│        NO                                                       │
│         ↓                                                       │
│  2. Sector configured? ───YES──→ Use Sector Mode               │
│         │                                                       │
│        NO                                                       │
│         ↓                                                       │
│  3. Use Full Integration Mode                                  │
└─────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│            Batch Integration (Bin Mode)                          │
│                (batch_integration.py)                           │
│                                                                 │
│  For each H5 file:                                             │
│    For each bin:                                               │
│      1. Convert bin angles to radians                          │
│      2. Set azimuth_range = (start_rad, end_rad)               │
│      3. Call ai.integrate1d(..., azimuth_range=...)            │
│      4. Save to: {filename}_{binname}.{format}                 │
│                                                                 │
│  Example output files:                                         │
│    sample001_Bin001.xy                                         │
│    sample001_Bin002.xy                                         │
│    ...                                                          │
│    sample001_Bin036.xy                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Step-by-Step Flow

### Step 1: User Opens Bin Configuration

```
Powder Module
  ↓
User clicks "⚙️ Configure Bins" button
  ↓
powder_module.open_bin_config() called
  ↓
Create BinConfigDialog instance
  ↓
dialog.exec() shows modal dialog
```

### Step 2: Configure Bins in Dialog

#### Option A: Quick Generate
```
User enters:
  - Start: 0
  - End: 360
  - Bins: 36
  ↓
Click "Generate" button
  ↓
bin_config_dialog.quick_generate() called
  ↓
Calculate bin_width = (360 - 0) / 36 = 10°
  ↓
Generate 36 bins:
  Bin001: 0° - 10°
  Bin002: 10° - 20°
  ...
  Bin036: 350° - 360°
  ↓
Update table display
```

#### Option B: Manual Add
```
User enters:
  - Name: Peak_A
  - Start: 45
  - End: 55
  ↓
Click "Add" button
  ↓
bin_config_dialog.manual_add() called
  ↓
Validate: start < end
  ↓
Add bin to list
  ↓
Update table display
  ↓
Clear input fields
  ↓
Repeat for more bins
```

### Step 3: Return Configuration

```
User reviews bin table
  ↓
Click "OK" button
  ↓
bin_config_dialog.accept_config() called
  ↓
Validate: at least 1 bin exists
  ↓
Emit bins_configured signal (optional)
  ↓
dialog.accept() closes dialog
  ↓
powder_module.open_bin_config() continues
  ↓
Get bins via dialog.get_bins()
  ↓
Store to self.bin_config
  ↓
Update UI info label
  ↓
Log bin details
```

### Step 4: Run Integration

```
User clicks "Run Integration"
  ↓
powder_module.run_integration() called
  ↓
Validate inputs (PONI, input, output)
  ↓
Check integration mode:
  - if bin_config exists: Use Bin Mode
  - elif sector_params exists: Use Sector Mode  
  - else: Use Full Integration
  ↓
Build integration script with bins parameter
  ↓
Start subprocess
  ↓
Monitor progress
```

### Step 5: Batch Integration (Bin Mode)

```
batch_integration.run_batch_integration(
  ...,
  bins=[
    {'name': 'Bin001', 'start': 0.0, 'end': 10.0},
    {'name': 'Bin002', 'start': 10.0, 'end': 20.0},
    ...
  ]
)
  ↓
BatchIntegrator.batch_integrate(..., bins=bins)
  ↓
For each H5 file (e.g., sample001.h5):
  ↓
  BatchIntegrator.integrate_single(..., bins=bins)
    ↓
    Read H5 image data
    ↓
    For each bin (e.g., Bin001):
      ↓
      Convert angles: 0° → 0 rad, 10° → 0.1745 rad
      ↓
      Set azimuth_range = (0, 0.1745)
      ↓
      Call ai.integrate1d(
        data,
        npt=4000,
        mask=mask,
        unit='2th_deg',
        azimuth_range=(0, 0.1745),
        ...
      )
      ↓
      Get result (2θ, Intensity)
      ↓
      Save to: output_dir/sample001_Bin001.xy
      ↓
    Repeat for Bin002, Bin003, ..., Bin036
    ↓
  All bins complete for sample001.h5
  ↓
Repeat for sample002.h5, sample003.h5, ...
  ↓
All files complete
  ↓
Return success
```

## Data Flow Diagram

```
BinConfigDialog          PowderModule            BatchIntegration
     │                        │                         │
     │  get_bins()            │                         │
     │───────────────────────>│                         │
     │    [bin list]          │                         │
     │                        │                         │
     │                        │  bins parameter         │
     │                        │────────────────────────>│
     │                        │                         │
     │                        │                         ├─> For each file
     │                        │                         │   For each bin
     │                        │                         │     integrate1d(
     │                        │                         │       azimuth_range
     │                        │                         │     )
     │                        │                         │     save file
     │                        │                         │
     │                        │  <─────────────────────│
     │                        │     Integration Results │
     │                        │                         │
```

## Integration Mode Priority

```
┌─────────────────────┐
│ Start Integration   │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Bins config? │───YES──┐
    └──────┬───────┘        │
           NO               │
           │                │
           ▼                ▼
    ┌──────────────┐  ┌──────────────┐
    │Sector config?│  │  BIN MODE    │
    └──────┬───────┘  │              │
           │          │ Multiple     │
        YES│NO        │ azimuth      │
           │  │       │ ranges       │
           ▼  ▼       │              │
    ┌──────┐ ┌─────┐ │ Output:      │
    │SECTOR│ │FULL │ │ file_bin.xy  │
    │ MODE │ │MODE │ └──────────────┘
    │      │ │     │
    │Single│ │Full │
    │azim  │ │ring │
    │range │ │     │
    │      │ │     │
    │Output│ │Out: │
    │file  │ │file │
    │.xy   │ │.xy  │
    └──────┘ └─────┘
```

## File Output Examples

### Example 1: 3 files × 36 bins

**Input Files:**
- `/data/sample001.h5`
- `/data/sample002.h5`
- `/data/sample003.h5`

**Bin Configuration:**
- 36 bins (Bin001 to Bin036)
- 10° per bin (0-360°)

**Output Files (108 total):**
```
/output/sample001_Bin001.xy
/output/sample001_Bin002.xy
...
/output/sample001_Bin036.xy

/output/sample002_Bin001.xy
/output/sample002_Bin002.xy
...
/output/sample002_Bin036.xy

/output/sample003_Bin001.xy
/output/sample003_Bin002.xy
...
/output/sample003_Bin036.xy
```

### Example 2: Custom Bins

**Input Files:**
- `/data/diamond_10GPa.h5`

**Bin Configuration:**
- 3 custom bins
  - Peak_111: 10° - 20°
  - Peak_220: 45° - 55°
  - Background: 90° - 100°

**Output Files (3 total):**
```
/output/diamond_10GPa_Peak_111.xy
/output/diamond_10GPa_Peak_220.xy
/output/diamond_10GPa_Background.xy
```

## User Interface States

### State 1: No Bins Configured (Initial)
```
┌────────────────────────────────────┐
│ Azimuthal Binning (Optional):     │
│ [⚙️ Configure Bins]                │
│ No bins configured (single         │ ◄── Gray text
│ integration)                       │
└────────────────────────────────────┘
```

### State 2: Few Bins Configured (≤5)
```
┌────────────────────────────────────┐
│ Azimuthal Binning (Optional):     │
│ [⚙️ Configure Bins]                │
│ ✓ 3 bins configured (Peak_111:    │ ◄── Orange bold
│   10.0°-20.0°, Peak_220:           │
│   45.0°-55.0°, Background:         │
│   90.0°-100.0°)                    │
└────────────────────────────────────┘
```

### State 3: Many Bins Configured (>5)
```
┌────────────────────────────────────┐
│ Azimuthal Binning (Optional):     │
│ [⚙️ Configure Bins]                │
│ ✓ 36 bins configured               │ ◄── Orange bold
└────────────────────────────────────┘
```

---

**Summary**: The bin configuration system provides flexible azimuthal binning for diffraction data, with intuitive UI and seamless integration into the existing powder module workflow.
