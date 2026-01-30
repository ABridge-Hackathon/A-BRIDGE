# app/user_locations/geocode.py
import requests
from app.common.redis_client import get_redis

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


def _cache_key(lat: float, lng: float) -> str:
    return f"geo:region:{round(lat, 4)}:{round(lng, 4)}"


def reverse_geocode_region(lat: float, lng: float) -> str:
    rds = get_redis()
    key = _cache_key(lat, lng)
    cached = rds.get(key)
    if cached:
        return cached

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "format": "jsonv2",
                "lat": lat,
                "lon": lng,
                "zoom": 12,  # 너무 자세히 말고 "구/군" 느낌
                "addressdetails": 1,
            },
            headers={
                "User-Agent": "asciiBack/1.0 (hackathon)",  # 필수 느낌
            },
            timeout=3,
        )
        if resp.status_code != 200:
            return ""

        data = resp.json()
        addr = data.get("address") or {}

        # 한국에서는 케이스가 다양해서 우선순위로 뽑기
        region = (
            addr.get("city_district")
            or addr.get("borough")
            or addr.get("county")
            or addr.get("city")
            or addr.get("town")
            or addr.get("suburb")
            or ""
        ).strip()

        if region:
            rds.set(key, region, ex=60 * 60 * 24)
        return region
    except Exception:
        return ""
