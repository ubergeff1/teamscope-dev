import { readFileSync, writeFileSync } from 'fs';

const src = readFileSync('/home/coder/teamscope_v2.js', 'utf8');

// ── Locate the component boundaries ────────────────────────────────────────
const compStart = src.indexOf('function TsCellSheet(');
const compEnd   = src.indexOf('\nfunction Rb()');
if (compStart < 0 || compEnd < 0) {
  console.error('ERROR: could not locate TsCellSheet boundaries');
  process.exit(1);
}

// ── New TsCellSheet (v3) ────────────────────────────────────────────────────
const newComp = `function TsCellSheet({cell:e,onClose:t}){
  const[r,setR]=b.useState(null),[loading,setL]=b.useState(!0);
  const[cons,setCons]=b.useState([]);
  const[selDeliv,setSel]=b.useState(null);
  const[editForm,setEdit]=b.useState({});
  const[saving,setSaving]=b.useState(!1);
  const[saveErr,setSaveErr]=b.useState(null);

  b.useEffect(()=>{
    if(!e)return;
    setL(!0);setR(null);setSel(null);setSaveErr(null);
    N1(e.cId,Vr(e.wkFrom),Vr(e.wkTo))
      .then(d=>{setR(d);})
      .catch(()=>setR(null))
      .finally(()=>setL(!1));
    _l().then(setCons).catch(()=>{});
  },[e]);

  if(!e)return null;

  const allDelivs=r?r.projects.flatMap(p=>p.deliverables.map(d=>({...d,project_id:p.project_id,project_name:p.project_name,project_color:p.project_color}))):[];
  const thisWeek=allDelivs.filter(d=>d.weeks.some(w=>w.week_start===e.wk));

  const startEdit=(d)=>{
    H.get('/projects/'+d.project_id+'/deliverables')
      .then(res=>{
        const full=res.data.find(x=>x.id===d.deliverable_id)||{};
        setEdit({...full});setSel(d);setSaveErr(null);
      })
      .catch(()=>{setEdit({deliverable_name:d.deliverable_name});setSel(d);});
  };

  const saveEdit=()=>{
    if(!selDeliv||!editForm.id)return;
    setSaving(!0);setSaveErr(null);
    const payload={
      name:editForm.name,
      status:editForm.status,
      start_date:editForm.start_date||null,
      business_days:editForm.business_days?parseInt(editForm.business_days):null,
      flat_hours:editForm.flat_hours?parseFloat(editForm.flat_hours):null,
      qa_hours:editForm.qa_hours?parseFloat(editForm.qa_hours):null,
      control_count:editForm.control_count?parseInt(editForm.control_count):null,
      hours_per_control:editForm.hours_per_control?parseFloat(editForm.hours_per_control):null,
      consultant_id:editForm.consultant_id?parseInt(editForm.consultant_id):null,
      qa_consultant_id:editForm.qa_consultant_id?parseInt(editForm.qa_consultant_id):null,
    };
    H.patch('/projects/'+selDeliv.project_id+'/deliverables/'+editForm.id,payload)
      .then(()=>{setSel(null);setL(!0);setR(null);N1(e.cId,Vr(e.wkFrom),Vr(e.wkTo)).then(d=>{setR(d);}).catch(()=>setR(null)).finally(()=>setL(!1));})
      .catch(er=>{setSaveErr(er?.response?.data?.detail||'Save failed');})
      .finally(()=>setSaving(!1));
  };

  const inp=(label,key,type,opts)=>s.jsxs('div',{className:'flex flex-col gap-1',children:[
    s.jsx('label',{className:'text-xs font-medium text-gray-500 dark:text-gray-400',children:label}),
    opts
      ?s.jsx('select',{className:'text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200',value:editForm[key]??'',onChange:ev=>setEdit(f=>({...f,[key]:ev.target.value})),children:opts.map(o=>s.jsx('option',{value:o.v,children:o.l},o.v))})
      :s.jsx('input',{type:type||'text',className:'text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200',value:editForm[key]??'',onChange:ev=>setEdit(f=>({...f,[key]:ev.target.value}))}),
  ]});

  const statusOpts=[{v:'not_started',l:'Not Started'},{v:'in_progress',l:'In Progress'},{v:'in_qa',l:'In QA'},{v:'delivered',l:'Delivered'}];
  const consOpts=[{v:'',l:'— None —'},...cons.map(c=>({v:String(c.id),l:c.name}))];
  const isCtrl=editForm.deliverable_type==='control_family';

  const listView=s.jsx('div',{className:'space-y-2',children:thisWeek.map((d,i)=>{
    const wh=d.weeks.find(w=>w.week_start===e.wk);
    const tot=d.weeks.reduce((acc,w)=>acc+w.hours,0);
    const isQa=d.phase_type==='qa';
    const col=isQa?'#94a3b8':d.project_color;
    return s.jsxs('div',{className:'flex items-stretch gap-3 px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors',onClick:()=>startEdit(d),children:[
      s.jsx('div',{className:'w-1 rounded-full shrink-0',style:{backgroundColor:col}}),
      s.jsxs('div',{className:'flex-1 min-w-0',children:[
        s.jsx('div',{className:'text-sm font-medium text-gray-800 dark:text-gray-200',children:d.deliverable_name}),
        s.jsxs('div',{className:'flex items-center gap-2 mt-0.5 flex-wrap',children:[
          s.jsx('span',{className:'text-xs font-medium',style:{color:col},children:isQa?'QA Review':'Consultant Draft'}),
          s.jsx('span',{className:'text-xs text-gray-400',children:'·'}),
          s.jsx('span',{className:'text-xs text-gray-400',children:d.project_name}),
        ]}),
      ]}),
      s.jsxs('div',{className:'text-right shrink-0 flex flex-col items-end justify-between',children:[
        s.jsxs('div',{className:'text-base font-bold tabular-nums',style:{color:col},children:[wh?wh.hours.toFixed(1):0,'h']}),
        s.jsxs('div',{className:'text-xs text-gray-400',children:[tot.toFixed(1),'h total']}),
        s.jsxs('div',{className:'flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 mt-1',children:[s.jsx(On,{size:11}),' Edit']}),
      ]}),
    ]},i);
  })});

  const editView=selDeliv&&s.jsxs('div',{className:'flex flex-col gap-4',children:[
    s.jsxs('div',{className:'flex items-center gap-2 mb-1',children:[
      s.jsx('button',{onClick:()=>setSel(null),className:'text-xs px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400',children:'← Back'}),
      s.jsxs('div',{className:'flex-1 min-w-0',children:[
        s.jsx('div',{className:'text-sm font-semibold text-gray-900 dark:text-gray-100',children:selDeliv.deliverable_name}),
        s.jsx('div',{className:'text-xs text-gray-400',children:selDeliv.project_name}),
      ]}),
    ]}),
    s.jsxs('div',{className:'grid grid-cols-2 gap-3',children:[
      s.jsx('div',{className:'col-span-2',children:inp('Name','name')}),
      inp('Status','status','text',statusOpts),
      inp('Start Date','start_date','date'),
      inp('Business Days','business_days','number'),
      inp('QA Hours','qa_hours','number'),
      isCtrl?s.jsxs(b.Fragment,{children:[inp('Control Count','control_count','number'),inp('Hrs / Control','hours_per_control','number')]})
            :inp('Flat Hours','flat_hours','number'),
      inp('Consultant','consultant_id','text',consOpts),
      inp('QA Consultant','qa_consultant_id','text',consOpts),
    ]}),
    saveErr&&s.jsx('div',{className:'text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded px-3 py-2',children:saveErr}),
    s.jsxs('div',{className:'flex gap-2 pt-1',children:[
      s.jsx('button',{onClick:saveEdit,disabled:saving,className:'flex-1 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors',children:saving?'Saving…':'Save Changes'}),
      s.jsx('button',{onClick:()=>setSel(null),className:'px-4 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors',children:'Cancel'}),
    ]}),
  ]});

  return s.jsxs('div',{className:'fixed inset-0 z-50 flex flex-col justify-end',style:{pointerEvents:'none'},children:[
    s.jsx('div',{className:'absolute inset-0 bg-black/30',style:{pointerEvents:'auto'},onClick:t}),
    s.jsxs('div',{className:'relative bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 shadow-2xl rounded-t-2xl flex flex-col',style:{maxHeight:'70vh',pointerEvents:'auto'},children:[
      s.jsx('div',{className:'w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-600 mx-auto mt-3 mb-2 shrink-0'}),
      s.jsxs('div',{className:'flex items-center gap-2 px-5 pb-3 shrink-0 flex-wrap border-b border-gray-100 dark:border-gray-800',children:[
        s.jsx('span',{className:'w-3 h-3 rounded-full shrink-0',style:{backgroundColor:e.cColor}}),
        s.jsx('span',{className:'font-semibold text-sm text-gray-900 dark:text-gray-100',children:e.cName}),
        s.jsx('span',{className:'text-gray-300 dark:text-gray-600',children:'·'}),
        s.jsx('span',{className:'text-sm text-gray-500 dark:text-gray-400',children:'Week of '+e.wkLabel}),
        s.jsx('button',{onClick:t,className:'ml-auto p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400',children:s.jsx(ot,{size:15})}),
      ]}),
      s.jsx('div',{className:'overflow-auto flex-1 px-5 py-4',children:
        loading
          ?s.jsx('div',{className:'flex items-center justify-center h-20 text-sm text-gray-400',children:'Loading…'})
          :selDeliv
            ?editView
            :thisWeek.length===0
              ?s.jsx('div',{className:'flex items-center justify-center h-20 text-sm text-gray-400',children:'No deliverables scheduled this week.'})
              :listView
      }),
    ]}),
  ]});
}
`;

// ── Apply replacement ───────────────────────────────────────────────────────
const before = src.slice(0, compStart);
const after  = src.slice(compEnd);   // starts with "\nfunction Rb()"
const patched = before + newComp + after;

writeFileSync('/home/coder/teamscope_v3.js', patched);

// ── Verify ─────────────────────────────────────────────────────────────────
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['TsCellSheet component present',   v.includes('function TsCellSheet(')],
  ['startEdit function',              v.includes('startEdit')],
  ['saveEdit function',               v.includes('saveEdit')],
  ['full project name (no truncate)', !v.includes('"text-xs text-gray-400 truncate"')],
  ['edit form grid',                  v.includes('grid-cols-2')],
  ['PATCH call',                      v.includes("H.patch('/projects/'")],
  ['Rb still present',                v.includes('function Rb()')],
  ['TsCellSheet count = 1',           (v.match(/function TsCellSheet\(/g)||[]).length === 1],
];

let ok = true;
for (const [name, pass] of checks) {
  console.log((pass ? '✓' : '✗') + ' ' + name);
  if (!pass) ok = false;
}
console.log('\nFile size:', v.length, 'bytes');
if (!ok) process.exit(1);
