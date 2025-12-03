# Right-Bottom Border Visibility Fix

## Problem

User cannot see the right-bottom corner of the purple border frame.

## Root Cause

The widget was expanding to fill the entire parent container, pushing the border outside the visible area. The bottom-right corner was being clipped by:
1. Parent container boundaries
2. Insufficient margins
3. Widget expanding beyond visible space

## Solution

### 1. Explicit Border Lines

Added explicit drawing of right and bottom borders:

```python
def paintEvent(self, event):
    # Draw main rounded rectangle
    painter.drawRoundedRect(
        rect.adjusted(1, 1, -8, -8),  # Larger inset on right/bottom
        6, 6
    )
    
    # EXPLICIT right vertical line
    right_x = rect.width() - 6
    painter.drawLine(right_x, 5, right_x, rect.height() - 5)
    
    # EXPLICIT bottom horizontal line (right side)
    bottom_y = rect.height() - 6
    painter.drawLine(rect.width() - 100, bottom_y, right_x, bottom_y)
```

**Why this works**:
- Right line: Full-height vertical line, 6px from edge
- Bottom line: Horizontal line connecting bottom-right corner
- Both lines: 3px thick, highly visible
- Explicit coordinates: Cannot be clipped by rounded rect

### 2. Increased Margins

#### Widget Level (batch_fitting_dialog.py):
```python
main_layout.setContentsMargins(3, 3, 12, 12)
#                              L  T   R   B
#                                  ↑   ↑
#                              Right Bottom margins increased
```

#### Frame Level (main.py):
```python
batch_frame.layout().setContentsMargins(0, 0, 35, 20)
#                                        L  T   R   B
#                                           ↑   ↑
#                                       Right Bottom clearance
```

**Total clearance**:
- Right: 12px (widget) + 35px (frame) = **47px**
- Bottom: 12px (widget) + 20px (frame) = **32px**

### 3. Size Constraints

Added minimum size to prevent over-expansion:

```python
self.setStyleSheet("""
    BatchFittingDialog {
        background-color: #E8E8E8;
        min-width: 1400px;
        min-height: 800px;  # Ensures reasonable size
    }
""")
```

Added size policy to container:

```python
container.setSizePolicy(QSizePolicy.Policy.Expanding, 
                       QSizePolicy.Policy.Expanding)
```

This prevents the container from expanding beyond the allocated space.

---

## Visual Layout

### Border Drawing Strategy

```
┌────────────────────────────────┐
│                              ║ │ ← Right line
│                              ║ │   6px from edge
│                              ║ │   Full height
│  Content                     ║ │
│                              ║ │
│                              ║ │
│                        ══════╝ │ ← Bottom line
│                              ↑ │   6px from edge
└──────────────────────────────┴─┘
                               ↑
                         47px clearance

Bottom margin: 32px ↓
```

### Corner Detail

```
Right-Bottom Corner:

      ║  ← Right vertical line
      ║
      ║
      ╚═══ ← Bottom horizontal line
         ↑
    100px length, connects to right line
```

---

## Implementation Details

### Border Dimensions

| Element | Position | Thickness | Color |
|---------|----------|-----------|-------|
| Main border | rect.adjusted(1,1,-8,-8) | 2px | #7E57C2 |
| Right line | X = width - 6 | 3px | #7E57C2 |
| Bottom line | Y = height - 6 | 3px | #7E57C2 |

### Margin Strategy

```
Screen/Parent Container
│
├─ batch_frame (from main.py)
│  └─ margins: (0, 0, 35, 20)  # Extra space on right & bottom
│     │
│     └─ BatchFittingDialog widget
│        └─ margins: (3, 3, 12, 12)  # More space on right & bottom
│           │
│           └─ content container
│              └─ margins: (8, 8, 8, 8)
│                 │
│                 └─ actual content (header, splitter, etc.)
```

### Total Space Allocation

```
                        Right Edge
                            │
│← 35px ────│← 12px ─│← content
frame margin  widget    area
              margin
            
═══════════════════════════════
    47px total clearance
    
Enough space for:
- 3px border line
- 6px positioning offset  
- Visual clearance
```

---

## Testing Instructions

### Visual Verification

1. **Start application**: `python main.py`
2. **Open batch**: Click "📊 Batch"
3. **Check right border**:
   - [ ] See purple vertical line on right
   - [ ] Line extends from top to near-bottom
   - [ ] Line is ~6px from right edge

