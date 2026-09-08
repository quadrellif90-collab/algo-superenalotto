// SuperEnalotto v8.3 - Frontend verde 7.18
const API = '';
let generatedSchedine = [];

function escapeHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function setTbodyHtml(tbody, rowsHtml) { tbody.innerHTML = rowsHtml; }

document.addEventListener('DOMContentLoaded', () => { init(); });

async function init() {
    await loadProssima();
    await loadEstrazioni();
    await loadGiocate();
    await loadStats();
    await loadPremi();
    await loadStorico(40);
    await loadBackups();
    await loadDailyStatus();
    bindEvents();
}

function bindEvents() {
    document.getElementById('btnGenera').addEventListener('click', genera);
    const btnRand = document.getElementById('btnGeneraRand');
    if (btnRand) btnRand.addEventListener('click', generaRand);
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
    const btnStrat = document.getElementById('btnGenStrategia');
    if (btnStrat) btnStrat.addEventListener('click', generaStrategia);
    const btnSalvaStrat = document.getElementById('btnSalvaStrategia');
    if (btnSalvaStrat) btnSalvaStrat.addEventListener('click', salvaStrategia);
    const btnGenMulti = document.getElementById('btnGenMulti');
    if (btnGenMulti) btnGenMulti.addEventListener('click', generaMultiStrategia);
    const btnImp = document.getElementById('btnImportaGiocata');
    if (btnImp) btnImp.addEventListener('click', importaGiocata);
    const btnClr = document.getElementById('btnClearGiocate');
    if (btnClr) btnClr.addEventListener('click', clearGiocate);
    const btnBak = document.getElementById('btnBackup');
    if (btnBak) btnBak.addEventListener('click', backupNow);
    const btnRes = document.getElementById('btnRestoreBackup');
    if (btnRes) btnRes.addEventListener('click', restoreBackup);
    // Daily enforcement system
    const btnDailyGen = document.getElementById('btnDailyGenerate');
    if (btnDailyGen) btnDailyGen.addEventListener('click', generaGiornaliera);
    const btnDailyReport = document.getElementById('btnDailyReport7');
    if (btnDailyReport) btnDailyReport.addEventListener('click', loadDailyReport7);
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
    if (data.oggi) {
        document.getElementById('nextDate').style.color = 'var(--warning)';
        // popup giorno estrazione (richiesta)
        const modal = document.getElementById('modalDrawDay');
        const txt = document.getElementById('drawDayText');
        if (modal && txt) {
            txt.textContent = `Oggi ${data.data} è estrazione — gioca entro le 19:30!`;
            modal.classList.add('active');
            try { new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==').play().catch(()=>{}); } catch {}
            setTimeout(()=> modal.classList.remove('active'), 6000);
        }
    }
    try { const jp = await apiGet('/api/jackpot'); if (jp.jackpot) document.getElementById('jackpot').textContent = jp.jackpot; } catch {}
}

async function loadEstrazioni() {
    const data = await apiGet('/api/estrazioni?n=20');
    const tbody = document.querySelector('#estrazioniTable tbody');
    tbody.innerHTML = data.map(e => `<tr><td>${escapeHtml(e.data)}</td><td class="numeri-cell">${escapeHtml(e.numeri.join(' - '))}</td><td>${escapeHtml(e.jolly||'-')}</td><td>${escapeHtml(e.star||'-')}</td></tr>`).join('');
}

async function loadGiocate() {
    const data = await apiGet('/api/giocate');
    const tbody = document.querySelector('#giocateTable tbody');
    let spent=0, won=0, m2=0,m3=0,m4=0;
    tbody.innerHTML = data.map(g => {
        spent+=1;
        let esito='<span class="esito-perdita">in attesa</span>';
        if (g.verificato && g.vincita>0) { won+=g.vincita; if(g.vincita>=100000) m4++; else if(g.vincita>=25) m3++; else if(g.vincita>=5) m2++; esito=`<span class="esito-vinto">+€${escapeHtml(g.vincita.toLocaleString('it-IT'))}</span>`; }
        else if (g.verificato) esito='<span class="esito-perdita">nessuna</span>';
        return `<tr><td>${escapeHtml(g.data)}</td><td class="numeri-cell">${escapeHtml(g.numeri)}</td><td>${escapeHtml(g.somma)}</td><td>${esito}</td><td><button class="btn btn-danger" style="padding:4px 8px;font-size:11px;" onclick="cancellaGiocata(${g.id})">🗑️</button></td></tr>`;
    }).join('');
    const roi = spent>0 ? ((won/spent-1)*100).toFixed(1) : '0.0';
    document.getElementById('statSpeso').textContent=`€${spent}`;
    document.getElementById('statVinto').textContent=`€${won.toLocaleString('it-IT')}`;
    document.getElementById('statRoi').textContent=`${roi}%`;
    document.getElementById('statM2').textContent=m2;
    document.getElementById('statM3').textContent=m3;
    document.getElementById('statM4').textContent=m4;
    // Mostra/nascondi bottone clear in base ai dati già caricati (evita doppia chiamata API)
    const btn = document.getElementById('btnClearGiocate');
    if (btn) btn.style.display = data.length > 0 ? 'block' : 'none';
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
        grid.innerHTML = items.map(([k,v]) => `<div class="stat"><span class="stat-label">${escapeHtml(k)}</span><span class="stat-value">${escapeHtml(v)}</span></div>`).join('');
        const top = document.getElementById('top10');
        if (top && s.num_counts) {
            const entries = Object.entries(s.num_counts).slice(0,10);
            top.innerHTML = entries.map(([n,c],i) => `${escapeHtml(i+1)}. Numero ${escapeHtml(n)} — ${escapeHtml(c)} volte`).join('<br>');
        }
    } catch {}
}

