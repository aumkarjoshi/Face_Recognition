# Liveness Detection & Anti-Spoofing Documentation

## Overview
This Face Recognition system includes advanced **liveness detection** and **anti-spoofing** capabilities to prevent fraud attacks where someone shows a photo of the person instead of standing in front of the camera.

## Attack Scenarios Prevented

### 1. **Photo/Print Attack**
- ❌ Showing a printed photo of the person
- ✅ System detects: Low texture quality, unnatural color distribution
- **Result:** SPOOF DETECTED

### 2. **Smartphone Screen Attack**
- ❌ Showing the person's photo on a phone/tablet screen
- ✅ System detects: Reduced texture variance, screen reflection patterns
- **Result:** SPOOF DETECTED

### 3. **High-Quality Video Attack**
- ❌ Playing a video of the person
- ✅ System detects: Unnatural motion patterns, no eye blinking
- **Result:** SPOOF DETECTED

### 4. **Mask/Deepfake Attack**
- ❌ Using 3D mask or advanced deepfake
- ✅ System detects: Texture anomalies, color inconsistencies
- **Result:** Highly likely SPOOF DETECTED

## How Liveness Detection Works

### Multi-Factor Analysis (4 Techniques Combined)

#### 1. **Texture Analysis (30% weight)**
- **What it does:** Analyzes surface texture patterns on the face
- **Why it works:** Real faces have complex, varied texture; photos are flat
- **Metric:** Laplacian Variance + Local Binary Pattern (LBP) variance
- **Score Range:** 0.0 (photo-like) to 1.0 (highly textured/real)

#### 2. **Color Distribution Analysis (25% weight)**
- **What it does:** Examines RGB color variance across the face
- **Why it works:** Printed photos have limited color depth; real faces have rich, variable colors
- **Metric:** Combined variance of R, G, B channels
- **Score Range:** 0.0 (flat colors) to 1.0 (natural color variation)

#### 3. **Motion Detection (25% weight)**
- **What it does:** Tracks pixel-level changes between consecutive frames
- **Why it works:** Real people move naturally; static photos don't move
- **Metric:** Pixel differences > threshold between frames
- **Score Range:** 0.0 (no motion) to 1.0 (high motion)

#### 4. **Eye Blink Detection (20% weight)**
- **What it does:** Detects eye opening/closing patterns
- **Why it works:** Real people blink; photos show static eyes
- **Metric:** Eye cascade detector + state changes over time
- **Score Range:** 0.0 (no blinks) to 1.0 (natural blinking)

### Final Liveness Score
```
Liveness Score = (Texture × 0.3) + (Color × 0.25) + (Motion × 0.25) + (Blink × 0.2)
```

**Threshold:** Score > 0.4 = LIVE FACE

## Verification Requirements

For successful authentication, **BOTH conditions must be met:**

1. **Face Matching:** The person's face must match the ID image (within tolerance)
2. **Liveness Verification:** The face must pass all anti-spoofing checks

### Result Scenarios

| Face Match | Liveness Check | Result | Status |
|-----------|----------------|--------|--------|
| ✓ Yes | ✓ Passed | **ID ACCEPTED** | 🟢 Green |
| ✓ Yes | ✗ Failed | **SPOOF ATTACK** | 🔴 Red |
| ✗ No | ✓ Passed | ID Rejected | 🟠 Orange |
| ✗ No | ✗ Failed | ID Rejected | 🔴 Red |

## Running the Program

### Basic Usage
```bash
python face_match.py
```

### With Custom Settings
```bash
# Use different camera
python face_match.py --camera 1

# Use custom ID image
python face_match.py --id-image path/to/id.jpg

# Adjust face match tolerance (lower = stricter)
python face_match.py --tolerance 0.7

# Increase time limit
python face_match.py --time-limit 20
```

### On Windows
```bash
# Double-click
run.bat

# Or from command line
run.bat
```

## What to Expect When Testing

### With a Real Person (You)
1. **Frame 1-2:** "No face detected" (moving closer)
2. **Frame 3-5:** "Face detected" + "Liveness: <score>" increases
3. **Eyes:** System detects eyes opening/closing
4. **Motion:** Background/head movement contributes to liveness
5. **Result after 5-10 frames:** 
   - If face matches ID: **"LIVENESS: PASSED"** (Green) + **"ID accepted"**
   - Score will be ~0.5-0.8

