# ============================================================
# gesture/detector.py — Hand landmark detection using MediaPipe.
#
# Responsibilities:
#   - Detect up to N hands in each BGR video frame.
#   - Draw skeleton landmarks onto the frame for visual feedback.
#   - Preprocess the detected hand region into a normalised
#     image tensor suitable for the TFLite classifier.
# ============================================================

import cv2
import mediapipe as mp
import numpy as np


class HandDetector:
    """
    Wraps MediaPipe's Hands solution to provide per-frame hand
    detection and landmark extraction.

    Args:
        max_hands      (int):   Maximum number of hands to track simultaneously.
        detection_conf (float): Minimum confidence for the initial hand-detection
                                model to accept a detection (0.0–1.0).
        tracking_conf  (float): Minimum confidence for the landmark-tracking model
                                to keep tracking a hand across frames (0.0–1.0).
                                If tracking falls below this value, detection is
                                re-run on that hand.
    """

    def __init__(self, max_hands=2, detection_conf=0.7, tracking_conf=0.5):
        self.mp_hands = mp.solutions.hands
        self.mp_draw  = mp.solutions.drawing_utils

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,          # Optimised for video streams, not static images
            max_num_hands=max_hands,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )

    def detect(self, frame):
        """
        Run hand detection on a single BGR frame.

        MediaPipe requires RGB input, so the frame is converted before
        processing, then the annotated BGR frame is returned alongside
        the raw landmark data.

        Args:
            frame (numpy.ndarray): BGR image from the camera.

        Returns:
            frame          (numpy.ndarray): The same frame with landmark
                                            skeletons drawn on it.
            landmarks_list (list[list[tuple]]): One entry per detected hand.
                           Each entry is a list of 21 (x, y, z) tuples
                           where x and y are normalised to [0, 1] relative
                           to the frame dimensions, and z is depth relative
                           to the wrist.
        """
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        landmarks_list = []

        if results.multi_hand_landmarks:
            for hand_lm in results.multi_hand_landmarks:
                # Draw the 21-point skeleton and the connections between them
                self.mp_draw.draw_landmarks(
                    frame, hand_lm, self.mp_hands.HAND_CONNECTIONS
                )
                # Collect the raw landmark coordinates for this hand
                lm = [(p.x, p.y, p.z) for p in hand_lm.landmark]
                landmarks_list.append(lm)

        return frame, landmarks_list

    def preprocess_for_model(self, frame, landmarks_list):
        """
        Convert the detected hand region into the input tensor expected
        by the TFLite gesture classifier.

        Processing steps:
          1. If a hand is detected, compute an axis-aligned bounding box
             around all 21 landmarks with a 40-pixel padding on each side.
          2. Crop that region of interest (ROI) from the frame.
             If no hand is present, use the entire frame as the ROI.
          3. Convert the ROI to grayscale (reduces input size and removes
             colour information that is irrelevant for gesture shape).
          4. Resize to 224×224 pixels to match the model's expected input.
          5. Normalise pixel values from [0, 255] to [0.0, 1.0].
          6. Reshape to (1, 224, 224, 1) — batch size 1, single channel.

        Args:
            frame          (numpy.ndarray): Current BGR frame (used for cropping).
            landmarks_list (list):          Output of detect(); may be empty.

        Returns:
            numpy.ndarray: Float32 tensor of shape (1, 224, 224, 1).
        """
        h, w = frame.shape[:2]

        if landmarks_list:
            lm = landmarks_list[0]  # Use the first (most prominent) hand only

            # Convert normalised coordinates to absolute pixel positions
            xs = [p[0] * w for p in lm]
            ys = [p[1] * h for p in lm]

            # Compute bounding box with 40 px padding, clamped to frame edges
            x1 = max(0, int(min(xs)) - 40)
            x2 = min(w, int(max(xs)) + 40)
            y1 = max(0, int(min(ys)) - 40)
            y2 = min(h, int(max(ys)) + 40)

            roi = frame[y1:y2, x1:x2]
        else:
            # No hand detected — fall back to the full frame so the pipeline
            # always receives a valid tensor (classifier will likely return NONE)
            roi = frame

        gray       = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        resized    = cv2.resize(gray, (224, 224))
        normalized = resized.astype(np.float32) / 255.0

        return normalized.reshape(1, 224, 224, 1)

    def close(self):
        """Release the MediaPipe Hands resources."""
        self.hands.close()
