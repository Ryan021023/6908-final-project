#!/bin/bash
# ============================================================
# install.sh — One-command dependency installer for the Pi.
#
# Usage:
#   bash install.sh
#
# What this script does:
#   1. Installs required system-level packages via apt.
#   2. Creates an isolated Python virtual environment (venv/).
#   3. Installs all Python packages listed in requirements.txt.
#   4. Creates the assets/music/ directory for audio files.
# ============================================================

set -e   # Exit immediately if any command returns a non-zero status

echo "=============================="
echo " CPSC 4908 Project Setup"
echo "=============================="

# Step 1 — System packages
# libatlas-base-dev  : optimised BLAS/LAPACK routines required by NumPy/MediaPipe
# libjpeg-dev        : JPEG codec needed by OpenCV
# libopenblas-dev    : alternative BLAS backend for faster linear algebra on ARM
# libhdf5-dev        : HDF5 I/O library (TensorFlow dependency)
# python3-pygame     : system-level SDL bindings used by pygame
echo "[1/5] Installing system packages..."
sudo apt update -q
sudo apt install -y python3-pip python3-venv i2c-tools libatlas-base-dev \
    libjpeg-dev libopenblas-dev libhdf5-dev python3-pygame

# Step 2 — Python virtual environment
# Using a venv keeps project dependencies isolated from the system Python.
echo "[2/5] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Step 3 — Python packages
echo "[3/5] Installing Python packages..."
pip install --upgrade pip
pip install RPLCD              # I²C LCD driver
pip install rpi_ws281x         # WS2812B LED strip driver
pip install opencv-python-headless  # OpenCV without GUI dependencies (lighter on Pi)
pip install mediapipe          # Hand landmark detection
pip install tflite-runtime     # Lightweight TFLite inference runtime (no full TF needed)
pip install pygame             # Audio playback

# Step 4 — Create the music asset directory
echo "[4/5] Creating directories..."
mkdir -p assets/music          # Place your .mp3 / .wav files here before running main.py

# Step 5 — Done
echo "[5/5] Setup complete!"
echo ""
echo "Next steps:"
echo "  Activate the virtual environment : source venv/bin/activate"
echo "  Run the hardware self-test       : python test_hardware.py"
echo "  Run the model self-test          : python test_model.py"
echo "  Start the main application       : sudo python main.py"
