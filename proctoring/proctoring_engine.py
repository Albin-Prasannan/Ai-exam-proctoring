import threading
from proctoring.control import stop_event
from proctoring.video_proctoring import start_video_proctor
# Removed audio_monitor import - audio monitoring now handled by JavaScript

def start_proctoring():
    stop_event.clear()

    threading.Thread(target=start_video_proctor, daemon=True).start()
    # Removed audio monitoring - handled by JavaScript in browser
    # threading.Thread(target=monitor_audio, daemon=True).start()
