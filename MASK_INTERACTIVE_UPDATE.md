# Mask Module - Interactive Drawing & Operations Update

## Changes Made

### 1. ✅ Interactive Drawing Functionality

**Added full mouse interaction for drawing masks:**

- **Circle Tool**: Click and drag to draw circles
- **Rectangle Tool**: Click and drag to draw rectangles  
- **Polygon Tool**: Click to add points, right-click or press Enter to finish
- **Point Tool**: Click to mask/unmask individual regions
- **Threshold Tool**: Click to set threshold value for automatic masking

**Mouse Events:**
- Left click: Start drawing / Add point
- Right click: Finish polygon
- Mouse move: Show preview of shape being drawn
- Key press (Enter/Escape): Finish/cancel polygon

### 2. ✅ Changed Actions to Radio Buttons

**Before:**
```
Action: [Mask Pixels ▼] (dropdown)
```

**After:**
```
Action: ⚪ Mask  ⚪ Unmask (radio buttons)
```

Now uses radio buttons for clearer selection of mask vs unmask action.

### 3. ✅ Added Mask Operations

**New operation buttons:**
- **↕️ Invert**: Invert the entire mask (masked ↔ unmasked)
- **➕ Grow**: Expand masked regions by 1 pixel (morphological dilation)
- **➖ Shrink**: Contract masked regions by 1 pixel (morphological erosion)
- **🔧 Fill Holes**: Fill holes inside masked regions

**Requirements:** scipy library (for grow/shrink/fill operations)

### 4. ✅ New UI Layout

```
┌─────────────────────────────────────────────────────┐
│ Drawing Tools & Operations                          │
├─────────────────────────────────────────────────────┤
│ Tool: [Select▼] | Action: ⚪Mask ⚪Unmask           │
│                                                     │
│ Operations: [↕️Invert] [➕Grow] [➖Shrink] [🔧Fill] │
└─────────────────────────────────────────────────────┘
```

## Tool Usage Guide

### Circle Tool
```
1. Select "Circle" from Tool dropdown
2. Choose Mask or Unmask action
3. Click and drag on image
4. Release to apply circular mask
```

### Rectangle Tool
```
1. Select "Rectangle" from Tool dropdown
2. Choose Mask or Unmask action
3. Click and drag to define rectangle
4. Release to apply rectangular mask
```

### Polygon Tool
```
1. Select "Polygon" from Tool dropdown
2. Choose Mask or Unmask action
3. Click to add points (yellow markers appear)
4. Right-click OR press Enter to finish and apply
5. Press Escape to cancel
```

### Point Tool
```
1. Select "Point" from Tool dropdown
2. Choose Mask or Unmask action
3. Click anywhere to mask/unmask circular region (radius=5px)
4. Click multiple times to paint mask
```

### Threshold Tool
```
1. Select "Threshold" from Tool dropdown
2. Choose Mask or Unmask action
3. Click on image
4. Enter threshold value in dialog
5. All pixels above threshold are masked/unmasked
```

### Select Tool
```
1. Select "Select" from Tool dropdown
2. Pan and zoom image without drawing
```

## Operation Buttons

### Invert
```
Before: ⬛⬛⬛⬜⬜⬜
After:  ⬜⬜⬜⬛⬛⬛
```
Inverts the entire mask.

### Grow (Dilate)
```
Before: ⬜⬜⬜⬜⬜
        ⬜⬛⬛⬛⬜
        ⬜⬜⬜⬜⬜

After:  ⬜⬛⬛⬛⬜
        ⬛⬛⬛⬛⬛
        ⬜⬛⬛⬛⬜
```
Expands masked regions by 1 pixel.

### Shrink (Erode)
```
Before: ⬜⬛⬛⬛⬜
        ⬛⬛⬛⬛⬛
        ⬜⬛⬛⬛⬜

After:  ⬜⬜⬜⬜⬜
        ⬜⬛⬛⬛⬜
        ⬜⬜⬜⬜⬜
```
Contracts masked regions by 1 pixel.

