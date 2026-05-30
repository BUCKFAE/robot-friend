import os
import shutil
from pathlib import Path


def clean_setup_dir(path: Path | str, delete_content: bool = True) -> None:
    """
    Creates or overrides a directory at the specified location
    :param path: The location where the new directory should be created
    :param delete_content: Whether to override existing content at the location
    """
    if os.path.isdir(path) and delete_content:
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=not delete_content)