async function loadPremi() {
    try {
        const data = await apiGet('/api/premi');
        const tbody = document.getElementById('premiBody');
        if (tbody && data.premi) {
            tbody.innerHTML = data.premi.map(p => `<tr><td>${escapeHtml(p.match)}</td><td>1:${escapeHtml(p.odds)}</td><td>€${escapeHtml(p.premio.toLocaleString('it-IT'))}</td><td>${escapeHtml(p.ultimo||'-')}</td></tr>`).join('');
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
        tbody.innerHTML = data.map(e => `<tr><td>${escapeHtml(e.data)}</td><td class="numeri-cell">${escapeHtml(e.numeri.join(' - '))}</td><td>${escapeHtml(e.jolly||'-')}</td><td>${escapeHtml(e.star||'-')}</td><td>${escapeHtml(e.numeri.reduce((a,b)=>a+b,0))}</td></tr>`).join('');
    } catch {}
}

async function genera() {
    const n = parseInt(document.getElementById('numSchedine').value);
    if (n>5) { alert('Max 5 schedine per volta'); return; }
    const data = await apiGet(`/api/genera?n=${n}&strategy=auto`);
    generatedSchedine = data;
    const container = document.getElementById('generated');
    container.innerHTML = data.map((s,i) => `<div class="schedina"><span class="schedina-num">Schedina ${escapeHtml(i+1)} <small style="opacity:.6">[${escapeHtml(s.strategy)}]</small>:</span><span class="schedina-nums">${escapeHtml(s.nums.join(' - '))}</span><span class="schedina-somma">[${escapeHtml(s.sum)}]</span></div>`).join('');
    document.getElementById('btnSalva').style.display='block';
    const badge = document.getElementById('autoStrategyBadge');
    if (badge && data[0]) badge.textContent = `Auto → ${data[0].strategy} (richiesta: ${data[0].requested})`;
    setStatus(`Generate ${n} schedine (auto: ${data[0]?.strategy||'?'})`);
    // suono Win (richiesta)
    try { const ctx=new (window.AudioContext||window.webkitAudioContext)(); const o=ctx.createOscillator(); o.type='sine'; o.frequency.value=880; o.connect(ctx.destination); o.start(); setTimeout(()=>{o.stop(); ctx.close();},180); } catch {}
}
async function generaRand() {
    const n = parseInt(document.getElementById('numSchedine').value);
    const data = await apiGet(`/api/genera?n=${n}&strategy=quartile`);
    generatedSchedine = data;
    document.getElementById('generated').innerHTML = data.map((s,i) => `<div class="schedina"><span class="schedina-num">Schedina ${escapeHtml(i+1)} [quartile]:</span><span class="schedina-nums">${escapeHtml(s.nums.join(' - '))}</span><span class="schedina-somma">[${escapeHtml(s.sum)}]</span></div>`).join('');
    document.getElementById('btnSalva').style.display='block';
    const badge = document.getElementById('autoStrategyBadge');
    if (badge) badge.textContent = 'Modalità manuale: quartile';
    setStatus(`Generate ${n} schedine (quartile)`);
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
    let html=`<div style="margin-bottom:16px;"><strong>Verificate:</strong> ${escapeHtml(result.checked)} | <strong>Saltate:</strong> ${escapeHtml(result.skipped)} | <strong>Totale:</strong> €${escapeHtml(result.tot_win.toLocaleString('it-IT'))}</div>`;
    if(result.results?.length){ html+='<div style="max-height:300px;overflow-y:auto;">'+result.results.map(r=>`<div style="padding:4px 0;border-bottom:1px solid var(--border);"><strong>${escapeHtml(r.data)}</strong> — ${escapeHtml(r.matches)} indovinati${r.jolly_hit?' (+Jolly)':''} → <span class="${r.premio>0?'esito-vinto':'esito-perdita'}">${r.premio>0?'€'+escapeHtml(r.premio.toLocaleString('it-IT')):'nessuna'}</span></div>`).join('')+'</div>'; }
    c.innerHTML=html; document.getElementById('modalVerifica').classList.add('active');
}
function closeModal(){ document.getElementById('modalVerifica').classList.remove('active'); }
function showNotification(msg) { document.getElementById('statusBar').textContent = msg; setTimeout(() => { if(document.getElementById('statusBar').textContent===msg) document.getElementById('statusBar').textContent='Pronto'; }, 4000); }
async function cancellaGiocata(id){ if(!confirm('Cancellare?')) return; const r=await apiPost('/api/cancella',{id}); if(r.ok){ showNotification(r.notification||'Schedina cancellata'); await loadGiocate(); } }
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

async function importaGiocata() {
    const status = document.getElementById('toolStatus');
    const data = document.getElementById('toolData').value.trim();
    const numeriStr = document.getElementById('toolNumeri').value.trim();
    if (!data || !numeriStr) { status.textContent='Inserisci data e numeri'; return; }
    const nums = numeriStr.split(/[-,\s]+/).map(x=>parseInt(x)).filter(x=>!isNaN(x));
    if (nums.length !== 6) { status.textContent='Devi inserire esattamente 6 numeri'; return; }
    status.textContent='Importazione...';
    try {
        const r = await apiPost('/api/importa_giocata', { data: data, numeri: nums });
        if (r.ok) { status.textContent=`Importata! Data: ${data}, Somma: ${nums.reduce((a,b)=>a+b,0)}. Verifica con "Verifica Tutte".`; document.getElementById('toolNumeri').value=''; }
        else status.textContent = `Errore: ${r.error||'bloccato'}`;
    } catch(e) { status.textContent='Errore rete'; }
}

async function clearGiocate() {
    if (!confirm('Cancellare TUTTE le giocate?')) return;
    try {
        const r = await apiPost('/api/clear_giocate', {});
        if (r.ok || r.deleted) {
            showNotification(r.notification||'Tutte le giocate cancellate');
            document.getElementById('btnClearGiocate').style.display='none';
            await loadGiocate();
        }
    } catch {}
}

async function loadBackups() {
    try {
        const data = await apiGet('/api/backups');
        const sel = document.getElementById('backupSelect');
        if (!sel) return;
        sel.innerHTML = '<option value="">Seleziona backup</option>';
        if (data.backups && data.backups.length > 0) {
            sel.style.display = 'block';
            data.backups.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.timestamp;
                opt.textContent = `${b.timestamp} (${b.size_db})`;
                sel.appendChild(opt);
            });
        } else {
            sel.style.display = 'none';
        }
    } catch {}
}

