"""Event handler for clients of the server."""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

import numpy as np
from livekit.wakeword import WakeWordModel
from wyoming.audio import AudioChunk, AudioChunkConverter, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, WakeModel, WakeProgram
from wyoming.server import AsyncEventHandler
from wyoming.wake import Detect, Detection, NotDetected

from . import __version__
from .state import State

_LOGGER = logging.getLogger(__name__)

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
FRAME_SAMPLES = 1280  # 80ms at 16kHz, matches livekit-wakeword's reference listener
CHUNK_FRAMES = 25  # 25 * 80ms = 2s window required by WakeWordModel.predict()

DEFAULT_MODEL = "hey_livekit"

LIVEKIT_ATTRIBUTION = Attribution(
    name="livekit", url="https://github.com/livekit/livekit-wakeword"
)
LAION_ATTRIBUTION = Attribution(
    name="laion",
    url="https://huggingface.co/laion/bud-e_wakeword-models_livekit-wakeword",
)

# Metadata for models bundled with this add-on: name -> (phrase, language, attribution)
BUNDLED_MODEL_INFO = {
    "hey_livekit": ("Hey LiveKit", "en", LIVEKIT_ATTRIBUTION),
    "nihao_livekit": ("Nihao LiveKit", "zh", LIVEKIT_ATTRIBUTION),
    "hey_buddy_en_medium": ("Hey Buddy", "en", LAION_ATTRIBUTION),
    "hey_buddy_en_small": ("Hey Buddy", "en", LAION_ATTRIBUTION),
    "hey_buddy_en_medium_v2": ("Hey Buddy", "en", LAION_ATTRIBUTION),
    "hey_buddy_en_large_v3": ("Hey Buddy", "en", LAION_ATTRIBUTION),
    "hey_buddy_de_medium": ("Hey Buddy", "de", LAION_ATTRIBUTION),
    "hey_buddy_de_small": ("Hey Buddy", "de", LAION_ATTRIBUTION),
    "stop_buddy_en_large_v2": ("Stop Buddy", "en", LAION_ATTRIBUTION),
    "go_buddy_en_large_v2": ("Go Buddy", "en", LAION_ATTRIBUTION),
}


@dataclass
class TriggerState:
    triggers_left: int
    is_detected: bool = False
    last_triggered: Optional[float] = None


