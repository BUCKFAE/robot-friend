from pathlib import Path


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent / 'data'

def _get_model_dir() -> Path:
    return _get_data_dir() / 'models'

def get_yolo_model_dir() -> Path:
    return _get_model_dir() / 'yolo'

def get_whisper_model_dir() -> Path:
    return _get_model_dir() / 'whisper'

def get_vosk_model_dir() -> Path:
    return _get_model_dir() / 'vosk'
