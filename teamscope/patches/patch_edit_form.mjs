/**
 * @file patch_edit_form.mjs
 *
 * @description
 * Overhauls the TsCellSheet deliverable edit form with new scheduling fields,
 * auto-date generation, and info tooltips. Changes include:
 *
 *   1. **Phase date extraction** -- When a deliverable is opened for editing
 *      (`startEdit`), the draft and QA phase objects are found in the
 *      `phases` array and their start/end dates are merged into `editForm`.
 *
 *   2. **Extended save payload** -- Adds `qa_business_days`,
 *      `workshop_sequential`, `qa_sequential`, `draft_start_date`,
 *      `draft_end_date`, `qa_start_date`, and `qa_end_date` to the PATCH
 *      payload sent to the API.
 *
 *   3. **Auto-generate handler** -- A new `autoGen()` function that first
 *      saves the current form values, then calls the
 *      `/auto-dates` API endpoint to let the server compute phase dates
 *      automatically. The returned dates are merged back into the form.
 *
 *   4. **Info tooltips** -- The `inp()` helper is enhanced to show a small
 *      "i" icon next to each label with a descriptive tooltip (from a
 *      `tips` lookup object).
 *
 *   5. **Restructured form grid** -- The 3-column grid is rearranged to
 *      group scheduling fields logically: Start Date, Due Date, then
 *      paired Consultant/QA rows for Days, Due, and Hours.
 *
 *   6. **Sequencing checkboxes** -- Two checkboxes control whether
 *      Workshop-to-Deliverable and Consultant-to-QA phases are sequential
 *      (each has an info tooltip explaining the behaviour).
 *
 *   7. **Auto Dates button** -- A purple "Auto Dates" button in the footer
 *      that is enabled only when all required scheduling fields are filled.
 *
 * @components
 *   - **TsCellSheet** (deliverable side-panel edit form)
 *
 * @strategy
 *   Six sequential search-and-replace operations on the bundled JS string,
 *   each targeting a unique code fragment. The script exits non-zero if any
 *   anchor string is not found, ensuring patches are applied atomically.
 */

import { readFileSync, writeFileSync } from 'fs';

/** Load the full bundle for patching. */
let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ═══════════════════════════════════════════════════════════════════════════════
// 1. UPDATE startEdit -- extract phase dates into editForm
// ═══════════════════════════════════════════════════════════════════════════════
//
// When the user clicks a deliverable to edit, `startEdit` populates
// `editForm` with the deliverable's fields. We extend it to also extract
// `draft_start_date`, `draft_end_date`, `qa_start_date`, and `qa_end_date`
// from the deliverable's `phases` array.

/** Original: sets editForm and selection state. */
const oldStartEdit = `setEdit({...full,flat_hours:ch});setSel(d);setSaveErr(null);`;

/**
 * New: finds draft ("dp") and QA ("qp") phase objects, then spreads their
 * date fields into editForm alongside the existing deliverable fields.
 */
const newStartEdit = `const dp=(full.phases||[]).find(p=>p.phase_type==='draft');const qp=(full.phases||[]).find(p=>p.phase_type==='qa');setEdit({...full,flat_hours:ch,draft_start_date:dp?dp.start_date:null,draft_end_date:dp?dp.end_date:null,qa_start_date:qp?qp.start_date:null,qa_end_date:qp?qp.end_date:null});setSel(d);setSaveErr(null);`;
if (!c.includes(oldStartEdit)) { console.error('FAIL: startEdit'); process.exit(1); }
c = c.replace(oldStartEdit, newStartEdit);
console.log('✓ startEdit updated');

// ═══════════════════════════════════════════════════════════════════════════════
// 2. UPDATE saveEdit payload -- add new scheduling fields
// ═══════════════════════════════════════════════════════════════════════════════
//
// The PATCH request body is extended with:
//   - `qa_business_days` (integer, number of QA working days)
//   - `workshop_sequential` (boolean, Workshop -> Deliverable ordering)
//   - `qa_sequential` (boolean, Consultant -> QA ordering)
//   - `draft_start_date`, `draft_end_date` (consultant phase dates)
//   - `qa_start_date`, `qa_end_date` (QA phase dates)

/** Original payload object literal. */
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

/** Extended payload with all new scheduling fields. */
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

// ═══════════════════════════════════════════════════════════════════════════════
// 3. ADD autoGen handler after saveEdit
// ═══════════════════════════════════════════════════════════════════════════════
//
// `autoGen()` is a two-step async operation:
//   a) PATCH the deliverable with current scheduling params (days, hours,
//      sequential flags, start/end dates).
//   b) POST to `/auto-dates` which computes phase dates server-side.
//   c) Merge the server response back into editForm.
//
// `canAutoGen` is a derived boolean that is true only when all required
// fields are filled (both day counts, both hour amounts, both sequential
// checkboxes, and at least one anchor date).

