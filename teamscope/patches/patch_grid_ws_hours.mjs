import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// 1. Add duration_hours to wsMap entries
const oldPush = 'wsM[cc.id][wk].push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed"});';
const newPush = 'wsM[cc.id][wk].push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed",hours:parseFloat(w.duration_hours||0)});';
if (!c.includes(oldPush)) { console.error('FAIL: wsMap push'); process.exit(1); }
c = c.replace(oldPush, newPush);
console.log('✓ Added hours to wsMap entries');

// 2. Replace Tb component
const tbStart = c.indexOf('function Tb({planned:e,');
const tbEnd = c.indexOf('\nfunction TsCellSheet(');
if (tbStart < 0 || tbEnd < 0) { console.error('FAIL: Tb bounds', tbStart, tbEnd); process.exit(1); }

const newTb = `function Tb({planned:e,actual:t,utilPct:n,projects:r,warnPct:a,dangerPct:l,workshops:ws}){
  const pm={};
  for(const p of(r||[])){pm[p.project_name]={name:p.project_name,color:p.color,hours:p.hours,wsHrs:0,ws:[]};}
  let totalWsHrs=0;
  for(const w of(ws||[])){
    const wh=w.hours||0;
    totalWsHrs+=wh;
    if(pm[w.proj_name]){pm[w.proj_name].ws.push(w.name);pm[w.proj_name].wsHrs+=wh;}
    else pm[w.proj_name]={name:w.proj_name,color:w.color,hours:0,wsHrs:wh,ws:[w.name]};
  }
  const pills=Object.values(pm);
  const hasPills=pills.length>0;
  const totalPlanned=e+totalWsHrs;
  return s.jsx("div",{className:Q("min-w-[140px] px-2 py-1.5 text-xs rounded select-none transition-colors",Pb(n,a,l)),
    children:hasPills?s.jsxs(s.Fragment,{children:[
      totalPlanned>0&&s.jsxs("div",{className:"flex items-baseline justify-between gap-2 mb-1.5",children:[
        s.jsxs("span",{className:"font-semibold tabular-nums",children:[totalPlanned.toFixed(1),"h"]}),
        t>0&&s.jsxs("span",{className:"opacity-60 tabular-nums text-[10px]",children:[t,"h actual"]}),
        n>0&&s.jsxs("span",{className:"opacity-60 tabular-nums",children:[n.toFixed(0),"%"]}),
      ]}),
      s.jsx("div",{className:"space-y-0.5",children:pills.map((o,i)=>{
        const pillHrs=o.hours+o.wsHrs;
        return s.jsxs("div",{className:"flex items-center gap-1 px-1.5 py-0.5 rounded-full text-white text-[10px] font-medium",
          style:{backgroundColor:o.color},children:[
          s.jsx("span",{className:"truncate flex-1",style:{maxWidth:80},children:o.name}),
          pillHrs>0&&s.jsx("span",{className:"shrink-0 font-semibold",children:pillHrs.toFixed(1)+"h"}),
          o.ws.length>0&&s.jsx("span",{className:"shrink-0 opacity-80",children:"\\uD83D\\uDCC5"}),
        ]},i);
      })})
    ]}):s.jsx("div",{className:"opacity-30 text-center py-1",children:"\\u2014"})
  });
}
`;

c = c.slice(0, tbStart) + newTb + c.slice(tbEnd);
console.log('✓ Tb rewritten with workshop hours');

// 3. Also add workshop hours to the TsCellSheet drawer header
// The wsThisWeek entries in TsCellSheet also need hours
// Check the wsThisWeek push in TsCellSheet
const oldTsPush = `wsList.push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed",workshop_date:w.workshop_date,status:w.status});`;
if (c.includes(oldTsPush)) {
  c = c.replace(oldTsPush, `wsList.push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed",workshop_date:w.workshop_date,status:w.status,duration_hours:w.duration_hours||0});`);
  console.log('✓ Added duration_hours to TsCellSheet ws entries');
}

writeFileSync('/home/coder/teamscope_v3.js', c);

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['wsMap has hours',     v.includes('hours:parseFloat(w.duration_hours||0)')],
  ['Tb totalWsHrs',       v.includes('totalWsHrs+=wh')],
  ['Tb totalPlanned',     v.includes('totalPlanned=e+totalWsHrs')],
  ['Tb pillHrs',           v.includes('pillHrs=o.hours+o.wsHrs')],
  ['TsCellSheet intact',   v.includes('function TsCellSheet(')],
  ['Rb intact',            v.includes('function Rb(')],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
