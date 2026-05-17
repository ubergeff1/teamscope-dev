/**
 * @file patch_project_header.mjs
 *
 * Replaces the Ub (project header/detail) component with an enhanced version
 * that adds:
 *   - Workshop count in the stats bar
 *   - Budgeted hours with inline-edit capability
 *   - "Hours by Consultant" breakdown panel showing how planned hours are
 *     distributed across assigned consultants (with progress bars against budget)
 *   - Unassigned hours tracking
 *   - Remaining budget indicator
 *
 * Also updates the Ub call-site in the parent component (tw) to pass
 * workshops, deliverables, and consultants as new props.
 *
 * Target component: Ub (the project header panel shown at the top of the
 * project detail page, displaying project metadata, stats, and action buttons).
 *
 * Search/replace strategy:
 *   1. String replacement of the Ub JSX call in the parent (tw) component
 *      to pass three new props: workshops (i), deliverables (l), consultants (c).
 *   2. Boundary-based slice of the Ub function: starts at "function Ub(" and
 *      ends at "const _i={not_started:" (the next constant declaration after Ub).
 *   3. The new Ub is inserted between those boundaries.
 *   4. Verification checks confirm both the call-site update and the new
 *      component features.
 */

import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ── Step 1: Update the Ub call-site in the parent (tw) component ───────────
// The existing call passes project, totalPlannedHours, deliverableCount,
// frameworks, onUpdate, onDelete, and onSyncAllocations.
// We add workshops (i), deliverables (l), and consultants (c) so Ub can
// compute per-consultant hour breakdowns.
const oldUbCall = `s.jsx(Ub,{project:r,totalPlannedHours:W,deliverableCount:l.length,frameworks:m,onUpdate:E,onDelete:D,onSyncAllocations:()=>u1(n).then(()=>{})})`;
const newUbCall = `s.jsx(Ub,{project:r,totalPlannedHours:W,deliverableCount:l.length,workshops:i,deliverables:l,consultants:c,frameworks:m,onUpdate:E,onDelete:D,onSyncAllocations:()=>u1(n).then(()=>{})})`;

if (!c.includes(oldUbCall)) { console.error('Cannot find Ub call'); process.exit(1); }
c = c.replace(oldUbCall, newUbCall);
console.log('✓ Updated Ub call with workshops/deliverables/consultants');

// ── Step 2: Locate the Ub function boundaries ─────────────────────────────
// Start: the function declaration
// End: the constant declaration that follows Ub in the bundle
const ubStart = c.indexOf('function Ub(');
if (ubStart < 0) { console.error('Cannot find Ub function'); process.exit(1); }

const ubEndMarker = `const _i={not_started:`;
const ubEnd = c.indexOf(ubEndMarker);
if (ubEnd < 0) { console.error('Cannot find end of Ub'); process.exit(1); }

console.log('Ub from', ubStart, 'to', ubEnd);

/**
 * New Ub component.
 *
 * Props (expanded from original):
 *   - project (e)            : the project object
 *   - totalPlannedHours (t)  : sum of all planned hours
 *   - deliverableCount (n)   : number of deliverables
 *   - workshops (ws)         : array of workshop objects for this project
 *   - deliverables (delivs)  : array of deliverable objects
 *   - consultants (allCons)  : array of all consultant objects
 *   - frameworks (r)         : array of framework objects
 *   - onUpdate (a)           : callback to update project fields
 *   - onDelete (l)           : callback to delete the project
 *   - onSyncAllocations (o)  : callback to sync grid allocations
 *
 * New state:
 *   - budgetEdit / setBudgetEdit     : inline budget editing (null = not editing)
 *   - budgetSaving / setBudgetSaving : tracks in-flight budget save
 *
 * Computed values:
 *   - conHrs     : object mapping consultant_id -> total assigned hours
 *   - unassigned : hours not assigned to any consultant
 *   - assignedTotal : sum of all values in conHrs
 *   - conMap     : Map of consultant_id -> consultant object (for name/color lookup)
 *   - wsCount    : number of workshops
 *   - budget     : the project's budgeted_hours value
 *
 * The component has two render modes:
 *   1. Edit mode (i=true): a form grid for editing project metadata
 *   2. Display mode: project header with stats bar and consultant breakdown
 *
 * External dependencies:
 *   - Ht  : CSS class for form inputs
 *   - $b  : array of project status options
 *   - Ib  : status -> CSS class mapping for project status badges
 *   - Mb  : toggle switch component (for snap_end_to_friday)
 *   - K1  : refresh/sync icon (with animate-spin when syncing)
 *   - On  : pencil/edit icon
 *   - Me  : trash/delete icon
 *   - lt  : checkmark/save icon
 */
