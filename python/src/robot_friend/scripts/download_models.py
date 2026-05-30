import shutil
from pathlib import Path

from robot_friend.person.person_recognizer import YOLOModel
from ultralytics.utils.downloads import attempt_download_asset

from robot_friend.resource_handler import get_model_dir
from robot_friend.utils.clean_setup_dir import clean_setup_dir


def download_models():
    print("Downloading models...")

    out_dir = get_model_dir()
    clean_setup_dir(out_dir)

    def _download(m: YOLOModel) -> None:
        print(f'Downloading: {m}')
        src = Path(attempt_download_asset(m.value))
        model_out_dir = out_dir / m.value
        shutil.move(str(src), str(model_out_dir))

    for model in YOLOModel:
        _download(model)

if __name__ == '__main__':
    download_models()