/** Anchor: the `.finally` of saveEdit followed by the `inp` helper. */
const saveEditEnd = `.finally(()=>setSaving(!1));
  };

  const inp=`;
if (!c.includes(saveEditEnd)) { console.error('FAIL: saveEditEnd'); process.exit(1); }

/**
 * Replacement block: closes saveEdit, defines autoGen + canAutoGen,
 * then continues with `const inp=`.
 */
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

// ═══════════════════════════════════════════════════════════════════════════════
// 4. ENHANCE the inp() helper with info-icon tooltips
// ═══════════════════════════════════════════════════════════════════════════════
//
// A `tips` dictionary maps field labels to descriptive tooltip text. The
// `inp()` helper is modified so that when a tip exists for the label, a
// small "i" circle is rendered next to the label with `title=` tooltip.

/** Original inp helper: plain label + children. */
const oldInp = `const inp=(label,key,type,opts)=>s.jsxs('div',{className:'flex flex-col gap-1',children:[
    s.jsx('label',{className:'text-xs font-medium text-gray-500 dark:text-gray-400',children:label}),`;

/**
 * New inp helper: adds a `tips` lookup and renders an "i" badge when a
 * tooltip is available. The label element now uses `s.jsxs` to include
 * both the text and the optional icon as children.
 */
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

// ═══════════════════════════════════════════════════════════════════════════════
// 5. REPLACE the editView grid with restructured fields
// ═══════════════════════════════════════════════════════════════════════════════
//
// The original 3-column grid had: Name (full-width), Status, Start Date,
// Business Days, Due Date, Consultant Hours, QA Hours, Consultant, QA
// Consultant.
//
// The new grid reorders fields into logical pairs:
//   Row 1: Name (full-width)
//   Row 2: Status | Start Date | Due Date
//   Row 3: Consultant Days | Consultant Due | Consultant Hours
//   Row 4: QA Days | QA Due | QA Hours
//   Row 5: Consultant | QA Consultant | (empty spacer)
//
// Below the grid, two checkboxes control sequential scheduling:
//   - "Workshop -> Deliverable are sequential"
//   - "Consultant -> QA are sequential"
// Each has an info tooltip explaining the effect.

/** Original grid JSX. */
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

/** Restructured grid + sequential-scheduling checkboxes. */
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

// ═══════════════════════════════════════════════════════════════════════════════
// 6. UPDATE footer buttons -- add Auto Dates button
// ═══════════════════════════════════════════════════════════════════════════════
//
// The original footer has "Save Changes" and "Cancel". We prepend an
// "Auto Dates" button (purple when enabled, gray when disabled) that
// calls `autoGen()`. A tooltip explains what fields are required.

/** Original footer buttons. */
const oldFooterButtons = `s.jsxs('div',{className:'flex gap-2',children:[
          s.jsx('button',{onClick:saveEdit,disabled:saving,style:{backgroundColor:'#2563eb',color:'#fff',border:'none',cursor:saving?'not-allowed':'pointer',opacity:saving?0.6:1},className:'flex-1 py-2 rounded-lg text-sm font-medium',children:saving?'Saving\u2026':'Save Changes'}),
          s.jsx('button',{onClick:()=>setSel(null),style:{cursor:'pointer'},className:'px-4 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800',children:'Cancel'}),
        ]})`;

/** New footer: Auto Dates (conditional purple) + Save Changes + Cancel. */
const newFooterButtons = `s.jsxs('div',{className:'flex gap-2',children:[
          s.jsx('button',{onClick:autoGen,disabled:saving||!canAutoGen,title:!canAutoGen?'Fill in Consultant Days, QA Days, Consultant Hours, QA Hours, check both sequential boxes, and set Start or Due Date':'Auto-generate all dates',style:{backgroundColor:canAutoGen?'#7c3aed':'#d1d5db',color:canAutoGen?'#fff':'#9ca3af',border:'none',cursor:saving||!canAutoGen?'not-allowed':'pointer',opacity:saving?0.6:1},className:'px-3 py-2 rounded-lg text-sm font-medium',children:saving?'Working\u2026':'\u2728 Auto Dates'}),
          s.jsx('button',{onClick:saveEdit,disabled:saving,style:{backgroundColor:'#2563eb',color:'#fff',border:'none',cursor:saving?'not-allowed':'pointer',opacity:saving?0.6:1},className:'flex-1 py-2 rounded-lg text-sm font-medium',children:saving?'Saving\u2026':'Save Changes'}),
          s.jsx('button',{onClick:()=>setSel(null),style:{cursor:'pointer'},className:'px-4 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800',children:'Cancel'}),
        ]})`;

if (!c.includes(oldFooterButtons)) { console.error('FAIL: footer'); process.exit(1); }
c = c.replace(oldFooterButtons, newFooterButtons);
console.log('✓ footer buttons updated');

// ─── Write and verify ────────────────────────────────────────────────────────

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
