import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from robot_friend.resource_handler import get_vosk_model_dir
from robot_friend.speech.backends.vosk.vosk_model import VoskModel
from robot_friend.utils.clean_setup_dir import clean_setup_dir
from robot_friend.utils.finch_logger import finch_logger


def download_vosk_models() -> None:
    finch_logger.info("Downloading vosk models...")

    for model in VoskModel:

        identifier = model.value.identifier
        url = f'{model.value.base_url}/{identifier}.zip'
        out_dir = get_vosk_model_dir() / identifier
        finch_logger.info("Downloading %s: %s", identifier, url)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_zip = Path(tmp) / f'{identifier}.zip'
            urllib.request.urlretrieve(url, tmp_zip)
            with zipfile.ZipFile(tmp_zip) as zf:
                zf.extractall(tmp)
            # The zip unpacks into a folder named after the archive; move its
            # contents to our stable, language-keyed dir (e.g. data/models/vosk-de).
            extracted = Path(tmp) / identifier
            clean_setup_dir(out_dir)
            for item in extracted.iterdir():
                shutil.move(str(item), str(out_dir / item.name))
        finch_logger.info("  -> %s", out_dir)




if __name__ == '__main__':
    download_vosk_models()
