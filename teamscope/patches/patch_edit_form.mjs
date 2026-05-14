import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// 1. Update startEdit to extract phase dates into editForm
const oldStartEdit = `setEdit({...full,flat_hours:ch});setSel(d);setSaveErr(null);`;
const newStartEdit = `const dp=(full.phases||[]).find(p=>p.phase_type==='draft');const qp=(full.phases||[]).find(p=>p.phase_type==='qa');setEdit({...full,flat_hours:ch,draft_start_date:dp?dp.start_date:null,draft_end_date:dp?dp.end_date:null,qa_start_date:qp?qp.start_date:null,qa_end_date:qp?qp.end_date:null});setSel(d);setSaveErr(null);`;
if (!c.includes(oldStartEdit)) { console.error('FAIL: startEdit'); process.exit(1); }
c = c.replace(oldStartEdit, newStartEdit);
console.log('✓ startEdit updated');

// 2. Update saveEdit payload to include new fields
const oldPayload = `const payload={
      name:editForm.name,
      status:editForm.status,
      start_date:editForm.start_date||null,
      end_date:editForm.end_date||null,
      business_days:editForm.business_days?parseInt(editForm.business_days):null,
      flat_hours:editForm.flat_hours!==''&&editForm.flat_hours!=null?parseFloat(editForm.flat_hours):null,
      qa_hours:editForm.qa_hours!==''&&editForm.qa_hours!=null?parseFloat(editForm.qa_hours):null,
      consultant_id:editForm.consultant_id?parseInt(editForm.consultant_id):null,
      qa_consultant_id:editForm.qa_consultant_id?parseInt(editForm.qa_consultant_id):null,
    };`;

const newPayload = `const payload={
      name:editForm.name,
      status:editForm.status,
      start_date:editForm.start_date||null,
      end_date:editForm.end_date||null,
      business_days:editForm.business_days?parseInt(editForm.business_days):null,
      qa_business_days:editForm.qa_business_days?parseInt(editForm.qa_business_days):null,
      workshop_sequential:!!editForm.workshop_sequential,
      qa_sequential:!!editForm.qa_sequential,
      flat_hours:editForm.flat_hours!==''&&editForm.flat_hours!=null?parseFloat(editForm.flat_hours):null,
      qa_hours:editForm.qa_hours!==''&&editForm.qa_hours!=null?parseFloat(editForm.qa_hours):null,
      consultant_id:editForm.consultant_id?parseInt(editForm.consultant_id):null,
      qa_consultant_id:editForm.qa_consultant_id?parseInt(editForm.qa_consultant_id):null,
      draft_start_date:editForm.draft_start_date||null,
      draft_end_date:editForm.draft_end_date||null,
      qa_start_date:editForm.qa_start_date||null,
      qa_end_date:editForm.qa_end_date||null,
    };`;

if (!c.includes(oldPayload)) { console.error('FAIL: payload'); process.exit(1); }
c = c.replace(oldPayload, newPayload);
console.log('✓ payload updated');

// 3. Add auto-generate handler after saveEdit function
const saveEditEnd = `.finally(()=>setSaving(!1));
  };

  const inp=`;
if (!c.includes(saveEditEnd)) { console.error('FAIL: saveEditEnd'); process.exit(1); }

const autoGenHandler = `.finally(()=>setSaving(!1));
  };

  const autoGen=()=>{
    if(!selDeliv||!editForm.id)return;
    setSaving(!0);setSaveErr(null);
    const pre={
      business_days:editForm.business_days?parseInt(editForm.business_days):null,
      qa_business_days:editForm.qa_business_days?parseInt(editForm.qa_business_days):null,
      flat_hours:editForm.flat_hours!==''&&editForm.flat_hours!=null?parseFloat(editForm.flat_hours):null,
      qa_hours:editForm.qa_hours!==''&&editForm.qa_hours!=null?parseFloat(editForm.qa_hours):null,
      workshop_sequential:!!editForm.workshop_sequential,
      qa_sequential:!!editForm.qa_sequential,
      start_date:editForm.start_date||null,
      end_date:editForm.end_date||null,
    };
    H.patch('/projects/'+selDeliv.project_id+'/deliverables/'+editForm.id,pre)
      .then(()=>H.post('/projects/'+selDeliv.project_id+'/deliverables/'+editForm.id+'/auto-dates'))
      .then(res=>{
        const full=res.data;
        const dp2=(full.phases||[]).find(p=>p.phase_type==='draft');
        const qp2=(full.phases||[]).find(p=>p.phase_type==='qa');
        setEdit(f=>({...f,...full,draft_start_date:dp2?dp2.start_date:null,draft_end_date:dp2?dp2.end_date:null,qa_start_date:qp2?qp2.start_date:null,qa_end_date:qp2?qp2.end_date:null}));
        if(onSaved)onSaved();
      })
      .catch(er=>{setSaveErr(er?.response?.data?.detail||'Auto-generate failed');})
      .finally(()=>setSaving(!1));
  };
  const canAutoGen=editForm.business_days&&editForm.qa_business_days&&editForm.flat_hours&&editForm.qa_hours&&editForm.workshop_sequential&&editForm.qa_sequential&&(editForm.start_date||editForm.end_date);

  const inp=`;

