/**
 * @file patch_slim_header.mjs
 *
 * @description
 * Replaces the project sheet header (Ub component) with a slimmer, more
 * information-dense layout. The original header used a `space-y-4` vertical
 * stack with a color swatch, title, stats grid, and consultant breakdown in
 * separate sections. This patch collapses everything into a compact two- or
 * three-line layout:
 *
 *   **Line 1** -- Color dot, project title, status badge, client name,
 *                 plus action buttons (Sync, Edit, Delete) on the right.
 *
 *   **Line 2** -- Inline stats: date range, deliverable/workshop counts,
 *                 planned hours (split into deliv + ws), and editable
 *                 budgeted hours.
 *
 *   **Line 3** (conditional) -- Per-consultant hour breakdown with colored
 *                 dots, unassigned-hours warning, and remaining-budget
 *                 indicator.
 *
 * Also adds two new computed values (`delivHrs`, `wsHrsTotal`) to break
 * down planned hours into deliverable vs. workshop contributions.
 *
 * @components
 *   - **Ub** (project sheet header)
 *
 * @strategy
 *   Locates the display section by its opening `space-y-4` class and the
 *   `const _i={not_started:` constant that immediately follows the Ub
 *   function body. Slices out the entire display block and replaces it
 *   with the new compact JSX. Then appends computed-value declarations
 *   (`delivHrs`, `wsHrsTotal`) after the existing `assignedTotal` line.
 */

import { readFileSync, writeFileSync } from 'fs';

/** Load the bundled JS for patching. */
let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ─── Locate the display section boundaries ───────────────────────────────────
//
// The display section starts with the `space-y-4` wrapper and ends just
// before the `const _i={not_started:` status-color mapping. We capture
// everything in between so we can replace it wholesale.

/** Start of the display JSX inside Ub. */
const displayStart = c.indexOf(`s.jsxs("div",{className:"space-y-4",children:[`);

/** End anchor: the line break + closing before the _i status-color constant. */
const displayEnd = c.indexOf(`\n  });\n}\nconst _i={not_started:`);

if (displayStart < 0 || displayEnd < 0) {
  console.error('Cannot find display section boundaries', displayStart, displayEnd);
  process.exit(1);
}

// displayEnd points to the `\n` before `]);}`; we want to include up to
// and including the closing `}` of the function body.
const endSlice = displayEnd + `\n  });\n}`.length;

console.log('Display from', displayStart, 'to', endSlice);

// ─── New compact header JSX ──────────────────────────────────────────────────
//
// The replacement uses `space-y-2` for tighter vertical spacing. Key
// sub-sections:
//
//   - Title row: color dot (3.5px circle), h1 title, status badge, client
//     name, and action buttons (Sync with spinner, Edit, Delete).
//
//   - Stats row (pl-6 to align with title): date range with arrow, counts
//     for deliverables and workshops, planned hours with a parenthetical
//     breakdown (delivHrs + wsHrsTotal), and an inline-editable budget.
//
//   - Consultant row (conditional, pl-6): per-consultant hours with color
//     dots, unassigned hours in orange, and a green/red remaining-budget
//     indicator when budget > 0.

