"""
Audio Stream Worker Module

A background audio stream worker using sounddevice that captures audio in a
background thread, processes chunks, calculates audio metrics, and maintains
a ring buffer for pre-roll extraction.

This module is self-contained and does not depend on other project modules
(except numpy).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

logger = logging.getLogger(__name__)

# --- Status Codes ---
AUDIO_STOPPED = "AUDIO_STOPPED"
AUDIO_STARTING = "AUDIO_STARTING"
AUDIO_RUNNING = "AUDIO_RUNNING"
AUDIO_DEVICE_ERROR = "AUDIO_DEVICE_ERROR"
AUDIO_READ_ERROR = "AUDIO_READ_ERROR"


@dataclass
class AudioStreamStatus:
    """Status dataclass containing all current audio stream metrics.

    Attributes:
        status: Current status code (one of AUDIO_STOPPED, AUDIO_STARTING,
                AUDIO_RUNNING, AUDIO_DEVICE_ERROR, AUDIO_READ_ERROR).
        rms: Root mean square of the most recent audio chunk.
        peak: Peak absolute amplitude of the most recent audio chunk.
        dbfs: Decibels relative to full scale of the most recent chunk.
        sample_rate: The sample rate in Hz.
        chunk_duration_ms: Duration of each processed chunk in milliseconds.
        buffer_duration_s: Total ring buffer duration in seconds.
        buffer_fill_s: How many seconds of audio are currently in the buffer.
        device_id: The device ID currently in use (or None).
        error_message: Description of the last error, if any.
    """

    status: str = AUDIO_STOPPED
    rms: float = 0.0
    peak: float = 0.0
    dbfs: float = -96.0
    sample_rate: int = 16000
    chunk_duration_ms: int = 100
    buffer_duration_s: float = 30.0
    buffer_fill_s: float = 0.0
    device_id: Optional[int] = None
    error_message: str = ""


class AudioRingBuffer:
    """A circular audio buffer backed by a numpy array.

    Provides efficient write and read operations for streaming audio data.
    The buffer holds a fixed number of samples and overwrites the oldest
    data when full.

    Args:
        max_samples: Maximum number of samples the buffer can hold.
        dtype: Numpy dtype for the buffer array.
    """

    def __init__(self, max_samples: int, dtype=np.float32):
        self._buffer = np.zeros(max_samples, dtype=dtype)
        self._max_samples = max_samples
        self._write_pos = 0
        self._total_written = 0

    @property
    def fill_level(self) -> int:
        """Number of valid samples currently in the buffer."""
        return min(self._total_written, self._max_samples)

    @property
    def max_samples(self) -> int:
        """Maximum capacity of the buffer in samples."""
        return self._max_samples

    def write(self, data: np.ndarray) -> None:
        """Write audio samples into the ring buffer.

        If data is larger than buffer capacity, only the last max_samples
        are retained.

        Args:
            data: 1D numpy array of audio samples to write.
        """
        n = len(data)
        if n == 0:
            return

        if n >= self._max_samples:
            # Only keep the last max_samples worth of data
            self._buffer[:] = data[-self._max_samples:]
            self._write_pos = 0
            self._total_written += n
            return

        # Calculate how much fits before wrapping
        space_to_end = self._max_samples - self._write_pos
        if n <= space_to_end:
            self._buffer[self._write_pos:self._write_pos + n] = data
        else:
            # Split write across the wrap boundary
            self._buffer[self._write_pos:] = data[:space_to_end]
            remainder = n - space_to_end
            self._buffer[:remainder] = data[space_to_end:]

        self._write_pos = (self._write_pos + n) % self._max_samples
        self._total_written += n

    def read_last(self, num_samples: int) -> np.ndarray:
        """Read the last N samples from the buffer.

        Args:
            num_samples: Number of most recent samples to retrieve.

        Returns:
            1D numpy array containing the requested samples. If fewer
            samples are available than requested, returns only what is
            available.
        """
        available = self.fill_level
        if num_samples > available:
            num_samples = available

        if num_samples == 0:
            return np.array([], dtype=self._buffer.dtype)

        # Calculate the start read position
        end_pos = self._write_pos
        start_pos = (end_pos - num_samples) % self._max_samples

        if start_pos < end_pos:
            return self._buffer[start_pos:end_pos].copy()
        else:
            # Wrapped read
            part1 = self._buffer[start_pos:]
            part2 = self._buffer[:end_pos]
            return np.concatenate([part1, part2])

    def clear(self) -> None:
        """Reset the buffer, clearing all stored audio data."""
        self._buffer[:] = 0
        self._write_pos = 0
        self._total_written = 0


class AudioStreamWorker:
    """Background audio stream worker using sounddevice.

    Opens a sounddevice InputStream in a background thread, processes audio
    in configurable chunks, calculates RMS/peak/dBFS metrics, and maintains
    a ring buffer holding the last 30 seconds of audio for pre-roll extraction.

    All errors are caught internally to prevent crashing the application.
    Thread-safe access to shared state is ensured via a threading lock.

    Args:
        sample_rate: Audio sample rate in Hz. Default 16000.
        chunk_duration_ms: Duration of each processing chunk in milliseconds.
            Default 100.
        buffer_duration_s: Duration of the ring buffer in seconds. Default 30.

    Example:
        >>> worker = AudioStreamWorker(sample_rate=16000)
        >>> worker.start()
        >>> status = worker.get_status()
        >>> pre_roll = worker.get_pre_roll(ms=2000)
        >>> worker.stop()
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration_ms: int = 100,
        buffer_duration_s: float = 30.0,
    ):
        self._sample_rate = sample_rate
        self._chunk_duration_ms = chunk_duration_ms
        self._buffer_duration_s = buffer_duration_s

        # Calculate derived values
        self._chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
        self._buffer_max_samples = int(sample_rate * buffer_duration_s)

        # Ring buffer for audio storage
        self._ring_buffer = AudioRingBuffer(self._buffer_max_samples)

        # Thread-safe shared state
        self._lock = threading.Lock()
        self._status = AUDIO_STOPPED
        self._rms = 0.0
        self._peak = 0.0
        self._dbfs = -96.0
        self._device_id: Optional[int] = None
        self._error_message = ""

        # Stream and thread management
        self._stream: Optional[object] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self, device_id: Optional[int] = None) -> None:
        """Start the audio stream in a background thread.

        Opens a sounddevice InputStream on the specified device (or default)
        and begins processing audio chunks.

        Args:
            device_id: The sounddevice device index to use. If None, uses
                the system default input device.
        """
        with self._lock:
            if self._status == AUDIO_RUNNING or self._status == AUDIO_STARTING:
                logger.warning("Audio stream already running or starting.")
                return
            self._status = AUDIO_STARTING
            self._device_id = device_id
            self._error_message = ""

        self._stop_event.clear()
        self._ring_buffer.clear()

        self._thread = threading.Thread(
            target=self._stream_loop,
            name="AudioStreamWorker",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the audio stream and clean up resources.

        Signals the background thread to stop, waits for it to finish,
        and closes the sounddevice stream.
        """
        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        with self._lock:
            self._status = AUDIO_STOPPED
            self._rms = 0.0
            self._peak = 0.0
            self._dbfs = -96.0
            self._error_message = ""

        self._stream = None
        self._thread = None

    def get_status(self) -> AudioStreamStatus:
        """Get the current audio stream status and metrics.

        Returns:
            AudioStreamStatus dataclass with all current metrics.
        """
        with self._lock:
            return AudioStreamStatus(
                status=self._status,
                rms=self._rms,
                peak=self._peak,
                dbfs=self._dbfs,
                sample_rate=self._sample_rate,
                chunk_duration_ms=self._chunk_duration_ms,
                buffer_duration_s=self._buffer_duration_s,
                buffer_fill_s=self._ring_buffer.fill_level / self._sample_rate,
                device_id=self._device_id,
                error_message=self._error_message,
            )

    def get_pre_roll(self, ms: int) -> np.ndarray:
        """Extract the last N milliseconds of audio from the ring buffer.

        Args:
            ms: Number of milliseconds of audio to retrieve.

        Returns:
            1D numpy float32 array containing the requested pre-roll audio.
            If fewer samples are available, returns only what is available.
        """
        num_samples = int(self._sample_rate * ms / 1000)
        with self._lock:
            return self._ring_buffer.read_last(num_samples)

    def _stream_loop(self) -> None:
        """Main background thread loop that opens the stream and reads chunks.

        This method runs in a daemon thread and handles all exceptions
        internally to avoid crashing the application.
        """
        if sd is None:
            with self._lock:
                self._status = AUDIO_DEVICE_ERROR
                self._error_message = "sounddevice module is not installed."
            logger.error("sounddevice is not available. Cannot start audio stream.")
            return

        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self._chunk_samples,
                device=self._device_id,
            )
            self._stream.start()
        except Exception as e:
            with self._lock:
                self._status = AUDIO_DEVICE_ERROR
                self._error_message = f"Failed to open audio device: {e}"
            logger.error("Failed to open audio device: %s", e)
            return

        with self._lock:
            self._status = AUDIO_RUNNING

        logger.info(
            "Audio stream started: rate=%d, chunk=%dms, device=%s",
            self._sample_rate,
            self._chunk_duration_ms,
            self._device_id,
        )

        try:
            while not self._stop_event.is_set():
                try:
                    data, overflowed = self._stream.read(self._chunk_samples)
                    if overflowed:
                        logger.debug("Audio input overflow detected.")
                except Exception as e:
                    with self._lock:
                        self._status = AUDIO_READ_ERROR
                        self._error_message = f"Audio read error: {e}"
                    logger.error("Audio read error: %s", e)
                    # Brief pause before retrying to avoid tight error loops
                    time.sleep(0.1)
                    continue

                # Flatten to 1D mono
                chunk = data[:, 0] if data.ndim > 1 else data.flatten()

                # Calculate metrics
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                peak = float(np.max(np.abs(chunk)))

                # Calculate dBFS (decibels relative to full scale)
                if rms > 0:
                    dbfs = float(20.0 * np.log10(rms))
                else:
                    dbfs = -96.0

                # Clamp dBFS to a reasonable floor
                dbfs = max(dbfs, -96.0)

                # Update shared state under lock
                with self._lock:
                    self._rms = rms
                    self._peak = peak
                    self._dbfs = dbfs
                    self._status = AUDIO_RUNNING
                    self._error_message = ""
                    self._ring_buffer.write(chunk)

        except Exception as e:
            with self._lock:
                self._status = AUDIO_READ_ERROR
                self._error_message = f"Unexpected stream error: {e}"
            logger.error("Unexpected error in audio stream loop: %s", e)
        finally:
            # Clean up the stream
            try:
                if self._stream is not None:
                    self._stream.stop()
                    self._stream.close()
            except Exception as e:
                logger.debug("Error closing audio stream: %s", e)

            logger.info("Audio stream loop exited.")
