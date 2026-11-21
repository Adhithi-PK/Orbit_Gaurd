# propagation.py
import math
from datetime import datetime, timezone
from sgp4.api import jday

def now_jd() -> tuple[float, float]:
    dt = datetime.now(timezone.utc)
    return jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)


def propagate_one(obj: dict, jd: float, fr: float) -> dict | None:
    e, r, v = obj["satrec"].sgp4(jd, fr)
    if e != 0:
        return None
    x, y, z = r
    vx, vy, vz = v
    alt = math.sqrt(x**2 + y**2 + z**2) - 6371.0  # km above surface
    return {
        "norad_id": obj["norad_id"],
        "name": obj["name"],
        "object_type": obj["object_type"],
        "x": x, "y": y, "z": z,          # ECI km
        "vx": vx, "vy": vy, "vz": vz,    # km/s
        "altitude_km": round(alt, 2),
    }


def propagate_catalog(catalog: dict[str, dict]) -> list[dict]:
    jd, fr = now_jd()
    results = []
    for obj in catalog.values():
        pos = propagate_one(obj, jd, fr)
        if pos:
            results.append(pos)
    return results