const newDisplay = `s.jsxs("div",{className:"space-y-2",children:[
      s.jsxs("div",{className:"flex items-start gap-3",children:[
        s.jsx("span",{className:"w-3.5 h-3.5 rounded-full mt-0.5 shrink-0",style:{backgroundColor:e.color}}),
        s.jsxs("div",{className:"flex-1 min-w-0",children:[
          s.jsxs("div",{className:"flex items-center gap-2 flex-wrap",children:[
            s.jsx("h1",{className:"text-lg font-bold text-gray-900 dark:text-gray-100",children:e.name}),
            s.jsx("span",{className:Q("px-1.5 py-0.5 rounded text-[10px] font-medium",Ib[e.status]),children:e.status.replace("_"," ")}),
            e.client_name&&s.jsxs("span",{className:"text-xs text-gray-400",children:["\\u2014 ",e.client_name]}),
          ]}),
        ]}),
        s.jsxs("div",{className:"flex items-center gap-1 shrink-0",children:[
          s.jsxs("button",{onClick:async()=>{g(!0);try{await o()}finally{g(!1)}},disabled:y,title:"Recalculate grid allocations",className:"flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 disabled:opacity-40",children:[s.jsx(K1,{size:11,className:y?"animate-spin":""})," ",y?"Syncing\\u2026":"Sync"]}),
          s.jsxs("button",{onClick:v,className:"flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded border border-gray-200 dark:border-gray-700",children:[s.jsx(On,{size:11})," Edit"]}),
          s.jsx("button",{onClick:l,className:"p-1 text-gray-400 hover:text-red-600 rounded transition-colors",children:s.jsx(Me,{size:13})}),
        ]}),
      ]}),
      s.jsx("div",{className:"flex items-center gap-3 flex-wrap text-[11px] text-gray-500 pl-6",children:[
        e.start_date&&s.jsxs("span",{children:[e.start_date," \\u2192 ",e.end_date??"ongoing"]}),
        e.start_date&&s.jsx("span",{className:"text-gray-300 dark:text-gray-600",children:"\\u00b7"}),
        s.jsxs("span",{children:[s.jsx("span",{className:"font-semibold text-gray-700 dark:text-gray-300",children:n})," deliverables"]}),
        s.jsx("span",{className:"text-gray-300 dark:text-gray-600",children:"\\u00b7"}),
        s.jsxs("span",{children:[s.jsx("span",{className:"font-semibold text-gray-700 dark:text-gray-300",children:wsCount})," workshops"]}),
        s.jsx("span",{className:"text-gray-300 dark:text-gray-600",children:"\\u00b7"}),
        s.jsxs("span",{children:[s.jsxs("span",{className:"font-semibold text-gray-700 dark:text-gray-300",children:[t.toFixed(0),"h"]})," planned"]}),
        s.jsxs("span",{className:"text-gray-400",children:["(",delivHrs.toFixed(0),"h deliv + ",wsHrsTotal.toFixed(0),"h ws)"]}),
        s.jsx("span",{className:"text-gray-300 dark:text-gray-600",children:"\\u00b7"}),
        budgetEdit!==null
          ?s.jsxs("span",{className:"flex items-center gap-1",children:[
              s.jsx("input",{type:"number",value:budgetEdit,onChange:ev=>setBudgetEdit(ev.target.value),onKeyDown:ev=>{if(ev.key==='Enter')saveBudget();if(ev.key==='Escape')setBudgetEdit(null);},autoFocus:!0,className:"w-14 text-center text-[11px] border border-gray-300 dark:border-gray-600 rounded px-1 py-0.5 bg-white dark:bg-gray-800",placeholder:"0"}),
              s.jsx("span",{children:"h budgeted"}),
              s.jsx("button",{onClick:saveBudget,disabled:budgetSaving,className:"text-[11px] text-brand-600 font-medium ml-1",children:budgetSaving?"\\u2026":"\\u2713"}),
              s.jsx("button",{onClick:()=>setBudgetEdit(null),className:"text-[11px] text-gray-400 ml-0.5",children:"\\u2717"}),
            ]})
          :s.jsxs("span",{className:"cursor-pointer hover:text-brand-600 transition-colors",onClick:()=>setBudgetEdit(budget!=null?String(budget):''),children:[
              s.jsxs("span",{className:"font-semibold "+(budget?"text-gray-700 dark:text-gray-300":"text-gray-300 dark:text-gray-600"),children:budget?budget+"h":"\\u2014"})," budgeted"
            ]}),
      ]}),
      (Object.keys(conHrs).length>0||unassigned>0)&&s.jsxs("div",{className:"flex items-center gap-3 flex-wrap text-[11px] text-gray-500 pl-6",children:[
        s.jsx("span",{className:"font-medium text-gray-400",children:"Hours:"}),
        ...Object.entries(conHrs).sort((a,b)=>b[1]-a[1]).map(([cid,hrs])=>{
          const cc=conMap.get(Number(cid));
          return s.jsxs("span",{className:"flex items-center gap-1",children:[
            s.jsx("span",{className:"w-2 h-2 rounded-full inline-block",style:{backgroundColor:cc?cc.color:'#999'}}),
            s.jsx("span",{className:"text-gray-600 dark:text-gray-400",children:cc?cc.name:'?'}),
            s.jsxs("span",{className:"font-semibold text-gray-700 dark:text-gray-300 tabular-nums",children:[hrs.toFixed(1),"h"]}),
          ]},cid);
        }),
        unassigned>0&&s.jsxs("span",{className:"flex items-center gap-1",children:[
          s.jsx("span",{className:"w-2 h-2 rounded-full inline-block border border-dashed border-gray-400"}),
          s.jsx("span",{className:"text-orange-500 italic",children:"Unassigned"}),
          s.jsxs("span",{className:"font-semibold text-orange-500 tabular-nums",children:[unassigned.toFixed(1),"h"]}),
        ]}),
        budget>0&&s.jsxs("span",{className:"flex items-center gap-1 ml-1",children:[
          s.jsx("span",{className:"text-gray-400",children:"\\u00b7"}),
          s.jsxs("span",{className:(budget-t)>=0?"text-green-600":"text-red-500",children:[(budget-t).toFixed(1),"h remaining"]}),
        ]}),
      ]}),
    ]})
  });
}`;

