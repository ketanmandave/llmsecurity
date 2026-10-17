from app.gateway.response_security.detectors.base import ConfiguredRegexResponseDetector, register_response_detector


@register_response_detector
class ToxicityDetector(ConfiguredRegexResponseDetector):
    config_name = "ToxicityDetector"