c = c.replace(saveEditEnd, autoGenHandler);
console.log('✓ autoGen handler added');

// 4. Replace the inp helper to support info tooltips
const oldInp = `const inp=(label,key,type,opts)=>s.jsxs('div',{className:'flex flex-col gap-1',children:[
    s.jsx('label',{className:'text-xs font-medium text-gray-500 dark:text-gray-400',children:label}),`;

const newInp = `const tips={
    'Name':'The deliverable name as it appears in reports and the grid.',
    'Status':'Current status: Not Started, In Progress, In QA, or Delivered.',
    'Start Date':'When work on this deliverable begins. Used for forward date generation.',
    'Due Date':'Overall due date for the entire deliverable (including QA).',
    'Consultant Days':'Number of business days for the consultant to complete their work.',
    'QA Days':'Number of business days for QA review after consultant work.',
    'Consultant Due':'Date by which the consultant must finish their draft.',
    'QA Due':'Date by which QA review must be completed.',
    'Consultant Hours':'Total hours budgeted for consultant work.',
    'QA Hours':'Total hours budgeted for QA/review work.',
    'Consultant':'The consultant assigned to do the primary work.',
    'QA Consultant':'The person assigned to review/QA the deliverable.',
  };
  const inp=(label,key,type,opts)=>s.jsxs('div',{className:'flex flex-col gap-1',children:[
    s.jsxs('label',{className:'text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center gap-1',children:[label,tips[label]&&s.jsx('span',{title:tips[label],className:'inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-[9px] font-bold cursor-help',children:'i'})]}),`;

if (!c.includes(oldInp)) { console.error('FAIL: inp'); process.exit(1); }
c = c.replace(oldInp, newInp);
console.log('✓ inp helper with info icons');

// 5. Replace the editView grid with new fields
const oldEditGrid = `s.jsxs('div',{style:{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:'12px'},children:[
      s.jsx('div',{style:{gridColumn:'1/-1'},children:inp('Name','name')}),
      inp('Status','status','text',statusOpts),
      inp('Start Date','start_date','date'),
      inp('Business Days','business_days','number'),
      inp('Due Date','end_date','date'),
      inp('Consultant Hours','flat_hours','number'),
      inp('QA Hours','qa_hours','number'),
      inp('Consultant','consultant_id','text',consOpts),
      inp('QA Consultant','qa_consultant_id','text',consOpts),
    ]}),`;

const newEditGrid = `s.jsxs('div',{style:{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:'12px'},children:[
      s.jsx('div',{style:{gridColumn:'1/-1'},children:inp('Name','name')}),
      inp('Status','status','text',statusOpts),
      inp('Start Date','start_date','date'),
      inp('Due Date','end_date','date'),
      inp('Consultant Days','business_days','number'),
      inp('Consultant Due','draft_end_date','date'),
      inp('Consultant Hours','flat_hours','number'),
      inp('QA Days','qa_business_days','number'),
      inp('QA Due','qa_end_date','date'),
      inp('QA Hours','qa_hours','number'),
      inp('Consultant','consultant_id','text',consOpts),
      inp('QA Consultant','qa_consultant_id','text',consOpts),
      s.jsx('div',{}),
    ]}),
    s.jsxs('div',{className:'flex flex-col gap-2 mt-1',children:[
      s.jsxs('label',{className:'flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 cursor-pointer',children:[
        s.jsx('input',{type:'checkbox',checked:!!editForm.workshop_sequential,onChange:ev=>setEdit(f=>({...f,workshop_sequential:ev.target.checked})),className:'w-3.5 h-3.5 rounded border-gray-300'}),
        'Workshop \\u2192 Deliverable are sequential',
        s.jsx('span',{title:'When checked, consultant work starts the business day after the linked workshop date.',className:'inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 text-[9px] font-bold cursor-help',children:'i'}),
      ]}),
      s.jsxs('label',{className:'flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 cursor-pointer',children:[
        s.jsx('input',{type:'checkbox',checked:!!editForm.qa_sequential,onChange:ev=>setEdit(f=>({...f,qa_sequential:ev.target.checked})),className:'w-3.5 h-3.5 rounded border-gray-300'}),
        'Consultant \\u2192 QA are sequential',
        s.jsx('span',{title:'When checked, QA starts the business day after the consultant due date.',className:'inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 text-[9px] font-bold cursor-help',children:'i'}),
      ]}),
    ]}),`;