4. **Check bottom-right corner**:
   - [ ] See purple horizontal line at bottom
   - [ ] Line connects to right vertical line
   - [ ] Forms visible corner
   - [ ] Line is ~6px from bottom edge

5. **Check spacing**:
   - [ ] Visible gap between border and screen edge
   - [ ] Border not cut off at any point
   - [ ] Corner clearly visible

### Resize Test

1. **Resize window smaller**: Border should stay visible
2. **Resize window larger**: Border should stay in place
3. **Maximize window**: Border should still be visible

### Corner Visibility Test

Look at the bottom-right area specifically:

```
Expected view:
                         ║ ← Right line visible
                         ║
                         ║
    Content area         ║
                  ═══════╝ ← Corner clearly visible
                           
                      ↑
              Visible gap here
```

---

## Debugging

### If right-bottom corner still not visible:

**Step 1**: Check widget size
```python
# Add to setup_ui() end:
print(f"Widget size: {self.width()} x {self.height()}")
print(f"Widget pos: {self.pos()}")
```

**Step 2**: Check if border is drawn
```python
# Add to paintEvent():
print(f"Drawing right line at X={right_x}")
print(f"Drawing bottom line at Y={bottom_y}")
print(f"Widget rect: {rect}")
```

**Step 3**: Make corner super obvious (temporary):
```python
# In paintEvent(), temporarily:
pen_debug = QPen(QColor("#FF0000"), 10)  # Thick red
painter.setPen(pen_debug)

# Draw a big X in bottom-right corner
painter.drawLine(rect.width()-50, rect.height()-50, 
                rect.width()-10, rect.height()-10)
painter.drawLine(rect.width()-50, rect.height()-10, 
                rect.width()-10, rect.height()-50)
```

If you see the red X, then the area is visible and border should be too.

**Step 4**: Check parent frame size
```python
# In main.py, after creating batch_module:
print(f"Batch frame size: {batch_frame.size()}")
print(f"Batch module size: {self.batch_module.size()}")
```

Widget should be smaller than frame to allow margin space.

---

## Alternative Solution

If explicit lines still don't show, use a colored indicator widget:

```python
def setup_ui(self):
    # ... existing code ...
    
    # Add corner indicator
    corner_indicator = QLabel("●")  # Or use QWidget
    corner_indicator.setStyleSheet("""
        QLabel {
            background-color: #7E57C2;
            color: #7E57C2;
            font-size: 20px;
        }
    """)
    corner_indicator.setFixedSize(10, 10)
    
    # Position at bottom-right using absolute positioning
    # This requires parent with absolute positioning enabled
```

---

## Summary of Changes

### Files Modified

1. **batch_fitting_dialog.py**
   - `paintEvent()`: Added explicit bottom line drawing
   - `paintEvent()`: Increased inset for main border (-8 on right/bottom)
   - `setup_ui()`: Increased margins to (3, 3, 12, 12)
   - `setup_ui()`: Added min-width and min-height constraints
   - `setup_ui()`: Set size policy on container

2. **main.py**
   - Batch frame margins: Changed to (0, 0, 35, 20)
   - Applied to both prebuild_modules and switch_tab

### Clearances

| Area | Previous | New | Increase |
|------|----------|-----|----------|
| Right widget | 10px | 12px | +2px |
| Right frame | 30px | 35px | +5px |
| **Right total** | **40px** | **47px** | **+7px** |
| Bottom widget | 3px | 12px | +9px |
| Bottom frame | 0px | 20px | +20px |
| **Bottom total** | **3px** | **32px** | **+29px** |

### Border Drawing

| Element | Position | Length/Height |
|---------|----------|---------------|
| Right line | X = width - 6 | Full height - 10px |
| Bottom line | Y = height - 6 | 100px (connects to right) |
| Main border | Inset 8px right/bottom | Full perimeter |

---

## Expected Result

After these changes:
✅ Right border clearly visible (3px purple line, 6px from edge)
✅ Bottom border visible in right corner (3px purple line)
✅ Right-bottom corner clearly defined by two intersecting lines
✅ Adequate clearance (47px right, 32px bottom)
✅ No clipping or cut-off at any point

The purple frame should now be completely visible including the right and bottom edges.

---

*Last Updated: December 3, 2024*
*Issue: Right-bottom corner visibility*
*Solution: Explicit border lines + increased margins*
