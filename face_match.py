import argparse
import sys
import os
import time
from typing import Tuple

import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1, MTCNN


def create_display_image(image: np.ndarray, width: int = 320) -> np.ndarray:
    height = int(image.shape[0] * width / image.shape[1])
    return cv2.resize(image, (width, height))


def draw_status(frame: np.ndarray, text: str, color: Tuple[int, int, int]) -> None:
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)


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
    parser = argparse.ArgumentParser(description="Match a live camera face to an ID image.")
    parser.add_argument("--id-image", default=default_id_image, help=f"Path to the scanned ID image (default: {default_id_image}).")
    parser.add_argument("--camera", type=int, default=0, help="Camera index to use (default: 0).")
    parser.add_argument("--tolerance", type=float, default=0.8, help="Face match tolerance (lower is stricter).")
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

    print("Press 'q' to quit or wait 8 seconds for automatic result.")
    start_time = time.time()
    matched = False

    while True:
        ret, frame = capture.read()
        if not ret:
            print("Unable to read from camera.", file=sys.stderr)
            break

        face_embeddings, boxes = compute_embeddings(frame, mtcnn, resnet)
        status_text = "No face detected"
        status_color = (0, 255, 255)

        if face_embeddings.shape[0] > 0 and boxes.shape[0] > 0:
            status_text = "Face detected"
            distances = np.linalg.norm(face_embeddings - reference_encoding, axis=1)
            for box, distance in zip(boxes, distances):
                color = (0, 255, 0) if distance <= args.tolerance else (0, 0, 255)
                label = f"Match {distance:.2f}" if distance <= args.tolerance else f"No match {distance:.2f}"
                matched = matched or (distance <= args.tolerance)

                left, top, right, bottom = [int(v) for v in box]
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 26), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, label, (left + 4, bottom - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            status_text = "ID Match confirmed" if matched else "Face does not match ID"
            status_color = (0, 255, 0) if matched else (0, 0, 255)

        elapsed = time.time() - start_time
        timer_text = f"Time: {elapsed:.1f}/8.0s"
        cv2.putText(frame, timer_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        draw_status(frame, status_text, status_color)
        cv2.imshow("Live Face Match", frame)
        cv2.imshow("ID Reference", id_display)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        if elapsed >= 8.0:
            break

    result_text = "ID accepted" if matched else "ID rejected"
    print(result_text)

    capture.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