class LiveKitWakeWordEventHandler(AsyncEventHandler):
    """Event handler for livekit-wakeword clients."""

    def __init__(
        self,
        threshold: float,
        trigger_level: int,
        refractory_seconds: float,
        state: State,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.client_id = str(time.monotonic_ns())
        self.threshold = threshold
        self.trigger_level = trigger_level
        self.refractory_seconds = refractory_seconds
        self.state = state
        self.converter = AudioChunkConverter(
            rate=SAMPLE_RATE, width=SAMPLE_WIDTH, channels=1
        )

        self.model = WakeWordModel()
        self.loaded_models: Dict[str, str] = {}  # name -> path loaded into self.model
        self.triggers: Dict[str, TriggerState] = {}

        self.pcm_buffer = bytearray()
        self.frame_buffer: Deque[np.ndarray] = deque(maxlen=CHUNK_FRAMES)
        self.audio_timestamp = 0

        _LOGGER.debug("Client connected: %s", self.client_id)

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            info = self._get_info()
            await self.write_event(info.event())
            _LOGGER.debug("Sent info to client: %s", self.client_id)
            return True

        if Detect.is_type(event.type):
            self._load_requested_models(Detect.from_event(event).names)
        elif AudioStart.is_type(event.type):
            _LOGGER.debug("Receiving audio from client: %s", self.client_id)

            self.audio_timestamp = 0
            self.pcm_buffer.clear()
            self.frame_buffer.clear()
            for ww_name in self.triggers:
                self.triggers[ww_name] = TriggerState(triggers_left=self.trigger_level)
        elif AudioChunk.is_type(event.type):
            chunk = self.converter.convert(AudioChunk.from_event(event))
            await self._process_audio(chunk.audio)
            self.audio_timestamp += chunk.milliseconds
        elif AudioStop.is_type(event.type):
            if not any(t.is_detected for t in self.triggers.values()):
                await self.write_event(NotDetected().event())
                _LOGGER.debug(
                    "Audio stopped without detection from client: %s", self.client_id
                )
        else:
            _LOGGER.debug("Unexpected event: type=%s, data=%s", event.type, event.data)

        return True

    def _load_requested_models(self, names) -> None:
        ww_names = set()
        if names:
            for ww_name in names:
                if ww_name in self.state.known_names():
                    ww_names.add(ww_name)

        if not ww_names:
            ww_names.add(DEFAULT_MODEL)

        for ww_name in ww_names - set(self.loaded_models.keys()):
            model_path = self.state.resolve_model(ww_name)
            if model_path is None:
                continue

            self.model.load_model(model_path, model_name=ww_name)
            self.loaded_models[ww_name] = str(model_path)
            self.triggers[ww_name] = TriggerState(triggers_left=self.trigger_level)

        for stale_name in set(self.triggers.keys()) - ww_names:
            self.triggers.pop(stale_name, None)

        _LOGGER.debug("Active models: %s", list(self.triggers.keys()))

    async def _process_audio(self, audio_bytes: bytes) -> None:
        self.pcm_buffer.extend(audio_bytes)

        frame_bytes = FRAME_SAMPLES * SAMPLE_WIDTH
        while len(self.pcm_buffer) >= frame_bytes:
            frame = np.frombuffer(
                bytes(self.pcm_buffer[:frame_bytes]), dtype=np.int16
            )
            del self.pcm_buffer[:frame_bytes]
            self.frame_buffer.append(frame)

            if len(self.frame_buffer) < CHUNK_FRAMES or not self.triggers:
                continue

            window = np.concatenate(list(self.frame_buffer))
            loop = asyncio.get_running_loop()
            scores = await loop.run_in_executor(None, self.model.predict, window)

            for ww_name, score in scores.items():
                trigger = self.triggers.get(ww_name)
                if trigger is None:
                    continue

                skip = (trigger.last_triggered is not None) and (
                    (time.monotonic() - trigger.last_triggered)
                    < self.refractory_seconds
                )
                if skip or score <= self.threshold:
                    continue

                trigger.triggers_left -= 1
                if trigger.triggers_left > 0:
                    continue

                trigger.is_detected = True
                trigger.last_triggered = time.monotonic()
                await self.write_event(
                    Detection(name=ww_name, timestamp=self.audio_timestamp).event()
                )
                _LOGGER.debug(
                    "Detected %s at %s (score=%.3f)",
                    ww_name,
                    self.audio_timestamp,
                    score,
                )

    async def disconnect(self) -> None:
        _LOGGER.debug("Client disconnected: %s", self.client_id)

    def _get_info(self) -> Info:
        models = []

        for name in sorted(self.state.bundled_models):
            phrase, language, attribution = BUNDLED_MODEL_INFO.get(
                name, (_get_phrase(name), "", Attribution(name="", url=""))
            )
            models.append(
                WakeModel(
                    name=name,
                    description=phrase,
                    phrase=phrase,
                    attribution=attribution,
                    installed=True,
                    languages=[language] if language else [],
                    version=__version__,
                )
            )

        for name in sorted(self.state.custom_models):
            phrase = _get_phrase(name)
            models.append(
                WakeModel(
                    name=name,
                    description=phrase,
                    phrase=phrase,
                    attribution=Attribution(name="", url=""),
                    installed=True,
                    languages=[],
                    version="",
                )
            )

        return Info(
            wake=[
                WakeProgram(
                    name="livekit-wakeword",
                    description=(
                        "Conv-attention wake word detection, backward compatible "
                        "with openWakeWord models."
                    ),
                    attribution=LIVEKIT_ATTRIBUTION,
                    installed=True,
                    version=__version__,
                    models=models,
                )
            ],
        )


def _get_phrase(name: str) -> str:
    phrase = name.lower().strip().replace("_", " ")
    return " ".join(w.capitalize() for w in phrase.split())
