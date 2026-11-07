"""Bounded, opt-in collection from permitted sources; never sends outreach."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Deliberately bounded to the two supported cities. No arbitrary query interpolation.
CITIES = {
    "павлодар": ("Павлодар", "52.20,76.80,52.38,77.10"),
    "pavlodar": ("Павлодар", "52.20,76.80,52.38,77.10"),
    "экибастуз": ("Экибастуз", "51.64,75.23,51.83,75.44"),
    "ekibastuz": ("Экибастуз", "51.64,75.23,51.83,75.44"),
}
CATEGORIES = {
    "кафе": ("amenity", "cafe"), "cafe": ("amenity", "cafe"),
    "ресторан": ("amenity", "restaurant"), "restaurant": ("amenity", "restaurant"),
    "парикмахерская": ("shop", "hairdresser"), "hairdresser": ("shop", "hairdresser"),
    "салон красоты": ("shop", "beauty"), "beauty": ("shop", "beauty"),
    "стоматология": ("amenity", "dentist"), "dentist": ("amenity", "dentist"),
    "автосервис": ("shop", "car_repair"), "car_repair": ("shop", "car_repair"),
    "отель": ("tourism", "hotel"), "hotel": ("tourism", "hotel"),
    "магазин": ("shop", "convenience"), "convenience": ("shop", "convenience"),
    "фитнес": ("leisure", "fitness_centre"), "fitness": ("leisure", "fitness_centre"),
}
MAX_BYTES = 2_000_000
_LAST_REQUEST = 0.0


class SourceError(Exception):
    """Only a fixed code is persisted: upstream bodies/URLs can contain secrets."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request(endpoint: str, query: str) -> dict:
    """One initial request and at most one retry; respect rate limits and TLS."""
    global _LAST_REQUEST
    try:
        interval = max(1.0, min(60.0, float(os.getenv("FLARE_REQUEST_INTERVAL", "3"))))
        timeout = max(1.0, min(60.0, float(os.getenv("FLARE_HTTP_TIMEOUT", "30"))))
    except ValueError as exc:
        raise SourceError("invalid_network_configuration") from exc
    delay = 0.0
    for attempt in range(2):
        time.sleep(max(delay, interval - (time.monotonic() - _LAST_REQUEST), 0))
        _LAST_REQUEST = time.monotonic()
        request = Request(
            endpoint,
            data=urlencode({"data": query}).encode(),
            headers={"User-Agent": "FlareStudioLocalMVP/0.1 (manual collection)",
                     "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise SourceError("response_too_large")
            result = json.loads(data)
            if not isinstance(result, dict) or not isinstance(result.get("elements"), list):
                raise SourceError("invalid_response")
            if result.get("remark"):
                # Overpass can return HTTP 200 with a runtime error and incomplete data.
                raise SourceError("upstream_runtime_error")
            return result
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise SourceError("access_denied") from exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After", "10")
                try:
                    delay = float(retry_after)
                except ValueError:
                    try:
                        delay = (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
                    except (TypeError, ValueError):
                        delay = 10
                if attempt or delay > 30:
                    raise SourceError("rate_limited") from exc
                delay = max(1.0, delay)
            elif exc.code in (502, 503, 504) and not attempt:
                delay = 3
            else:
                raise SourceError("upstream_http_error") from exc
        except (URLError, TimeoutError, OSError) as exc:
            if attempt:
                raise SourceError("network_unavailable") from exc
            delay = 2
        except (ValueError, UnicodeError) as exc:
            raise SourceError("invalid_response") from exc
    raise SourceError("network_unavailable")


def fetch_osm(city: str, category: str, limit: int = 20) -> list[dict]:
    if city.strip().casefold() not in CITIES:
        raise SourceError("unsupported_city")
    if category.strip().casefold() not in CATEGORIES:
        raise SourceError("unsupported_category")
    if not 1 <= limit <= 100:
        raise SourceError("invalid_limit")
    city_name, bbox = CITIES[city.strip().casefold()]
    key, value = CATEGORIES[category.strip().casefold()]
    query = f'[out:json][timeout:20][maxsize:16777216];nwr["name"]["{key}"="{value}"]({bbox});out tags {limit};'
    endpoint = os.getenv("FLARE_OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    if not endpoint.startswith("https://"):
        raise SourceError("https_required")
    result = _request(endpoint, query)
    observed_at = _now()
    records = []
    for element in result["elements"][:limit]:
        tags = element.get("tags", {})
        kind, osm_id = element.get("type"), element.get("id")
        if not tags.get("name") or kind not in ("node", "way", "relation") or not isinstance(osm_id, int):
            continue
        actual_city = tags.get("addr:city", city_name)
        # Ignore explicitly tagged other cities inside the approximate bounding box.
        if actual_city.strip().casefold() not in (city_name.casefold(), city.strip().casefold()):
            continue
        street = tags.get("addr:street", "")
        house = tags.get("addr:housenumber", "")
        address = ", ".join(x for x in (street, house) if x)
        profile = tags.get("contact:instagram", "")
        # OSM attribution is retained with each fact via the source URL/evidence.
        records.append({
            "name": tags["name"], "category": category, "city": city_name, "address": address,
            "source_url": f"https://www.openstreetmap.org/{kind}/{osm_id}",
            "source_external_id": f"{kind}/{osm_id}", "observed_at": observed_at,
            "confidence": 0.65,
            "excerpt": "© OpenStreetMap contributors, ODbL. Публичные теги; принадлежность контактов требует проверки.",
            "phone": (tags.get("contact:phone") or tags.get("phone", "")).split(";")[0].strip(),
            "phone_verified": False,
            "email": tags.get("contact:email") or tags.get("email", ""),
            "profile_url": profile if profile.startswith("https://") else "",
            "website": tags.get("contact:website") or tags.get("website", ""),
            "website_status": "unchecked",
        })
    return records


def _unavailable(name: str) -> str:
    if name == "2gis":
        return "api_key_and_storage_permission_required"
    if name == "yandex":
        return "license_prohibits_storage"
    if name == "instagram":
        return "no_universal_public_business_search_api"
    return "unknown_source"


def collect_sources(conn, city: str, category: str, source_names: list[str], limit: int = 20,
                    *, fetcher: Callable | None = None) -> list[dict]:
    """Persist one attempt per source; a failed source never prevents the next one.

    fetcher(name, city, category, limit) is a test seam, with no network side effects
    when supplied. Production only calls the implemented OSM adapter.
    """
    from .core import upsert_business
    from .db import get_source

    reports = []
    for raw_name in dict.fromkeys(source_names):
        name = raw_name.strip().casefold()
        source_id = get_source(conn, name)
        started = _now()
        cursor = conn.execute(
            "INSERT INTO collection_attempts(source_id,city,category,started_at,status,count) VALUES(?,?,?,?,?,0)",
            (source_id, city, category, started, "running"),
        )
        attempt_id = cursor.lastrowid
        conn.commit()
        count, invalid, error, status = 0, 0, None, "completed"
        try:
            if fetcher is None and name != "osm":
                raise SourceError(_unavailable(name))
            records = fetcher(name, city, category, limit) if fetcher else fetch_osm(city, category, limit)
            for record in records:
                try:
                    # Bad rows roll back alone; all other records/sources continue.
                    conn.execute("SAVEPOINT source_record")
                    upsert_business(conn, record, source_name=name)
                    conn.execute("RELEASE SAVEPOINT source_record")
                    count += 1
                except Exception:
                    conn.execute("ROLLBACK TO SAVEPOINT source_record")
                    conn.execute("RELEASE SAVEPOINT source_record")
                    invalid += 1
            if invalid:
                status, error = ("partial" if count else "failed"), "invalid_records"
        except SourceError as exc:
            error = exc.code
            status = "unavailable" if name != "osm" else "failed"
        except Exception:
            # Persist no exception representation: it may contain business contacts.
            status, error = "failed", "source_processing_error"
        conn.execute(
            "UPDATE collection_attempts SET finished_at=?,status=?,count=?,error_code=? WHERE id=?",
            (_now(), status, count, error, attempt_id),
        )
        conn.commit()
        reports.append({"source": name, "status": status, "received": count, "error": error})
    return reports