const newUb = `function Ub({project:e,totalPlannedHours:t,deliverableCount:n,workshops:ws,deliverables:delivs,consultants:allCons,frameworks:r,onUpdate:a,onDelete:l,onSyncAllocations:o}){
  /* Standard edit mode state */
  const[i,u]=b.useState(!1),[c,p]=b.useState({}),[m,x]=b.useState(!1),[y,g]=b.useState(!1);
  /* NEW: inline budget editing state */
  const[budgetEdit,setBudgetEdit]=b.useState(null);
  const[budgetSaving,setBudgetSaving]=b.useState(!1);

  /** Copy project data into edit form and enter edit mode */
  function v(){p({...e}),u(!0)}
  /** Update a single field in the edit form */
  function k(h,w){p(E=>({...E,[h]:w}))}
  /** Save edited project data via onUpdate callback */
  async function d(){x(!0);try{await a(c),u(!1)}finally{x(!1)}}

  /**
   * saveBudget: saves the inline budget edit.
   * Converts empty string to null, otherwise parses as float.
   * Calls onUpdate with just the budgeted_hours field.
   */
  async function saveBudget(){
    if(budgetEdit===null)return;
    setBudgetSaving(!0);
    try{
      const val=budgetEdit===''?null:parseFloat(budgetEdit);
      await a({budgeted_hours:val});
      setBudgetEdit(null);
    }finally{setBudgetSaving(!1);}
  }

  /**
   * Compute per-consultant hours from deliverables.
   * For each deliverable:
   *   - flat_hours are attributed to the assigned consultant (consultant_id)
   *   - qa_hours are attributed to the QA consultant (qa_consultant_id)
   *   - If no consultant is assigned, hours go to the "unassigned" bucket
   */
  const conHrs={};
  let unassigned=0;
  for(const dv of(delivs||[])){
    const hrs=dv.total_planned_hours||0;
    if(hrs===0)continue;
    const fh=parseFloat(dv.flat_hours||0);
    const qh=parseFloat(dv.qa_hours||0);
    /* Attribute flat hours to the assigned consultant */
    if(dv.consultant_id){
      conHrs[dv.consultant_id]=(conHrs[dv.consultant_id]||0)+fh;
    }else if(fh>0){unassigned+=fh;}
    /* Attribute QA hours to the QA consultant */
    if(dv.qa_consultant_id){
      conHrs[dv.qa_consultant_id]=(conHrs[dv.qa_consultant_id]||0)+qh;
    }else if(qh>0){unassigned+=qh;}
  }
  /**
   * Compute workshop hours per consultant.
   * Each workshop's duration_hours is added to every assigned consultant
   * (each consultant gets the full duration, not split).
   * Workshops with no assigned consultants add to unassigned.
   */
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

  /** Total hours assigned to any consultant */
  const assignedTotal=Object.values(conHrs).reduce((a,b)=>a+b,0);
  /** Map for O(1) consultant lookup by ID (for name and color) */
  const conMap=new Map((allCons||[]).map(cc=>[cc.id,cc]));

  const wsCount=(ws||[]).length;
  const budget=e.budgeted_hours;

  /** Look up the selected framework for the impact level dropdown */
  const f=r.find(h=>h.id===(c.framework_id??e.framework_id));

  return s.jsx("div",{className:"bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5",children:
    /* Edit mode: full project metadata form */
    i?s.jsxs("div",{className:"space-y-3",children:[
      s.jsxs("div",{className:"grid grid-cols-2 gap-3",children:[
        /* Project name (required) */
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Project name *"}),s.jsx("input",{type:"text",value:c.name??"",onChange:h=>k("name",h.target.value),className:Ht})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Client name"}),s.jsx("input",{type:"text",value:c.client_name??"",onChange:h=>k("client_name",h.target.value),className:Ht})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Status"}),s.jsx("select",{value:c.status??"active",onChange:h=>k("status",h.target.value),className:Ht,children:$b.map(h=>s.jsx("option",{value:h,children:h.replace("_"," ")},h))})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Color"}),s.jsx("input",{type:"color",value:c.color??"#4C9BE8",onChange:h=>k("color",h.target.value),className:"h-9 w-full cursor-pointer rounded border border-gray-300 dark:border-gray-700"})]}),
        /* Framework dropdown: changing it resets the impact level */
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Framework"}),s.jsxs("select",{value:c.framework_id??"",onChange:h=>{k("framework_id",h.target.value?Number(h.target.value):null),k("impact_level_id",null)},className:Ht,children:[s.jsx("option",{value:"",children:"None"}),r.map(h=>s.jsx("option",{value:h.id,children:h.name},h.id))]})]}),
        /* Impact level: disabled when no framework is selected */
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Impact level"}),s.jsxs("select",{value:c.impact_level_id??"",onChange:h=>k("impact_level_id",h.target.value?Number(h.target.value):null),className:Ht,disabled:!f,children:[s.jsx("option",{value:"",children:"None"}),f==null?void 0:f.impact_levels.map(h=>s.jsx("option",{value:h.id,children:h.name},h.id))]})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Start date"}),s.jsx("input",{type:"date",value:c.start_date??"",onChange:h=>k("start_date",h.target.value||null),className:Ht})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"End date"}),s.jsx("input",{type:"date",value:c.end_date??"",onChange:h=>k("end_date",h.target.value||null),className:Ht})]}),
      ]}),
      s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Notes"}),s.jsx("textarea",{value:c.notes??"",onChange:h=>k("notes",h.target.value),rows:2,className:Ht})]}),
      /* Snap-to-Friday toggle: consultant due dates snap to Friday of their week */
      s.jsxs("div",{className:"flex items-center justify-between py-1",children:[
        s.jsxs("div",{children:[
          s.jsx("p",{className:"text-sm font-medium text-gray-700 dark:text-gray-300",children:"Snap due dates to Friday"}),
          s.jsx("p",{className:"text-xs text-gray-500 mt-0.5",children:"Consultant due dates move to the Friday of the week work is due. QA starts the following Monday."}),
        ]}),
        s.jsx(Mb,{checked:c.snap_end_to_friday??!1,onChange:h=>k("snap_end_to_friday",h)}),
      ]}),
      /* Save and Cancel buttons for edit mode */
      s.jsxs("div",{className:"flex gap-2 pt-1",children:[
        s.jsxs("button",{onClick:d,disabled:m||!c.name,className:"flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white text-sm font-medium rounded-md",children:[s.jsx(lt,{size:14})," ",m?"Saving\\u2026":"Save"]}),
        s.jsx("button",{onClick:()=>u(!1),className:"px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md",children:"Cancel"}),
      ]}),
    ]})
    /* Display mode: project header with stats and consultant breakdown */
    :s.jsxs("div",{className:"space-y-4",children:[
      /* Top section: project color dot, name, status badge, action buttons */
      s.jsxs("div",{className:"flex items-start gap-4",children:[
        s.jsx("span",{className:"w-4 h-4 rounded-full mt-1 shrink-0",style:{backgroundColor:e.color}}),
        s.jsxs("div",{className:"flex-1 min-w-0",children:[
          s.jsxs("div",{className:"flex items-center gap-3 flex-wrap",children:[
            s.jsx("h1",{className:"text-xl font-bold text-gray-900 dark:text-gray-100",children:e.name}),
            /* Status badge using the Ib class map */
            s.jsx("span",{className:Q("px-2 py-0.5 rounded text-xs font-medium",Ib[e.status]),children:e.status.replace("_"," ")}),
          ]}),
          e.client_name&&s.jsx("p",{className:"text-sm text-gray-500 mt-0.5",children:e.client_name}),
        ]}),
        /* Action buttons: Sync to Grid, Edit, Delete */
        s.jsxs("div",{className:"flex items-center gap-1 shrink-0",children:[
          /* Sync button: recalculates grid allocations from deliverable data */
          s.jsxs("button",{onClick:async()=>{g(!0);try{await o()}finally{g(!1)}},disabled:y,title:"Recalculate grid allocations from deliverable data",className:"flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700 disabled:opacity-40",children:[s.jsx(K1,{size:13,className:y?"animate-spin":""})," ",y?"Syncing\\u2026":"Sync to Grid"]}),
          s.jsxs("button",{onClick:v,className:"flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700",children:[s.jsx(On,{size:13})," Edit"]}),
          s.jsx("button",{onClick:l,className:"p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors",children:s.jsx(Me,{size:15})}),
        ]}),
      ]}),
      /**
       * Stats bar: 4-column grid showing key project metrics.
       * Columns: Deliverables, Workshops, Planned Hours, Budgeted Hours
       *
       * The Budgeted Hours cell supports inline editing: clicking the value
       * enters edit mode with a number input + save/cancel buttons.
       */
      s.jsxs("div",{className:"grid grid-cols-4 gap-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3",children:[
        s.jsxs("div",{className:"text-center",children:[
          s.jsx("div",{className:"text-lg font-bold text-gray-900 dark:text-gray-100 tabular-nums",children:n}),
          s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Deliverables"}),
        ]}),
        /* NEW: workshop count stat */
        s.jsxs("div",{className:"text-center",children:[
          s.jsx("div",{className:"text-lg font-bold text-gray-900 dark:text-gray-100 tabular-nums",children:wsCount}),
          s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Workshops"}),
        ]}),
        s.jsxs("div",{className:"text-center",children:[
          s.jsxs("div",{className:"text-lg font-bold text-gray-900 dark:text-gray-100 tabular-nums",children:[t.toFixed(0),"h"]}),
          s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Planned Hours"}),
        ]}),
        /* NEW: budgeted hours with inline edit */
        s.jsxs("div",{className:"text-center",children:[
          budgetEdit!==null
            /* Edit mode: number input with Enter to save, Escape to cancel */
            ?s.jsxs("div",{className:"flex items-center justify-center gap-1",children:[
                s.jsx("input",{type:"number",value:budgetEdit,onChange:ev=>setBudgetEdit(ev.target.value),onKeyDown:ev=>{if(ev.key==='Enter')saveBudget();if(ev.key==='Escape')setBudgetEdit(null);},autoFocus:!0,className:"w-20 text-center text-sm border border-gray-300 dark:border-gray-600 rounded px-1 py-0.5 bg-white dark:bg-gray-800",placeholder:"0"}),
                s.jsx("button",{onClick:saveBudget,disabled:budgetSaving,className:"text-xs text-brand-600 hover:text-brand-700 font-medium",children:budgetSaving?"\\u2026":"\\u2713"}),
                s.jsx("button",{onClick:()=>setBudgetEdit(null),className:"text-xs text-gray-400 hover:text-gray-600",children:"\\u2717"}),
              ]})
            /* Display mode: clickable value that enters edit mode */
            :s.jsxs("div",{className:"text-lg font-bold tabular-nums cursor-pointer hover:text-brand-600 transition-colors "+(budget?"text-gray-900 dark:text-gray-100":"text-gray-300 dark:text-gray-600"),onClick:()=>setBudgetEdit(budget!=null?String(budget):''),children:budget?budget+'h':'\\u2014'}),
          s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Budgeted Hours"}),
        ]}),
      ]}),
      /**
       * NEW: Hours by Consultant breakdown panel.
       * Only shown when there are assigned or unassigned hours.
       * Renders:
       *   - Header row with "Hours by Consultant" label and summary totals
       *   - One row per consultant (sorted by hours descending) with:
       *     color dot, name, hours value, and optional budget progress bar
       *   - An "Unassigned" row (if unassigned > 0) with dashed border dot
       *   - A footer with "Remaining Budget" (green if positive, red if negative)
       */
      (Object.keys(conHrs).length>0||unassigned>0)&&s.jsxs("div",{className:"rounded-lg border border-gray-100 dark:border-gray-800 overflow-hidden",children:[
        /* Header: label + summary stats */
        s.jsxs("div",{className:"flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/50 text-xs font-medium text-gray-500",children:[
          s.jsx("span",{children:"Hours by Consultant"}),
          s.jsxs("span",{className:"tabular-nums",children:["Assigned: ",assignedTotal.toFixed(1),"h",unassigned>0?" | Unassigned: "+unassigned.toFixed(1)+"h":"",budget?" | Budget: "+budget+"h":""]}),
        ]}),
        /* Consultant rows + unassigned row */
        s.jsx("div",{className:"divide-y divide-gray-100 dark:divide-gray-800",children:
          [...Object.entries(conHrs).sort((a,b)=>b[1]-a[1]).map(([cid,hrs])=>{
            const cc=conMap.get(Number(cid));
            return s.jsxs("div",{className:"flex items-center gap-2 px-3 py-1.5",children:[
              /* Consultant color dot */
              s.jsx("span",{className:"w-2.5 h-2.5 rounded-full shrink-0",style:{backgroundColor:cc?cc.color:'#999'}}),
              s.jsx("span",{className:"text-sm text-gray-700 dark:text-gray-300 flex-1",children:cc?cc.name:'Unknown'}),
              s.jsxs("span",{className:"text-sm font-semibold tabular-nums text-gray-900 dark:text-gray-100",children:[hrs.toFixed(1),"h"]}),
              /* Progress bar against budget (only shown when budget > 0) */
              budget>0&&s.jsx("div",{className:"w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden ml-2",children:
                s.jsx("div",{className:"h-full rounded-full",style:{width:Math.min(100,hrs/budget*100)+"%",backgroundColor:cc?cc.color:'#999'}}),
              }),
            ]},cid);
          }),
          /* Unassigned hours row: dashed border dot, italic text, orange color */
          unassigned>0&&s.jsxs("div",{className:"flex items-center gap-2 px-3 py-1.5",children:[
            s.jsx("span",{className:"w-2.5 h-2.5 rounded-full shrink-0 border border-dashed border-gray-400"}),
            s.jsx("span",{className:"text-sm text-gray-400 italic flex-1",children:"Unassigned"}),
            s.jsxs("span",{className:"text-sm font-semibold tabular-nums text-orange-500",children:[unassigned.toFixed(1),"h"]}),
          ]},'unassigned'),
          ].filter(Boolean)
        }),
        /* Footer: remaining budget (green if positive, red if over budget) */
        budget>0&&s.jsxs("div",{className:"flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/50 text-xs font-medium",children:[
          s.jsx("span",{className:"text-gray-500",children:"Remaining Budget"}),
          s.jsxs("span",{className:(budget-t)>=0?"text-green-600":"text-red-500",children:[(budget-t).toFixed(1),"h"]}),
        ]}),
      ]}),
    ]})
  });
}
`;