async function loadRanking() {
    try {
        const data = await apiGet('/api/ranking');
        const tbody = document.querySelector('#rankingTable tbody');
        if (!tbody) return;
        const list = Array.isArray(data) ? data : (data.rankings || []);
        tbody.innerHTML = list.map(item => `<tr><td>${escapeHtml(item.strategy || item.name || 'N/A')}</td><td>${escapeHtml(item.score != null ? item.score.toFixed?.(3) ?? item.score : 'N/A')}</td><td>${escapeHtml(item.rank || 'N/A')}</td></tr>`).join('');
    } catch (err) {
        console.error('Failed to load ranking', err);
    }
}

async function backupNow() {
    const btn = document.getElementById('btnBackup');
    if (!btn) return;
    btn.disabled = true;
    btn.textContent = '💾 Backup in corso...';
    try {
        const r = await apiPost('/api/backup', {});
        showNotification(`Backup: ${r.backup}`);
        await loadBackups();
    } catch {
        showNotification('Errore backup');
    }
    btn.disabled = false;
    btn.textContent = '💾 Backup Ora';
}

async function restoreBackup() {
    const sel = document.getElementById('backupSelect');
    if (!sel || !sel.value) { showNotification('Nessun backup selezionato'); return; }
    if (!confirm(`Ripristinare backup ${sel.value}? Perderai le modifiche successive.`)) return;
    try {
        const r = await apiPost('/api/restore_backup', {timestamp: sel.value});
        showNotification(`Ripristinato: ${r.restored.join(', ')}`);
        await loadGiocate();
        await loadBackups();
    } catch {
        showNotification('Errore ripristino');
    }
}

