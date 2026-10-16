from collections import namedtuple
from pathlib import Path


settings_path = Path(__file__).resolve().parent / "settings.txt"
settings = {}


def get_settings():
    if settings:
        return settings
    Reviewer = namedtuple("Reviewer", "name username")
    if not settings_path.exists():
        return settings

    for line in settings_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "reviewer":
            if "reviewers" not in settings:
                settings["reviewers"] = []
            name, username = value.split(",")
            name = name.strip()
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            username = username.strip()
            settings["reviewers"].append(Reviewer(name, username))
        else:
            settings[key] = value
    return settings
