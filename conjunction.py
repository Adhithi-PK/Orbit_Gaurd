# conjunction.py
import numpy as np
from scipy.spatial import KDTree
import math
from datetime import datetime, timezone
from propagation import now_jd

CONJUNCTION_THRESHOLD_KM = 5.0
SIGMA_POS_KM = 0.1
TCA_STEP_S = 10      # seconds
TCA_WINDOW_S = 3600  # look 1 hour ahead


def propagate_obj(obj, jd, fr):
    e, r, v = obj["satrec"].sgp4(jd, fr)
    if e != 0:
        return None, None
    return np.array(r), np.array(v)


def compute_tca(obj_a, obj_b):
    """
    Step through next hour at TCA_STEP_S intervals.
    Return time of closest approach + miss distance.
    """
    jd0, fr0 = now_jd()
    best_dist = float('inf')
    best_dt = 0

    for step in range(0, TCA_WINDOW_S, TCA_STEP_S):
        offset_days = step / 86400.0
        # Keep integer and fractional JD parts separate for precision
        total_fr = fr0 + offset_days
        jd_int = jd0 + int(total_fr)
        fr = total_fr - int(total_fr)

        r_a, _ = propagate_obj(obj_a, jd_int, fr)
        r_b, _ = propagate_obj(obj_b, jd_int, fr)
        if r_a is None or r_b is None:
            continue

        dist = np.linalg.norm(r_a - r_b)
        if dist < best_dist:
            best_dist = dist
            best_dt = step

    return best_dt, round(best_dist, 4)


def compute_pc(miss_km, sigma=SIGMA_POS_KM):
    """Simplified 1D Gaussian collision probability approximation.
    P_c ≈ exp(-0.5 * (miss / σ_combined)²) where σ_combined = √2 * σ_pos.
    Not a full Foster/Akella 2D Pc — suitable for screening & demo purposes."""
    combined_sigma = math.sqrt(2) * sigma
    if combined_sigma == 0:
        return 0.0
    return round(math.exp(-0.5 * (miss_km / combined_sigma) ** 2), 6)


def build_tree(positions):
    coords = np.array([[p["x"], p["y"], p["z"]] for p in positions])
    return KDTree(coords), positions


def find_conjunctions(positions, catalog):
    if len(positions) < 2:
        return []

    tree, objs = build_tree(positions)
    pairs = tree.query_pairs(r=CONJUNCTION_THRESHOLD_KM)

    results = []
    for i, j in pairs:
        a, b = objs[i], objs[j]

        miss = math.sqrt(
            (a["x"] - b["x"])**2 +
            (a["y"] - b["y"])**2 +
            (a["z"] - b["z"])**2
        )
        if miss < 0.001:
            continue

        pc = compute_pc(miss)

        # TCA
        obj_a = catalog.get(a["norad_id"])
        obj_b = catalog.get(b["norad_id"])
        tca_s, tca_miss = (None, None)
        if obj_a and obj_b:
            tca_s, tca_miss = compute_tca(obj_a, obj_b)

        results.append({
            "object_a": a["norad_id"],
            "name_a": a["name"],
            "object_b": b["norad_id"],
            "name_b": b["name"],
            "miss_distance_km": round(miss, 4),
            "Pc": pc,
            "risk": "HIGH" if pc > 1e-4 else "MEDIUM" if pc > 1e-6 else "LOW",
            "tca_seconds_from_now": tca_s,
            "tca_miss_km": tca_miss,
        })

    results.sort(key=lambda x: x["Pc"], reverse=True)
    return results