// === STRATEGIE ===
let generatedStrategia = [];
async function generaStrategia() {
    const strat = document.getElementById('strategiaSelect').value;
    const container = document.getElementById('strategiaGenerated');
    const status = document.getElementById('strategiaStatus');
    status.textContent='Generazione...';
    try {
        const r = await apiGet(`/api/genera?n=1&strategy=${strat}`);
        if (r.length > 0) {
            generatedStrategia = r;
            const s = r[0];
            container.innerHTML = `<div class="schedina"><span class="schedina-num">Strategia ${escapeHtml(strat)}:</span><span class="schedina-nums">${escapeHtml(s.nums.join(' - '))}</span><span class="schedina-somma">[${escapeHtml(s.sum)}]</span></div>`;
            status.textContent=`Generata (${strat}), somma ${s.sum}`;
            document.getElementById('btnSalvaStrategia').style.display='block';
        }
    } catch {
        status.textContent='Errore generazione';
    }
}
async function salvaStrategia() {
    if (generatedStrategia.length===0) return;
    const s = generatedStrategia[0];
    try {
        const r = await apiPost('/api/salva', { schedine: [{nums: s.nums}] });
        if (r.blocked) { showNotification(r.msg||'Bloccato'); } else { showNotification(`Salvata! ${r.saved} schedina`); document.getElementById('btnSalvaStrategia').style.display='none'; }
        await loadGiocate();
    } catch {
        showNotification('Errore salvataggio');
    }
}

