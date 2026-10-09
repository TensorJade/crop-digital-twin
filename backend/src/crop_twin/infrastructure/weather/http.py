"""Small bounded HTTPS transport for exactly two public data endpoints."""

from threading import BoundedSemaphore
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from crop_twin.domain.simulation.weather import WeatherUnavailable

POWER_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/hourly/point"
STATION_ENDPOINT = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"


class NoRedirect(HTTPRedirectHandler):
    """A provider redirect cannot turn a fixed source into an arbitrary network target."""

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise HTTPError(req.full_url, code, "Redirect rejected", headers, fp)


class WeatherHttp:
    """Share a two-request limit; never fetch URLs supplied by the browser."""

    def __init__(self) -> None:
        self._slots = BoundedSemaphore(2)

    def get(self, endpoint: str, parameters: dict[str, str], limit: int) -> bytes:
        """Retrieve bounded bytes with verified HTTPS and a 15-second socket timeout."""
        if endpoint not in {POWER_ENDPOINT, STATION_ENDPOINT}:
            raise ValueError("Unsupported weather endpoint")
        if not self._slots.acquire(blocking=False):
            raise WeatherUnavailable("WEATHER_BUSY", "天气服务正在处理请求，请稍后重试")
        try:
            url = endpoint + ("?" + urlencode(parameters) if parameters else "")
            request = Request(url, headers={"User-Agent": "CropDigitalTwin/0.6.0"})
            with build_opener(NoRedirect()).open(request, timeout=15) as response:
                data = cast(bytes, response.read(limit + 1))
            if len(data) > limit:
                raise WeatherUnavailable("WEATHER_TOO_LARGE", "天气资料过大，请缩短日期范围")
            return data
        except (URLError, TimeoutError, OSError) as error:
            if isinstance(error, HTTPError):
                error.close()
            raise WeatherUnavailable(
                "WEATHER_NETWORK_FAILED", "天气数据源暂时无法访问，请稍后重试或导入CSV"
            ) from None
        finally:
            self._slots.release()
