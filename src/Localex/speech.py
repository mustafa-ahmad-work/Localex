"""
Windows SAPI local Text-to-Speech (TTS) engine.
Provides async speech, pause/resume, stop, volume, rate, and voice selection.
Works 100% offline using built-in Windows speech synthesis.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# SAPI Voice Flags
SVSFlagsAsync = 1
SVSFPurgeBeforeSpeak = 2


class SpeechEngine:
    """
    Manages offline speech synthesis via Windows SAPI.
    """

    def __init__(self) -> None:
        self._voice: Any = None
        self._is_paused = False
        self._is_speaking = False
        self._lock = threading.Lock()
        self._init_sapi()

    def _init_sapi(self) -> bool:
        with self._lock:
            try:
                import win32com.client
                # Initialize COM for the current thread
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                except Exception:
                    pass
                self._voice = win32com.client.Dispatch("SAPI.SpVoice")
                return True
            except Exception as e:
                logger.warning(f"Windows SAPI initialization failed: {e}")
                self._voice = None
                return False

    @property
    def is_available(self) -> bool:
        return self._voice is not None

    def get_voices(self) -> List[Dict[str, str]]:
        """Returns a list of installed voices with their IDs and readable descriptions."""
        if not self.is_available:
            self._init_sapi()
        if not self.is_available:
            return []

        voices_list: List[Dict[str, str]] = []
        try:
            tokens = self._voice.GetVoices()
            for i in range(tokens.Count):
                token = tokens.Item(i)
                desc = token.GetDescription()
                voices_list.append({
                    "id": token.Id,
                    "name": desc,
                })
        except Exception as e:
            logger.error(f"Error enumerating SAPI voices: {e}")
        return voices_list

    def set_voice(self, voice_identifier: str) -> bool:
        """Sets the active voice by token ID or description substring."""
        if not self.is_available:
            return False
        try:
            tokens = self._voice.GetVoices()
            for i in range(tokens.Count):
                token = tokens.Item(i)
                if token.Id == voice_identifier or voice_identifier in token.GetDescription():
                    self._voice.Voice = token
                    return True
        except Exception as e:
            logger.error(f"Failed to set voice: {e}")
        return False

    def set_rate(self, rate: int) -> None:
        """Rate ranges from -10 (slowest) to +10 (fastest). Default is 0."""
        if not self.is_available:
            return
        clamped_rate = max(-10, min(10, int(rate)))
        try:
            self._voice.Rate = clamped_rate
        except Exception as e:
            logger.error(f"Failed to set rate: {e}")

    def set_volume(self, volume: int) -> None:
        """Volume ranges from 0 to 100."""
        if not self.is_available:
            return
        clamped_vol = max(0, min(100, int(volume)))
        try:
            self._voice.Volume = clamped_vol
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")

    def speak(self, text: str, voice_id: Optional[str] = None, rate: Optional[int] = None, volume: Optional[int] = None) -> bool:
        """
        Speaks text asynchronously without blocking the UI thread.
        Purges any ongoing speech before starting new speech.
        """
        if not text or not text.strip():
            return False

        if not self.is_available:
            if not self._init_sapi():
                return False

        try:
            if voice_id:
                self.set_voice(voice_id)
            if rate is not None:
                self.set_rate(rate)
            if volume is not None:
                self.set_volume(volume)

            # SVSFlagsAsync (1) + SVSFPurgeBeforeSpeak (2) = 3
            self._voice.Speak(text, SVSFlagsAsync | SVSFPurgeBeforeSpeak)
            self._is_speaking = True
            self._is_paused = False
            return True
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            return False

    def pause(self) -> None:
        if self.is_available and not self._is_paused:
            try:
                self._voice.Pause()
                self._is_paused = True
            except Exception as e:
                logger.error(f"Failed to pause voice: {e}")

    def resume(self) -> None:
        if self.is_available and self._is_paused:
            try:
                self._voice.Resume()
                self._is_paused = False
            except Exception as e:
                logger.error(f"Failed to resume voice: {e}")

    def stop(self) -> None:
        """Immediately stops any speech."""
        if self.is_available:
            try:
                # Speak empty string with purge flag stops instantly
                self._voice.Speak("", SVSFPurgeBeforeSpeak)
                self._is_speaking = False
                self._is_paused = False
            except Exception as e:
                logger.error(f"Failed to stop voice: {e}")


# Singleton instance
default_speech = SpeechEngine()
