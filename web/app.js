// SuperEnalotto Frontend - app.js

const API = '';

// State
let generatedSchedine = [];

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    init();
});

async function init() {
    await loadProssima();
    await loadEstrazioni();
    await loadGiocate();
    bindEvents();
}

function bindEvents() {
    document.getElementById('btnGenera').addEventListener('click', genera);
    document.getElementById('btnSalva').addEventListener('click', salva);
    document.getElementById('btnVerifica').addEventListener('click', verifica);
    document.getElementById('btnAutoVerifica').addEventListener('click', autoVerifica);
    document.getElementById('closeModal').addEventListener('click', closeModal);
}

async function apiGet(endpoint) {
    const res = await fetch(`${API}${endpoint}`);
    return res.json();
}

async function apiPost(endpoint, data) {
    const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    return res.json();
}

async function loadProssima() {
    const data = await apiGet('/api/prossima');
    document.getElementById('nextDate').textContent = data.data;
    if (data.oggi) {
        document.getElementById('nextDate').style.color = 'var(--success)';
    }
    try {
        const jp = await apiGet('/api/jackpot');
        if (jp.jackpot) document.getElementById('jackpot').textContent = jp.jackpot;
    } catch {}
}

async function loadEstrazioni() {
    const data = await apiGet('/api/estrazioni?n=20');
    const tbody = document.querySelector('#estrazioniTable tbody');
    tbody.innerHTML = data.map(e => `
        <tr>
            <td>${e.data}</td>
            <td class="numeri-cell">${e.numeri.join(' - ')}</td>
            <td>${e.jolly || '-'}</td>
            <td>${e.star || '-'}</td>
        </tr>
    `).join('');
}

async function loadGiocate() {
    const data = await apiGet('/api/giocate');
    const tbody = document.querySelector('#giocateTable tbody');
    
    let spent = 0, won = 0, m2 = 0, m3 = 0, m4 = 0;
    
    tbody.innerHTML = data.map(g => {
        spent += 1;
        let esito = '<span class="esito-perdita">in attesa</span>';
        if (g.verificato && g.vincita > 0) {
            won += g.vincita;
            if (g.vincita >= 100000) m4++;
            else if (g.vincita >= 25) m3++;
            else if (g.vincita >= 5) m2++;
            esito = `<span class="esito-vinto">+€${g.vincita.toLocaleString('it-IT')}</span>`;
        } else if (g.verificato) {
            esito = '<span class="esito-perdita">nessuna</span>';
        }
        return `
            <tr>
                <td>${g.data}</td>
                <td class="numeri-cell">${g.numeri}</td>
                <td>${g.somma}</td>
                <td>${esito}</td>
                <td><button class="btn btn-danger" style="padding:4px 8px;font-size:11px;" onclick="cancellaGiocata(${g.id})">🗑️</button></td>
            </tr>
        `;
    }).join('');

    const roi = spent > 0 ? ((won / spent - 1) * 100).toFixed(1) : '0.0';
    document.getElementById('statSpeso').textContent = `€${spent}`;
    document.getElementById('statVinto').textContent = `€${won.toLocaleString('it-IT')}`;
    document.getElementById('statRoi').textContent = `${roi}%`;
    document.getElementById('statM2').textContent = m2;
    document.getElementById('statM3').textContent = m3;
    document.getElementById('statM4').textContent = m4;
}

async function genera() {
    const n = parseInt(document.getElementById('numSchedine').value);
    const data = await apiGet(`/api/genera?n=${n}`);
    generatedSchedine = data;
    
    const container = document.getElementById('generated');
    container.innerHTML = data.map((s, i) => `
        <div class="schedina">
            <span class="schedina-num">Schedina ${i + 1}:</span>
            <span class="schedina-nums">${s.nums.join(' - ')}</span>
            <span class="schedina-somma">[${s.sum}]</span>
        </div>
    `).join('');
    
    document.getElementById('btnSalva').style.display = 'block';
    setStatus(`Generate ${n} schedine`);
}

async function salva() {
    if (generatedSchedine.length === 0) return;
    const result = await apiPost('/api/salva', { schedine: generatedSchedine });
    if (result.blocked) {
        if (result.msg) {
            alert(result.msg);
        }
        setStatus('Salvataggio parziale o bloccato');
    } else {
        setStatus('Schedine salvate!');
        document.getElementById('btnSalva').style.display = 'none';
    }
    await loadGiocate();
}

async function verifica() {
    const result = await apiPost('/api/verifica', { only_unchecked: false });
    showVerifica(result);
    await loadGiocate();
}

async function autoVerifica() {
    const result = await apiPost('/api/verifica', { only_unchecked: true });
    showVerifica(result);
    await loadGiocate();
}

function showVerifica(result) {
    const container = document.getElementById('verificaResult');
    let html = `
        <div style="margin-bottom:16px;">
            <strong>Verificate:</strong> ${result.checked} &nbsp;|&nbsp;
            <strong>Saltate:</strong> ${result.skipped} &nbsp;|&nbsp;
            <strong>Totale:</strong> €${result.tot_win.toLocaleString('it-IT')}
        </div>
    `;
    if (result.results && result.results.length > 0) {
        html += '<div style="max-height:300px;overflow-y:auto;">';
        html += result.results.map(r => {
            const cls = r.premio > 0 ? 'esito-vinto' : 'esito-perdita';
            return `<div style="padding:4px 0;border-bottom:1px solid var(--border);">
                <strong>${r.data}</strong> — ${r.matches} indovinati${r.jolly_hit ? ' (+Jolly)' : ''} → 
                <span class="${cls}">${r.premio > 0 ? '€' + r.premio.toLocaleString('it-IT') : 'nessuna'}</span>
            </div>`;
        }).join('');
        html += '</div>';
    }
    container.innerHTML = html;
    document.getElementById('modalVerifica').classList.add('active');
}

function closeModal() {
    document.getElementById('modalVerifica').classList.remove('active');
}

async function cancellaGiocata(id) {
    if (!confirm('Cancellare questa giocata?')) return;
    await apiPost('/api/cancella', { id });
    await loadGiocate();
}

function setStatus(msg) {
    document.getElementById('statusBar').textContent = msg;
}
