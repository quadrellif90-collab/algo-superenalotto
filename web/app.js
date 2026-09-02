// SuperEnalotto v8.1 - Frontend verde 7.18
const API = '';
let generatedSchedine = [];

document.addEventListener('DOMContentLoaded', () => { init(); });

async function init() {
    await loadProssima();
    await loadEstrazioni();
    await loadGiocate();
    await loadStats();
    await loadPremi();
    await loadStorico(40);
    bindEvents();
}

function bindEvents() {
    document.getElementById('btnGenera').addEventListener('click', genera);
    document.getElementById('btnSalva').addEventListener('click', salva);
    document.getElementById('btnVerifica').addEventListener('click', verifica);
    document.getElementById('btnAutoVerifica').addEventListener('click', autoVerifica);
    document.getElementById('closeModal').addEventListener('click', closeModal);
    document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));
    const btnAgg = document.getElementById('btnAggiornaStorico');
    if (btnAgg) btnAgg.addEventListener('click', aggiornaStorico);
    const btnVal = document.getElementById('btnValuta');
    if (btnVal) btnVal.addEventListener('click', valuta);
    const btnGraf = document.getElementById('btnGrafici');
    if (btnGraf) btnGraf.addEventListener('click', mostraGrafici);
}

function switchTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab===name));
    document.querySelectorAll('.tab-content').forEach(c => {
        const show = c.id === `tab-${name}`;
        c.style.display = show ? (name==='gioca' ? 'grid' : 'block') : 'none';
        if (show) c.classList.add('active'); else c.classList.remove('active');
    });
}

async function apiGet(endpoint) { const res = await fetch(`${API}${endpoint}`); return res.json(); }
async function apiPost(endpoint, data) { const res = await fetch(`${API}${endpoint}`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); return res.json(); }

async function loadProssima() {
    const data = await apiGet('/api/prossima');
    document.getElementById('nextDate').textContent = data.data;
    if (data.oggi) document.getElementById('nextDate').style.color = 'var(--warning)';
    try { const jp = await apiGet('/api/jackpot'); if (jp.jackpot) document.getElementById('jackpot').textContent = jp.jackpot; } catch {}
}

async function loadEstrazioni() {
    const data = await apiGet('/api/estrazioni?n=20');
    const tbody = document.querySelector('#estrazioniTable tbody');
    tbody.innerHTML = data.map(e => `<tr><td>${e.data}</td><td class="numeri-cell">${e.numeri.join(' - ')}</td><td>${e.jolly||'-'}</td><td>${e.star||'-'}</td></tr>`).join('');
}

async function loadGiocate() {
    const data = await apiGet('/api/giocate');
    const tbody = document.querySelector('#giocateTable tbody');
    let spent=0, won=0, m2=0,m3=0,m4=0;
    tbody.innerHTML = data.map(g => {
        spent+=1;
        let esito='<span class="esito-perdita">in attesa</span>';
        if (g.verificato && g.vincita>0) { won+=g.vincita; if(g.vincita>=100000) m4++; else if(g.vincita>=25) m3++; else if(g.vincita>=5) m2++; esito=`<span class="esito-vinto">+€${g.vincita.toLocaleString('it-IT')}</span>`; }
        else if (g.verificato) esito='<span class="esito-perdita">nessuna</span>';
        return `<tr><td>${g.data}</td><td class="numeri-cell">${g.numeri}</td><td>${g.somma}</td><td>${esito}</td><td><button class="btn btn-danger" style="padding:4px 8px;font-size:11px;" onclick="cancellaGiocata(${g.id})">🗑️</button></td></tr>`;
    }).join('');
    const roi = spent>0 ? ((won/spent-1)*100).toFixed(1) : '0.0';
    document.getElementById('statSpeso').textContent=`€${spent}`;
    document.getElementById('statVinto').textContent=`€${won.toLocaleString('it-IT')}`;
    document.getElementById('statRoi').textContent=`${roi}%`;
    document.getElementById('statM2').textContent=m2;
    document.getElementById('statM3').textContent=m3;
    document.getElementById('statM4').textContent=m4;
}

async function loadStats() {
    try {
        const s = await apiGet('/api/stats');
        const grid = document.getElementById('statsGrid');
        if (!grid) return;
        const items = [
            ['Estrazioni', s.count], ['Media', s.mean?.toFixed(1)], ['Mediana', s.median], ['Std Dev', s.std?.toFixed(1)],
            ['Q1', s.q1], ['Q3', s.q3], ['Min', s.min], ['Max', s.max],
        ];
        grid.innerHTML = items.map(([k,v]) => `<div class="stat"><span class="stat-label">${k}</span><span class="stat-value">${v}</span></div>`).join('');
        const top = document.getElementById('top10');
        if (top && s.num_counts) {
            const entries = Object.entries(s.num_counts).slice(0,10);
            top.innerHTML = entries.map(([n,c],i) => `${i+1}. Numero ${n} — ${c} volte`).join('<br>');
        }
    } catch {}
}

