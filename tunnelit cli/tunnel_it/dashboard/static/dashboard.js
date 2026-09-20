const state = {
  metrics: [],
  history: [],
  currentSessionId: null,
  charts: {
    sparklines: {
      total: null,
      success: null,
      latency: null,
      errors: null
    },
    main: null
  },
  filters: { path: '', status: '' }
};

let eventSource = null;
let firstMetricTime = null;

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function init() {
  state.charts.sparklines.total = document.getElementById('sparkline-total');
  state.charts.sparklines.success = document.getElementById('sparkline-2xx');
  state.charts.sparklines.latency = document.getElementById('sparkline-latency');
  state.charts.sparklines.errors = document.getElementById('sparkline-errors');
  state.charts.main = document.getElementById('main-chart');

  setupCopyButtons();
  setupFilters();
  setupHistory();
  setupActions();
  connectSSE();
  
  setInterval(updateUptime, 1000);
}

function connectSSE() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource('/events');
  eventSource.onmessage = (e) => {
    if (state.currentSessionId) return; // Ignore if viewing history
    try {
      const metric = JSON.parse(e.data);
      if (state.metrics.length === 0) firstMetricTime = new Date(metric.timestamp);
      state.metrics.push(metric);
      updateAll();
    } catch (err) {
      console.error(err);
    }
  };
}

function updateAll() {
  updateMetricCards();
  updateStatusBreakdown();
  updateMainChart();
  updateTable();
  updateErrorsPanel();
  updateFooter();
}

function drawSparkline(svgEl, dataPoints, strokeColor) {
    if (!svgEl) return;
    if (dataPoints.length === 0) {
        svgEl.innerHTML = '';
        return;
    }
    
    const width = 100;
    const height = 45;
    const max = Math.max(...dataPoints, 1);
    const min = Math.min(...dataPoints, 0);
    const range = max - min;
    
    const points = dataPoints.map((val, i) => {
        const x = dataPoints.length > 1 ? (i / (dataPoints.length - 1)) * width : width;
        const y = height - (range > 0 ? ((val - min) / range) * height * 0.8 : height * 0.5) - 5;
        return `${x},${y}`;
    });

    let d = `M ${points[0].split(',')[0]} ${points[0].split(',')[1]} `;
    for (let i = 1; i < points.length; i++) {
        d += `L ${points[i].split(',')[0]} ${points[i].split(',')[1]} `;
    }

    svgEl.innerHTML = `
        <path d="${d}" fill="none" stroke="${strokeColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    `;
}

function updateMetricCards() {
    const total = state.metrics.length;
    const success = state.metrics.filter(m => m.status_code >= 200 && m.status_code < 300).length;
    const successRate = total > 0 ? Math.round((success / total) * 100) : 0;
    
    const latencies = state.metrics.map(m => m.duration_ms).sort((a,b) => a-b);
    const avgLatency = total > 0 ? Math.round(latencies.reduce((a,b) => a+b, 0) / total) : 0;
    const p95Latency = latencies.length > 0 ? Math.round(latencies[Math.floor(latencies.length * 0.95)]) : 0;
    
    const errors = state.metrics.filter(m => m.status_code >= 400 || m.is_slow).length;

    document.getElementById('metric-total').textContent = total;
    document.getElementById('metric-2xx-badge').textContent = `${successRate}% OK`;
    document.getElementById('metric-2xx').textContent = successRate + '%';
    document.getElementById('metric-p95-badge').textContent = `P95: ${p95Latency}ms`;
    document.getElementById('metric-avg').innerHTML = `${avgLatency}<span class="text-base text-gray-400 font-normal">ms</span>`;
    document.getElementById('metric-errors-badge').textContent = `${errors} FAULTS`;
    document.getElementById('metric-errors').textContent = errors;

    const N = 60;
    const recent = state.metrics.slice(-N);
    const totalData = [];
    const successData = [];
    const latencyData = [];
    const errorData = [];
    
    let cumTotal = Math.max(0, total - recent.length);
    recent.forEach((m) => {
        cumTotal++;
        totalData.push(cumTotal);
        successData.push(m.status_code >= 200 && m.status_code < 300 ? 1 : 0);
        latencyData.push(m.duration_ms);
        errorData.push(m.status_code >= 400 ? 1 : 0);
    });

    drawSparkline(state.charts.sparklines.total, totalData, '#38bdf8');
    drawSparkline(state.charts.sparklines.success, successData, '#3dd598');
    drawSparkline(state.charts.sparklines.latency, latencyData, '#f59e0b');
    drawSparkline(state.charts.sparklines.errors, errorData, '#ef4444');
}

