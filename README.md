<<<<<<< HEAD
# Face_Recognition
Python code to do a live Face match using an ID
=======
# Face-to-ID Matching Prototype

This project demonstrates a Python prototype for matching a guest's live face from a webcam feed to the face found in an ID image.

## What it does

- Loads a scanned ID image.
- Detects the face on the ID.
- Captures live video from the camera.
- Detects the guest's face in each frame.
- Compares the live face to the ID face and shows a match score.

## Requirements

- Python 3.8 or newer
- pip
- A webcam attached to the system
- A scanned ID image containing a clear face

## Installation

```bash
python3 -m pip install -r requirements.txt
```

If installation fails on macOS, make sure you have the command line developer tools installed:

```bash
xcode-select --install
```

If you still have trouble installing dependencies, use a clean virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Usage

By default, the script uses the test ID image at `/Users/aumkarjoshi/Desktop/Face Recognition/Images/1.jpg`.

```bash
python3 face_match.py
```

To override the ID image path:

```bash
python3 face_match.py --id-image /path/to/id-image.jpg
```

Optional arguments:

- `--camera`: camera index (default `0`)
- `--tolerance`: acceptance threshold for face matching (default `0.8`)

Example:

```bash
python3 face_match.py --camera 0 --tolerance 0.55
```

## How it works

The script uses `facenet-pytorch` to detect faces and extract face embeddings from the ID image and the live camera frames. It then compares the embeddings and draws a bounding box with match/mismatch status on the video.

The first run may download a pre-trained face recognition model, so the script can take a little longer the first time it starts.

## Notes

- The prototype assumes a single face on the ID image.
- For production kiosk use, add liveness checks, face quality checks, and stronger anti-spoofing.
>>>>>>> 6b7612f (Initial face matching prototype)
