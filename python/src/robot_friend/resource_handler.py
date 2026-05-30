from pathlib import Path


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent / 'data'

def get_model_dir() -> Path:
    return _get_data_dir() / 'models'
