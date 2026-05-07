# ============================================================
# test_hardware.py — Standalone hardware self-test suite.
#
# Purpose:
#   Verify that each hardware peripheral is wired correctly and
#   that the relevant Python driver can communicate with it.
#   This script intentionally does NOT require the camera or the
#   gesture model — you can run it early in the setup process.
#
# Usage:
#   source venv/bin/activate
#   python test_hardware.py
#
# Each test function is independent; comment out any you don't
# need, or call them individually from the Python REPL.
# ============================================================

import time


def test_lcd():
    """
    Test the I²C LCD display.
    Writes two different messages and verifies that the display
    clears without errors. Visual confirmation required.
    """
    print("\n[TEST] LCD display...")
    from control.lcd_display import LCDDisplay

    lcd = LCDDisplay()
    lcd.show("LCD Test", "Hello World!")
    time.sleep(2)

    lcd.show("Line 1 OK", "Line 2 OK")
    time.sleep(2)

    lcd.clear()
    lcd.close()
    print("[PASS] LCD OK")


def test_led():
    """
    Test the WS2812B LED strip.
    Cycles through three operating modes so you can visually confirm
    that the strip responds correctly:
      - 'playing' : animated rainbow-chase pattern
      - 'paused'  : slow breathing (pulse) effect
      - 'idle'    : all LEDs off
    """
    print("\n[TEST] WS2812B LED strip...")
    from control.led_controller import LEDController

    led = LEDController()

    print("  → Playing mode (rainbow chase)...")
    led.set_mode("playing")
    time.sleep(3)

    print("  → Paused mode (breathing pulse)...")
    led.set_mode("paused")
    time.sleep(3)

    print("  → Idle mode (LEDs off)...")
    led.set_mode("idle")
    time.sleep(1)

    led.close()
    print("[PASS] LED OK")


def test_model():
    """
    Test the TFLite gesture classification model.
    Feeds a random (dummy) input tensor through the model and prints
    the predicted gesture label and confidence. The prediction will be
    meaningless for random data, but a successful run confirms that the
    model file loads and the interpreter executes without errors.
    """
    print("\n[TEST] TFLite model...")
    import numpy as np
    from gesture.classifier import GestureClassifier

    # threshold=0.0 ensures any prediction is returned, even for random input
    clf = GestureClassifier("gesture_model.lite", "labels.txt", threshold=0.0)

    dummy = np.random.rand(1, 224, 224, 1).astype("float32")
    gesture, conf = clf.predict(dummy)

    print(f"  → Dummy input → predicted: {gesture} (confidence: {conf:.2%})")
    print("[PASS] Model OK")


def test_camera():
    """
    Test basic camera access via OpenCV's VideoCapture.
    Reads one frame and reports its shape. This is a quick sanity check;
    for the full Pi Camera integration (rpicam-vid subprocess), refer to
    the PiCamera class in main.py.
    """
    print("\n[TEST] Camera...")
    import cv2

    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if ret:
        print(f"  → Frame captured successfully. Shape: {frame.shape}")
        print("[PASS] Camera OK")
    else:
        print("[FAIL] Camera not found or failed to read a frame.")


# ---------------------------------------------------------------
# Run all tests when executed directly
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 40)
    print("  Hardware Test Suite")
    print("=" * 40)

    test_lcd()
    test_led()
    test_model()
    test_camera()

    print("\n[DONE] All tests completed.")
