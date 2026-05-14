import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

const oldTb = `function Tb({planned:e,actual:t,utilPct:n,projects:r,warnPct:a,dangerPct:l,workshops:ws}){const hasWs=ws&&ws.length>0;return s.jsx("div",{className:Q("min-w-[140px] px-2 py-1.5 text-xs rounded select-none transition-colors",Pb(n,a,l)),children:(e>0||hasWs)?s.jsxs(s.Fragment,{children:[e>0&&s.jsxs("div",{className:"flex items-baseline justify-between gap-2 mb-1.5",children:[s.jsxs("span",{className:"font-semibold tabular-nums",children:[e,"h"]}),t>0&&s.jsxs("span",{className:"opacity-60 tabular-nums text-[10px]",children:[t,"h actual"]}),s.jsxs("span",{className:"opacity-60 tabular-nums",children:[n.toFixed(0),"%"]})]}),e>0&&s.jsx("div",{className:"space-y-0.5 mb-0.5",children:r.map((o,i)=>s.jsxs("div",{className:"flex items-center justify-between gap-1 px-1.5 py-0.5 rounded-full text-white text-[10px] font-medium",style:{backgroundColor:o.color},children:[s.jsx("span",{className:"truncate",style:{maxWidth:72},children:o.project_name}),s.jsxs("span",{className:"shrink-0 font-semibold",children:[o.hours,"h"]})]},i))}),hasWs&&s.jsx("div",{className:"space-y-0.5",children:ws.map((o,i)=>s.jsx("div",{className:"flex items-center gap-1 px-1.5 py-0.5 rounded text-white text-[10px] font-medium truncate",style:{backgroundColor:o.color,opacity:.85},children:"\uD83D\uDCC5 "+o.name},i))})]}):s.jsx("div",{className:"opacity-30 text-center py-1",children:"\u2014"})})}\n`;

// New Tb: merges deliverables and workshops into one pill per project
const newTb = `function Tb({planned:e,actual:t,utilPct:n,projects:r,warnPct:a,dangerPct:l,workshops:ws}){const pm={};for(const p of(r||[])){pm[p.project_name]={name:p.project_name,color:p.color,hours:p.hours,ws:[]};}for(const w of(ws||[])){if(pm[w.proj_name])pm[w.proj_name].ws.push(w.name);else pm[w.proj_name]={name:w.proj_name,color:w.color,hours:0,ws:[w.name]};}const pills=Object.values(pm);const hasPills=pills.length>0;return s.jsx("div",{className:Q("min-w-[140px] px-2 py-1.5 text-xs rounded select-none transition-colors",Pb(n,a,l)),children:hasPills?s.jsxs(s.Fragment,{children:[e>0&&s.jsxs("div",{className:"flex items-baseline justify-between gap-2 mb-1.5",children:[s.jsxs("span",{className:"font-semibold tabular-nums",children:[e,"h"]}),t>0&&s.jsxs("span",{className:"opacity-60 tabular-nums text-[10px]",children:[t,"h actual"]}),s.jsxs("span",{className:"opacity-60 tabular-nums",children:[n.toFixed(0),"%"]})]}),s.jsx("div",{className:"space-y-0.5",children:pills.map((o,i)=>s.jsxs("div",{className:"flex items-center gap-1 px-1.5 py-0.5 rounded-full text-white text-[10px] font-medium",style:{backgroundColor:o.color},children:[s.jsx("span",{className:"truncate flex-1",style:{maxWidth:80},children:o.name}),o.hours>0&&s.jsx("span",{className:"shrink-0 font-semibold",children:o.hours+"h"}),o.ws.length>0&&s.jsx("span",{className:"shrink-0 opacity-80",children:"\uD83D\uDCC5"})]},i))})]}):s.jsx("div",{className:"opacity-30 text-center py-1",children:"\u2014"})})}\n`;

if (!c.includes(oldTb)) { console.error('oldTb not found'); process.exit(1); }
c = c.replace(oldTb, newTb);
writeFileSync('/home/coder/teamscope_v3.js', c);

const checks = [
  ['merged pm map',        c.includes('const pm={};')],
  ['single pill loop',     c.includes('pills.map((o,i)')],
  ['workshop emoji pill',  c.includes('o.ws.length>0')],
  ['hours in merged pill', c.includes('o.hours>0&&')],
  ['Rb present',           c.includes('function Rb()')],
];
let ok = true;
for (const [n,p] of checks) { console.log((p?'✓':'✗')+' '+n); if(!p) ok=false; }
console.log('Size:', c.length);
process.exit(ok ? 0 : 1);
