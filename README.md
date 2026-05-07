# 6908-final-project

# Gesture-Controlled Music Player

A Raspberry Pi project that lets you control music playback using hand gestures — no buttons, no touchscreen. Just wave your hand in front of the camera.

Built for EECS 6908 Final Project.

---

## Overview

This system uses a Pi Camera to capture live video, runs hand landmark detection via MediaPipe, and classifies the detected gesture with a custom TFLite model. Recognized gestures are mapped to audio commands (play/pause, next track, volume, etc.) and dispatched in real time. Status is shown on an I²C LCD display, and a WS2812B LED strip provides visual feedback for the current playback state.

---

## Supported Gestures

| Gesture | Action |
|---|---|
| Thumbs Up | Volume Up |
| Thumbs Down | Volume Down |
| Fist | Stop |
| Open Palm | Play |
| Point Up | Next Track |
| Peace | Previous Track |
| ILoveYou | Mute |
| _(none)_ | Idle |

---

## Hardware Requirements

- Raspberry Pi (Pi 4 or Pi 5 recommended)
- Raspberry Pi Camera Module (compatible with `rpicam-vid`)
- 16×2 I²C LCD display (default address `0x27`)
- WS2812B LED strip — 12 LEDs or more, connected to GPIO 10 (PWM0)
- Speaker or audio output connected to the Pi
- Power supply adequate for Pi + LEDs (≥3A recommended)

---

## Project Structure

```
.
├── main.py                  # Entry point — camera loop, inference, dispatch
├── config.py                # All hardware & model parameters in one place
├── install.sh               # One-command dependency installer
├── requirements.txt         # Python package list
├── gesture_model.lite       # Trained TFLite gesture classification model
├── gesture_recognizer.task  # MediaPipe gesture recognizer task file
├── labels.txt               # Gesture class labels
├── gesture/
│   ├── detector.py          # Hand landmark detection (MediaPipe)
│   └── classifier.py        # TFLite inference wrapper
├── control/
│   ├── audio_player.py      # pygame-based music playback
│   ├── command_dispatcher.py# Maps gestures → actions
│   ├── lcd_display.py       # RPLCD I²C display driver
│   └── led_controller.py    # rpi_ws281x LED strip control
├── assets/
│   └── music/               # Drop your .mp3 / .wav files here
├── test_hardware.py         # Hardware sanity check (LCD, LED, audio)
└── test_model.py            # Model inference sanity check
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ryan021023/6908-final-project.git
cd 6908-final-project
```

### 2. Run the installer

```bash
bash install.sh
```

This will install all system packages, create a Python virtual environment, and install all Python dependencies.

### 3. Add music files

Place `.mp3` or `.wav` files into the `assets/music/` directory:

```bash
cp your_songs/*.mp3 assets/music/
```

### 4. Verify hardware (optional but recommended)

```bash
source venv/bin/activate
python test_hardware.py
python test_model.py
```

---

## Running

```bash
source venv/bin/activate
sudo python main.py
```

> `sudo` is required for WS2812B LED control via the PWM/DMA interface.

Press **`q`** in the preview window or **`Ctrl+C`** in the terminal to shut down cleanly.

---

## Configuration

All tunable parameters live in `config.py` — no need to touch source code:

| Parameter | Default | Description |
|---|---|---|
| `MODEL_PATH` | `gesture_model.lite` | Path to TFLite model |
| `LABELS_PATH` | `labels.txt` | Path to class labels |
| `CONFIDENCE_THRESHOLD` | `0.6` | Minimum confidence to trigger an action |
| `COOLDOWN_FRAMES` | `15` | Frames to wait before the same gesture fires again |
| `LCD_ADDRESS` | `0x27` | I²C address (run `i2cdetect -y 1` to check yours) |
| `LED_COUNT` | `12` | Number of WS2812B LEDs |
| `LED_PIN` | `10` | GPIO pin for LED data line |
| `LED_BRIGHTNESS` | `16` | LED brightness 0–255 |
| `FRAME_WIDTH/HEIGHT` | `640×480` | Camera capture resolution |

---

## Dependencies

| Package | Purpose |
|---|---|
| `opencv-python-headless` | Camera capture & frame processing |
| `mediapipe` | Hand landmark detection |
| `tflite-runtime` | Lightweight gesture classification inference |
| `pygame` | Audio playback |
| `RPLCD` | I²C LCD display driver |
| `rpi-ws281x` | WS2812B LED strip control |
| `numpy` | Array operations |

---

## Troubleshooting

**Camera not detected**
Ensure the camera is enabled: `sudo raspi-config` → Interface Options → Camera. Verify `rpicam-vid` works standalone before running the project.

**LCD shows nothing**
Run `i2cdetect -y 1` and update `LCD_ADDRESS` in `config.py` to match the detected address.

**LEDs don't light up**
Make sure you're running with `sudo`. The WS2812B driver requires DMA access. Check that `LED_PIN` matches your wiring.

**Low FPS / dropped frames**
Lower `FRAME_WIDTH`/`FRAME_HEIGHT` in `config.py`, or reduce `mediapipe` model complexity in `gesture/detector.py`.

---

## License

For academic use — EECS 6908 Final Project.
