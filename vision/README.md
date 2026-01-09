# ROXY Vision - Hand Tracker

## Dependencies (optional stack)
- `opencv-python>=4.8.0`
- `mediapipe<0.10.0` (legacy `solutions` API used by `RoxyHandTracker`)
- `numpy`

Install vision extras from repo root (not needed for core service):
```bash
pip install -r requirements-vision.txt
```

## MediaPipe 0.10+ (Tasks API)
- If you upgrade to `mediapipe>=0.10`, you must supply the Tasks model:
  - Download `hand_landmarker.task` to a stable path (e.g. `/opt/roxy/vision/hand_landmarker.task`):
    ```bash
    wget -O /opt/roxy/vision/hand_landmarker.task \
      https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
    ```
  - Update the tracker to point at that file (Tasks API implementation pending).
- Current default is to stay on `<0.10` for compatibility.

## Usage
`vision/hand_tracker.py` uses the webcam (`camera_id=0`) and can broadcast over websocket. Run directly for local testing:
```bash
python vision/hand_tracker.py --camera 0 --port 9877
```
