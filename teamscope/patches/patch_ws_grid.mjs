import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// 1. Add wsMap state
c = c.replace(
  '[w,E]=b.useState(!1),[D,j]=b.useState(null),[Xc,setXc]=b.useState(null),',
  '[w,E]=b.useState(!1),[D,j]=b.useState(null),[Xc,setXc]=b.useState(null),[wsMap,setWsMap]=b.useState({}),'
);

// 2. Add workshop fetch useEffect (note: }}} to close inner-for, outer-for, try)
const wsFetch = 'b.useEffect(()=>{Am("active").then(async ps=>{const wsM={};await Promise.all(ps.map(async pr=>{try{const wsList=await hd(pr.id);for(const w of wsList){if(!w.workshop_date)continue;const wk=Vr(Nd(new Date(w.workshop_date+"T12:00:00")));for(const cc of w.consultants){if(!wsM[cc.id])wsM[cc.id]={};if(!wsM[cc.id][wk])wsM[cc.id][wk]=[];wsM[cc.id][wk].push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed"});}}}catch(ex){}}));setWsMap(wsM);}).catch(()=>{});},[]);';

c = c.replace(
  ']),b.useEffect(()=>{Promise.all([Am(),_l()]).then(([T,L])=>{y(T),v(L)})},[]);function W(',
  `]),b.useEffect(()=>{Promise.all([Am(),_l()]).then(([T,L])=>{y(T),v(L)})},[]);${wsFetch}function W(`
);

// 3. Pass workshops to Tb call
c = c.replace(
  'jsx(Tb,{planned:G.planned_hours,actual:G.actual_hours,utilPct:G.utilization_pct,projects:G.projects,warnPct:t,dangerPct:n})',
  'jsx(Tb,{planned:G.planned_hours,actual:G.actual_hours,utilPct:G.utilization_pct,projects:G.projects,warnPct:t,dangerPct:n,workshops:(wsMap[T.consultant_id]||{})[L]||[]})'
);

// 4. Replace Tb component (single-line, no newlines inside)
const tbStart = c.indexOf('function Tb(');
const tbEnd   = c.indexOf('\nfunction TsCellSheet(');
const newTb = 'function Tb({planned:e,actual:t,utilPct:n,projects:r,warnPct:a,dangerPct:l,workshops:ws}){const hasWs=ws&&ws.length>0;return s.jsx("div",{className:Q("min-w-[140px] px-2 py-1.5 text-xs rounded select-none transition-colors",Pb(n,a,l)),children:(e>0||hasWs)?s.jsxs(s.Fragment,{children:[e>0&&s.jsxs("div",{className:"flex items-baseline justify-between gap-2 mb-1.5",children:[s.jsxs("span",{className:"font-semibold tabular-nums",children:[e,"h"]}),t>0&&s.jsxs("span",{className:"opacity-60 tabular-nums text-[10px]",children:[t,"h actual"]}),s.jsxs("span",{className:"opacity-60 tabular-nums",children:[n.toFixed(0),"%"]})]}),e>0&&s.jsx("div",{className:"space-y-0.5 mb-0.5",children:r.map((o,i)=>s.jsxs("div",{className:"flex items-center justify-between gap-1 px-1.5 py-0.5 rounded-full text-white text-[10px] font-medium",style:{backgroundColor:o.color},children:[s.jsx("span",{className:"truncate",style:{maxWidth:72},children:o.project_name}),s.jsxs("span",{className:"shrink-0 font-semibold",children:[o.hours,"h"]})]},i))}),hasWs&&s.jsx("div",{className:"space-y-0.5",children:ws.map((o,i)=>s.jsx("div",{className:"flex items-center gap-1 px-1.5 py-0.5 rounded text-white text-[10px] font-medium truncate",style:{backgroundColor:o.color,opacity:.85},children:"\uD83D\uDCC5 "+o.name},i))})]}):s.jsx("div",{className:"opacity-30 text-center py-1",children:"\u2014"})})}\n';
c = c.slice(0, tbStart) + newTb + c.slice(tbEnd);

writeFileSync('/home/coder/teamscope_v3.js', c);

const checks = [
  ['wsMap state',            c.includes('wsMap,setWsMap]=b.useState({})')],
  ['workshop fetch (wsM)',   c.includes('const wsM={}')],
  ['three closing braces',   c.includes('}}}catch(ex){')],
  ['workshops passed to Tb', c.includes('workshops:(wsMap[T.consultant_id]')],
  ['Tb renders workshops',   c.includes('hasWs=ws&&ws.length>0')],
  ['Rb still present',       c.includes('function Rb()')],
  ['TsCellSheet present',    c.includes('function TsCellSheet(')],
];
let ok = true;
for (const [name, pass] of checks) {
  console.log((pass ? '✓' : '✗') + ' ' + name);
  if (!pass) ok = false;
}
console.log('Size:', c.length);
process.exit(ok ? 0 : 1);
