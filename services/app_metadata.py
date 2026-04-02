from pathlib import Path
import sys


def _get_runtime_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _load_app_version():
    version_file = _get_runtime_root() / "VERSION"
    if version_file.exists():
        version = version_file.read_text(encoding="utf-8-sig").strip()
        if version:
            return version
    return "1.1.0"


APP_NAME = " "
APP_VERSION = _load_app_version()
COMPANY_NAME = "CDA"
FILE_DESCRIPTION = ""
PRODUCT_NAME = ""
