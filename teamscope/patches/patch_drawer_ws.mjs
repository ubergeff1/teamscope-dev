/**
 * @file patch_drawer_ws.mjs
 *
 * Enhances the TsCellSheet bottom-sheet drawer (previously patched by
 * patch_v3.mjs) with workshop awareness:
 *   - Adds an `onSaved` callback prop so the parent grid can refresh after edits
 *   - Fetches workshops for the selected consultant/week and displays them
 *     as purple-tinted cards above the deliverable list
 *   - Replaces the 2-column edit grid with a 3-column layout and simplifies
 *     the hours fields (always shows flat_hours, removes control_count split)
 *   - Moves the Save/Cancel buttons into a sticky footer bar
 *   - Uses a combined "isEmpty" check that considers both deliverables and workshops
 *
 * Target component: TsCellSheet (the cell-detail bottom sheet in the
 * resource-planning grid).
 *
 * Search/replace strategy:
 *   1. Reads the previously-patched teamscope_v3.js.
 *   2. Locates TsCellSheet by its declaration string and the following Rb()
 *      function boundary (same boundary markers as patch_v3.mjs).
 *   3. Replaces the entire TsCellSheet body with the new version.
 *   4. Writes the result back to teamscope_v3.js (in-place update).
 *   5. Runs verification checks specific to the workshop-aware features.
 */

import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ── Locate TsCellSheet boundaries ──────────────────────────────────────────
// Same boundary markers used by patch_v3.mjs.  The `start` parameter in
// indexOf ensures we search for Rb() only AFTER TsCellSheet's declaration.
const start = c.indexOf('function TsCellSheet(');
const end   = c.indexOf('\nfunction Rb()', start);
if (start < 0 || end < 0) { console.error('Cannot locate TsCellSheet'); process.exit(1); }

/**
 * New TsCellSheet component.  Key differences from the v3 version:
 *
 * Props:
 *   - cell (e)      : the selected grid cell data
 *   - onClose (t)   : callback to close the drawer
 *   - onSaved       : NEW - callback fired after a successful save so the
 *                      parent grid can refresh its data
 *
 * New state:
 *   - wsThisWeek / setWsThisWeek : array of workshop objects that fall in
 *     the selected week for the selected consultant
 *
 * Workshop fetching (in useEffect):
 *   - Calls Am("active") to get all active projects
 *   - For each project, calls hd(pr.id) to get workshops
 *   - Filters workshops by: (a) having a workshop_date, (b) the date falling
 *     in the selected week (using Vr/Nd date helpers), (c) the consultant
 *     being assigned to the workshop
 *
 * Edit form changes:
 *   - flat_hours is pre-computed for control_family types (count * hrs_per_control)
 *   - Error handling on startEdit shows a warning message
 *   - Save/Cancel buttons moved to a sticky footer outside the scroll area
 *   - Grid changed from 2-column to 3-column layout
 */
