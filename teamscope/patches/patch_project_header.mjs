import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// 1. Pass workshops and consultants to Ub from tw
const oldUbCall = `s.jsx(Ub,{project:r,totalPlannedHours:W,deliverableCount:l.length,frameworks:m,onUpdate:E,onDelete:D,onSyncAllocations:()=>u1(n).then(()=>{})})`;
const newUbCall = `s.jsx(Ub,{project:r,totalPlannedHours:W,deliverableCount:l.length,workshops:i,deliverables:l,consultants:c,frameworks:m,onUpdate:E,onDelete:D,onSyncAllocations:()=>u1(n).then(()=>{})})`;

if (!c.includes(oldUbCall)) { console.error('Cannot find Ub call'); process.exit(1); }
c = c.replace(oldUbCall, newUbCall);
console.log('✓ Updated Ub call with workshops/deliverables/consultants');

// 2. Replace the Ub component - find its boundaries
const ubStart = c.indexOf('function Ub(');
if (ubStart < 0) { console.error('Cannot find Ub function'); process.exit(1); }

// Find the end - look for the const after Ub
const ubEndMarker = `const _i={not_started:`;
const ubEnd = c.indexOf(ubEndMarker);
if (ubEnd < 0) { console.error('Cannot find end of Ub'); process.exit(1); }

console.log('Ub from', ubStart, 'to', ubEnd);

