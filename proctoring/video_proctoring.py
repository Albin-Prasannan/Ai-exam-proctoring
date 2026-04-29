import cv2
import time
import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from proctoring.control import stop_event

# Initialize Haar Cascade
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# NEW: Initialize Face Landmarker (Tasks API)
model_path = 'face_landmarker.task'  # Make sure this file is in your project directory
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,  # Optimized for video frames
    num_faces=1
)
detector = vision.FaceLandmarker.create_from_options(options)

CAPTURE_DIR = "static/captures"
VIOLATION_FILE = "static/violation_status.txt"
os.makedirs(CAPTURE_DIR, exist_ok=True)

# These landmark indices remain the same in the new model
LEFT_EYE = 33
RIGHT_EYE = 362

def start_video_proctor():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("ERROR: Could not open camera")
            return
            
        last_capture = 0
        look_away_start = None
        
        # Initialize violation file
        with open(VIOLATION_FILE, 'w') as f:
            f.write("false|Normal|0")
        
        print("Video proctoring started successfully")
        
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Could not read frame from camera")
                break

            # Convert frame for different detectors
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # NEW: Convert to MediaPipe Image format
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int(time.time() * 1000)

            # Detect with Haar (for face count) and MediaPipe (for gaze)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # NEW: Detect using Tasks API
            result = detector.detect_for_video(mp_image, timestamp_ms)

            status = "Normal"
            violation_detected = False

            # ---- Face violations ----
            num_faces = len(faces)
            if num_faces == 0:
                status = "No Face Detected"
                violation_detected = True
                print("VIOLATION: No face detected")
            elif num_faces > 1:
                status = "Multiple Faces Detected"
                violation_detected = True
                print(f"VIOLATION: Multiple faces detected ({num_faces})")

            # ---- Eye gaze using new result format ----
            if result.face_landmarks:
                # result.face_landmarks is a list of faces, each having a list of landmarks
                lm = result.face_landmarks[0]
                if lm[LEFT_EYE].x < 0.3 or lm[RIGHT_EYE].x > 0.7:
                    if look_away_start is None:
                        look_away_start = time.time()
                    elif time.time() - look_away_start > 3:
                        status = "Looking Away"
                        violation_detected = True
                        print("VIOLATION: Looking away detected")
                else:
                    look_away_start = None

            # ---- Write violation status to file for web app to check ----
            with open(VIOLATION_FILE, 'w') as f:
                f.write(f"{str(violation_detected).lower()}|{status}|{int(time.time())}")

            # ---- Save screenshot ----
            if violation_detected and time.time() - last_capture > 5:
                cv2.imwrite(f"{CAPTURE_DIR}/violation_{int(time.time())}.jpg", frame)
                last_capture = time.time()

            # ---- Draw visuals ----
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)

            cv2.putText(frame, status, (20,40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

            # Removed GUI display - not needed for web application
            # cv2.imshow("Exam Proctoring", frame)

            # Check for stop event (without GUI waitKey)
            if stop_event.is_set():
                break

            # Small delay to prevent excessive CPU usage
            time.sleep(0.1)

        # NEW: Properly close the detector
        detector.close()
        cap.release()
        # Removed cv2.destroyAllWindows() since we're not using GUI display
        
        # Clean up violation file
        if os.path.exists(VIOLATION_FILE):
            os.remove(VIOLATION_FILE)
            
    except Exception as e:
        print(f"ERROR in video proctoring: {e}")
        # Clean up on error
        try:
            if 'cap' in locals():
                cap.release()
            if os.path.exists(VIOLATION_FILE):
                os.remove(VIOLATION_FILE)
        except:
            pass