const newComp = `function TsCellSheet({cell:e,onClose:t,onSaved:onSaved}){
  const[r,setR]=b.useState(null),[loading,setL]=b.useState(!0);
  const[cons,setCons]=b.useState([]);
  const[selDeliv,setSel]=b.useState(null);
  const[editForm,setEdit]=b.useState({});
  const[saving,setSaving]=b.useState(!1);
  const[saveErr,setSaveErr]=b.useState(null);
  /* NEW: tracks workshops that fall in the selected week for this consultant */
  const[wsThisWeek,setWsThisWeek]=b.useState([]);

  b.useEffect(()=>{
    if(!e)return;
    setL(!0);setR(null);setSel(null);setSaveErr(null);setWsThisWeek([]);
    /* Fetch resource-plan data for the consultant + week range */
    N1(e.cId,Vr(e.wkFrom),Vr(e.wkTo))
      .then(d=>{setR(d);})
      .catch(()=>setR(null))
      .finally(()=>setL(!1));
    /* Fetch consultant list for assignment dropdowns */
    _l().then(setCons).catch(()=>{});
    /**
     * Workshop fetch: iterate over all active projects, fetch workshops
     * for each, then filter to this consultant + this week.
     * Am("active") -> array of projects
     * hd(pr.id)    -> array of workshops for a project
     * Vr()         -> formats a date to a week-start string (YYYY-MM-DD)
     * Nd()         -> returns the Monday of the week containing the given date
     */
    Am("active").then(async ps=>{
      const wsList=[];
      await Promise.all(ps.map(async pr=>{
        try{
          const ws=await hd(pr.id);
          for(const w of ws){
            if(!w.workshop_date)continue;
            /* Convert the workshop date to its week-start for comparison */
            const wk=Vr(Nd(new Date(w.workshop_date+"T12:00:00")));
            if(wk!==e.wk)continue;
            /* Only include if this consultant is assigned to the workshop */
            if(!w.consultants.some(cc=>cc.id===e.cId))continue;
            wsList.push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed",workshop_date:w.workshop_date,status:w.status});
          }
        }catch(ex){}
      }));
      setWsThisWeek(wsList);
    }).catch(()=>{});
  },[e]);

  if(!e)return null;

  /* Flatten deliverables from all projects, attaching project metadata */
  const allDelivs=r?r.projects.flatMap(p=>p.deliverables.map(d=>({...d,project_id:p.project_id,project_name:p.project_name,project_color:p.project_color}))):[];
  /* Filter to deliverables with hours in the selected week */
  const thisWeek=allDelivs.filter(d=>d.weeks.some(w=>w.week_start===e.wk));

  /**
   * startEdit: fetches the full deliverable record from the API.
   * NEW: pre-computes flat_hours for control_family types by multiplying
   * control_count * hours_per_control, so the edit form always shows a
   * single "Consultant Hours" field.
   */
  const startEdit=(d)=>{
    H.get('/projects/'+d.project_id+'/deliverables')
      .then(res=>{
        const full=res.data.find(x=>x.id===d.deliverable_id)||{};
        /* Compute consolidated hours: use flat_hours if present, else derive from controls */
        const ch=full.flat_hours!=null?full.flat_hours:(full.control_count&&full.hours_per_control?parseFloat(full.control_count)*parseFloat(full.hours_per_control):null);
        setEdit({...full,flat_hours:ch});setSel(d);setSaveErr(null);
      })
      .catch(err=>{console.error('[TsCellSheet] startEdit fetch failed',err);setEdit({deliverable_name:d.deliverable_name});setSel(d);setSaveErr('Could not load deliverable details \u2014 changes may not save');});
  };

  /**
   * saveEdit: sends PATCH with updated deliverable fields.
   * NEW: includes debug logging, better error messages for missing data,
   * and calls onSaved() callback on success so the parent grid refreshes.
   */
  const saveEdit=()=>{
    console.log('[TsCellSheet] saveEdit called, selDeliv=',selDeliv,'editForm.id=',editForm.id,'editForm=',editForm);
    if(!selDeliv){setSaveErr('Error: no deliverable selected');return;}
    if(!editForm.id){setSaveErr('Error: deliverable id missing (id='+editForm.id+')');return;}
    setSaving(!0);setSaveErr(null);
    const payload={
      name:editForm.name,
      status:editForm.status,
      start_date:editForm.start_date||null,
      business_days:editForm.business_days?parseInt(editForm.business_days):null,
      /* Guard against empty-string values for numeric fields */
      flat_hours:editForm.flat_hours!==''&&editForm.flat_hours!=null?parseFloat(editForm.flat_hours):null,
      qa_hours:editForm.qa_hours!==''&&editForm.qa_hours!=null?parseFloat(editForm.qa_hours):null,
      consultant_id:editForm.consultant_id?parseInt(editForm.consultant_id):null,
      qa_consultant_id:editForm.qa_consultant_id?parseInt(editForm.qa_consultant_id):null,
    };
    H.patch('/projects/'+selDeliv.project_id+'/deliverables/'+editForm.id,payload)
      .then(()=>{setSel(null);setL(!0);setR(null);N1(e.cId,Vr(e.wkFrom),Vr(e.wkTo)).then(d=>{setR(d);}).catch(()=>setR(null)).finally(()=>setL(!1));if(onSaved)onSaved();})
      .catch(er=>{setSaveErr(er?.response?.data?.detail||'Save failed');})
      .finally(()=>setSaving(!1));
  };

  /**
   * inp: reusable labeled form field helper.
   * Renders either a <select> (when opts is provided) or an <input>.
   */
  const inp=(label,key,type,opts)=>s.jsxs('div',{className:'flex flex-col gap-1',children:[
    s.jsx('label',{className:'text-xs font-medium text-gray-500 dark:text-gray-400',children:label}),
    opts
      ?s.jsx('select',{className:'text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200',value:editForm[key]??'',onChange:ev=>setEdit(f=>({...f,[key]:ev.target.value})),children:opts.map(o=>s.jsx('option',{value:o.v,children:o.l},o.v))})
      :s.jsx('input',{type:type||'text',className:'text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200',value:editForm[key]??'',onChange:ev=>setEdit(f=>({...f,[key]:ev.target.value}))}),
  ]});

  const statusOpts=[{v:'not_started',l:'Not Started'},{v:'in_progress',l:'In Progress'},{v:'in_qa',l:'In QA'},{v:'delivered',l:'Delivered'}];
  const consOpts=[{v:'',l:'\u2014 None \u2014'},...cons.map(c=>({v:String(c.id),l:c.name}))];

  /**
   * wsCards: renders workshop cards with a purple-tinted background.
   * These appear above the deliverable list to give visual distinction.
   * Each card shows the workshop name (with calendar emoji), project name,
   * and optional status.
   */
  const wsCards=wsThisWeek.map((w,i)=>s.jsxs('div',{className:'flex items-stretch gap-3 px-4 py-3 rounded-xl border',style:{backgroundColor:'#f5f3ff',borderColor:'#ddd6fe'},children:[
    s.jsx('div',{className:'w-1 rounded-full shrink-0',style:{backgroundColor:w.color}}),
    s.jsxs('div',{className:'flex-1 min-w-0',children:[
      s.jsxs('div',{className:'text-sm font-medium text-gray-800',children:['\uD83D\uDCC5 ',w.name]}),
      s.jsxs('div',{className:'flex items-center gap-2 mt-0.5 flex-wrap',children:[
        s.jsx('span',{className:'text-xs font-medium',style:{color:w.color},children:'Workshop'}),
        s.jsx('span',{className:'text-xs text-gray-400',children:'\u00b7'}),
        s.jsx('span',{className:'text-xs text-gray-400',children:w.proj_name}),
        w.status&&s.jsxs(b.Fragment,{children:[
          s.jsx('span',{className:'text-xs text-gray-400',children:'\u00b7'}),
          /* Display status with underscores replaced by spaces */
          s.jsx('span',{className:'text-xs text-gray-400',children:w.status.replace(/_/g,' ')}),
        ]}),
      ]}),
    ]}),
    /* Workshop date displayed on the right side */
    s.jsx('div',{className:'shrink-0 text-xs text-gray-400 self-center',children:w.workshop_date}),
  ]},i));

  /**
   * listView: combines workshop cards (wsCards) and deliverable cards.
   * Workshop cards appear first, followed by clickable deliverable rows.
   */
  const listView=s.jsx('div',{className:'space-y-2',children:[
    ...wsCards,
    ...thisWeek.map((d,i)=>{
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
            s.jsx('span',{className:'text-xs text-gray-400',children:'\u00b7'}),
            s.jsx('span',{className:'text-xs text-gray-400',children:d.project_name}),
          ]}),
        ]}),
        s.jsxs('div',{className:'text-right shrink-0 flex flex-col items-end justify-between',children:[
          s.jsxs('div',{className:'text-base font-bold tabular-nums',style:{color:col},children:[wh?wh.hours.toFixed(1):0,'h']}),
          s.jsxs('div',{className:'text-xs text-gray-400',children:[tot.toFixed(1),'h total']}),
          s.jsxs('div',{className:'flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 mt-1',children:[s.jsx(On,{size:11}),' Edit']}),
        ]}),
      ]},i);
    }),
  ]});

  /**
   * editView: 3-column form layout (changed from 2-column in v3).
   * Always shows a single "Consultant Hours" field instead of splitting
   * between flat_hours and control_count * hours_per_control.
   */
  const editView=selDeliv&&s.jsxs('div',{className:'flex flex-col gap-4',children:[
    s.jsxs('div',{className:'flex items-center gap-2 mb-1',children:[
      s.jsx('button',{onClick:()=>setSel(null),className:'text-xs px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400',children:'\u2190 Back'}),
      s.jsxs('div',{className:'flex-1 min-w-0',children:[
        s.jsx('div',{className:'text-sm font-semibold text-gray-900 dark:text-gray-100',children:selDeliv.deliverable_name}),
        s.jsx('div',{className:'text-xs text-gray-400',children:selDeliv.project_name}),
      ]}),
    ]}),
    /* 3-column grid layout with inline styles (not Tailwind) for precise control */
    s.jsxs('div',{style:{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:'12px'},children:[
      s.jsx('div',{style:{gridColumn:'1/-1'},children:inp('Name','name')}),
      inp('Status','status','text',statusOpts),
      inp('Start Date','start_date','date'),
      inp('Business Days','business_days','number'),
      inp('Consultant Hours','flat_hours','number'),
      inp('QA Hours','qa_hours','number'),
      s.jsx('div',{}),
      inp('Consultant','consultant_id','text',consOpts),
      inp('QA Consultant','qa_consultant_id','text',consOpts),
    ]}),
  ]});

  /**
   * isEmpty: true when there are no deliverables AND no workshops for this
   * consultant in this week.  Used to show the "nothing here" message.
   */
  const isEmpty=!loading&&thisWeek.length===0&&wsThisWeek.length===0;

  /* Main bottom-sheet render */
  return s.jsxs('div',{className:'fixed inset-0 z-50 flex flex-col justify-end',style:{pointerEvents:'none'},children:[
    /* Backdrop */
    s.jsx('div',{className:'absolute inset-0 bg-black/30',style:{pointerEvents:'auto'},onClick:t}),
    s.jsxs('div',{className:'relative bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 shadow-2xl rounded-t-2xl flex flex-col',style:{maxHeight:'70vh',pointerEvents:'auto'},children:[
      /* Drag handle */
      s.jsx('div',{className:'w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-600 mx-auto mt-3 mb-2 shrink-0'}),
      /* Header: consultant dot, name, week label, close button */
      s.jsxs('div',{className:'flex items-center gap-2 px-5 pb-3 shrink-0 flex-wrap border-b border-gray-100 dark:border-gray-800',children:[
        s.jsx('span',{className:'w-3 h-3 rounded-full shrink-0',style:{backgroundColor:e.cColor}}),
        s.jsx('span',{className:'font-semibold text-sm text-gray-900 dark:text-gray-100',children:e.cName}),
        s.jsx('span',{className:'text-gray-300 dark:text-gray-600',children:'\u00b7'}),
        s.jsx('span',{className:'text-sm text-gray-500 dark:text-gray-400',children:'Week of '+e.wkLabel}),
        s.jsx('button',{onClick:t,className:'ml-auto p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400',children:s.jsx(ot,{size:15})}),
      ]}),
      /* Scrollable content area */
      s.jsx('div',{className:'overflow-auto flex-1 px-5 py-4',children:
        loading
          ?s.jsx('div',{className:'flex items-center justify-center h-20 text-sm text-gray-400',children:'Loading\u2026'})
          :selDeliv
            ?editView
            :isEmpty
              ?s.jsx('div',{className:'flex items-center justify-center h-20 text-sm text-gray-400',children:'No deliverables or workshops this week.'})
              :listView
      }),
      /**
       * Sticky footer: only shown when in edit mode (selDeliv is set).
       * Contains the error banner and Save/Cancel buttons, kept outside
       * the scroll area so they're always visible.
       */
      selDeliv&&s.jsxs('div',{className:'shrink-0 px-5 py-3 border-t border-gray-100 dark:border-gray-800 flex flex-col gap-2',children:[
        saveErr&&s.jsx('div',{className:'text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded px-3 py-2',children:saveErr}),
        s.jsxs('div',{className:'flex gap-2',children:[
          /* Save button with inline styles for consistent blue color */
          s.jsx('button',{onClick:saveEdit,disabled:saving,style:{backgroundColor:'#2563eb',color:'#fff',border:'none',cursor:saving?'not-allowed':'pointer',opacity:saving?0.6:1},className:'flex-1 py-2 rounded-lg text-sm font-medium',children:saving?'Saving\u2026':'Save Changes'}),
          s.jsx('button',{onClick:()=>setSel(null),style:{cursor:'pointer'},className:'px-4 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800',children:'Cancel'}),
        ]}),
      ]}),
    ]}),
  ]});
}
`;