async function generaMultiStrategia() {
    const strat = document.getElementById('strategiaSelect').value;
    const container = document.getElementById('strategiaGenerated');
    const status = document.getElementById('strategiaStatus');
    status.textContent = 'Generazione 5 schedine...';
    try {
        const r = await apiGet(`/api/genera?n=5&strategy=${strat}`);
        if (r.length > 0) {
            generatedStrategia = r;
            container.innerHTML = r.map((s, i) =>
                `<div class="schedina"><span class="schedina-num">Schedina ${escapeHtml(i+1)}:</span><span class="schedina-nums">${escapeHtml(s.nums.join(' - '))}</span><span class="schedina-somma">[${escapeHtml(s.sum)}]</span></div>`
            ).join('');
            status.textContent = `Generate ${r.length} schedine (${strat}). Salva una alla volta.`;
            document.getElementById('btnSalvaStrategia').style.display = 'block';
        }
    } catch {
        status.textContent = 'Errore generazione';
    }
}

// === DAILY ENFORCEMENT SYSTEM ===
let dailyStatus = null;

async function loadDailyStatus() {
    try {
        const data = await apiGet('/api/daily/status');
        dailyStatus = data;
        renderDailyStatus(data);
    } catch (err) {
        console.error('Failed to load daily status', err);
    }
}

function renderDailyStatus(data) {
    const container = document.getElementById('dailyStrategies');
    if (!container) return;
    const strategies = data.strategies || {};
    const entries = Object.entries(strategies);
    const played = entries.filter(([,v]) => v.played).length;
    const total = entries.length;
    let html = `<div class="daily-header">
        <h4>Gioco Responsabile — ${escapeHtml(data.date)}</h4>
        <span class="daily-counter">${played}/${total} strategie utilizzate oggi</span>
    </div>`;
    html += '<div class="daily-tiers">';
    const tiers = { A: { label: 'Tier A — Priorità Alta', color: '#22c55e' }, B: { label: 'Tier B — Priorità Media', color: '#f59e0b' }, C: { label: 'Tier C — Esplorativa', color: '#94a3b8' } };
    for (const [tierKey, tierInfo] of Object.entries(tiers)) {
        const tierEntries = entries.filter(([,v]) => v.tier === tierKey);
        if (tierEntries.length === 0) continue;
        html += `<div class="daily-tier" style="border-left: 3px solid ${tierInfo.color};">
            <div class="daily-tier-label">${escapeHtml(tierInfo.label)}</div>`;
        for (const [name, info] of tierEntries) {
            const statusClass = info.played ? 'played' : 'available';
            const playedLabel = info.played ? (info.is_override ? 'Override' : 'Giocata') : 'Disponibile';
            html += `<div class="daily-strategy ${statusClass}">
                <div class="daily-strat-info">
                    <span class="daily-priority">#${escapeHtml(info.priority)}</span>
                    <strong>${escapeHtml(info.label)}</strong>
                    <span class="daily-transparency">${escapeHtml(info.transparency)}</span>
                </div>
                <div class="daily-strat-status">
                    <span class="daily-badge ${statusClass}">${escapeHtml(playedLabel)}</span>
                    ${info.played && info.numeri ? `<span class="daily-nums">${escapeHtml(info.numeri)}</span>` : ''}
                    ${!info.played ? `<button class="btn btn-small" onclick="generaOverride('${escapeHtml(name)}')">Scegli</button>` : ''}
                </div>
            </div>`;
        }
        html += '</div>';
    }
    html += '</div>';
    container.innerHTML = html;
}

