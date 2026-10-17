import importlib
import pkgutil

from app.gateway.response_security.detectors.base import BaseResponseDetector, registered_detectors


def discover_response_detectors() -> list[type[BaseResponseDetector]]:
    for module in pkgutil.iter_modules(__path__):
        if module.name != "base":
            importlib.import_module(f"{__name__}.{module.name}")
    return registered_detectors()