const newUb = `function Ub({project:e,totalPlannedHours:t,deliverableCount:n,workshops:ws,deliverables:delivs,consultants:allCons,frameworks:r,onUpdate:a,onDelete:l,onSyncAllocations:o}){
  const[i,u]=b.useState(!1),[c,p]=b.useState({}),[m,x]=b.useState(!1),[y,g]=b.useState(!1);
  const[budgetEdit,setBudgetEdit]=b.useState(null);
  const[budgetSaving,setBudgetSaving]=b.useState(!1);

  function v(){p({...e}),u(!0)}
  function k(h,w){p(E=>({...E,[h]:w}))}
  async function d(){x(!0);try{await a(c),u(!1)}finally{x(!1)}}

  async function saveBudget(){
    if(budgetEdit===null)return;
    setBudgetSaving(!0);
    try{
      const val=budgetEdit===''?null:parseFloat(budgetEdit);
      await a({budgeted_hours:val});
      setBudgetEdit(null);
    }finally{setBudgetSaving(!1);}
  }

  // Compute per-consultant hours from deliverables
  const conHrs={};
  let unassigned=0;
  for(const dv of(delivs||[])){
    const hrs=dv.total_planned_hours||0;
    if(hrs===0)continue;
    // flat_hours go to consultant, qa_hours go to qa_consultant
    const fh=parseFloat(dv.flat_hours||0);
    const qh=parseFloat(dv.qa_hours||0);
    if(dv.consultant_id){
      conHrs[dv.consultant_id]=(conHrs[dv.consultant_id]||0)+fh;
    }else if(fh>0){unassigned+=fh;}
    if(dv.qa_consultant_id){
      conHrs[dv.qa_consultant_id]=(conHrs[dv.qa_consultant_id]||0)+qh;
    }else if(qh>0){unassigned+=qh;}
  }
  // Workshop hours: duration_hours * consultant_count, split among assigned consultants
  for(const w of(ws||[])){
    const wh=parseFloat(w.duration_hours||0);
    if(wh===0)continue;
    if(w.consultants&&w.consultants.length>0){
      for(const wc of w.consultants){
        conHrs[wc.id]=(conHrs[wc.id]||0)+wh;
      }
    }else{
      unassigned+=wh;
    }
  }

  const assignedTotal=Object.values(conHrs).reduce((a,b)=>a+b,0);
  const conMap=new Map((allCons||[]).map(cc=>[cc.id,cc]));

  const wsCount=(ws||[]).length;
  const budget=e.budgeted_hours;

  const f=r.find(h=>h.id===(c.framework_id??e.framework_id));

  return s.jsx("div",{className:"bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5",children:
    i?s.jsxs("div",{className:"space-y-3",children:[
      s.jsxs("div",{className:"grid grid-cols-2 gap-3",children:[
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Project name *"}),s.jsx("input",{type:"text",value:c.name??"",onChange:h=>k("name",h.target.value),className:Ht})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Client name"}),s.jsx("input",{type:"text",value:c.client_name??"",onChange:h=>k("client_name",h.target.value),className:Ht})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Status"}),s.jsx("select",{value:c.status??"active",onChange:h=>k("status",h.target.value),className:Ht,children:$b.map(h=>s.jsx("option",{value:h,children:h.replace("_"," ")},h))})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Color"}),s.jsx("input",{type:"color",value:c.color??"#4C9BE8",onChange:h=>k("color",h.target.value),className:"h-9 w-full cursor-pointer rounded border border-gray-300 dark:border-gray-700"})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Framework"}),s.jsxs("select",{value:c.framework_id??"",onChange:h=>{k("framework_id",h.target.value?Number(h.target.value):null),k("impact_level_id",null)},className:Ht,children:[s.jsx("option",{value:"",children:"None"}),r.map(h=>s.jsx("option",{value:h.id,children:h.name},h.id))]})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Impact level"}),s.jsxs("select",{value:c.impact_level_id??"",onChange:h=>k("impact_level_id",h.target.value?Number(h.target.value):null),className:Ht,disabled:!f,children:[s.jsx("option",{value:"",children:"None"}),f==null?void 0:f.impact_levels.map(h=>s.jsx("option",{value:h.id,children:h.name},h.id))]})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Start date"}),s.jsx("input",{type:"date",value:c.start_date??"",onChange:h=>k("start_date",h.target.value||null),className:Ht})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"End date"}),s.jsx("input",{type:"date",value:c.end_date??"",onChange:h=>k("end_date",h.target.value||null),className:Ht})]}),
      ]}),
      s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Notes"}),s.jsx("textarea",{value:c.notes??"",onChange:h=>k("notes",h.target.value),rows:2,className:Ht})]}),
      s.jsxs("div",{className:"flex items-center justify-between py-1",children:[
        s.jsxs("div",{children:[
          s.jsx("p",{className:"text-sm font-medium text-gray-700 dark:text-gray-300",children:"Snap due dates to Friday"}),
          s.jsx("p",{className:"text-xs text-gray-500 mt-0.5",children:"Consultant due dates move to the Friday of the week work is due. QA starts the following Monday."}),
        ]}),
        s.jsx(Mb,{checked:c.snap_end_to_friday??!1,onChange:h=>k("snap_end_to_friday",h)}),
      ]}),
      s.jsxs("div",{className:"flex gap-2 pt-1",children:[
        s.jsxs("button",{onClick:d,disabled:m||!c.name,className:"flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white text-sm font-medium rounded-md",children:[s.jsx(lt,{size:14})," ",m?"Saving\\u2026":"Save"]}),
        s.jsx("button",{onClick:()=>u(!1),className:"px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md",children:"Cancel"}),
      ]}),
    ]})
    :s.jsxs("div",{className:"space-y-4",children:[
      s.jsxs("div",{className:"flex items-start gap-4",children:[
        s.jsx("span",{className:"w-4 h-4 rounded-full mt-1 shrink-0",style:{backgroundColor:e.color}}),
        s.jsxs("div",{className:"flex-1 min-w-0",children:[
          s.jsxs("div",{className:"flex items-center gap-3 flex-wrap",children:[
            s.jsx("h1",{className:"text-xl font-bold text-gray-900 dark:text-gray-100",children:e.name}),
            s.jsx("span",{className:Q("px-2 py-0.5 rounded text-xs font-medium",Ib[e.status]),children:e.status.replace("_"," ")}),
          ]}),
          e.client_name&&s.jsx("p",{className:"text-sm text-gray-500 mt-0.5",children:e.client_name}),
        ]}),
        s.jsxs("div",{className:"flex items-center gap-1 shrink-0",children:[
          s.jsxs("button",{onClick:async()=>{g(!0);try{await o()}finally{g(!1)}},disabled:y,title:"Recalculate grid allocations from deliverable data",className:"flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700 disabled:opacity-40",children:[s.jsx(K1,{size:13,className:y?"animate-spin":""})," ",y?"Syncing\\u2026":"Sync to Grid"]}),
          s.jsxs("button",{onClick:v,className:"flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700",children:[s.jsx(On,{size:13})," Edit"]}),
          s.jsx("button",{onClick:l,className:"p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors",children:s.jsx(Me,{size:15})}),
        ]}),
      ]}),
      s.jsxs("div",{className:"grid grid-cols-4 gap-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3",children:[
        s.jsxs("div",{className:"text-center",children:[
          s.jsx("div",{className:"text-lg font-bold text-gray-900 dark:text-gray-100 tabular-nums",children:n}),
          s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Deliverables"}),
        ]}),
        s.jsxs("div",{className:"text-center",children:[
          s.jsx("div",{className:"text-lg font-bold text-gray-900 dark:text-gray-100 tabular-nums",children:wsCount}),
          s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Workshops"}),
        ]}),
        s.jsxs("div",{className:"text-center",children:[
          s.jsxs("div",{className:"text-lg font-bold text-gray-900 dark:text-gray-100 tabular-nums",children:[t.toFixed(0),"h"]}),
          s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Planned Hours"}),
        ]}),
        s.jsxs("div",{className:"text-center",children:[
          budgetEdit!==null
            ?s.jsxs("div",{className:"flex items-center justify-center gap-1",children:[
                s.jsx("input",{type:"number",value:budgetEdit,onChange:ev=>setBudgetEdit(ev.target.value),onKeyDown:ev=>{if(ev.key==='Enter')saveBudget();if(ev.key==='Escape')setBudgetEdit(null);},autoFocus:!0,className:"w-20 text-center text-sm border border-gray-300 dark:border-gray-600 rounded px-1 py-0.5 bg-white dark:bg-gray-800",placeholder:"0"}),
                s.jsx("button",{onClick:saveBudget,disabled:budgetSaving,className:"text-xs text-brand-600 hover:text-brand-700 font-medium",children:budgetSaving?"\\u2026":"\\u2713"}),
                s.jsx("button",{onClick:()=>setBudgetEdit(null),className:"text-xs text-gray-400 hover:text-gray-600",children:"\\u2717"}),
              ]})
            :s.jsxs("div",{className:"text-lg font-bold tabular-nums cursor-pointer hover:text-brand-600 transition-colors "+(budget?"text-gray-900 dark:text-gray-100":"text-gray-300 dark:text-gray-600"),onClick:()=>setBudgetEdit(budget!=null?String(budget):''),children:budget?budget+'h':'\\u2014'}),
          s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Budgeted Hours"}),
        ]}),
      ]}),
      (Object.keys(conHrs).length>0||unassigned>0)&&s.jsxs("div",{className:"rounded-lg border border-gray-100 dark:border-gray-800 overflow-hidden",children:[
        s.jsxs("div",{className:"flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/50 text-xs font-medium text-gray-500",children:[
          s.jsx("span",{children:"Hours by Consultant"}),
          s.jsxs("span",{className:"tabular-nums",children:["Assigned: ",assignedTotal.toFixed(1),"h",unassigned>0?" | Unassigned: "+unassigned.toFixed(1)+"h":"",budget?" | Budget: "+budget+"h":""]}),
        ]}),
        s.jsx("div",{className:"divide-y divide-gray-100 dark:divide-gray-800",children:
          [...Object.entries(conHrs).sort((a,b)=>b[1]-a[1]).map(([cid,hrs])=>{
            const cc=conMap.get(Number(cid));
            return s.jsxs("div",{className:"flex items-center gap-2 px-3 py-1.5",children:[
              s.jsx("span",{className:"w-2.5 h-2.5 rounded-full shrink-0",style:{backgroundColor:cc?cc.color:'#999'}}),
              s.jsx("span",{className:"text-sm text-gray-700 dark:text-gray-300 flex-1",children:cc?cc.name:'Unknown'}),
              s.jsxs("span",{className:"text-sm font-semibold tabular-nums text-gray-900 dark:text-gray-100",children:[hrs.toFixed(1),"h"]}),
              budget>0&&s.jsx("div",{className:"w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden ml-2",children:
                s.jsx("div",{className:"h-full rounded-full",style:{width:Math.min(100,hrs/budget*100)+"%",backgroundColor:cc?cc.color:'#999'}}),
              }),
            ]},cid);
          }),
          unassigned>0&&s.jsxs("div",{className:"flex items-center gap-2 px-3 py-1.5",children:[
            s.jsx("span",{className:"w-2.5 h-2.5 rounded-full shrink-0 border border-dashed border-gray-400"}),
            s.jsx("span",{className:"text-sm text-gray-400 italic flex-1",children:"Unassigned"}),
            s.jsxs("span",{className:"text-sm font-semibold tabular-nums text-orange-500",children:[unassigned.toFixed(1),"h"]}),
          ]},'unassigned'),
          ].filter(Boolean)
        }),
        budget>0&&s.jsxs("div",{className:"flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/50 text-xs font-medium",children:[
          s.jsx("span",{className:"text-gray-500",children:"Remaining Budget"}),
          s.jsxs("span",{className:(budget-t)>=0?"text-green-600":"text-red-500",children:[(budget-t).toFixed(1),"h"]}),
        ]}),
      ]}),
    ]})
  });
}
`;

c = c.slice(0, ubStart) + newUb + c.slice(ubEnd);

writeFileSync('/home/coder/teamscope_v3.js', c);

// Verify
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['Ub function',         v.includes('function Ub({project:e,totalPlannedHours:t')],
  ['workshops prop',      v.includes('workshops:ws,deliverables:delivs,consultants:allCons')],
  ['budgetEdit state',    v.includes('budgetEdit,setBudgetEdit')],
  ['conHrs calc',         v.includes('conHrs[dv.consultant_id]')],
  ['unassigned calc',     v.includes('unassigned+=fh')],
  ['workshop hours calc', v.includes('conHrs[wc.id]=(conHrs[wc.id]||0)+wh')],
  ['budgeted_hours',      v.includes('budgeted_hours')],
  ['saveBudget',          v.includes('async function saveBudget()')],
  ['Hours by Consultant', v.includes('Hours by Consultant')],
  ['Remaining Budget',    v.includes('Remaining Budget')],
  ['Ub count=1',          (v.match(/function Ub\(/g)||[]).length===1],
  ['_i const present',    v.includes("const _i={not_started:")],
  ['Ub call updated',     v.includes('workshops:i,deliverables:l,consultants:c,frameworks:m')],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