function updateStatusBreakdown() {
    const total = state.metrics.length || 1;
    const s2xx = state.metrics.filter(m => m.status_code >= 200 && m.status_code < 300).length;
    const s3xx = state.metrics.filter(m => m.status_code >= 300 && m.status_code < 400).length;
    const s4xx = state.metrics.filter(m => m.status_code >= 400 && m.status_code < 500).length;
    const s5xx = state.metrics.filter(m => m.status_code >= 500).length;
    const slow = state.metrics.filter(m => m.is_slow).length;

    const hScore = Math.round(((s2xx + s3xx) / total) * 100);
    document.getElementById('health-score').textContent = hScore + '%';

    document.getElementById('bar-2xx').style.width = (s2xx/total*100) + '%';
    document.getElementById('bar-3xx').style.width = (s3xx/total*100) + '%';
    document.getElementById('bar-4xx').style.width = (s4xx/total*100) + '%';
    document.getElementById('bar-5xx').style.width = (s5xx/total*100) + '%';
    document.getElementById('bar-slow').style.width = (slow/total*100) + '%';

    document.getElementById('legend-2xx-pct').textContent = Math.round(s2xx/total*100) + '%';
    document.getElementById('legend-2xx-count').textContent = s2xx;
    document.getElementById('legend-3xx-pct').textContent = Math.round(s3xx/total*100) + '%';
    document.getElementById('legend-3xx-count').textContent = s3xx;
    document.getElementById('legend-4xx-pct').textContent = Math.round(s4xx/total*100) + '%';
    document.getElementById('legend-4xx-count').textContent = s4xx;
    document.getElementById('legend-5xx-pct').textContent = Math.round(s5xx/total*100) + '%';
    document.getElementById('legend-5xx-count').textContent = s5xx;
    document.getElementById('legend-slow-pct').textContent = Math.round(slow/total*100) + '%';
    document.getElementById('legend-slow-count').textContent = slow;
}

function updateMainChart() {
    const svg = state.charts.main;
    if (!svg) return;
    
    const recent = state.metrics.slice(-20);
    if(recent.length === 0) {
        svg.innerHTML = '';
        return;
    }
    
    const width = 540;
    const height = 180;
    const maxLat = Math.max(...recent.map(m => m.duration_ms), 16);
    
    let content = `
        <line x1="0" y1="0" x2="${width}" y2="0" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
        <line x1="0" y1="${height/2}" x2="${width}" y2="${height/2}" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
        <line x1="0" y1="${height}" x2="${width}" y2="${height}" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
    `;
    
    let points = [];
    recent.forEach((m, i) => {
        const x = (i / Math.max(recent.length - 1, 1)) * width;
        const y = height - ((m.duration_ms / maxLat) * height * 0.9);
        points.push({x, y});
    });
    
    if(points.length > 0) {
        let d = `M ${points[0].x},${points[0].y} `;
        for(let i=1; i<points.length; i++){
            d += `L ${points[i].x},${points[i].y} `;
        }
        
        let areaD = d + `L ${width},${height} L 0,${height} Z`;
        
        content += `
            <defs>
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgba(139, 92, 246, 0.2)"/>
                    <stop offset="100%" stop-color="rgba(139, 92, 246, 0)"/>
                </linearGradient>
            </defs>
            <path d="${areaD}" fill="url(#chartGrad)" />
            <path d="${d}" fill="none" stroke="#8b5cf6" stroke-width="2" class="glow-purple" />
        `;
        
        const lastP = points[points.length-1];
        content += `
            <circle cx="${lastP.x}" cy="${lastP.y}" r="4" fill="#8b5cf6" class="glow-purple">
                <animate attributeName="r" values="4;8;4" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="1;0;1" dur="2s" repeatCount="indefinite" />
            </circle>
        `;
    }
    
    svg.innerHTML = content;
    
    const avg = recent.reduce((sum, m) => sum + m.duration_ms, 0) / recent.length;
    const p95 = [...recent].sort((a,b)=>a.duration_ms - b.duration_ms)[Math.floor(recent.length * 0.95)]?.duration_ms || 0;
    
    document.getElementById('sub-avg').textContent = `${Math.round(avg)}ms`;
    document.getElementById('sub-p95').textContent = `${Math.round(p95)}ms`;
    document.getElementById('sub-throughput').textContent = `${recent.length} reqs`; 
    
    if (recent.length > 0) {
        document.getElementById('x-label-1').textContent = new Date(recent[0].timestamp).toLocaleTimeString();
        document.getElementById('x-label-4').textContent = new Date(recent[recent.length-1].timestamp).toLocaleTimeString();
    }
}

