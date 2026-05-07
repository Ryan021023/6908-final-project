# ============================================================
# test_model.py — Minimal TFLite model smoke test.
#
# Purpose:
#   Load the gesture classification model directly via the
#   TFLite interpreter, run a single inference with a random
#   input tensor, and report the output shape and latency.
#   Use this to confirm the model file is valid and that the
#   TFLite runtime is installed and functional on the Pi.
#
# Usage:
#   source venv/bin/activate
#   python test_model.py
# ============================================================

import numpy as np
import time

# Try the lightweight tflite-runtime package first (recommended for Pi).
# Fall back to the full TensorFlow Lite interpreter if tflite-runtime
# is not installed.
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow as tf
    tflite = tf.lite

# ------------------------------------------------------------------
# Load the model and allocate tensor buffers
# ------------------------------------------------------------------
interpreter = tflite.Interpreter(model_path="gesture_model.lite")
interpreter.allocate_tensors()

# Retrieve metadata about the model's input and output tensors
input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Input  tensor shape:", input_details[0]['shape'])
print("Output tensor shape:", output_details[0]['shape'])

# ------------------------------------------------------------------
# Run a single inference with a random (dummy) input
# ------------------------------------------------------------------
# The input shape is read from the model itself so this test adapts
# automatically if the model is replaced with a different variant.
input_shape  = input_details[0]['shape']
dummy_input  = np.random.rand(*input_shape).astype(np.float32)

start = time.time()
interpreter.set_tensor(input_details[0]['index'], dummy_input)
interpreter.invoke()
output = interpreter.get_tensor(output_details[0]['index'])
end = time.time()

# ------------------------------------------------------------------
# Report results
# ------------------------------------------------------------------
print("Raw output (class probabilities):", output)
print(f"Inference time: {(end - start) * 1000:.2f} ms")
