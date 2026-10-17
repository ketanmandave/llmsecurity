from app.gateway.response_security.detectors.base import ConfiguredRegexResponseDetector, register_response_detector


@register_response_detector
class HallucinationMarkerDetector(ConfiguredRegexResponseDetector):
    config_name = "HallucinationMarkerDetector"
