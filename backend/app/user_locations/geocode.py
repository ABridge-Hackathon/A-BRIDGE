import requests
from app.common.redis_client import get_redis

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

#  실패시: "00도 00시" 형식 유지
DEFAULT_REGION = "강원도 원주시"


def _cache_key(lat: float, lng: float) -> str:
    return f"geo:region:{round(lat, 4)}:{round(lng, 4)}"


def _decode_cached(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (bytes, bytearray)):
        try:
            return v.decode("utf-8")
        except Exception:
            return ""
    return str(v)


def _format_kor_region(addr: dict) -> str:
    """
    반환 형식:
    1) "{city} {district}" -> "00시 00구"
    2) "{state} {city}"    -> "00도 00시"
    실패하면 "" 반환
    """
    state = (addr.get("state") or "").strip()  # 예: "경기도", "강원도", "서울특별시"
    city = (addr.get("city") or "").strip()  # 예: "수원시", "원주시"
    district = (
        addr.get("city_district") or addr.get("borough") or addr.get("suburb") or ""
    ).strip()  # 예: "팔달구"

    # 1) 00시 00구 우선
    if city.endswith("시") and district.endswith("구"):
        return f"{city} {district}"

    # 2) 00도 00시
    if state and city.endswith("시"):
        # state가 "서울특별시" 같은 케이스여도 요구사항은 "00도 00시"만 허용이라면
        # 이런 경우는 실패 처리하고 DEFAULT로 보내는 게 엄격함.
        # 여기선 "도"로 끝나는 것만 허용.
        if state.endswith("도"):
            return f"{state} {city}"

    return ""


def reverse_geocode_region(lat: float, lng: float) -> str:
    rds = get_redis()
    key = _cache_key(lat, lng)

    cached = _decode_cached(rds.get(key))
    if cached:
        return cached

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "format": "jsonv2",
                "lat": lat,
                "lon": lng,
                "zoom": 12,
                "addressdetails": 1,
            },
            headers={"User-Agent": "asciiBack/1.0 (hackathon)"},
            timeout=3,
        )
        if resp.status_code != 200:
            return DEFAULT_REGION

        data = resp.json()
        addr = data.get("address") or {}

        region = _format_kor_region(addr)
        if not region:
            return DEFAULT_REGION

        rds.set(key, region, ex=60 * 60 * 24)
        return region

    except Exception:
        return DEFAULT_REGION
