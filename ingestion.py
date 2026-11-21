# ingestion.py
import httpx
import asyncio
import math
import os
from datetime import datetime, timezone
import logging
from sgp4.api import Satrec, WGS84, jday
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
BASE_URL = "https://www.space-track.org"

QUERIES = {
    "active": "/basicspacedata/query/class/gp/DECAY_DATE/null-val/EPOCH/%3Enow-30/orderby/NORAD_CAT_ID/format/json",
    "debris": "/basicspacedata/query/class/gp/OBJECT_TYPE/DEBRIS/EPOCH/%3Enow-30/orderby/NORAD_CAT_ID/format/json",
}

_catalog: dict[str, dict] = {}
_last_fetched: datetime | None = None

# SGP4 internal epoch: 1949 December 31 00:00 UT
_SGP4_EPOCH_JD = 2433281.5


def _epoch_to_sgp4_days(epoch_str: str) -> float:
    """Convert ISO epoch string to 'days since 1949 Dec 31 00:00 UT' for sgp4init."""
    dt = datetime.fromisoformat(epoch_str.replace("Z", "+00:00"))
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                  dt.second + dt.microsecond / 1e6)
    return (jd + fr) - _SGP4_EPOCH_JD


def build_satrec(raw: dict) -> Satrec | None:
    try:
        epoch_days = _epoch_to_sgp4_days(raw["EPOCH"])
        sat = Satrec()
        # Space-Track GP JSON gives MEAN_MOTION_DOT as rev/day² (÷2 convention)
        # and MEAN_MOTION_DDOT as rev/day³ (÷6 convention).
        # sgp4init expects radians/minute² and radians/minute³ respectively.
        ndot = float(raw["MEAN_MOTION_DOT"]) * (2 * math.pi) / (1440.0 ** 2)
        nddot = float(raw["MEAN_MOTION_DDOT"]) * (2 * math.pi) / (1440.0 ** 3)
        sat.sgp4init(
            WGS84, 'i',
            int(raw["NORAD_CAT_ID"]),
            epoch_days,
            float(raw["BSTAR"]),
            ndot,
            nddot,
            float(raw["ECCENTRICITY"]),
            math.radians(float(raw["ARG_OF_PERICENTER"])),
            math.radians(float(raw["INCLINATION"])),
            math.radians(float(raw["MEAN_ANOMALY"])),
            float(raw["MEAN_MOTION"]) * 2 * math.pi / 1440,
            math.radians(float(raw["RA_OF_ASC_NODE"])),
        )
        return sat
    except Exception as e:
        logger.warning(f"sgp4init failed {raw.get('NORAD_CAT_ID')}: {e}")
        return None


def _parse_entry(raw: dict, feed: str) -> dict | None:
    sat = build_satrec(raw)
    if not sat:
        return None
    return {
        "norad_id": str(raw["NORAD_CAT_ID"]),
        "name": raw.get("OBJECT_NAME", "UNKNOWN").strip(),
        "object_type": raw.get("OBJECT_TYPE") or ("DEBRIS" if feed == "debris" else "PAYLOAD"),
        "epoch": raw["EPOCH"],
        "satrec": sat,
        "country": raw.get("COUNTRY_CODE"),
    }


async def ingest_all() -> dict[str, dict]:
    global _catalog, _last_fetched

    user = os.getenv("SPACETRACK_USER")
    pwd = os.getenv("SPACETRACK_PASS")

    if not user or not pwd:
        logger.error("SPACETRACK_USER and SPACETRACK_PASS must be set in environment / .env")
        raise RuntimeError("Missing Space-Track credentials")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        login_resp = await client.post(
            LOGIN_URL,
            data={"identity": user, "password": pwd},
        )
        login_resp.raise_for_status()
        logger.info("Space-Track login OK")

        _catalog = {}
        for feed, query in QUERIES.items():
            resp = await client.get(query)
            resp.raise_for_status()
            entries = resp.json()
            logger.info(f"{feed}: {len(entries)} raw entries")
            for raw in entries:
                obj = _parse_entry(raw, feed)
                if obj:
                    _catalog[obj["norad_id"]] = obj
            await asyncio.sleep(3)

    _last_fetched = datetime.now(timezone.utc)
    logger.info(f"Catalog: {len(_catalog)} total")
    return _catalog


def get_catalog() -> dict[str, dict]: return _catalog
def get_by_type(t: str) -> list[dict]: return [v for v in _catalog.values() if v["object_type"].upper() == t.upper()]
def get_last_fetched() -> datetime | None: return _last_fetched