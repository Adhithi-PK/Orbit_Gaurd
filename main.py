# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import asyncio
import logging

from ingestion import ingest_all, get_catalog, get_by_type
from propagation import propagate_catalog
from conjunction import find_conjunctions
from maneuver import recommend_maneuver

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ingest_all()
    yield


app = FastAPI(title="ASTRA SSA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _positions_map() -> dict[str, dict]:
    """Run CPU-heavy propagation off the event loop."""
    catalog = get_catalog()
    positions = await asyncio.to_thread(propagate_catalog, catalog)
    return {p["norad_id"]: p for p in positions}


@app.get("/satellites")
async def satellites():
    pm = await _positions_map()
    return [p for p in pm.values() if p["object_type"] != "DEBRIS"]


@app.get("/debris")
async def debris():
    pm = await _positions_map()
    return [p for p in pm.values() if p["object_type"] == "DEBRIS"]


@app.get("/conjunctions")
async def conjunctions():
    pm = await _positions_map()
    positions = list(pm.values())
    catalog = get_catalog()
    return await asyncio.to_thread(find_conjunctions, positions, catalog)


@app.websocket("/ws/conjunctions")
async def ws_conjunctions(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            pm = await _positions_map()
            positions = list(pm.values())
            catalog = get_catalog()
            data = await asyncio.to_thread(find_conjunctions, positions, catalog)
            await websocket.send_json(data)
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)


@app.get("/maneuver/{norad_id}")
async def maneuver(norad_id: str):
    positions = await _positions_map()
    # BUG FIX: was missing second argument `catalog`
    catalog = get_catalog()
    conjs = await asyncio.to_thread(find_conjunctions, list(positions.values()), catalog)
    match = next((c for c in conjs if c["object_a"] == norad_id or c["object_b"] == norad_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="No conjunction found for this object")
    if match["object_b"] == norad_id:
        match["object_a"], match["object_b"] = match["object_b"], match["object_a"]
    return recommend_maneuver(match, positions)


@app.get("/heatmap")
async def heatmap():
    catalog = get_catalog()
    positions = await asyncio.to_thread(propagate_catalog, catalog)
    bands: dict[int, int] = {}
    for p in positions:
        # Focus on DEBRIS in Low Earth Orbit (0-2000 km)
        if p.get("object_type") == "DEBRIS":
            alt = p.get("altitude_km", 0)
            if 0 <= alt <= 2000:
                bin_start = int(alt // 100) * 100
                bands[bin_start] = bands.get(bin_start, 0) + 1
    
    # Return sorted by altitude
    sorted_bins = sorted(bands.items(), key=lambda item: item[0])
    return [
        {"band": f"{k}-{k + 100}km", "count": v}
        for k, v in sorted_bins
    ]


@app.get("/status")
async def status():
    catalog = get_catalog()
    return {
        "total": len(catalog),
        "satellites": sum(1 for v in catalog.values() if v["object_type"] != "DEBRIS"),
        "debris": sum(1 for v in catalog.values() if v["object_type"] == "DEBRIS"),
    }