// ── Apply replacement ──────────────────────────────────────────────────────
// Slice out the old Ub (from ubStart to ubEnd) and insert the new version.
// Everything from ubEnd onward (starting with "const _i=...") is preserved.
c = c.slice(0, ubStart) + newUb + c.slice(ubEnd);

writeFileSync('/home/coder/teamscope_v3.js', c);

// ── Verify ─────────────────────────────────────────────────────────────────
// Comprehensive checks covering both the call-site update and the new
// component features.
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  /* Core function exists with expanded props */
  ['Ub function',         v.includes('function Ub({project:e,totalPlannedHours:t')],
  ['workshops prop',      v.includes('workshops:ws,deliverables:delivs,consultants:allCons')],
  /* Budget inline-edit state */
  ['budgetEdit state',    v.includes('budgetEdit,setBudgetEdit')],
  /* Per-consultant hours computation from deliverables */
  ['conHrs calc',         v.includes('conHrs[dv.consultant_id]')],
  /* Unassigned hours tracking */
  ['unassigned calc',     v.includes('unassigned+=fh')],
  /* Workshop hours added to consultant totals */
  ['workshop hours calc', v.includes('conHrs[wc.id]=(conHrs[wc.id]||0)+wh')],
  /* Budget save sends budgeted_hours field */
  ['budgeted_hours',      v.includes('budgeted_hours')],
  ['saveBudget',          v.includes('async function saveBudget()')],
  /* Consultant breakdown panel */
  ['Hours by Consultant', v.includes('Hours by Consultant')],
  /* Remaining budget indicator */
  ['Remaining Budget',    v.includes('Remaining Budget')],
  /* Ensure exactly one Ub function exists */
  ['Ub count=1',          (v.match(/function Ub\(/g)||[]).length===1],
  /* The constant that follows Ub must still exist */
  ['_i const present',    v.includes("const _i={not_started:")],
  /* Call-site was updated with new props */
  ['Ub call updated',     v.includes('workshops:i,deliverables:l,consultants:c,frameworks:m')],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
