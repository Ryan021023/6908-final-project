# ============================================================
# gesture/classifier.py — TFLite gesture classification model.
#
# Responsibilities:
#   - Load the TFLite model and its class-label file at startup.
#   - Accept a preprocessed image tensor from HandDetector and
#     return the predicted gesture name with its confidence score.
#   - Suppress low-confidence predictions by returning "NONE"
#     when the top score falls below the configured threshold.
# ============================================================

import numpy as np

# Prefer the lightweight tflite-runtime package (smaller install, faster
# import on Pi). Fall back to the full TensorFlow Lite interpreter if
# tflite-runtime is not installed.
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow as tf
    tflite = tf.lite


class GestureClassifier:
    """
    Runs TFLite inference on a preprocessed hand-region tensor and
    maps the output probability vector to a human-readable gesture label.

    Args:
        model_path  (str):   Path to the .lite / .tflite model file.
        labels_path (str):   Path to the plain-text labels file.
                             Each non-empty line is one class name,
                             in the same order as the model's output nodes.
        threshold   (float): Confidence threshold in [0, 1]. Predictions
                             with a top score below this value are returned
                             as ("NONE", confidence) instead of a real label.
    """

    def __init__(self, model_path, labels_path, threshold=0.75):
        self.threshold = threshold

        # ------------------------------------------------------------------
        # Load class labels from the text file.
        # Each line corresponds to one output neuron (index 0, 1, 2, …).
        # Blank lines are skipped so the file can include blank lines for
        # readability without corrupting the index mapping.
        # ------------------------------------------------------------------
        self.labels = {}
        with open(labels_path, "r") as f:
            for idx, line in enumerate(f):
                name = line.strip()
                if name:
                    self.labels[idx] = name

        # ------------------------------------------------------------------
        # Load the TFLite model and allocate memory for its input/output
        # tensors. allocate_tensors() must be called before set_tensor()
        # or invoke() will raise an error.
        # ------------------------------------------------------------------
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        self.input_details  = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def predict(self, features):
        """
        Run a single inference pass and return the top gesture prediction.

        Args:
            features (numpy.ndarray): Preprocessed input tensor of shape
                                      (1, 224, 224, 1), dtype float32.
                                      Produced by HandDetector.preprocess_for_model().

        Returns:
            gesture    (str):   Predicted gesture label (e.g. "THUMBS_UP"),
                                or "NONE" if confidence is below the threshold
                                or if features is None.
            confidence (float): Probability of the top class in [0.0, 1.0].
        """
        # Guard against None input — can happen if the detector had no frame
        if features is None:
            return "NONE", 0.0

        # Copy the input tensor into the interpreter's input buffer
        self.interpreter.set_tensor(self.input_details[0]['index'], features)

        # Execute the model
        self.interpreter.invoke()

        # Retrieve the output probability vector (one value per gesture class)
        output = self.interpreter.get_tensor(self.output_details[0]['index'])[0]

        # Find the index of the highest-probability class
        idx        = int(np.argmax(output))
        confidence = float(output[idx])

        # Reject low-confidence predictions to avoid spurious actions
        if confidence < self.threshold:
            return "NONE", confidence

        # Map the winning index to its label name; fall back to "UNKNOWN"
        # if the index is somehow not present in the labels dictionary
        gesture = self.labels.get(idx, "UNKNOWN")
        return gesture, confidence
