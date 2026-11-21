# maneuver.py
import math

MU = 398600.4418       # Earth gravitational parameter, km³/s²
EARTH_RADIUS = 6371.0  # km


def orbital_velocity(r_km: float) -> float:
    if r_km <= 0:
        raise ValueError(f"Orbital radius must be positive, got {r_km}")
    return math.sqrt(MU / r_km)


def hohmann_dv(r1_km: float, r2_km: float) -> dict:
    """
    Hohmann transfer delta-v between two circular orbits.
    r1, r2 = radius from Earth center (km)
    """
    if r1_km <= 0 or r2_km <= 0:
        return {"error": "Invalid orbital radii", "dv_total_ms": 0}

    v1 = orbital_velocity(r1_km)
    v2 = orbital_velocity(r2_km)
    a_transfer = (r1_km + r2_km) / 2

    v_trans1 = math.sqrt(MU * (2 / r1_km - 1 / a_transfer))
    v_trans2 = math.sqrt(MU * (2 / r2_km - 1 / a_transfer))

    dv1 = abs(v_trans1 - v1)
    dv2 = abs(v2 - v_trans2)
    dv_total = dv1 + dv2

    return {
        "dv1_ms": round(dv1 * 1000, 2),
        "dv2_ms": round(dv2 * 1000, 2),
        "dv_total_ms": round(dv_total * 1000, 2),
        "transfer_time_s": round(math.pi * math.sqrt(a_transfer**3 / MU), 2),
    }


def recommend_maneuver(conjunction: dict, positions: dict[str, dict]) -> dict:
    norad_a = conjunction["object_a"]
    obj = positions.get(norad_a)
    if not obj:
        return {"error": "object not found"}

    r1 = math.sqrt(obj["x"]**2 + obj["y"]**2 + obj["z"]**2)
    if r1 < EARTH_RADIUS:
        return {"error": f"Object radius {r1:.1f} km is below Earth surface"}

    r2 = r1 + 5.0  # 5 km altitude raise

    dv = hohmann_dv(r1, r2)
    return {
        "norad_id": norad_a,
        "name": obj["name"],
        "current_altitude_km": round(r1 - EARTH_RADIUS, 2),
        "target_altitude_km": round(r2 - EARTH_RADIUS, 2),
        "maneuver": dv,
        "conjunction_Pc": conjunction["Pc"],
    }