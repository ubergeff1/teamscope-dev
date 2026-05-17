/**
 * @file patch_v3.mjs
 *
 * Replaces the TsCellSheet component (the cell-detail bottom sheet) with a
 * fully rewritten "v3" version that adds:
 *   - Inline editing of deliverables (name, status, dates, hours, assignments)
 *   - A two-view layout: list view showing deliverables for the selected week,
 *     and an edit view with a form grid
 *   - PATCH-based save that writes changes back through the API
 *
 * Target component: TsCellSheet (the bottom-sheet drawer shown when a user
 * taps a cell in the resource-planning grid).
 *
 * Search/replace strategy:
 *   1. Locate the TsCellSheet function by searching for its declaration string
 *      ("function TsCellSheet(").
 *   2. Locate the next function boundary ("function Rb()") to know where the
 *      old component ends.
 *   3. Splice the new component source in between the code before TsCellSheet
 *      and the code starting at Rb, preserving everything outside TsCellSheet.
 *   4. Write the patched bundle to a new file (teamscope_v3.js) so the
 *      original is never modified in-place.
 *   5. Run a set of verification checks to confirm the patch applied correctly.
 */

import { readFileSync, writeFileSync } from 'fs';

/** Read the source bundle that will be patched. */
const src = readFileSync('/home/coder/teamscope_v2.js', 'utf8');

// ── Locate the component boundaries ────────────────────────────────────────
// "function TsCellSheet(" is the exact declaration string produced by the
// bundler for this component.  "function Rb()" is the very next top-level
// function in the bundle, so the slice between them is the entire old
// TsCellSheet body.
const compStart = src.indexOf('function TsCellSheet(');
const compEnd   = src.indexOf('\nfunction Rb()');
if (compStart < 0 || compEnd < 0) {
  console.error('ERROR: could not locate TsCellSheet boundaries');
  process.exit(1);
}