### Fill Holes
```
Before: ⬛⬛⬛⬛⬛
        ⬛⬜⬜⬜⬛
        ⬛⬜⬜⬜⬛
        ⬛⬜⬜⬜⬛
        ⬛⬛⬛⬛⬛

After:  ⬛⬛⬛⬛⬛
        ⬛⬛⬛⬛⬛
        ⬛⬛⬛⬛⬛
        ⬛⬛⬛⬛⬛
        ⬛⬛⬛⬛⬛
```
Fills holes inside masked regions.

## Visual Feedback

### Drawing Preview
- **Circle**: Yellow dashed circle shows radius
- **Rectangle**: Yellow dashed rectangle shows bounds
- **Polygon**: Yellow dots connected by lines

### Mask Overlay
- **Red transparent overlay**: Shows masked regions (alpha=0.3)
- **Image underneath**: Diffraction pattern with log scale

## Code Architecture

### New State Variables
```python
self.drawing = False          # Currently drawing?
self.draw_start = None        # Start point of shape
self.draw_current = None      # Current mouse position
self.polygon_points = []      # Points in polygon
```

### Event Handlers
```python
on_mouse_press(event)    # Start drawing / add point
on_mouse_move(event)     # Update preview
on_mouse_release(event)  # Finish shape
on_key_press(event)      # Handle Enter/Escape
```

### Mask Application
```python
apply_point_mask(x, y, radius)        # Point tool
apply_circle_mask(start, end)         # Circle tool
apply_rectangle_mask(start, end)      # Rectangle tool
apply_polygon_mask()                  # Polygon tool
apply_threshold_mask()                # Threshold tool
```

### Operations
```python
invert_mask()      # Invert entire mask
grow_mask()        # Morphological dilation
shrink_mask()      # Morphological erosion  
fill_holes()       # Fill holes in mask
```

## Dependencies

### Required
- PyQt6
- numpy
- matplotlib

### Optional (for operations)
- scipy (for grow/shrink/fill operations)

If scipy is not available, operation buttons show warning message.

## Testing

### Basic Workflow Test
```
1. Run main.py
2. Click "🎭 Mask"
3. Click "📂 Load Image"
4. Select diffraction image
5. Select "Circle" tool
6. Check "Mask" radio button
7. Click and drag on image → Circle appears ✅
8. Release → Red overlay shows mask ✅
9. Select "Unmask" radio button
10. Draw another circle → Removes mask ✅
11. Click "↕️ Invert" → Mask inverts ✅
```

### Polygon Test
```
1. Select "Polygon" tool
2. Click to add 4-5 points
3. Yellow dots and lines appear ✅
4. Right-click to finish
5. Polygon region is masked ✅
```

### Threshold Test
```
1. Select "Threshold" tool
2. Click on image
3. Dialog appears asking for value ✅
4. Enter value (e.g., 1000)
5. All bright pixels are masked ✅
```

## Tips for Users

1. **Undo**: Use "🗑️ Clear All" to start over (no undo yet)
2. **Combine tools**: Use multiple tools to build complex masks
3. **Operations**: Apply grow/shrink to refine mask edges
4. **Threshold**: Quick way to mask hot pixels or beamstop
5. **Save often**: Save mask frequently to avoid losing work

## Known Limitations

1. No undo/redo functionality (planned for future)
2. Polygon can't be edited after creation
3. Grow/shrink require scipy library
4. Canvas must have focus for keyboard events (click on image first)

## Future Enhancements

- [ ] Add undo/redo stack
- [ ] Adjustable brush size for point tool
- [ ] Edit existing polygons
- [ ] Mask statistics display (% masked pixels)
- [ ] Keyboard shortcuts for all tools
- [ ] Auto-mask hot pixels detection
- [ ] Beamstop mask templates

---

**Status**: ✅ Complete and functional
**Date**: December 2, 2025
**Version**: 2.0 - Interactive Edition