if (!c.includes(oldEditGrid)) { console.error('FAIL: editGrid'); process.exit(1); }
c = c.replace(oldEditGrid, newEditGrid);
console.log('✓ editView grid replaced');

// 6. Update the footer buttons to add Auto-generate
const oldFooterButtons = `s.jsxs('div',{className:'flex gap-2',children:[
          s.jsx('button',{onClick:saveEdit,disabled:saving,style:{backgroundColor:'#2563eb',color:'#fff',border:'none',cursor:saving?'not-allowed':'pointer',opacity:saving?0.6:1},className:'flex-1 py-2 rounded-lg text-sm font-medium',children:saving?'Saving\u2026':'Save Changes'}),
          s.jsx('button',{onClick:()=>setSel(null),style:{cursor:'pointer'},className:'px-4 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800',children:'Cancel'}),
        ]})`;

const newFooterButtons = `s.jsxs('div',{className:'flex gap-2',children:[
          s.jsx('button',{onClick:autoGen,disabled:saving||!canAutoGen,title:!canAutoGen?'Fill in Consultant Days, QA Days, Consultant Hours, QA Hours, check both sequential boxes, and set Start or Due Date':'Auto-generate all dates',style:{backgroundColor:canAutoGen?'#7c3aed':'#d1d5db',color:canAutoGen?'#fff':'#9ca3af',border:'none',cursor:saving||!canAutoGen?'not-allowed':'pointer',opacity:saving?0.6:1},className:'px-3 py-2 rounded-lg text-sm font-medium',children:saving?'Working\u2026':'\u2728 Auto Dates'}),
          s.jsx('button',{onClick:saveEdit,disabled:saving,style:{backgroundColor:'#2563eb',color:'#fff',border:'none',cursor:saving?'not-allowed':'pointer',opacity:saving?0.6:1},className:'flex-1 py-2 rounded-lg text-sm font-medium',children:saving?'Saving\u2026':'Save Changes'}),
          s.jsx('button',{onClick:()=>setSel(null),style:{cursor:'pointer'},className:'px-4 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800',children:'Cancel'}),
        ]})`;

if (!c.includes(oldFooterButtons)) { console.error('FAIL: footer'); process.exit(1); }
c = c.replace(oldFooterButtons, newFooterButtons);
console.log('✓ footer buttons updated');

writeFileSync('/home/coder/teamscope_v3.js', c);

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['phase extraction in startEdit', v.includes("phase_type==='draft'")],
  ['qa_business_days in payload',   v.includes('qa_business_days:editForm.qa_business_days')],
  ['workshop_sequential payload',   v.includes('workshop_sequential:!!editForm.workshop_sequential')],
  ['autoGen handler',               v.includes('const autoGen=()=>{')],
  ['canAutoGen check',              v.includes('const canAutoGen=')],
  ['info tips object',              v.includes("const tips={")],
  ['info icon i',                   v.includes("children:'i'")],
  ['Consultant Days field',         v.includes("inp('Consultant Days','business_days'")],
  ['QA Days field',                 v.includes("inp('QA Days','qa_business_days'")],
  ['Consultant Due field',          v.includes("inp('Consultant Due','draft_end_date'")],
  ['QA Due field',                  v.includes("inp('QA Due','qa_end_date'")],
  ['workshop sequential checkbox',  v.includes('workshop_sequential:ev.target.checked')],
  ['qa sequential checkbox',        v.includes('qa_sequential:ev.target.checked')],
  ['Auto Dates button',             v.includes('Auto Dates')],
  ['auto-dates API call',           v.includes("'/auto-dates'")],
  ['TsCellSheet count=1',           (v.match(/function TsCellSheet\(/g)||[]).length===1],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
