from geopy.geocoders import Nominatim

from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

class GeoLocater:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="spatially_collector")

    def geocode(self, address: str) -> tuple[float, float] | tuple[None, None]:

        retries = 1
        delay = 1

        for attempt in range(retries):
            try:
                location = self.geolocator.geocode(address)
                if location is not None:
                    return location.latitude, location.longitude
                else:
                    return None, None
            except (GeocoderTimedOut, GeocoderServiceError):
                time.sleep(delay)
                delay *= 2  # Exponential backoff

        return None, None