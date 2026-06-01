"""Instância única de Jinja2Templates compartilhada pelos routers web."""
import subprocess
from datetime import datetime

from fastapi.templating import Jinja2Templates


def _get_git_version() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "0"


templates = Jinja2Templates(directory="../frontend/templates")
templates.env.globals["now"] = datetime.utcnow
templates.env.globals["static_version"] = _get_git_version()
