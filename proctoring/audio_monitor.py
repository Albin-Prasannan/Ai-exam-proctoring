import sounddevice as sd
import numpy as np
import time
from proctoring.control import stop_event

THRESHOLD = 0.05
DURATION = 3

def monitor_audio():
    violation_start = None

    def callback(indata, frames, time_info, status):
        nonlocal violation_start
        if stop_event.is_set():
            raise sd.CallbackStop()

        volume = np.linalg.norm(indata)
        if volume > THRESHOLD:
            if violation_start is None:
                violation_start = time.time()
            elif time.time() - violation_start > DURATION:
                print("Audio violation detected")
        else:
            violation_start = None

    with sd.InputStream(callback=callback):
        while not stop_event.is_set():
            time.sleep(0.1)