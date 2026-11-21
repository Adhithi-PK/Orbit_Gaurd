// charts.js

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

export function renderConjunctionTable(data) {
    const tbody = document.querySelector('#conjunction-table tbody');
    tbody.innerHTML = '';

    if (!data || !data.length) return;

    const top = data.slice(0, 20);
    top.forEach(c => {
        const tr = document.createElement('tr');

        const tdA = document.createElement('td');
        tdA.textContent = (c.name_a || '').slice(0, 12);
        tdA.title = c.name_a || '';

        const tdB = document.createElement('td');
        tdB.textContent = (c.name_b || '').slice(0, 12);
        tdB.title = c.name_b || '';

        const tdMiss = document.createElement('td');
        tdMiss.textContent = c.miss_distance_km;

        const tdPc = document.createElement('td');
        tdPc.textContent = c.Pc != null ? c.Pc.toExponential(2) : 'N/A';

        const tdRisk = document.createElement('td');
        tdRisk.className = `risk-${c.risk}`;
        const badge = document.createElement('span');
        badge.className = 'risk-badge';
        badge.textContent = c.risk;
        tdRisk.appendChild(badge);

        tr.append(tdA, tdB, tdMiss, tdPc, tdRisk);
        tbody.appendChild(tr);
    });
}


export function renderHeatmap(data) {
    const container = document.getElementById('heatmap-chart');
    container.innerHTML = '';

    if (!data || !data.length) return;

    const max = Math.max(...data.map(d => d.count));
    if (max <= 0) return;

    data.forEach(d => {
        const pct = (d.count / max * 100).toFixed(1);
        const row = document.createElement('div');
        row.className = 'bar-row';
        row.innerHTML = `
            <div class="bar-label">${escapeHtml(d.band)}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${pct}%"></div>
            </div>
            <div class="bar-count">${d.count}</div>
        `;
        container.appendChild(row);
    });
}


export function renderStatus(data) {
    if (!data) return;
    document.getElementById('stat-total').textContent = (data.total || 0).toLocaleString();
    document.getElementById('stat-sats').textContent = (data.satellites || 0).toLocaleString();
    document.getElementById('stat-debris').textContent = (data.debris || 0).toLocaleString();
}


// Track high-risk alerts — capped to avoid unbounded memory growth
let previousHighRisk = new Set();
const MAX_TRACKED_ALERTS = 500;

export function checkAlerts(conjunctions) {
    if (!conjunctions || !conjunctions.length) return;

    // Build current high-risk set for this cycle
    const currentKeys = new Set();
    const high = conjunctions.filter(c => c.risk === "HIGH");

    high.forEach(c => {
        const key = `${c.object_a}-${c.object_b}`;
        currentKeys.add(key);
        if (!previousHighRisk.has(key)) {
            showToast(c);
        }
    });

    // Replace with current cycle's keys to prevent unbounded growth
    // Keep only keys that are still active
    if (previousHighRisk.size > MAX_TRACKED_ALERTS) {
        previousHighRisk = currentKeys;
    } else {
        currentKeys.forEach(k => previousHighRisk.add(k));
    }
}

let activeToasts = 0;

function showToast(c) {
    const offset = activeToasts * 140;
    activeToasts++;

    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: ${24 + offset}px;
        right: 24px;
        background: #1a1a2e;
        border: 1px solid rgba(239,68,68,0.5);
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 14px 18px;
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        color: #f1f5f9;
        max-width: 320px;
        z-index: 9999;
        box-shadow: 0 8px 32px rgba(239,68,68,0.2);
        animation: slideIn 0.3s ease;
        transition: opacity 0.3s ease;
    `;
    toast.innerHTML = `
        <div style="color:#ef4444; font-weight:700; font-size:11px; letter-spacing:1px; margin-bottom:6px;">
            ⚠ HIGH RISK CONJUNCTION
        </div>
        <div style="margin-bottom:4px;">
            <span style="color:#94a3b8;">Objects: </span>
            ${escapeHtml(c.name_a || '')} × ${escapeHtml(c.name_b || '')}
        </div>
        <div style="margin-bottom:4px;">
            <span style="color:#94a3b8;">Miss Distance: </span>
            ${c.miss_distance_km} km
        </div>
        <div style="margin-bottom:4px;">
            <span style="color:#94a3b8;">Pc: </span>
            ${c.Pc != null ? c.Pc.toExponential(2) : 'N/A'}
        </div>
        <div>
            <span style="color:#94a3b8;">TCA: </span>
            ${c.tca_seconds_from_now ? c.tca_seconds_from_now + 's from now' : 'N/A'}
        </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toast.remove();
            activeToasts = Math.max(0, activeToasts - 1);
        }, 300);
    }, 6000);
}