// ── Apply replacement ──────────────────────────────────────────────────────
// Splice new component between the code before TsCellSheet and Rb().
c = c.slice(0, start) + newComp + c.slice(end);
writeFileSync('/home/coder/teamscope_v3.js', c);

// ── Verify ─────────────────────────────────────────────────────────────────
// Check that all workshop-specific features are present and that surrounding
// code (Rb) was not damaged.
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['wsThisWeek state',        v.includes('wsThisWeek,setWsThisWeek')],
  /* Confirms the workshop fetch logic using Am("active") is present */
  ['workshop fetch in effect', v.includes('Am("active").then(async ps=>{')],
  /* Confirms workshop cards are rendered from wsThisWeek state */
  ['wsCards rendered',        v.includes('wsCards=wsThisWeek.map')],
  /* Confirms the combined empty check considers workshops */
  ['isEmpty check',           v.includes('wsThisWeek.length===0')],
  /* Ensure exactly one TsCellSheet exists (no duplication) */
  ['TsCellSheet count=1',     (v.match(/function TsCellSheet\(/g)||[]).length===1],
  /* Rb is the next function boundary - must still exist */
  ['Rb present',              v.includes('function Rb(')],
];
let ok=true;
for(const[n,p] of checks){console.log((p?'✓':'✗')+' '+n);if(!p)ok=false;}
console.log('Size:',v.length);
process.exit(ok?0:1);