async function generaGiornaliera() {
    const status = document.getElementById('dailyGenerateStatus');
    if (status) status.textContent = 'Generazione schedina del giorno...';
    try {
        const r = await apiGet('/api/daily/generate');
        if (r.error) {
            if (status) status.textContent = `⚠️ ${escapeHtml(r.error)}`;
            return;
        }
        if (r.blocked) {
            if (status) status.textContent = `🚫 Bloccato: ${escapeHtml(r.error || 'Strategia non disponibile')}`;
            return;
        }
        const container = document.getElementById('dailyResult');
        if (container) {
            container.innerHTML = `<div class="schedina">
                <div class="daily-result-header">
                    <span class="daily-badge tier-${escapeHtml(r.tier)}">Tier ${escapeHtml(r.tier)} — Priorità #${escapeHtml(r.priority)}</span>
                    ${r.is_override ? '<span class="daily-badge override">Override</span>' : ''}
                </div>
                <span class="schedina-num">${escapeHtml(r.label)} (${escapeHtml(r.strategy)}):</span>
                <span class="schedina-nums">${escapeHtml(r.nums.join(' - '))}</span>
                <span class="schedina-somma">[${escapeHtml(r.somma)}]</span>
                <div class="daily-transparency-note">${escapeHtml(r.transparency)}</div>
            </div>`;
            container.style.display = 'block';
        }
        if (status) status.textContent = `✅ Generata: ${escapeHtml(r.label)} — somma ${escapeHtml(r.somma)}`;
        await loadDailyStatus();
    } catch (err) {
        if (status) status.textContent = 'Errore nella generazione';
    }
}

async function generaOverride(strategy) {
    if (!confirm(`Sei sicuro di voler usare la strategia "${strategy}"? Questa azione sovrascrive la priorità giornaliera.`)) return;
    const status = document.getElementById('dailyGenerateStatus');
    if (status) status.textContent = `Generazione override: ${strategy}...`;
    try {
        const r = await apiGet(`/api/daily/generate?strategy=${strategy}&override=1`);
        if (r.error) {
            if (status) status.textContent = `⚠️ ${escapeHtml(r.error)}`;
            return;
        }
        if (r.blocked) {
            if (status) status.textContent = `🚫 Bloccato: ${escapeHtml(r.error)}`;
            return;
        }
        const container = document.getElementById('dailyResult');
        if (container) {
            container.innerHTML = `<div class="schedina">
                <div class="daily-result-header">
                    <span class="daily-badge tier-${escapeHtml(r.tier)}">Tier ${escapeHtml(r.tier)} — Priorità #${escapeHtml(r.priority)}</span>
                    <span class="daily-badge override">Override attivo</span>
                </div>
                <span class="schedina-num">${escapeHtml(r.label)} (${escapeHtml(r.strategy)}):</span>
                <span class="schedina-nums">${escapeHtml(r.nums.join(' - '))}</span>
                <span class="schedina-somma">[${escapeHtml(r.somma)}]</span>
                <div class="daily-transparency-note">${escapeHtml(r.transparency)}</div>
            </div>`;
            container.style.display = 'block';
        }
        if (status) status.textContent = `✅ Override completato: ${escapeHtml(r.label)}`;
        await loadDailyStatus();
    } catch (err) {
        if (status) status.textContent = 'Errore nella generazione override';
    }
}

async function loadDailyReport7() {
    const container = document.getElementById('dailyReport7');
    if (!container) return;
    container.innerHTML = '<p style="color:var(--text-muted)">Caricamento report 7 giorni...</p>';
    try {
        const data = await apiGet('/api/daily/report7');
        const report = data.report || [];
        let html = '<h4>Report Compliance 7 Giorni</h4><table class="table"><thead><tr><th>Data</th><th>Estrazione</th><th>Giocate</th><th>Strategie</th><th>Override</th><th>Compliant</th></tr></thead><tbody>';
        for (const day of report) {
            const statusIcon = day.compliant ? '✅' : '❌';
            const strategiesList = day.strategies_used.length > 0 ? day.strategies_used.join(', ') : 'Nessuna';
            html += `<tr>
                <td>${escapeHtml(day.date)}</td>
                <td>${day.is_draw_day ? '📅 Sì' : '—'}</td>
                <td>${escapeHtml(day.plays_count)}</td>
                <td>${escapeHtml(strategiesList)}</td>
                <td>${day.any_override ? '⚠️ Sì' : 'No'}</td>
                <td>${statusIcon}</td>
            </tr>`;
        }
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = '<p style="color:var(--text-muted)">Errore nel caricamento del report</p>';
    }
}
