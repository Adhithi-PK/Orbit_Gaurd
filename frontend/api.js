// api.js
const BASE = "http://127.0.0.1:8000";

async function safeFetch(url, fallback = null) {
    try {
        const res = await fetch(url);
        if (!res.ok) {
            console.error(`API ${url} returned ${res.status}`);
            return fallback;
        }
        return await res.json();
    } catch (err) {
        console.error(`API ${url} failed:`, err);
        return fallback;
    }
}

export async function fetchStatus() {
    return await safeFetch(`${BASE}/status`, { total: 0, satellites: 0, debris: 0 });
}

export async function fetchSatellites() {
    return await safeFetch(`${BASE}/satellites`, []);
}

export async function fetchDebris() {
    return await safeFetch(`${BASE}/debris`, []);
}

export async function fetchConjunctions() {
    return await safeFetch(`${BASE}/conjunctions`, []);
}

export async function fetchHeatmap() {
    return await safeFetch(`${BASE}/heatmap`, []);
}

export async function fetchManeuver(noradId) {
    return await safeFetch(`${BASE}/maneuver/${noradId}`, null);
}

export function connectConjunctionSocket(onData) {
    let reconnectDelay = 1000;
    const MAX_DELAY = 30000;

    function connect() {
        const ws = new WebSocket("ws://127.0.0.1:8000/ws/conjunctions");

        ws.onopen = () => {
            console.log("WebSocket connected");
            reconnectDelay = 1000; // reset backoff on success
        };

        ws.onmessage = e => {
            try {
                const data = JSON.parse(e.data);
                onData(data);
            } catch (err) {
                console.error("WebSocket parse error:", err);
            }
        };

        ws.onerror = e => {
            console.error("WebSocket error:", e);
        };

        ws.onclose = () => {
            console.warn(`WebSocket closed, reconnecting in ${reconnectDelay}ms`);
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, MAX_DELAY);
        };

        return ws;
    }

    return connect();
}
