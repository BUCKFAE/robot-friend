import sys

from faster_whisper import download_model

from robot_friend.resource_handler import get_yolo_model_dir
from robot_friend.speech.backends.faster_whisper.WhisperTranscriber import WhisperModel
from robot_friend.utils.clean_setup_dir import clean_setup_dir
from robot_friend.utils.get_current_host import is_pi_host


def download_whisper_models(models: list[WhisperModel]):
    print("Downloading whisper models...")

    out_dir = get_yolo_model_dir()

    def _download(m: WhisperModel) -> None:
        print(f'Downloading: {m}')
        model_out_dir = out_dir / f'whisper-{str(m.value)}'
        clean_setup_dir(model_out_dir)
        download_model(m.value, output_dir=str(model_out_dir))

    for model in models:
        _download(model)


if __name__ == '__main__':
    models = list(WhisperModel) if not is_pi_host() else [
        WhisperModel.SMALL
    ]
    download_whisper_models(models)
