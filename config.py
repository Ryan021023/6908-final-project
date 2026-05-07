# ============================================================
# config.py — Global configuration. All hardware parameters
#             are centralised here; change values in this file
#             rather than editing the source modules directly.
# ============================================================

# ---------- Model ----------
MODEL_PATH  = "gesture_model.lite"   # Path to the TFLite gesture classification model
LABELS_PATH = "labels.txt"           # Path to the class-label text file
INPUT_SHAPE  = 132    # Flattened landmark feature length: 21 keypoints × 2 hands × 3 axes (x, y, z)
                      # Must match the shape used during model training
NUM_CLASSES  = 7      # Total number of gesture classes

# ---------- Camera ----------
CAMERA_INDEX  = 0     # Pi Camera index (usually 0 for the first attached camera)
FRAME_WIDTH   = 640   # Capture width in pixels
FRAME_HEIGHT  = 480   # Capture height in pixels

# ---------- LCD Display ----------
LCD_ADDRESS = 0x27    # I²C address of the LCD module (run `i2cdetect -y 1` to confirm)
LCD_COLS    = 16      # Number of character columns
LCD_ROWS    = 2       # Number of character rows

# ---------- WS2812B LED Strip ----------
LED_COUNT      = 12       # Total number of LED pixels on the strip
LED_PIN        = 10       # GPIO pin connected to the data line (GPIO 10 = PWM0, physical pin 12)
LED_FREQ       = 800000   # PWM signal frequency in Hz (800 kHz is standard for WS2812B)
LED_DMA        = 10       # DMA channel used to drive the signal
LED_INVERT     = False    # Set True if using an inverting level-shifter on the data line
LED_CHANNEL    = 0        # PWM hardware channel (0 for GPIO 10/18, 1 for GPIO 13/19)
LED_BRIGHTNESS = 16       # Global brightness 0–255. At 16 (~6%), 12 LEDs draw ~360 mA,
                          # which is within the Raspberry Pi's USB power budget

# ---------- Gesture → Action Mapping ----------
# Maps each recognised gesture label to a named command string.
# The CommandDispatcher reads this table to decide what action to trigger.
GESTURE_ACTIONS = {
    "THUMBS_UP"  : "volume_up",
    "FIST"       : "stop",
    "OPEN_PALM"  : "play_pause",
    "POINT"      : "next_track",
    "PEACE"      : "prev_track",
    "FINGER_GUN" : "volume_down",
    "NONE"       : "idle",
}

# ---------- Inference ----------
CONFIDENCE_THRESHOLD = 0.6   # Minimum confidence score required to dispatch an action.
                              # Predictions below this value are treated as NONE/idle.
COOLDOWN_FRAMES      = 15    # Minimum number of frames that must pass before the same
                              # gesture can trigger an action again (prevents rapid-fire repeats).