// Splice the new compact header into the bundle, replacing the old section.
c = c.slice(0, displayStart) + newDisplay + c.slice(endSlice);

// ─── Add delivHrs and wsHrsTotal computations ────────────────────────────────
//
// The new header references `delivHrs` and `wsHrsTotal` to show the
// breakdown of planned hours. These must be computed before the JSX return.
// We insert them right after the existing `assignedTotal` declaration.

/** Anchor: the line that computes assignedTotal from conHrs. */
const insertAfter = `const assignedTotal=Object.values(conHrs).reduce((a,b)=>a+b,0);`;
if (!c.includes(insertAfter)) { console.error('Cannot find assignedTotal'); process.exit(1); }

/**
 * `delivHrs` -- sum of `flat_hours` + `qa_hours` across all deliverables.
 * `wsHrsTotal` -- sum of `duration_hours * consultant_count` across workshops.
 */
const addCalcs = `const assignedTotal=Object.values(conHrs).reduce((a,b)=>a+b,0);
  const delivHrs=(delivs||[]).reduce((a,d)=>a+(parseFloat(d.flat_hours||0))+(parseFloat(d.qa_hours||0)),0);
  const wsHrsTotal=(ws||[]).reduce((a,w)=>a+(parseFloat(w.duration_hours||0))*(w.consultants?w.consultants.length:0),0);`;

c = c.replace(insertAfter, addCalcs);

// ─── Write and verify ────────────────────────────────────────────────────────

writeFileSync('/home/coder/teamscope_v3.js', c);

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['slim layout',       v.includes('space-y-2')],
  ['start/end date',    v.includes('e.start_date," \\u2192 "')],
  ['deliv hours',       v.includes('delivHrs.toFixed(0)')],
  ['ws hours',          v.includes('wsHrsTotal.toFixed(0)')],
  ['inline consultants',v.includes('font-medium text-gray-400",children:"Hours:"')],
  ['remaining budget',  v.includes('remaining"]})')],
  ['no space-y-4',      !v.includes('space-y-4')],
  ['Ub count=1',        (v.match(/function Ub\(/g)||[]).length===1],
  ['_i present',        v.includes("const _i={not_started:")],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
