"""Single entrypoint for fetching the project's ML assets.

Edit the three lists below to choose which YOLO, Vosk and Whisper models to
pull, then run this script. It is idempotent: assets already present on disk are
skipped, so re-running only fetches what is missing.

By default all asset groups are fetched. Pass a subset of ``GROUPS`` as
positional arguments to fetch only some — e.g. ``download_data.py vosk`` on the
Pi, which runs Hailo for image detection (no YOLO) and Vosk for ASR.
"""

import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from robot_friend.audio.backends.faster_whisper.whisper_audio_detector import (
    WhisperModel,
)
from robot_friend.audio.backends.vosk.vosk_model import VoskModel
from robot_friend.image.backends.ultralytics.yolo_detector import YOLOModel
from robot_friend.resource_handler import (
    get_vosk_model_dir,
    get_whisper_model_dir,
    get_yolo_model_dir,
)
from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.get_current_host import is_pi_host

# Edit these lists to choose which assets to download.
YOLO_MODELS = [YOLOModel.YOLO_V8N]
VOSK_MODELS = [VoskModel.VOSK_SMALL_EN_US_015, VoskModel.VOSK_SMALL_DE_015]
WHISPER_MODELS = [WhisperModel.SMALL]


def _is_present(target: Path) -> bool:
    """Report whether an asset already exists at ``target`` (file or non-empty dir)."""
    if target.is_dir():
        return any(target.iterdir())
    return target.is_file() and target.stat().st_size > 0


def _skip_if_present(label: str, target: Path) -> bool:
    """Log and report whether ``target`` is already present, so callers can skip.

    Args:
        label: Human-readable name of the asset, for logging.
        target: Path the asset would be written to.

    Returns:
        ``True`` if the asset already exists (and the download should be
        skipped), ``False`` otherwise.
    """
    if _is_present(target):
        finch_logger.info("Skipping %s, already present: %s", label, target)
        return True
    return False


def _download_yolo(model: YOLOModel) -> None:
    target = get_yolo_model_dir() / model.value
    if _skip_if_present(model.name, target):
        return
    # Imported lazily (like yolo_detector.py) so this module stays importable
    # without the `yolo` extra / Ultralytics config dir present.
    from ultralytics.utils.downloads import attempt_download_asset

    finch_logger.info("Downloading YOLO %s -> %s", model.name, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    src = Path(attempt_download_asset(model.value))
    shutil.move(str(src), str(target))


def _download_vosk(model: VoskModel) -> None:
    identifier = model.config.identifier
    target = get_vosk_model_dir() / identifier
    if _skip_if_present(model.name, target):
        return
    url = f"{model.config.base_url}/{identifier}.zip"
    finch_logger.info("Downloading Vosk %s: %s", identifier, url)
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_zip = Path(tmp) / f"{identifier}.zip"
        urllib.request.urlretrieve(url, tmp_zip)
        with zipfile.ZipFile(tmp_zip) as zf:
            zf.extractall(tmp)
        # The zip unpacks into a folder named after the archive; move its
        # contents into our stable, identifier-keyed dir.
        extracted = Path(tmp) / identifier
        for item in extracted.iterdir():
            shutil.move(str(item), str(target / item.name))
    finch_logger.info("  -> %s", target)


def _download_whisper(model: WhisperModel) -> None:
    target = get_whisper_model_dir() / f"whisper-{model.value}"
    if _skip_if_present(model.name, target):
        return
    # Imported lazily so this module stays importable (and vosk-only runs work)
    # without the `audio` extra's faster-whisper installed.
    from faster_whisper import download_model

    finch_logger.info("Downloading Whisper %s -> %s", model.name, target)
    target.mkdir(parents=True, exist_ok=True)
    download_model(model.value, output_dir=str(target))


if __name__ == "__main__":
    if not is_pi_host():
        [_download_yolo(m) for m in YOLO_MODELS]
    [_download_vosk(m) for m in VOSK_MODELS]
