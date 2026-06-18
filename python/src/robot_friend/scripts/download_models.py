import shutil
from pathlib import Path

from ultralytics.utils.downloads import attempt_download_asset

from robot_friend.image.backends.ultralytics.YOLODetector import YOLOModel
from robot_friend.resource_handler import get_yolo_model_dir
from robot_friend.utils.clean_setup_dir import clean_setup_dir
from robot_friend.utils.finch_logger import finch_logger


def download_models():
    finch_logger.info("Downloading models...")

    out_dir = get_yolo_model_dir()
    clean_setup_dir(out_dir)

    def _download(m: YOLOModel) -> None:
        finch_logger.info("Downloading: %s", m)
        src = Path(attempt_download_asset(m.value))
        model_out_dir = out_dir / m.value
        shutil.move(str(src), str(model_out_dir))

    for model in YOLOModel:
        _download(model)

if __name__ == '__main__':
    download_models()
