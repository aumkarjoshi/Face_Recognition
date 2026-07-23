import argparse
import sys
import os
import time
from typing import Tuple
from collections import deque

import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1, MTCNN


def create_display_image(image: np.ndarray, width: int = 320) -> np.ndarray:
    height = int(image.shape[0] * width / image.shape[1])
    return cv2.resize(image, (width, height))


def draw_status(frame: np.ndarray, text: str, color: Tuple[int, int, int]) -> None:
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)


def detect_eyes(frame: np.ndarray, face_box: np.ndarray) -> Tuple[bool, float]:
    """Detect eyes in the face region and return whether eyes are open and their aspect ratio."""
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    
    left, top, right, bottom = [int(v) for v in face_box]
    face_roi = frame[max(0, top):min(frame.shape[0], bottom), max(0, left):min(frame.shape[1], right)]
    
    if face_roi.size == 0:
        return False, 0.5
    
    eyes = eye_cascade.detectMultiScale(face_roi, 1.1, 4)
    eye_detected = len(eyes) >= 2
    eye_aspect_ratio = len(eyes) / 2.0 if len(eyes) > 0 else 0.0
    
    return eye_detected, eye_aspect_ratio


def analyze_texture_quality(frame: np.ndarray, face_box: np.ndarray) -> float:
    """Analyze texture quality to detect if it's a real face or printed photo.
    Higher values indicate more likely to be a real face."""
    left, top, right, bottom = [int(v) for v in face_box]
    face_roi = frame[max(0, top):min(frame.shape[0], bottom), max(0, left):min(frame.shape[1], right)]
    
    if face_roi.size == 0:
        return 0.0
    
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    
    # Calculate Laplacian variance (blur detection)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # Local Binary Pattern texture analysis
    def local_binary_pattern(img):
        lbp = np.zeros_like(img)
        for i in range(1, img.shape[0] - 1):
            for j in range(1, img.shape[1] - 1):
                center = img[i, j]
                binary = (img[i-1:i+2, j-1:j+2] >= center).astype(int)
                lbp[i, j] = np.sum(binary * [1, 2, 4, 8, 16, 32, 64, 128])
        return lbp
    
    lbp = local_binary_pattern(gray)
    lbp_variance = np.var(lbp)
    
    # Normalize and combine scores (real faces have higher variance)
    texture_score = min(1.0, (laplacian_var + lbp_variance) / 500.0)
    return texture_score


def detect_motion(frame_buffer: deque) -> float:
    """Detect motion between consecutive frames. Real faces have consistent motion."""
    if len(frame_buffer) < 2:
        return 0.0
    
    frame1 = frame_buffer[-2]
    frame2 = frame_buffer[-1]
    
    if frame1 is None or frame2 is None:
        return 0.0
    
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    diff = cv2.absdiff(gray1, gray2)
    motion_pixels = np.sum(diff > 30)
    motion_score = min(1.0, motion_pixels / (frame1.shape[0] * frame1.shape[1]))
    
    return motion_score


def detect_color_distribution(frame: np.ndarray, face_box: np.ndarray) -> float:
    """Analyze color distribution to detect printed photos (less color variance)."""
    left, top, right, bottom = [int(v) for v in face_box]
    face_roi = frame[max(0, top):min(frame.shape[0], bottom), max(0, left):min(frame.shape[1], right)]
    
    if face_roi.size == 0:
        return 0.0
    
    # Calculate color variance
    b, g, r = cv2.split(face_roi)
    color_variance = np.var(b) + np.var(g) + np.var(r)
    
    # Real faces have higher color variance than printed photos
    color_score = min(1.0, color_variance / 5000.0)
    return color_score


