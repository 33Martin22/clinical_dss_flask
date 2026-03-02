/* charts.js — Plotly chart rendering with dark theme */

const COLORS = { Low:'#10b981', Medium:'#f59e0b', High:'#ef4444' };
const DARK   = { paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
                 font:{ family:'DM Mono, monospace', color:'#7a92b0', size:11 },
                 margin:{l:20,r:20,t:30,b:30} };

function riskTrendChart(elementId, dates, risks) {
  if (!dates || !dates.length) return;
  Plotly.newPlot(elementId, [{
    x: dates, y: risks, type:'scatter', mode:'lines+markers',
    line:{ color:'#3b82f6', width:2, dash:'dot' },
    marker:{ size:10, color: risks.map(r => r===3?COLORS.High:r===2?COLORS.Medium:COLORS.Low),
             line:{color:'#111827',width:2} },
    hovertemplate:'<b>%{y}</b><br>%{x}<extra></extra>',
  }], {
    ...DARK,
    yaxis:{ tickvals:[1,2,3], ticktext:['Low','Medium','High'],
            range:[0,4], gridcolor:'#1f2d45', zeroline:false },
    xaxis:{ gridcolor:'#1f2d45', zeroline:false },
    height:240,
  }, {responsive:true, displayModeBar:false});
}

function pieChart(elementId, counts) {
  const labels = Object.keys(counts).filter(k=>counts[k]>0);
  if (!labels.length) return;
  Plotly.newPlot(elementId, [{
    type:'pie', labels, values:labels.map(l=>counts[l]),
    marker:{colors:labels.map(l=>COLORS[l])},
    hole:0.5, textinfo:'label+percent',
    hovertemplate:'<b>%{label}</b>: %{value}<extra></extra>',
    textfont:{ color:'#e8edf5', size:12 },
  }], { ...DARK, height:240, showlegend:false,
       margin:{l:10,r:10,t:10,b:10} },
  {responsive:true, displayModeBar:false});
}

function probBar(elementId, probs) {
  if (!probs || !probs.length) return;
  const labels = ['High','Low','Medium'];
  Plotly.newPlot(elementId, [{
    type:'bar', x:labels, y:probs.map(p=>p*100),
    marker:{ color:labels.map(l=>COLORS[l]),
             line:{color:'rgba(0,0,0,0)',width:0} },
    text:probs.map(p=>(p*100).toFixed(1)+'%'),
    textposition:'auto', textfont:{color:'#fff'},
  }], { ...DARK,
    yaxis:{ range:[0,100], title:'Probability (%)', gridcolor:'#1f2d45', zeroline:false },
    xaxis:{ zeroline:false },
    height:220,
  }, {responsive:true, displayModeBar:false});
}

function shapBar(elementId, features) {
  if (!features || !features.length) return;
  const names  = features.map(f=>f[0]).reverse();
  const values = features.map(f=>f[1]).reverse();
  Plotly.newPlot(elementId, [{
    type:'bar', orientation:'h', y:names, x:values,
    marker:{ color:'#3b82f6',
             line:{color:'rgba(0,0,0,0)',width:0} },
    text:values.map(v=>v.toFixed(4)), textposition:'auto',
    textfont:{color:'#fff'},
  }], { ...DARK,
    xaxis:{ title:'Mean |SHAP value|', gridcolor:'#1f2d45', zeroline:false },
    yaxis:{ zeroline:false },
    height:220,
  }, {responsive:true, displayModeBar:false});
}

function radarChart(elementId, vitals) {
  const norm = {
    'Resp Rate': Math.min(vitals.rr/30, 1),
    'SpO₂':     vitals.spo2/100,
    'Sys BP':   Math.min(vitals.sbp/200, 1),
    'HR':       Math.min(vitals.hr/150, 1),
    'Temp':     Math.min((vitals.temp-35)/7, 1),
  };
  const cats = [...Object.keys(norm), Object.keys(norm)[0]];
  const vals = [...Object.values(norm), Object.values(norm)[0]];
  Plotly.newPlot(elementId, [{
    type:'scatterpolar', r:vals, theta:cats, fill:'toself',
    fillcolor:'rgba(59,130,246,.15)',
    line:{color:'#3b82f6', width:2},
    marker:{size:5, color:'#3b82f6'},
  }], { ...DARK,
    polar:{ bgcolor:'rgba(0,0,0,0)',
            radialaxis:{visible:true, range:[0,1], gridcolor:'#1f2d45', tickfont:{size:9}},
            angularaxis:{gridcolor:'#1f2d45'} },
    height:240, margin:{l:30,r:30,t:30,b:30},
  }, {responsive:true, displayModeBar:false});
}

// Toggle review cards
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.review-card-header').forEach(h => {
    h.addEventListener('click', () => {
      h.closest('.review-card').classList.toggle('open');
    });
  });
});