// ── New TsCellSheet (v3) ────────────────────────────────────────────────────
// The replacement component accepts {cell, onClose} props and introduces:
//   - r / setR          : the fetched resource-plan data for this consultant + week range
//   - loading / setL    : loading spinner state
//   - cons / setCons    : list of all consultants (for assignment dropdowns)
//   - selDeliv / setSel : the currently-selected deliverable (switches to edit view)
//   - editForm / setEdit: form state for the selected deliverable
//   - saving / setSaving: tracks in-flight save request
//   - saveErr / setSaveErr: API error message to display
const newComp = `function TsCellSheet({cell:e,onClose:t}){
  const[r,setR]=b.useState(null),[loading,setL]=b.useState(!0);
  const[cons,setCons]=b.useState([]);
  const[selDeliv,setSel]=b.useState(null);
  const[editForm,setEdit]=b.useState({});
  const[saving,setSaving]=b.useState(!1);
  const[saveErr,setSaveErr]=b.useState(null);

  /**
   * useEffect: fires whenever the cell prop changes.
   * Fetches resource-plan data (N1) for the consultant/week range,
   * and also fetches the full consultant list (_l) for dropdown options.
   */
  b.useEffect(()=>{
    if(!e)return;
    setL(!0);setR(null);setSel(null);setSaveErr(null);
    N1(e.cId,Vr(e.wkFrom),Vr(e.wkTo))
      .then(d=>{setR(d);})
      .catch(()=>setR(null))
      .finally(()=>setL(!1));
    _l().then(setCons).catch(()=>{});
  },[e]);

  /* If no cell is selected, render nothing. */
  if(!e)return null;

  /**
   * Flatten all deliverables from all projects into a single array,
   * attaching project metadata (id, name, color) to each deliverable
   * so the list view can render project context.
   */
  const allDelivs=r?r.projects.flatMap(p=>p.deliverables.map(d=>({...d,project_id:p.project_id,project_name:p.project_name,project_color:p.project_color}))):[];
  /** Filter to only deliverables that have hours in the selected week. */
  const thisWeek=allDelivs.filter(d=>d.weeks.some(w=>w.week_start===e.wk));

  /**
   * startEdit: fetches the full deliverable record from the API so we have
   * all editable fields, then switches to the edit view.
   * Falls back to a minimal stub if the fetch fails.
   */
  const startEdit=(d)=>{
    H.get('/projects/'+d.project_id+'/deliverables')
      .then(res=>{
        const full=res.data.find(x=>x.id===d.deliverable_id)||{};
        setEdit({...full});setSel(d);setSaveErr(null);
      })
      .catch(()=>{setEdit({deliverable_name:d.deliverable_name});setSel(d);});
  };

  /**
   * saveEdit: sends a PATCH request to update the selected deliverable,
   * then refreshes the resource-plan data so the list view is current.
   * Numeric fields are parsed to their correct types before sending.
   */
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

  /**
   * inp: helper that renders a labeled form field (input or select).
   * @param {string} label - Display label
   * @param {string} key   - Key into editForm state
   * @param {string} type  - HTML input type (text, number, date)
   * @param {Array}  opts  - If provided, renders a <select> instead of <input>
   */
  const inp=(label,key,type,opts)=>s.jsxs('div',{className:'flex flex-col gap-1',children:[
    s.jsx('label',{className:'text-xs font-medium text-gray-500 dark:text-gray-400',children:label}),
    opts
      ?s.jsx('select',{className:'text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200',value:editForm[key]??'',onChange:ev=>setEdit(f=>({...f,[key]:ev.target.value})),children:opts.map(o=>s.jsx('option',{value:o.v,children:o.l},o.v))})
      :s.jsx('input',{type:type||'text',className:'text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200',value:editForm[key]??'',onChange:ev=>setEdit(f=>({...f,[key]:ev.target.value}))}),
  ]});

  /** Dropdown options for the status field. */
  const statusOpts=[{v:'not_started',l:'Not Started'},{v:'in_progress',l:'In Progress'},{v:'in_qa',l:'In QA'},{v:'delivered',l:'Delivered'}];
  /** Dropdown options for consultant assignment (includes a "None" sentinel). */
  const consOpts=[{v:'',l:'— None —'},...cons.map(c=>({v:String(c.id),l:c.name}))];
  /** Control-family deliverables show control_count + hours_per_control instead of flat_hours. */
  const isCtrl=editForm.deliverable_type==='control_family';

  /**
   * listView: renders a card for each deliverable scheduled this week.
   * Each card shows the deliverable name, project name, phase type
   * (QA vs Consultant Draft), hours for this week, and total hours.
   * Clicking a card opens the edit view via startEdit().
   */
  const listView=s.jsx('div',{className:'space-y-2',children:thisWeek.map((d,i)=>{
    const wh=d.weeks.find(w=>w.week_start===e.wk);
    const tot=d.weeks.reduce((acc,w)=>acc+w.hours,0);
    const isQa=d.phase_type==='qa';
    /** QA rows use a neutral slate color; regular rows use the project color. */
    const col=isQa?'#94a3b8':d.project_color;
    return s.jsxs('div',{className:'flex items-stretch gap-3 px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors',onClick:()=>startEdit(d),children:[
      /* Colored left-edge indicator bar */
      s.jsx('div',{className:'w-1 rounded-full shrink-0',style:{backgroundColor:col}}),
      s.jsxs('div',{className:'flex-1 min-w-0',children:[
        s.jsx('div',{className:'text-sm font-medium text-gray-800 dark:text-gray-200',children:d.deliverable_name}),
        s.jsxs('div',{className:'flex items-center gap-2 mt-0.5 flex-wrap',children:[
          /* Phase type label (QA Review / Consultant Draft) */
          s.jsx('span',{className:'text-xs font-medium',style:{color:col},children:isQa?'QA Review':'Consultant Draft'}),
          s.jsx('span',{className:'text-xs text-gray-400',children:'·'}),
          /* Full project name (not truncated - deliberate v3 improvement) */
          s.jsx('span',{className:'text-xs text-gray-400',children:d.project_name}),
        ]}),
      ]}),
      s.jsxs('div',{className:'text-right shrink-0 flex flex-col items-end justify-between',children:[
        /* Hours for this specific week */
        s.jsxs('div',{className:'text-base font-bold tabular-nums',style:{color:col},children:[wh?wh.hours.toFixed(1):0,'h']}),
        /* Total hours across all weeks for this deliverable */
        s.jsxs('div',{className:'text-xs text-gray-400',children:[tot.toFixed(1),'h total']}),
        /* Edit affordance using the pencil icon (On) */
        s.jsxs('div',{className:'flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 mt-1',children:[s.jsx(On,{size:11}),' Edit']}),
      ]}),
    ]},i);
  })});

  /**
   * editView: rendered when a deliverable is selected for editing.
   * Shows a back button, the deliverable/project name, and a 2-column
   * grid of form fields.  For control_family types the grid shows
   * control_count + hours_per_control; otherwise it shows flat_hours.
   */
  const editView=selDeliv&&s.jsxs('div',{className:'flex flex-col gap-4',children:[
    s.jsxs('div',{className:'flex items-center gap-2 mb-1',children:[
      s.jsx('button',{onClick:()=>setSel(null),className:'text-xs px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400',children:'← Back'}),
      s.jsxs('div',{className:'flex-1 min-w-0',children:[
        s.jsx('div',{className:'text-sm font-semibold text-gray-900 dark:text-gray-100',children:selDeliv.deliverable_name}),
        s.jsx('div',{className:'text-xs text-gray-400',children:selDeliv.project_name}),
      ]}),
    ]}),
    /* Two-column form grid for deliverable fields */
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
    /* Error message banner (only shown when saveErr is set) */
    saveErr&&s.jsx('div',{className:'text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded px-3 py-2',children:saveErr}),
    /* Action buttons: Save and Cancel */
    s.jsxs('div',{className:'flex gap-2 pt-1',children:[
      s.jsx('button',{onClick:saveEdit,disabled:saving,className:'flex-1 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors',children:saving?'Saving…':'Save Changes'}),
      s.jsx('button',{onClick:()=>setSel(null),className:'px-4 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors',children:'Cancel'}),
    ]}),
  ]});

  /**
   * Main render: a fixed-position bottom sheet with:
   *   - A semi-transparent backdrop that closes the sheet on click
   *   - A rounded top panel with drag handle, consultant header, and
   *     scrollable content area that switches between loading / list / edit / empty states
   */
  return s.jsxs('div',{className:'fixed inset-0 z-50 flex flex-col justify-end',style:{pointerEvents:'none'},children:[
    /* Backdrop overlay - clicking closes the sheet via onClose (t) */
    s.jsx('div',{className:'absolute inset-0 bg-black/30',style:{pointerEvents:'auto'},onClick:t}),
    s.jsxs('div',{className:'relative bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 shadow-2xl rounded-t-2xl flex flex-col',style:{maxHeight:'70vh',pointerEvents:'auto'},children:[
      /* Drag handle indicator */
      s.jsx('div',{className:'w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-600 mx-auto mt-3 mb-2 shrink-0'}),
      /* Header row: consultant color dot, name, week label, close button */
      s.jsxs('div',{className:'flex items-center gap-2 px-5 pb-3 shrink-0 flex-wrap border-b border-gray-100 dark:border-gray-800',children:[
        s.jsx('span',{className:'w-3 h-3 rounded-full shrink-0',style:{backgroundColor:e.cColor}}),
        s.jsx('span',{className:'font-semibold text-sm text-gray-900 dark:text-gray-100',children:e.cName}),
        s.jsx('span',{className:'text-gray-300 dark:text-gray-600',children:'·'}),
        s.jsx('span',{className:'text-sm text-gray-500 dark:text-gray-400',children:'Week of '+e.wkLabel}),
        s.jsx('button',{onClick:t,className:'ml-auto p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400',children:s.jsx(ot,{size:15})}),
      ]}),
      /* Scrollable content area - switches between four states */
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
// Slice the original source into "everything before TsCellSheet" and
// "everything from Rb() onward", then sandwich the new component between them.
const before = src.slice(0, compStart);
const after  = src.slice(compEnd);   // starts with "\nfunction Rb()"
const patched = before + newComp + after;

writeFileSync('/home/coder/teamscope_v3.js', patched);

// ── Verify ─────────────────────────────────────────────────────────────────
// Read back the written file and run a series of sanity checks to ensure the
// patch was applied correctly and no surrounding code was damaged.
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['TsCellSheet component present',   v.includes('function TsCellSheet(')],
  ['startEdit function',              v.includes('startEdit')],
  ['saveEdit function',               v.includes('saveEdit')],
  /* v3 removes the truncate class that was present in v2 - verify it's gone */
  ['full project name (no truncate)', !v.includes('"text-xs text-gray-400 truncate"')],
  ['edit form grid',                  v.includes('grid-cols-2')],
  /* Confirm the PATCH endpoint is wired up for saving edits */
  ['PATCH call',                      v.includes("H.patch('/projects/'")],
  /* Rb is the next function after TsCellSheet - must still exist */
  ['Rb still present',                v.includes('function Rb()')],
  /* Ensure we didn't accidentally duplicate TsCellSheet */
  ['TsCellSheet count = 1',           (v.match(/function TsCellSheet\(/g)||[]).length === 1],
];

let ok = true;
for (const [name, pass] of checks) {
  console.log((pass ? '✓' : '✗') + ' ' + name);
  if (!pass) ok = false;
}
console.log('\nFile size:', v.length, 'bytes');
if (!ok) process.exit(1);