async function loadPremi() {
    try {
        const data = await apiGet('/api/premi');
        const tbody = document.getElementById('premiBody');
        if (tbody && data.premi) {
            tbody.innerHTML = data.premi.map(p => `<tr><td>${p.match}</td><td>1:${p.odds}</td><td>€${p.premio.toLocaleString('it-IT')}</td><td>${p.ultimo||'-'}</td></tr>`).join('');
        }
        const info = document.getElementById('jackpotInfo');
        if (info && data.jackpot) info.textContent = `Jackpot attuale: ${data.jackpot} — aggiornato da config/API`;
    } catch {}
}

async function loadStorico(n=40) {
    try {
        const data = await apiGet(`/api/estrazioni?n=${n}`);
        const tbody = document.querySelector('#storicoTable tbody');
        if (!tbody) return;
        tbody.innerHTML = data.map(e => `<tr><td>${e.data}</td><td class="numeri-cell">${e.numeri.join(' - ')}</td><td>${e.jolly||'-'}</td><td>${e.star||'-'}</td><td>${e.numeri.reduce((a,b)=>a+b,0)}</td></tr>`).join('');
    } catch {}
}

async function genera() {
    const n = parseInt(document.getElementById('numSchedine').value);
    const data = await apiGet(`/api/genera?n=${n}`);
    generatedSchedine = data;
    const container = document.getElementById('generated');
    container.innerHTML = data.map((s,i) => `<div class="schedina"><span class="schedina-num">Schedina ${i+1}:</span><span class="schedina-nums">${s.nums.join(' - ')}</span><span class="schedina-somma">[${s.sum}]</span></div>`).join('');
    document.getElementById('btnSalva').style.display='block';
    setStatus(`Generate ${n} schedine`);
}
async function salva() {
    if (generatedSchedine.length===0) return;
    const result = await apiPost('/api/salva', { schedine: generatedSchedine });
    if (result.blocked) { if(result.msg) alert(result.msg); setStatus('Bloccato'); } else { setStatus('Salvate!'); document.getElementById('btnSalva').style.display='none'; }
    await loadGiocate();
}
async function verifica() { const r=await apiPost('/api/verifica', {only_unchecked:false}); showVerifica(r); await loadGiocate(); await loadPremi(); }
async function autoVerifica() { const r=await apiPost('/api/verifica', {only_unchecked:true}); showVerifica(r); await loadGiocate(); }
function showVerifica(result) {
    const c=document.getElementById('verificaResult');
    let html=`<div style="margin-bottom:16px;"><strong>Verificate:</strong> ${result.checked} | <strong>Saltate:</strong> ${result.skipped} | <strong>Totale:</strong> €${result.tot_win.toLocaleString('it-IT')}</div>`;
    if(result.results?.length){ html+='<div style="max-height:300px;overflow-y:auto;">'+result.results.map(r=>`<div style="padding:4px 0;border-bottom:1px solid var(--border);"><strong>${r.data}</strong> — ${r.matches} indovinati${r.jolly_hit?' (+Jolly)':''} → <span class="${r.premio>0?'esito-vinto':'esito-perdita'}">${r.premio>0?'€'+r.premio.toLocaleString('it-IT'):'nessuna'}</span></div>`).join('')+'</div>'; }
    c.innerHTML=html; document.getElementById('modalVerifica').classList.add('active');
}
function closeModal(){ document.getElementById('modalVerifica').classList.remove('active'); }
async function cancellaGiocata(id){ if(!confirm('Cancellare?')) return; await apiPost('/api/cancella',{id}); await loadGiocate(); }
function setStatus(msg){ document.getElementById('statusBar').textContent=msg; }

async function aggiornaStorico(){
    const btn=document.getElementById('btnAggiornaStorico');
    const status=document.getElementById('storicoStatus');
    btn.disabled=true; status.textContent='Aggiornamento...';
    try { const r=await apiPost('/api/aggiorna_storico',{}); status.textContent=`Aggiunte ${r.added||0} estrazioni`; await loadEstrazioni(); await loadStorico(40); await loadStats(); } catch { status.textContent='Errore'; }
    btn.disabled=false;
}
async function valuta(){
    const c=document.getElementById('valutaResult');
    c.textContent='Calcolo...';
    try { const r=await apiGet('/api/valuta?n=50'); c.textContent=r.text || JSON.stringify(r,null,2); } catch { c.textContent='Errore'; }
}
async function mostraGrafici(){
    const c=document.getElementById('graficiContainer');
    c.innerHTML='<p style="color:var(--text-muted)">Generazione grafici...</p>';
    try { const r=await apiGet('/api/grafici'); if(r.img){ c.innerHTML=`<img src="${r.img}" style="max-width:100%; border:1px solid var(--border); border-radius:8px;">`; } else c.textContent=r.msg||'Grafici non disponibili'; } catch { c.textContent='Errore grafici'; }
}
