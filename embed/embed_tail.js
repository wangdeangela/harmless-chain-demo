// === Streamlit 嵌入模式：无 Flask API，保留 90 秒拓扑动画 ===
if (window.__CF_EMBED__) {
  const CF = window.__CF_EMBED__;

  async function loadScenarioEmbed(scId) {
    const a = CF.assets[scId];
    if (!a) return;
    LOGS = a.logs;
    TOPO = a.topology;
    const f = formatLogs(LOGS);
    renderLogLines($('log-siem'), f.siem);
    renderLogLines($('log-plan'), []);
    renderLogLines($('log-waf'), f.waf, 'alert');
    renderLogLines($('log-fw'), f.fw);
    renderLogLines($('log-app'), f.app);
    renderLogLines($('log-auth'), f.auth);
    renderLogLines($('log-exec'), f.exec);
    renderLogLines($('log-audit'), f.audit);
    resetLiveLogs();
    resetTopoProgress();
    resetVerdictUI();
    $('topo-hint').textContent = '选择场景后点击「启动验证」';
    document.querySelectorAll('.pipe .s').forEach(s => s.classList.remove('on', 'ok'));
    renderTopology(TOPO, { pathStep: 0, animate: false });
  }

  async function initEmbed() {
    renderLegend();
    CFG = CF.platform;
    const mx = CF.matrix;
    $('matrix').querySelector('tbody').innerHTML = mx.map(r =>
      `<tr data-gap="${r.gap}"><td>${r.poc}</td><td>${r.collector.replace('alerted + blocked', '有告警且已拦截').replace('alerted + 未阻断', '有告警未拦截').replace('silent', '无记录').replace('任意', '任意')}</td><td>${r.status === 'blocked' ? '已拦截' : r.status === 'confirmed' ? '成立' : '—'}</td><td>${zhGap(r.gap)}</td></tr>`
    ).join('');
    $('scene-table').querySelector('tbody').innerHTML = CFG.scenarios.map(s =>
      `<tr class="${s.demo ? 'hl' : ''}"><td>${s.name}</td><td>${s.tracks}</td><td>${s.attack}</td><td>${s.demo ? '<span class="tag g">可运行</span>' : '待接入'}</td></tr>`
    ).join('');
    const modeSel = $('mode');
    if (modeSel) {
      modeSel.innerHTML = '<option value="simulated">离线推演</option>';
      modeSel.disabled = true;
    }
    $('b-portal').className = 'badge ok';
    $('b-portal').textContent = '在线演示 ●';
    $('b-target').textContent = '靶场(离线) ○';
    $('b-openaev').textContent = 'OpenAEV ○';
    await loadScenarioEmbed($('scenario').value || CF.defaultScenario);
  }

  $('scenario').onchange = () => loadScenarioEmbed($('scenario').value);
  $('runBtn').onclick = async () => {
    const btn = $('runBtn');
    btn.disabled = true;
    const sc = $('scenario').value;
    const token = ++topoAnimToken;
    document.querySelectorAll('.pipe .s').forEach(s => s.classList.remove('on', 'ok'));
    resetVerdictUI();
    switchTab('center');
    $('workspace').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    try {
      const data = CF.assets[sc]?.runData;
      if (!data) throw new Error('未知场景: ' + sc);
      if (token !== topoAnimToken) return;
      renderResult(data, true);
      await playTopologyAnimation(data, token);
    } catch (e) {
      alert(e);
    }
    btn.disabled = false;
  };

  initEmbed();
} else {
  $('runBtn').onclick = async () => {
    const btn = $('runBtn'); btn.disabled = true;
    const sc = $('scenario').value, mode = $('mode').value;
    const token = ++topoAnimToken;
    document.querySelectorAll('.pipe .s').forEach(s => s.classList.remove('on', 'ok'));
    resetVerdictUI();
    switchTab('center');
    $('workspace').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    try {
      const data = await fetch(`/api/run/${sc}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode }) }).then(r => r.json());
      if (token !== topoAnimToken) return;
      renderResult(data, true);
      await playTopologyAnimation(data, token);
    } catch (e) { alert(e); }
    btn.disabled = false;
  };

  async function health() {
    const h = await fetch('/api/health').then(r => r.json());
    [['b-portal', '控制台', true], ['b-target', '靶场', h.target], ['b-openaev', 'OpenAEV', h.openaev]].forEach(([id, lbl, ok]) => {
      const el = $(id); el.className = 'badge ' + (ok ? 'ok' : ''); el.textContent = lbl + (ok ? ' ●' : ' ○');
    });
  }
  init();
  health(); setInterval(health, 15000);
}