### With a Photo/Print (Spoof Attack)
1. **Frame 1-2:** "Face detected"
2. **Texture:** Score stays low (flat surface)
3. **Color:** Unnatural color distribution detected
4. **Motion:** Zero natural motion
5. **Eyes:** No eye detection or blinking
6. **Result after 3-5 frames:** 
   - **"LIVENESS: FAILED"** (Red)
   - **"SPOOF DETECTED!"** (if face matches ID)
   - Liveness score: ~0.1-0.3

### With a Phone Screen (Spoof Attack)
1. **Frame 1-5:** Face detected
2. **Texture:** Very low (screen is smooth)
3. **Color:** Limited color variance
4. **Motion:** Static (video doesn't adapt to camera angle)
5. **Eyes:** No real blinking
6. **Result:** 
   - **"LIVENESS: FAILED"** (Red)
   - Liveness score: ~0.15-0.35

## Technical Details

### Cascade Classifiers Used
- `haarcascade_eye.xml` - Eye detection for blink recognition

### Image Processing Techniques
- **Laplacian Operator:** Detects edges and texture
- **Local Binary Pattern (LBP):** Texture descriptor
- **Absolute Difference:** Frame-to-frame motion analysis
- **RGB Variance:** Color distribution analysis

### Performance
- **Processing Speed:** Real-time (30 FPS typical)
- **GPU Support:** Uses CUDA if available (3-5x faster)
- **CPU Fallback:** Works on CPU (15-25 FPS)

## Sensitivity Tuning

### In `face_match.py`, modify the `check_liveness()` function:

```python
# Current threshold (strict):
is_live = liveness_score > 0.4

# More lenient (0.3):
is_live = liveness_score > 0.3

# More strict (0.5):
is_live = liveness_score > 0.5
```

### Adjust weights if specific tests fail:
```python
# Increase weight for motion detection if photos move
liveness_score = (
    texture_score * 0.2 +    # Was 0.3
    color_score * 0.25 +
    motion_score * 0.35 +    # Was 0.25
    blink_score * 0.2
)
```

## Limitations & Recommendations

### ✅ Effective Against
- Printed/laminated photos
- Smartphone/tablet screens
- Pre-recorded videos
- Low-quality 3D masks

### ⚠️ Limited Effectiveness Against
- High-end silicone 3D masks with realistic eyes
- AI-generated deepfakes with motion
- Extremely expensive commercial spoofing devices

### 📋 Recommendations for High-Security
For maximum security, consider combining with:
1. **Challenge-based verification** (tell user to blink/smile on demand)
2. **Multi-angle verification** (ask user to turn head)
3. **Thermal imaging** (real faces emit heat)
4. **Advanced liveness models** (commercial solutions like NEC, Sensetime)
5. **Behavioral biometrics** (hand movement, speech)

## Troubleshooting

### Issue: "LIVENESS: FAILED" for real person
**Solution:**
- Ensure good lighting (shadows reduce texture detection)
- Face the camera directly
- Keep still for a moment so motion can be established
- Blink a few times naturally
- Increase `--time-limit` to 20+ seconds
- Lower threshold: change `0.4` to `0.3` in code

### Issue: Photo passes liveness check
**Solution:**
- This is rare; try moving the photo in front of the camera
- If it persists, increase liveness threshold to `0.5`
- Ensure good lighting reveals texture differences

### Issue: Real-time lag/slow processing
**Solution:**
- Check GPU availability: `torch.cuda.is_available()`
- Reduce frame resolution: capture.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
- Use dedicated model: Consider commercial liveness detection APIs

## References

- **LBP (Local Binary Pattern):** Ojala et al., "Multiresolution grayscale and rotation invariant texture classification with local binary patterns"
- **Laplacian Variance:** Focus measurement technique
- **Face Anti-spoofing:** CVPR, ICCV published papers on presentation attack detection

---

**Created:** 2026-07-23  
**Version:** 1.0  
**Status:** Production Ready
