# ============================================================
# control/audio_player.py — Music playback controller.
#
# Uses pygame.mixer to play .mp3 and .wav files from a local
# directory. Supports play/pause toggle, stop, next/prev track
# navigation, and stepped volume control.
#
# The playlist is built once at startup by globbing the music
# directory. Tracks are sorted alphabetically so playback order
# is deterministic.
# ============================================================

import pygame
import os
import glob


class AudioPlayer:
    """
    Manages a playlist and delegates all audio output to pygame.mixer.

    Args:
        music_dir (str): Directory to scan for .mp3 and .wav files.
                         Defaults to "assets/music".
    """

    def __init__(self, music_dir="assets/music"):
        pygame.mixer.init()

        self.music_dir   = music_dir
        # Build a sorted playlist of all .mp3 and .wav files in the directory
        self.playlist    = sorted(
            glob.glob(os.path.join(music_dir, "*.mp3")) +
            glob.glob(os.path.join(music_dir, "*.wav"))
        )
        self.current_idx = 0      # Index of the currently loaded track
        self.volume      = 0.5    # Initial volume: 50%

        pygame.mixer.music.set_volume(self.volume)

        # Pre-load the first track so it is ready to play immediately
        if self.playlist:
            self._load(self.current_idx)

    # ── Internal helpers ─────────────────────────────────────

    def _load(self, idx):
        """Load the track at playlist[idx] into the mixer buffer."""
        pygame.mixer.music.load(self.playlist[idx])

    def _has_music(self):
        """Return True if at least one audio file was found in music_dir."""
        return len(self.playlist) > 0

    # ── Playback controls ────────────────────────────────────

    def play_pause(self):
        """
        Toggle between playing and paused states.

        - If music is currently playing  → pause it.
        - If music is paused (get_pos != -1) → unpause (resume from position).
        - If music has never been started (get_pos == -1) → start from beginning.
        """
        if not self._has_music():
            return

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
        else:
            if pygame.mixer.music.get_pos() == -1:
                # Track has not been started yet
                pygame.mixer.music.play()
            else:
                # Track was paused — resume from where it left off
                pygame.mixer.music.unpause()

    def stop(self):
        """Stop playback completely and reset the playback position."""
        pygame.mixer.music.stop()

    def next_track(self):
        """
        Advance to the next track in the playlist and start playing.
        Wraps around to the first track after the last one.
        """
        if not self._has_music():
            return
        self.current_idx = (self.current_idx + 1) % len(self.playlist)
        self._load(self.current_idx)
        pygame.mixer.music.play()

    def prev_track(self):
        """
        Return to the previous track in the playlist and start playing.
        Wraps around to the last track when called from the first track.
        """
        if not self._has_music():
            return
        self.current_idx = (self.current_idx - 1) % len(self.playlist)
        self._load(self.current_idx)
        pygame.mixer.music.play()

    # ── Volume controls ──────────────────────────────────────

    def volume_up(self):
        """
        Increase volume by 10%, capped at 100%.

        Returns:
            float: New volume level in [0.0, 1.0].
        """
        self.volume = min(1.0, self.volume + 0.1)
        pygame.mixer.music.set_volume(self.volume)
        return self.volume

    def volume_down(self):
        """
        Decrease volume by 10%, floored at 0%.

        Returns:
            float: New volume level in [0.0, 1.0].
        """
        self.volume = max(0.0, self.volume - 0.1)
        pygame.mixer.music.set_volume(self.volume)
        return self.volume

    # ── State queries ────────────────────────────────────────

    def is_playing(self):
        """Return True if audio is actively playing (not paused or stopped)."""
        return pygame.mixer.music.get_busy()

    def current_track(self):
        """
        Return the file path of the currently loaded track.
        Used by LCDDisplay to show the track name on screen.

        Returns:
            str: Absolute or relative file path, or "" if the playlist is empty.
        """
        if self.playlist:
            return self.playlist[self.current_idx]
        return ""

    def get_volume_pct(self):
        """Return the current volume as an integer percentage (0–100)."""
        return int(self.volume * 100)

    # ── Cleanup ──────────────────────────────────────────────

    def close(self):
        """Stop playback and shut down the pygame mixer cleanly."""
        pygame.mixer.music.stop()
        pygame.mixer.quit()
