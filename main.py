# ============================================================
# main.py — Application entry point.
#
# Pipeline:
#   1. Initialise all hardware peripherals (LCD, LED strip, audio player).
#   2. Launch the Pi Camera capture loop in a background thread.
#   3. For each captured frame:
#        a. Detect hand landmarks with MediaPipe (HandDetector).
#        b. Preprocess landmarks into a flat feature vector.
#        c. Classify the gesture with the TFLite model (GestureClassifier).
#        d. Dispatch the corresponding action (CommandDispatcher).
#   4. Overlay the gesture label on the preview window.
#   5. Shut down all hardware cleanly on exit.
# ============================================================

import cv2
import time
import numpy as np
import subprocess
import threading
import config

from gesture.detector    import HandDetector
from gesture.classifier  import GestureClassifier
from control.lcd_display import LCDDisplay
from control.led_controller   import LEDController
from control.audio_player     import AudioPlayer
from control.command_dispatcher import CommandDispatcher


class PiCamera:
    """
    Wraps the `rpicam-vid` command-line tool as a background subprocess
    and exposes a simple OpenCV-compatible read() interface.

    Why not use cv2.VideoCapture?
    Python 3.11 on Raspberry Pi OS no longer ships the V4L2 backend
    that VideoCapture relies on for the Pi Camera Module. Spawning
    rpicam-vid directly and reading raw YUV420 frames from its stdout
    is the officially recommended workaround.

    Args:
        width  (int): Capture frame width in pixels.
        height (int): Capture frame height in pixels.
        fps    (int): Target capture frame rate.
    """

    def __init__(self, width=640, height=480, fps=15):
        self.width  = width
        self.height = height

        self._frame      = None          # Most recent decoded BGR frame
        self._lock       = threading.Lock()
        self._running    = True

        # YUV420 raw frame size: width × height × 1.5 bytes per pixel
        self._frame_size = width * height * 3 // 2

        # Launch rpicam-vid in continuous streaming mode.
        # --codec yuv420  : raw uncompressed output (no decode overhead)
        # --timeout 0     : run indefinitely until the process is killed
        # --output -      : pipe frames to stdout
        # --nopreview     : suppress the hardware overlay preview window
        self._proc = subprocess.Popen(
            ['rpicam-vid',
             '--width',  str(width),
             '--height', str(height),
             '--codec',  'yuv420',
             '--timeout', '0',
             '--output', '-',
             '--nopreview',
             f'--framerate={fps}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        # Start the background reader thread immediately.
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        """
        Background thread: continuously reads raw YUV420 data from the
        rpicam-vid subprocess, converts each frame to BGR, and stores
        it for retrieval by read().
        """
        while self._running:
            raw = self._proc.stdout.read(self._frame_size)

            # If we received fewer bytes than expected the stream has ended.
            if len(raw) < self._frame_size:
                break

            # Reshape the flat byte buffer into a YUV420 2-D array and
            # convert to BGR so the rest of the pipeline can treat it as
            # a standard OpenCV frame.
            yuv   = np.frombuffer(raw, dtype=np.uint8).reshape(
                        (self.height * 3 // 2, self.width))
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

            with self._lock:
                self._frame = frame

    def read(self):
        """
        Return the most recently captured frame.

        Returns:
            (bool, numpy.ndarray): (True, BGR frame) if a frame is available,
                                   (False, None) if no frame has been captured yet.
        """
        with self._lock:
            if self._frame is not None:
                return True, self._frame.copy()
        return False, None

    def release(self):
        """Stop the background thread and terminate the rpicam-vid process."""
        self._running = False
        self._proc.terminate()


def main():
    # ------------------------------------------------------------------
    # Hardware initialisation
    # ------------------------------------------------------------------
    print("[INFO] Initialising hardware...")

    lcd   = LCDDisplay()
    led   = LEDController()
    audio = AudioPlayer(music_dir="assets/music")

    lcd.show_startup()       # Display a boot message on the LCD
    led.set_mode("playing")  # Briefly light up the LEDs to confirm they work

    # ------------------------------------------------------------------
    # Model / inference initialisation
    # ------------------------------------------------------------------
    detector = HandDetector(max_hands=2)

    classifier = GestureClassifier(
        model_path  = config.MODEL_PATH,
        labels_path = config.LABELS_PATH,
        threshold   = config.CONFIDENCE_THRESHOLD,
    )

    dispatcher = CommandDispatcher(led, lcd, audio)

    # ------------------------------------------------------------------
    # Camera startup
    # ------------------------------------------------------------------
    print("[INFO] Starting camera...")
    cam = PiCamera(width=config.FRAME_WIDTH, height=config.FRAME_HEIGHT)

    # Allow 2 seconds for the camera sensor to stabilise its exposure
    # and white-balance before the first frame is processed.
    time.sleep(2)
    led.set_mode("idle")

    print("[INFO] System ready. Press Ctrl+C or 'q' to quit.")

    fps_start   = time.time()
    frame_count = 0

    # ------------------------------------------------------------------
    # Main capture / inference loop
    # ------------------------------------------------------------------
    try:
        while True:
            ret, frame = cam.read()
            if not ret:
                # No frame available yet — yield the CPU briefly and retry.
                time.sleep(0.01)
                continue

            # Step 1: Detect hand landmarks and draw them onto the frame.
            frame, landmarks_list = detector.detect(frame)

            # Step 2: Convert the raw landmarks into the flat feature
            #         vector expected by the TFLite model.
            features = detector.preprocess_for_model(frame, landmarks_list)

            # Step 3: Run inference to obtain the gesture label and
            #         its associated confidence score.
            gesture, confidence = classifier.predict(features)

            # Step 4: Translate the gesture into a hardware action
            #         (e.g. play/pause, volume change, LED update).
            dispatcher.dispatch(gesture, confidence)

            # ----------------------------------------------------------
            # FPS monitoring — logged to console once per second
            # ----------------------------------------------------------
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps         = frame_count / elapsed
                frame_count = 0
                fps_start   = time.time()
                print(f"[INFO] FPS: {fps:.1f} | Gesture: {gesture} ({confidence:.0%})")

            # ----------------------------------------------------------
            # On-screen overlay — gesture label in the top-left corner
            # ----------------------------------------------------------
            cv2.putText(
                frame,
                f"{gesture}  {confidence:.0%}",
                (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 255, 0),   # Green text
                2
            )
            cv2.imshow("Gesture System", frame)

            # Press 'q' to quit gracefully from the preview window.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt received — shutting down...")

    # ------------------------------------------------------------------
    # Graceful shutdown — release all hardware resources in reverse order
    # ------------------------------------------------------------------
    cam.release()
    cv2.destroyAllWindows()
    detector.close()
    led.close()
    lcd.show_goodbye()   # Display a farewell message before turning off the LCD
    time.sleep(1)
    lcd.close()
    audio.close()


if __name__ == "__main__":
    main()
