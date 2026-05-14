import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// Find the ww function boundaries
const wwStart = c.indexOf('function ww({template:');
if (wwStart < 0) { console.error('Cannot find ww'); process.exit(1); }

// Find the end of ww by brace-counting
let depth = 0, i = wwStart;
while (i < c.length) {
  if (c[i] === '{') depth++;
  if (c[i] === '}') { depth--; if (depth === 0) { i++; break; } }
  i++;
}
const wwEnd = i;
console.log('ww found at', wwStart, '-', wwEnd, 'len=', wwEnd - wwStart);

const newWw = `function ww({template:e,frameworks:t,expanded:n,onToggle:r,onEdit:a,onDelete:l,onAddDeliverable:o,onEditDeliverable:i,onDeleteDeliverable:u}){
  const c=t.find(x=>x.id===e.framework_id),p=c==null?void 0:c.impact_levels.find(x=>x.id===e.impact_level_id);
  const m=e.deliverable_templates.length;
  const wsCount=(e.workshop_templates||[]).length;
  const totalHrs=e.deliverable_templates.reduce((acc,d)=>acc+(d.default_flat_hours||0)+(d.default_qa_hours||0),0);
  const wsHrs=(e.workshop_templates||[]).reduce((acc,w)=>acc+(w.duration_hours||0),0);
  const totalPlanned=totalHrs+wsHrs;
  const byType={};
  e.deliverable_templates.forEach(d=>{const tp=d.deliverable_type||'other';byType[tp]=(byType[tp]||0)+1;});

  const stat=(label,value,sub)=>s.jsxs('div',{className:'flex flex-col items-center px-4 py-2',children:[
    s.jsx('div',{className:'text-lg font-bold text-gray-900 dark:text-gray-100 tabular-nums',children:value}),
    s.jsx('div',{className:'text-[11px] text-gray-500 font-medium',children:label}),
    sub&&s.jsx('div',{className:'text-[10px] text-gray-400 mt-0.5',children:sub}),
  ]});

  return s.jsxs("div",{className:"bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden",children:[
    s.jsxs("div",{className:"flex items-center gap-3 px-4 py-3",children:[
      s.jsx("button",{onClick:r,className:"text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors",children:n?s.jsx(Du,{size:16}):s.jsx(El,{size:16})}),
      s.jsxs("div",{className:"flex-1 min-w-0",children:[
        s.jsxs("div",{className:"flex items-center gap-2 flex-wrap",children:[
          s.jsx("h3",{className:"font-semibold text-gray-900 dark:text-gray-100 text-sm",children:e.name}),
          c&&s.jsx("span",{className:"px-1.5 py-0.5 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400 text-[10px] font-medium rounded",children:c.name}),
          p&&s.jsx("span",{className:"px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-[10px] rounded",children:p.name}),
          s.jsxs("span",{className:"px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 text-[10px] rounded",children:[m," deliverable",m!==1?"s":""]})
        ]}),
        e.description&&s.jsx("p",{className:"text-xs text-gray-500 mt-0.5 truncate",children:e.description})
      ]}),
      s.jsxs("div",{className:"flex gap-1 shrink-0",children:[
        s.jsx("button",{onClick:a,className:"p-1.5 text-gray-400 hover:text-brand-600 transition-colors rounded hover:bg-gray-100 dark:hover:bg-gray-800",children:s.jsx(On,{size:14})}),
        s.jsx("button",{onClick:l,className:"p-1.5 text-gray-400 hover:text-red-600 transition-colors rounded hover:bg-gray-100 dark:hover:bg-gray-800",children:s.jsx(Me,{size:14})})
      ]})
    ]}),
    n&&s.jsx("div",{className:"border-t border-gray-100 dark:border-gray-800 px-4 py-3",children:
      s.jsxs("div",{className:"space-y-3",children:[
        s.jsxs("div",{className:"flex items-center justify-around bg-gray-50 dark:bg-gray-800/50 rounded-lg py-2",children:[
          stat('Deliverables',m),
          stat('Workshops',wsCount),
          stat('Planned Hours',totalPlanned>0?totalPlanned+'h':'\\u2014',totalHrs>0&&wsHrs>0?totalHrs+'h deliv + '+wsHrs+'h ws':null),
        ]}),
        Object.keys(byType).length>0&&s.jsxs("div",{className:"flex flex-wrap gap-1.5",children:[
          s.jsx("span",{className:"text-[11px] text-gray-400 font-medium mr-1 self-center",children:"Types:"}),
          ...Object.entries(byType).map(([tp,cnt])=>s.jsxs("span",{className:"px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-[11px] text-gray-600 dark:text-gray-400 font-medium",children:[cnt,"\\xd7 ",tp.replace(/_/g,' ')]},tp)),
        ]}),
        (e.workshop_templates||[]).length>0&&s.jsxs("div",{className:"flex flex-wrap gap-1.5",children:[
          s.jsx("span",{className:"text-[11px] text-gray-400 font-medium mr-1 self-center",children:"Workshops:"}),
          ...(e.workshop_templates||[]).map((w,wi)=>s.jsxs("span",{className:"px-2 py-0.5 rounded-full text-[11px] font-medium",style:{backgroundColor:'#f5f3ff',color:'#7c3aed'},children:["\\uD83D\\uDCC5 ",w.name,w.duration_hours?' ('+w.duration_hours+'h)':'']},wi)),
        ]}),
      ]})
    }),
  ]});
}`;

c = c.slice(0, wwStart) + newWw + c.slice(wwEnd);
writeFileSync('/home/coder/teamscope_v3.js', c);

// verify
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['ww function exists',     v.includes('function ww({template:')],
  ['stat helper',            v.includes("stat('Deliverables'")],
  ['workshop count',         v.includes("stat('Workshops',wsCount)")],
  ['planned hours',          v.includes("stat('Planned Hours'")],
  ['byType breakdown',       v.includes('Object.entries(byType)')],
  ['workshop pills',         v.includes('workshop_templates||[]')],
  ['ww count=1',             (v.match(/function ww\(/g)||[]).length===1],
  ['Nw present',             v.includes('function Nw(')],
];
let ok=true;
for(const[n,p] of checks){console.log((p?'\\u2713':'\\u2717')+' '+n);if(!p)ok=false;}
console.log('Size:',v.length);
process.exit(ok?0:1);
