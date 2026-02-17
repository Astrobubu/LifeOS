"""
HAL 9000 Voice Synthesis — Piper TTS
Converts text to OGG opus voice notes for Telegram.
"""
import io
import logging
import asyncio
import wave
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent / "models" / "hal-voice" / "hal.onnx"

_voice = None


def _get_voice():
    """Lazy-load the Piper voice model (singleton)."""
    global _voice
    if _voice is None:
        try:
            from piper import PiperVoice
            _voice = PiperVoice.load(str(MODEL_PATH))
            logger.info("HAL voice model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load HAL voice model: {e}")
            raise
    return _voice


def _synthesize_blocking(text: str) -> bytes:
    """Synthesize text to OGG opus bytes (blocking, runs in thread)."""
    from pydub import AudioSegment

    voice = _get_voice()

    # Synthesize to WAV in memory
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, "w") as wav_file:
        voice.synthesize_wav(text, wav_file)
    wav_buf.seek(0)

    # Convert WAV to OGG opus via pydub
    audio = AudioSegment.from_wav(wav_buf)
    ogg_buf = io.BytesIO()
    audio.export(ogg_buf, format="ogg", codec="libopus")
    return ogg_buf.getvalue()


async def synthesize(text: str) -> bytes | None:
    """Synthesize text to OGG opus bytes (async, non-blocking).

    Returns bytes on success, None on failure.
    """
    if not text or not text.strip():
        return None

    # Strip markdown formatting for cleaner speech
    clean = text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _synthesize_blocking, clean)
    except Exception as e:
        logger.error(f"Voice synthesis failed: {e}")
        return None
