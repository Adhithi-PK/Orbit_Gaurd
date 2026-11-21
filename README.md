# 🛰️ Orbit Guard (ASTRA SSA)

**A real-time Space Situational Awareness (SSA) dashboard** that tracks satellites and space debris, flags potential collisions (conjunctions), and suggests avoidance maneuvers — all visualised on an interactive 3D globe.

Built for **ASTRA 2026 Hackathon** at VIT Bhopal University.

---

## ✨ Features

- **Live catalog ingestion** – pulls active satellites and debris from [Space-Track.org](https://www.space-track.org) (GP data, last 30 days).
- **SGP4 orbit propagation** – computes current position (ECI, km) and velocity (km/s) for every object.
- **Conjunction detection** – KD-Tree spatial search flags object pairs closer than **5 km**.
- **Time of Closest Approach (TCA)** – scans the next hour in 10 s steps for each flagged pair.
- **Collision probability (Pc)** – simplified Gaussian estimate with `HIGH / MEDIUM / LOW` risk levels.
- **Maneuver recommendation** – Hohmann-transfer delta-v for a 5 km altitude raise.
- **Debris density heatmap** – LEO debris count per 100 km altitude band.
- **3D globe frontend** – Three.js Earth with satellites (cyan) and debris (red), drag-to-rotate, scroll-to-zoom.
- **Live alerts** – WebSocket pushes conjunctions every 10 s; HIGH-risk events trigger toast notifications.

---

## 🏗️ Architecture

```
┌────────────────┐   Space-Track API   ┌──────────────────────────────┐
│  Space-Track   │ ──────────────────▶ │  FastAPI backend (main.py)   │
└────────────────┘                     │  ├─ ingestion.py   (catalog) │
                                       │  ├─ propagation.py (SGP4)    │
                                       │  ├─ conjunction.py (KDTree)  │
                                       │  └─ maneuver.py    (Hohmann) │
                                       └──────────────┬───────────────┘
                                         REST + WebSocket│
                                       ┌──────────────▼───────────────┐
                                       │ Frontend (HTML/JS/Three.js)  │
                                       │ globe.js · charts.js · api.js│
                                       └──────────────────────────────┘
```

## 📁 Project Structure

```
Orbit_Gaurd/
├── main.py            # FastAPI app: REST endpoints + WebSocket
├── ingestion.py       # Space-Track login, fetch, SGP4 satrec build
├── propagation.py     # Current-time position/velocity propagation
├── conjunction.py     # KD-Tree screening, TCA, Pc, risk level
├── maneuver.py        # Hohmann delta-v maneuver recommendation
├── requirements.txt
└── frontend/
    ├── index.html     # Dashboard layout
    ├── style.css      # Styling
    ├── api.js         # REST/WebSocket client
    ├── globe.js       # Three.js globe + object rendering
    └── charts.js      # Conjunction table, heatmap, alerts
```

---

## 🧰 Tech Stack

| Layer     | Tools                                           |
|-----------|-------------------------------------------------|
| Backend   | Python, FastAPI, Uvicorn, httpx, WebSockets     |
| Science   | sgp4, NumPy, SciPy (KDTree)                     |
| Frontend  | HTML, CSS, vanilla JS (ES modules), Three.js r128 |
| Data      | Space-Track.org GP catalog                      |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- A free [Space-Track.org](https://www.space-track.org/auth/createAccount) account

### 1. Clone & install

```bash
git clone https://github.com/<your-username>/Orbit_Gaurd.git
cd Orbit_Gaurd
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add credentials

Create a `.env` file in the project root:

```env
SPACETRACK_USER=your_email@example.com
SPACETRACK_PASS=your_password
```

> ⚠️ Never commit `.env`. Add it to `.gitignore`.

### 3. Run the backend

```bash
uvicorn main:app --reload
```

The server starts at `http://127.0.0.1:8000` and downloads the catalog on startup (takes a few seconds). Interactive API docs: `http://127.0.0.1:8000/docs`.

### 4. Run the frontend

The frontend expects the API at `127.0.0.1:8000`. Serve it with any static server (ES modules don't work from `file://`):

```bash
cd frontend
python -m http.server 5500
```

Open **http://localhost:5500**.

---

## 🔌 API Reference

| Method | Endpoint                 | Description                                              |
|--------|--------------------------|----------------------------------------------------------|
| GET    | `/status`                | Catalog totals (objects, satellites, debris)             |
| GET    | `/satellites`            | Current positions of all non-debris objects              |
| GET    | `/debris`                | Current positions of debris                              |
| GET    | `/conjunctions`          | Objects within 5 km, sorted by Pc                        |
| WS     | `/ws/conjunctions`       | Streams conjunction list every 10 s                      |
| GET    | `/maneuver/{norad_id}`   | Recommended Hohmann maneuver for an object in conjunction |
| GET    | `/heatmap`               | Debris count per 100 km LEO altitude band                |

**Example conjunction response**

```json
{
  "object_a": "25544",
  "name_a": "ISS (ZARYA)",
  "object_b": "99999",
  "name_b": "SOME DEBRIS",
  "miss_distance_km": 3.1245,
  "Pc": 0.000012,
  "risk": "MEDIUM",
  "tca_seconds_from_now": 420,
  "tca_miss_km": 1.82
}
```

---

## 🧮 How It Works

1. **Ingest** – Log in to Space-Track and fetch active + debris GP elements; build an SGP4 `Satrec` for each object.
2. **Propagate** – Evaluate SGP4 at the current UTC time to get ECI position/velocity.
3. **Screen** – Build a KD-Tree over all positions and query pairs within 5 km.
4. **Refine** – For each pair, step through the next hour (10 s steps) to find TCA and minimum miss distance.
5. **Score** – Compute Pc and classify: `HIGH` (> 1e-4), `MEDIUM` (> 1e-6), else `LOW`.
6. **Advise** – Compute Hohmann delta-v for a +5 km altitude raise on the primary object.

---

## ⚠️ Limitations

- **Demo-grade Pc**: uses a simplified 1D Gaussian with a fixed σ (0.1 km), not a full Foster/Akella 2D Pc or real covariance data.
- **Screening is instantaneous**: pairs are found from current positions only; close approaches later in the hour between currently distant objects aren't detected.
- **Simplified maneuver**: fixed 5 km altitude raise; no optimisation or fuel/operational constraints.
- **TLE/GP accuracy**: SGP4 accuracy degrades with element age (typically a few km/day).
- **Space-Track rate limits**: the catalog loads once at startup; restart to refresh.
- Backend URL is hardcoded in `frontend/api.js`; CORS is open (`*`) — fine for local/demo, tighten for production.

## 🗺️ Roadmap

- Periodic catalog refresh in the background
- Click-to-select objects on the globe with maneuver panel
- Real covariance-based Pc (Foster 2D)
- Look-ahead conjunction screening over multiple hours
- Docker setup and configurable backend URL

---

## 🙏 Acknowledgements

- [Space-Track.org](https://www.space-track.org) for orbital data
- [python-sgp4](https://github.com/brandon-rhodes/python-sgp4)
- [Three.js](https://threejs.org)