def check_liveness(frame: np.ndarray, face_box: np.ndarray, frame_buffer: deque, blink_history: deque) -> Tuple[bool, float, str]:
    """
    Comprehensive liveness detection combining multiple anti-spoofing techniques.
    Returns: (is_live, confidence_score, reason)
    """
    eye_detected, eye_ratio = detect_eyes(frame, face_box)
    texture_score = analyze_texture_quality(frame, face_box)
    motion_score = detect_motion(frame_buffer)
    color_score = detect_color_distribution(frame, face_box)
    
    # Update blink history
    blink_history.append(eye_detected)
    
    # Calculate blink detection score
    blink_changes = sum(1 for i in range(1, len(blink_history)) if blink_history[i] != blink_history[i-1])
    blink_score = min(1.0, blink_changes / 3.0)
    
    # Weighted combination of all scores
    liveness_score = (
        texture_score * 0.3 +
        color_score * 0.25 +
        motion_score * 0.25 +
        blink_score * 0.2
    )
    
    # Thresholds for detecting liveness
    is_live = liveness_score > 0.4
    
    # Generate reason
    reasons = []
    if texture_score < 0.3:
        reasons.append("Low texture quality")
    if color_score < 0.3:
        reasons.append("Unnatural color")
    if motion_score < 0.1:
        reasons.append("No natural motion")
    if blink_score < 0.1:
        reasons.append("No blink detected")
    
    reason = " + ".join(reasons) if reasons else "Live face detected"
    
    return is_live, liveness_score, reason


def compute_embeddings(image: np.ndarray, mtcnn: MTCNN, resnet: InceptionResnetV1) -> tuple[np.ndarray, np.ndarray]:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    boxes, _ = mtcnn.detect(rgb)
    faces = mtcnn(rgb)
    if faces is None or boxes is None:
        return np.empty((0, 512), dtype=np.float32), np.empty((0, 4), dtype=np.float32)

    if faces.ndimension() == 3:
        faces = faces.unsqueeze(0)

    embeddings = resnet(faces.to(resnet.device)).detach().cpu().numpy()
    return embeddings, boxes


