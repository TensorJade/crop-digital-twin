"""Bounded external weather failure categories, separate from agricultural accuracy."""

from crop_twin.domain.farm.rules import FarmError


class WeatherUnavailable(FarmError):
    """External data failed safely; no provider body or network exception is exposed."""
