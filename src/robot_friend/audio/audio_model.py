from abc import ABC, abstractmethod


class AudioModel(ABC):
    """A downloadable ASR model (Vosk or Whisper), identified by name.

    Implemented by the per-backend model enums so the download script and the
    backends can treat any model uniformly.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return the model's stable identifier (used for logging and paths)."""
        ...