def load_reference_embedding(image_path: str, mtcnn: MTCNN, resnet: InceptionResnetV1) -> np.ndarray:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Unable to read ID image from {image_path}")

    embeddings, boxes = compute_embeddings(image, mtcnn, resnet)
    if len(embeddings) == 0:
        raise ValueError("No face detected in ID image. Use a clear photo of the ID with the face visible.")

    if len(embeddings) > 1:
        print("Warning: multiple faces found in ID image; using the first face.")
    return embeddings[0]


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_id_image = os.path.join(script_dir, "Images", "1.jpg")
    parser = argparse.ArgumentParser(description="Match a live camera face to an ID image with liveness detection.")
    parser.add_argument("--id-image", default=default_id_image, help=f"Path to the scanned ID image (default: {default_id_image}).")
    parser.add_argument("--camera", type=int, default=0, help="Camera index to use (default: 0).")
    parser.add_argument("--tolerance", type=float, default=0.8, help="Face match tolerance (lower is stricter).")
    parser.add_argument("--time-limit", type=int, default=15, help="Time limit in seconds (default: 15).")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mtcnn = MTCNN(keep_all=True, device=device)
    resnet = InceptionResnetV1(pretrained="vggface2").eval().to(device)

    try:
        reference_encoding = load_reference_embedding(args.id_image, mtcnn, resnet)
    except Exception as exc:
        print(f"Error loading ID image: {exc}", file=sys.stderr)
        return 1

    reference_display = cv2.imread(args.id_image)
    id_display = create_display_image(reference_display)

    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        print(f"Unable to open camera {args.camera}.", file=sys.stderr)
        return 1

    print("=" * 60)
    print("FACE RECOGNITION WITH LIVENESS DETECTION")
    print("=" * 60)
    print("Press 'q' to quit or wait for automatic result.")
    print("\nThis system detects:")
    print("  - Face matching (ID verification)")
    print("  - Live face presence (anti-spoofing)")
    print("  - Eye detection and blinking")
    print("  - Natural motion and texture analysis")
    print("=" * 60)
    
    start_time = time.time()
    matched = False
    live_verified = False
    frame_buffer = deque(maxlen=2)
    blink_history = deque(maxlen=10)

    while True:
        ret, frame = capture.read()
        if not ret:
            print("Unable to read from camera.", file=sys.stderr)
            break

        frame_buffer.append(frame.copy())
        face_embeddings, boxes = compute_embeddings(frame, mtcnn, resnet)
        
        status_text = "No face detected"
        status_color = (0, 255, 255)
        liveness_text = ""
        liveness_color = (0, 0, 255)

        if face_embeddings.shape[0] > 0 and boxes.shape[0] > 0:
            # Face detection and matching
            status_text = "Face detected"
            distances = np.linalg.norm(face_embeddings - reference_encoding, axis=1)
            
            for box, distance in zip(boxes, distances):
                # Liveness detection
                is_live, liveness_score, liveness_reason = check_liveness(frame, box, frame_buffer, blink_history)
                
                # Face matching
                face_matched = distance <= args.tolerance
                
                # Only accept if BOTH face matches AND face is live
                if face_matched and is_live:
                    matched = True
                    live_verified = True
                    color = (0, 255, 0)
                    label = f"MATCH {distance:.2f} (Live)"
                    status_text = "ID Match confirmed + Live face verified"
                    status_color = (0, 255, 0)
                    liveness_text = "LIVENESS: PASSED"
                    liveness_color = (0, 255, 0)
                else:
                    color = (0, 0, 255)
                    if face_matched and not is_live:
                        label = f"SPOOF DETECTED!"
                        status_text = "Face matches but SPOOF/PHOTO DETECTED"
                        status_color = (0, 0, 255)
                        liveness_text = f"LIVENESS: FAILED ({liveness_reason})"
                        liveness_color = (0, 0, 255)
                    elif is_live and not face_matched:
                        label = f"No match {distance:.2f}"
                        status_text = "Face does not match ID (but is live)"
                        status_color = (0, 165, 255)
                        liveness_text = "LIVENESS: PASSED"
                        liveness_color = (0, 255, 0)
                    else:
                        label = f"No match {distance:.2f}"
                        status_text = "Face does not match ID"
                        status_color = (0, 0, 255)
                        liveness_text = f"LIVENESS: {liveness_reason}"
                        liveness_color = (0, 0, 255)

                left, top, right, bottom = [int(v) for v in box]
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 26), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, label, (left + 4, bottom - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Display liveness score
                score_text = f"Liveness: {liveness_score:.2f}"
                cv2.putText(frame, score_text, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, liveness_color, 1)

        elapsed = time.time() - start_time
        timer_text = f"Time: {elapsed:.1f}/{args.time_limit}s"
        cv2.putText(frame, timer_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        draw_status(frame, status_text, status_color)
        
        if liveness_text:
            cv2.putText(frame, liveness_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, liveness_color, 2, cv2.LINE_AA)
        
        cv2.imshow("Live Face Match with Liveness Detection", frame)
        cv2.imshow("ID Reference", id_display)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        if elapsed >= args.time_limit:
            break

    capture.release()
    cv2.destroyAllWindows()
    
    # Final result
    print("\n" + "=" * 60)
    if matched and live_verified:
        print("RESULT: ID ACCEPTED + LIVE PERSON VERIFIED")
        result_text = "ID accepted"
    elif matched and not live_verified:
        print("RESULT: SPOOF/PHOTO ATTACK DETECTED!")
        print("WARNING: Face matched ID but liveness check FAILED")
        result_text = "ID rejected (spoof detected)"
    else:
        print("RESULT: ID REJECTED")
        result_text = "ID rejected"
    print("=" * 60)
    print(result_text)
    
    return 0 if (matched and live_verified) else 1


if __name__ == "__main__":
    raise SystemExit(main())