function updateTable() {
    const tbody = document.getElementById('requests-tbody');
    document.getElementById('request-count-badge').textContent = `${state.metrics.length} captured`;
    
    let html = '';
    const filtered = state.metrics.filter(m => {
        const text = (m.path + ' ' + m.method).toLowerCase();
        const matchesText = state.filters.path === '' || text.includes(state.filters.path);
        const sGroup = Math.floor(m.status_code / 100) + 'xx';
        const matchesStatus = state.filters.status === '' || sGroup === state.filters.status;
        return matchesText && matchesStatus;
    }).slice(-100).reverse();
    
    filtered.forEach(m => {
        const time = new Date(m.timestamp).toLocaleTimeString();
        const mClass = `badge-${m.method.toLowerCase()} px-1.5 py-0.5 rounded text-[10px] font-bold inline-block w-[60px] text-center`;
        
        let sClass = '';
        if(m.status_code >= 200 && m.status_code < 300) sClass = 'text-brand-mint';
        else if(m.status_code >= 300 && m.status_code < 400) sClass = 'text-brand-cyan';
        else if(m.status_code >= 400 && m.status_code < 500) sClass = 'text-brand-orange';
        else if(m.status_code >= 500) sClass = 'text-brand-red';

        html += `
            <tr class="hover:bg-[#181a22] transition-colors group">
                <td class="py-2.5 px-2 text-gray-500 whitespace-nowrap">${time}</td>
                <td class="py-2.5 px-2"><span class="${mClass}">${m.method}</span></td>
                <td class="py-2.5 px-2 text-gray-300 truncate max-w-[200px]" title="${m.path}">${m.path}${m.query?'?'+m.query:''}</td>
                <td class="py-2.5 px-2 ${sClass} font-medium">${m.status_code}</td>
                <td class="py-2.5 px-2 ${m.is_slow ? 'text-brand-yellow' : 'text-gray-400'}">${m.duration_ms.toFixed(1)}ms</td>
                <td class="py-2.5 px-2 text-gray-500">${formatBytes(m.request_bytes)}</td>
                <td class="py-2.5 px-2 text-gray-500">${formatBytes(m.response_bytes)}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    document.getElementById('table-footer-text').textContent = `Displaying ${filtered.length} of ${state.metrics.length} active requests`;
}

function updateErrorsPanel() {
    const list = document.getElementById('errors-list');
    const errors = state.metrics.filter(m => m.status_code >= 400 || m.is_slow).slice(-50).reverse();
    
    document.getElementById('errors-badge').textContent = `${errors.length} ERRORS`;
    
    if(errors.length === 0) {
        list.innerHTML = `
            <div class="w-10 h-10 rounded-full bg-[#1b1d26] border border-[#272a38] flex items-center justify-center text-brand-mint mb-3 mx-auto">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
            </div>
            <span class="text-sm italic font-medium text-gray-400 block text-center">No errors yet</span>
            <p class="text-xs text-gray-500 mt-1 max-w-[220px] text-center mx-auto">Tunnel traffic is responding without any 4xx or 5xx faults.</p>
        `;
        list.className = "py-8 flex flex-col items-center justify-center text-center flex-1";
        return;
    }
    
    list.className = "flex-1 overflow-y-auto space-y-2 mt-4 max-h-[300px] pr-2";
    let html = '';
    errors.forEach(m => {
        let type = m.status_code >= 500 ? 'error' : 'warning';
        if (m.is_asset_404) type = 'asset-404';
        
        let color = m.status_code >= 500 ? 'text-brand-red' : 'text-brand-orange';
        
        html += `
            <div class="error-item ${type}">
                <div class="flex justify-between items-start mb-1 text-xs">
                    <span class="text-gray-300 font-mono truncate mr-2">${m.method} ${m.path}</span>
                    <span class="${color} font-bold font-mono">${m.status_code}</span>
                </div>
                <div class="text-[10px] text-gray-500 font-mono">
                    ${new Date(m.timestamp).toLocaleTimeString()} • ${m.duration_ms.toFixed(1)}ms
                </div>
            </div>
        `;
    });
    list.innerHTML = html;
}

function updateFooter() {
    const total = state.metrics.length;
    const failures = state.metrics.filter(m => m.status_code >= 400).length;
    const failRate = total > 0 ? (failures / total * 100).toFixed(1) : "0.0";
    
    const latencies = state.metrics.map(m => m.duration_ms).sort((a,b)=>a-b);
    const avg = total > 0 ? (latencies.reduce((a,b)=>a+b,0)/total).toFixed(1) : "0.0";
    const p95 = latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.95)].toFixed(1) : "0.0";
    
    document.getElementById('footer-failure-rate').textContent = failRate + '%';
    document.getElementById('footer-failure-rate-big').textContent = Math.round(parseFloat(failRate)) + '%';
    document.getElementById('footer-avg').textContent = avg + 'ms';
    document.getElementById('footer-avg-big').innerHTML = `${avg}<span class="text-xs font-normal text-gray-400">ms</span>`;
    document.getElementById('footer-p95').textContent = p95 + 'ms';
    document.getElementById('footer-p95-big').innerHTML = `${p95}<span class="text-xs font-normal text-gray-400">ms</span>`;
}

function updateUptime() {
    if (!firstMetricTime) return;
    const diff = Math.floor((new Date() - firstMetricTime) / 1000);
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    const s = diff % 60;
    
    let text = '';
    if (h > 0) text += `${h}h `;
    if (m > 0) text += `${m}m `;
    text += `${s}s`;
    
    document.getElementById('footer-uptime').textContent = text;
}

function setupCopyButtons() {
    const toast = (msg) => {
        const el = document.createElement('div');
        el.className = 'toast success';
        el.innerHTML = `
            <svg class="w-4 h-4 text-brand-mint" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
            <span class="text-gray-200 ml-2">${msg}</span>
        `;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 3000);
    };

    const attach = (id) => {
        const btn = document.getElementById(id);
        if(!btn) return;
        btn.addEventListener('click', () => {
            const val = btn.getAttribute('data-value');
            navigator.clipboard.writeText(val);
            
            const originalHTML = btn.innerHTML;
            btn.innerHTML = `<svg class="w-3.5 h-3.5 text-brand-mint" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>`;
            setTimeout(() => { btn.innerHTML = originalHTML; }, 1500);
            
            toast('Copied to clipboard');
        });
    };
    
    attach('copy-tunnel-id');
    attach('copy-public-url');
}

function setupFilters() {
    const input = document.getElementById('filter-input');
    if(input) {
        input.addEventListener('input', e => {
            state.filters.path = e.target.value.toLowerCase();
            updateTable();
        });
    }
    
    const btn = document.getElementById('status-filter-btn');
    if(btn) {
        btn.addEventListener('click', () => {
            const current = state.filters.status;
            let next = '2xx';
            if(current === '2xx') next = '4xx';
            else if(current === '4xx') next = '5xx';
            else if(current === '5xx') next = '';
            
            state.filters.status = next;
            btn.querySelector('span').textContent = next === '' ? 'All Status' : next;
            updateTable();
        });
    }
}

function setupHistory() {
    fetch('/api/history').then(r=>r.json()).then(reports => {
        const select = document.getElementById('history-select');
        if(!select) return;
        reports.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.id;
            opt.textContent = `${r.tunnel_id} • ${new Date(r.started_at).toLocaleString()} • ${r.total_requests} reqs`;
            select.appendChild(opt);
        });
    });
    
    const loadBtn = document.getElementById('load-history-btn');
    if(loadBtn) {
        loadBtn.addEventListener('click', () => {
            const id = document.getElementById('history-select').value;
            if(!id) return;
            fetch('/api/report/'+id).then(r=>r.json()).then(data => {
                state.metrics = data.metrics || [];
                state.currentSessionId = id;
                firstMetricTime = state.metrics.length > 0 ? new Date(state.metrics[0].timestamp) : null;
                document.getElementById('system-status').innerHTML = `<span class="text-gray-400">Viewing Archive: ${id.substring(0,8)}</span>`;
                updateAll();
            });
        });
    }
}

function setupActions() {
    const clearBtn = document.getElementById('clear-btn');
    if(clearBtn) {
        clearBtn.addEventListener('click', () => {
            state.metrics = [];
            state.currentSessionId = null;
            firstMetricTime = null;
            document.getElementById('system-status').innerHTML = `
                <span class="relative flex h-2 w-2">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-mint opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-brand-mint"></span>
                </span>
                Healthy (Live)
            `;
            updateAll();
        });
    }
    
    const exportBtn = document.getElementById('export-btn');
    if(exportBtn) {
        exportBtn.addEventListener('click', () => {
            fetch('/api/report').then(r=>r.json()).then(data => {
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `tunnel-report-${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.json`;
                a.click();
                URL.revokeObjectURL(url);
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', init);