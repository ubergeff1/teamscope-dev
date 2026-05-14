import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// Find exact boundaries of Wb
const wbStart = c.indexOf('function Wb(');
const wbEnd = c.indexOf('function mo(');

if (wbStart < 0 || wbEnd < 0) { console.error('Cannot find Wb boundaries', wbStart, wbEnd); process.exit(1); }

console.log('Wb from', wbStart, 'to', wbEnd);

const newWb = `function Wb({deliverable:e,workshops:t,consultants:n,onSave:r,onCancel:a}){
  const[l,o]=b.useState(()=>{
    const dp=(e.phases||[]).find(p=>p.phase_type==='draft');
    const qp=(e.phases||[]).find(p=>p.phase_type==='qa');
    return{...e,draft_start_date:dp?dp.start_date:null,draft_end_date:dp?dp.end_date:null,qa_start_date:qp?qp.start_date:null,qa_end_date:qp?qp.end_date:null};
  });
  const[i,u]=b.useState(!1);
  const[autoErr,setAutoErr]=b.useState(null);
  function c(y,g){o(v=>({...v,[y]:g}))}
  const p=t.find(y=>y.id===l.workshop_id),m=(p==null?void 0:p.workshop_date)??null;

  async function x(){
    u(!0);
    try{await r(l)}
    finally{u(!1)}
  }

  async function doAutoGen(){
    u(!0);setAutoErr(null);
    try{
      const pre={
        business_days:l.business_days?parseInt(l.business_days):null,
        qa_business_days:l.qa_business_days?parseInt(l.qa_business_days):null,
        flat_hours:l.flat_hours!=null?parseFloat(l.flat_hours):null,
        qa_hours:l.qa_hours!=null?parseFloat(l.qa_hours):null,
        workshop_sequential:!!l.workshop_sequential,
        qa_sequential:!!l.qa_sequential,
        start_date:l.start_date||null,
        end_date:l.end_date||null,
      };
      await r(pre);
      const res=await H.post('/projects/'+e.project_id+'/deliverables/'+e.id+'/auto-dates');
      const full=res.data;
      const dp2=(full.phases||[]).find(pp=>pp.phase_type==='draft');
      const qp2=(full.phases||[]).find(pp=>pp.phase_type==='qa');
      o(f=>({...f,...full,draft_start_date:dp2?dp2.start_date:null,draft_end_date:dp2?dp2.end_date:null,qa_start_date:qp2?qp2.start_date:null,qa_end_date:qp2?qp2.end_date:null}));
    }catch(er){setAutoErr(er?.response?.data?.detail||'Auto-generate failed');}
    finally{u(!1);}
  }

  const canAuto=l.business_days&&l.qa_business_days&&l.flat_hours&&l.qa_hours&&l.workshop_sequential&&l.qa_sequential&&(l.start_date||l.end_date);

  const tip=(text)=>s.jsx('span',{title:text,className:'inline-flex items-center justify-center w-3 h-3 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 text-[8px] font-bold cursor-help ml-0.5',children:'i'});
  const lbl=(text,tipText)=>s.jsxs('label',{className:'block text-[10px] font-medium text-gray-500 mb-1 flex items-center gap-0.5',children:[text,tipText&&tip(tipText)]});

  return s.jsxs("div",{className:"px-4 pb-4 pt-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50",children:[
    s.jsxs("div",{className:"grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3",children:[
      s.jsxs("div",{className:"col-span-2 sm:col-span-3 lg:col-span-4",children:[
        lbl("Name *","The deliverable name"),
        s.jsx("input",{type:"text",value:l.name??"",onChange:y=>c("name",y.target.value),className:De,autoFocus:!0}),
      ]}),
      s.jsxs("div",{children:[
        lbl("Consultant","Assigned consultant"),
        s.jsxs("select",{value:l.consultant_id??"",onChange:y=>c("consultant_id",y.target.value?Number(y.target.value):null),className:De,children:[
          s.jsx("option",{value:"",children:"\\u2014 None \\u2014"}),
          n.map(y=>s.jsx("option",{value:y.id,children:y.name},y.id)),
        ]}),
      ]}),
      s.jsxs("div",{children:[
        lbl("QA Person","Assigned QA reviewer"),
        s.jsxs("select",{value:l.qa_consultant_id??"",onChange:y=>c("qa_consultant_id",y.target.value?Number(y.target.value):null),className:De,children:[
          s.jsx("option",{value:"",children:"\\u2014 None \\u2014"}),
          n.map(y=>s.jsx("option",{value:y.id,children:y.name},y.id)),
        ]}),
      ]}),
      s.jsxs("div",{children:[
        lbl("Workshop","Linked workshop"),
        s.jsxs("select",{value:l.workshop_id??"",onChange:y=>c("workshop_id",y.target.value?Number(y.target.value):null),className:De,children:[
          s.jsx("option",{value:"",children:"\\u2014 None \\u2014"}),
          t.map(y=>s.jsxs("option",{value:y.id,children:[y.name,y.workshop_date?\` (\${ta(y.workshop_date)})\`:""]},y.id)),
        ]}),
      ]}),
      s.jsxs("div",{children:[
        lbl("Start Date","When work begins"),
        s.jsx("input",{type:"date",value:l.start_date??"",onChange:y=>c("start_date",y.target.value||null),className:De}),
      ]}),
      s.jsxs("div",{children:[
        lbl("Due Date","Overall due date"),
        s.jsx("input",{type:"date",value:l.end_date??"",onChange:y=>c("end_date",y.target.value||null),className:De}),
      ]}),
      s.jsxs("div",{children:[
        lbl("Consultant Days","Business days for consultant"),
        s.jsx("input",{type:"number",min:1,step:1,value:l.business_days??"",onChange:y=>c("business_days",y.target.value?Number(y.target.value):null),className:De}),
      ]}),
      s.jsxs("div",{children:[
        lbl("Consultant Due","Consultant draft deadline"),
        s.jsx("input",{type:"date",value:l.draft_end_date??"",onChange:y=>c("draft_end_date",y.target.value||null),className:De}),
      ]}),
      s.jsxs("div",{children:[
        lbl("Consultant Hours","Hours for consultant work"),
        s.jsx("input",{type:"number",min:0,step:.5,value:l.flat_hours??"",onChange:y=>c("flat_hours",y.target.value?Number(y.target.value):null),className:De}),
      ]}),
      s.jsxs("div",{children:[
        lbl("QA Days","Business days for QA review"),
        s.jsx("input",{type:"number",min:1,step:1,value:l.qa_business_days??"",onChange:y=>c("qa_business_days",y.target.value?Number(y.target.value):null),className:De}),
      ]}),
      s.jsxs("div",{children:[
        lbl("QA Due","QA review deadline"),
        s.jsx("input",{type:"date",value:l.qa_end_date??"",onChange:y=>c("qa_end_date",y.target.value||null),className:De}),
      ]}),
      s.jsxs("div",{children:[
        lbl("QA Hours","Hours for QA review"),
        s.jsx("input",{type:"number",min:0,step:.5,value:l.qa_hours??"",onChange:y=>c("qa_hours",y.target.value?Number(y.target.value):null),className:De}),
      ]}),
    ]}),
    s.jsxs("div",{className:"flex flex-col gap-1.5 mt-3",children:[
      s.jsxs("label",{className:"flex items-center gap-2 text-[10px] text-gray-600 dark:text-gray-400 cursor-pointer",children:[
        s.jsx("input",{type:"checkbox",checked:!!l.workshop_sequential,onChange:y=>c("workshop_sequential",y.target.checked),className:"w-3.5 h-3.5 rounded border-gray-300"}),
        "Workshop \\u2192 Deliverable sequential",
        tip("Consultant work starts next business day after workshop"),
      ]}),
      s.jsxs("label",{className:"flex items-center gap-2 text-[10px] text-gray-600 dark:text-gray-400 cursor-pointer",children:[
        s.jsx("input",{type:"checkbox",checked:!!l.qa_sequential,onChange:y=>c("qa_sequential",y.target.checked),className:"w-3.5 h-3.5 rounded border-gray-300"}),
        "Consultant \\u2192 QA sequential",
        tip("QA starts next business day after consultant due date"),
      ]}),
    ]}),
    autoErr&&s.jsx("div",{className:"mt-2 text-[10px] text-red-500 bg-red-50 dark:bg-red-900/20 rounded px-2 py-1",children:autoErr}),
    s.jsxs("div",{className:"flex items-center gap-2 mt-3",children:[
      s.jsxs("button",{onClick:doAutoGen,disabled:i||!canAuto,onMouseDown:y=>y.stopPropagation(),title:!canAuto?"Fill Consultant Days, QA Days, Hours, check both boxes, set Start/Due Date":"Auto-generate all dates",className:"flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md disabled:opacity-40 "+(canAuto?"bg-purple-600 hover:bg-purple-700 text-white":"bg-gray-200 text-gray-400"),children:["\\u2728 Auto Dates"]}),
      s.jsxs("button",{onClick:x,disabled:i||!l.name,onMouseDown:y=>y.stopPropagation(),className:"flex items-center gap-1 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white text-xs font-medium rounded-md",children:[s.jsx(lt,{size:12})," ",i?"Saving\\u2026":"Save"]}),
      s.jsxs("button",{onClick:a,onMouseDown:y=>y.stopPropagation(),className:"flex items-center gap-1 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md",children:[s.jsx(ot,{size:12})," Cancel"]}),
    ]}),
  ]});
}
`;

c = c.slice(0, wbStart) + newWb + c.slice(wbEnd);
writeFileSync('/home/coder/teamscope_v3.js', c);

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['Wb function',         v.includes('function Wb(')],
  ['mo function',         v.includes('function mo(')],
  ['Hb function',         v.includes('function Hb(')],
  ['Consultant Days',     v.includes('"Consultant Days","Business days for consultant"')],
  ['QA Days',             v.includes('"QA Days","Business days for QA review"')],
  ['Consultant Due',      v.includes('"Consultant Due","Consultant draft deadline"')],
  ['QA Due',              v.includes('"QA Due","QA review deadline"')],
  ['workshop checkbox',   v.includes('"workshop_sequential",y.target.checked')],
  ['qa checkbox',         v.includes('"qa_sequential",y.target.checked')],
  ['Auto Dates button',   v.includes('Auto Dates')],
  ['doAutoGen',           v.includes('async function doAutoGen()')],
  ['tip helper',          v.includes('const tip=(text)')],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
