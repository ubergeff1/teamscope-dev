/**
 * @file patch_inline_stats_duedate.mjs
 *
 * @description
 * Implements two features in the bundled teamscope_v3.js file:
 *
 *   1. **Inline Stats Row** -- Replaces the 4-column grid of stats cards
 *      (Deliverables, Workshops, Planned Hours, Budgeted Hours) at the top
 *      of the project sheet with a compact, single-line inline layout using
 *      middle-dot separators. The budget figure becomes an editable inline
 *      input that the user can click to toggle.
 *
 *   2. **Due Date Field in TsCellSheet** -- Adds a "Due Date" (`end_date`)
 *      date-picker to the deliverable edit form inside the TsCellSheet
 *      component, and wires its value into the save payload so changes
 *      persist to the API.
 *
 * @components
 *   - **Ub** (project header / stats section)
 *   - **TsCellSheet** (deliverable side-panel edit form)
 *
 * @strategy
 *   The script reads the entire bundle as a string, then uses indexOf /
 *   slice / replace to locate exact JSX fragments and swap them out.
 *   After writing, a verification step re-reads the file and asserts
 *   every expected string is present (and the old grid class is gone).
 */

import { readFileSync, writeFileSync } from 'fs';

/** Load the full bundle into memory so we can perform text surgery. */
let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ─── 1. Change stats from grid to inline row ─────────────────────────────────
//
// The original layout uses a `grid grid-cols-4` container with four card-style
// children (Deliverables, Workshops, Planned Hours, Budgeted Hours). We replace
// the entire grid with a `flex` row of inline `<span>` elements separated by
// Unicode middle-dot characters (·), producing a much more compact header.

/** Exact JSX string of the OLD 4-column stats grid (up to the "Planned Hours" card). */
const oldStats = `s.jsxs("div",{className:"grid grid-cols-4 gap-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3",children:[
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
        ]}),`;

if (!c.includes(oldStats)) {
  console.error('Cannot find old stats section');
  process.exit(1);
}

// We need to capture the FULL old stats block, which extends past "Planned
// Hours" down through the "Budgeted Hours" card and the grid's closing tags.
// We locate the budget label text, then scan forward for the two closing `]})`
// sequences that terminate both the budget card and the outer grid container.

const statsStart = c.indexOf(oldStats);

/** Position of the budget label inside the grid (used as an anchor). */
const budgetEditEnd = c.indexOf(`s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Budgeted Hours"`)

/** The closing `]}),\n      ]}),` that ends the budget card AND the grid wrapper. */
const closingAfterBudget = c.indexOf(`]}),\n      ]}),`, budgetEditEnd);

if (closingAfterBudget < 0) {
  console.error('Cannot find end of stats section');
  process.exit(1);
}

/** Full substring of the old grid stats block that will be excised. */
const oldFullStats = c.slice(statsStart, closingAfterBudget + `]}),\n      ]}),`.length);

/**
 * Replacement JSX: a `flex` row where each metric is an inline span.
 *
 * Layout: "N deliverables · N workshops · Xh planned · Xh budgeted"
 *
 * The budget figure is interactive:
 *   - When `budgetEdit` is non-null, it renders an `<input type="number">`
 *     with Enter-to-save / Escape-to-cancel, plus checkmark / cross buttons.
 *   - Otherwise it renders a clickable span that enters edit mode on click.
 */
const newStats = `s.jsxs("div",{className:"flex items-center gap-4 flex-wrap text-sm text-gray-500 mt-1",children:[
        s.jsxs("span",{className:"flex items-center gap-1",children:[s.jsx("span",{className:"font-semibold text-gray-900 dark:text-gray-100",children:n})," deliverable",n!==1?"s":""]}),
        s.jsx("span",{className:"text-gray-300 dark:text-gray-600",children:"\\u00b7"}),
        s.jsxs("span",{className:"flex items-center gap-1",children:[s.jsx("span",{className:"font-semibold text-gray-900 dark:text-gray-100",children:wsCount})," workshop",wsCount!==1?"s":""]}),
        s.jsx("span",{className:"text-gray-300 dark:text-gray-600",children:"\\u00b7"}),
        s.jsxs("span",{className:"flex items-center gap-1",children:[s.jsxs("span",{className:"font-semibold text-gray-900 dark:text-gray-100",children:[t.toFixed(0),"h"]})," planned"]}),
        s.jsx("span",{className:"text-gray-300 dark:text-gray-600",children:"\\u00b7"}),
        budgetEdit!==null
          ?s.jsxs("span",{className:"flex items-center gap-1",children:[
              s.jsx("input",{type:"number",value:budgetEdit,onChange:ev=>setBudgetEdit(ev.target.value),onKeyDown:ev=>{if(ev.key==='Enter')saveBudget();if(ev.key==='Escape')setBudgetEdit(null);},autoFocus:!0,className:"w-16 text-center text-sm border border-gray-300 dark:border-gray-600 rounded px-1 py-0.5 bg-white dark:bg-gray-800",placeholder:"0"}),
              s.jsx("span",{children:"h budgeted"}),
              s.jsx("button",{onClick:saveBudget,disabled:budgetSaving,className:"text-xs text-brand-600 hover:text-brand-700 font-medium ml-1",children:budgetSaving?"\\u2026":"\\u2713"}),
              s.jsx("button",{onClick:()=>setBudgetEdit(null),className:"text-xs text-gray-400 hover:text-gray-600 ml-0.5",children:"\\u2717"}),
            ]})
          :s.jsxs("span",{className:"flex items-center gap-1 cursor-pointer hover:text-brand-600 transition-colors",onClick:()=>setBudgetEdit(budget!=null?String(budget):''),children:[
              s.jsxs("span",{className:"font-semibold "+(budget?"text-gray-900 dark:text-gray-100":"text-gray-300 dark:text-gray-600"),children:budget?budget+"h":"\\u2014"})," budgeted"
            ]}),
      ]}),`;

// Perform the splice: cut out the old grid, insert the new inline row.
c = c.slice(0, statsStart) + newStats + c.slice(statsStart + oldFullStats.length);
console.log('✓ Stats changed to inline');


// ─── 2. Add Due Date to TsCellSheet edit form ────────────────────────────────
//
// The edit form in TsCellSheet originally has 8 fields in a 3-column grid.
// We insert a "Due Date" date picker (`end_date`) immediately after the
// "Business Days" field, and remove the empty `<div>` spacer that was used
// to fill the third column.

/** Exact JSX of the existing form fields (before modification). */
const oldFields = `inp('Status','status','text',statusOpts),
      inp('Start Date','start_date','date'),
      inp('Business Days','business_days','number'),
      inp('Consultant Hours','flat_hours','number'),
      inp('QA Hours','qa_hours','number'),
      s.jsx('div',{}),
      inp('Consultant','consultant_id','text',consOpts),
      inp('QA Consultant','qa_consultant_id','text',consOpts),`;

if (!c.includes(oldFields)) {
  console.error('Cannot find edit form fields');
  process.exit(1);
}

/**
 * New field list with Due Date added after Business Days.
 * The empty spacer div is removed to keep the grid balanced.
 */
const newFields = `inp('Status','status','text',statusOpts),
      inp('Start Date','start_date','date'),
      inp('Business Days','business_days','number'),
      inp('Due Date','end_date','date'),
      inp('Consultant Hours','flat_hours','number'),
      inp('QA Hours','qa_hours','number'),
      inp('Consultant','consultant_id','text',consOpts),
      inp('QA Consultant','qa_consultant_id','text',consOpts),`;

c = c.replace(oldFields, newFields);
console.log('✓ Added Due Date field');


// ─── 3. Add end_date to saveEdit payload ─────────────────────────────────────
//
// The saveEdit function builds a `payload` object that is POSTed/PATCHed to
// the API. We add `end_date` so the due-date value from the form is persisted.

/** Exact JSX of the original payload object literal. */
const oldPayload = `const payload={
      name:editForm.name,
      status:editForm.status,
      start_date:editForm.start_date||null,
      business_days:editForm.business_days?parseInt(editForm.business_days):null,
      flat_hours:editForm.flat_hours!==''&&editForm.flat_hours!=null?parseFloat(editForm.flat_hours):null,
      qa_hours:editForm.qa_hours!==''&&editForm.qa_hours!=null?parseFloat(editForm.qa_hours):null,
      consultant_id:editForm.consultant_id?parseInt(editForm.consultant_id):null,
      qa_consultant_id:editForm.qa_consultant_id?parseInt(editForm.qa_consultant_id):null,
    };`;

if (!c.includes(oldPayload)) {
  console.error('Cannot find save payload');
  process.exit(1);
}

/**
 * Updated payload with `end_date` inserted right after `start_date`.
 * The value is coerced to null when empty to match API expectations.
 */
const newPayload = `const payload={
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

c = c.replace(oldPayload, newPayload);
console.log('✓ Added end_date to save payload');

// ─── Write the patched bundle back to disk ───────────────────────────────────

writeFileSync('/home/coder/teamscope_v3.js', c);

// ─── Verification ────────────────────────────────────────────────────────────
//
// Re-read the file and run a series of assertions to confirm every expected
// string landed correctly and no duplicates were introduced.

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['inline stats',    v.includes('deliverable",n!==1?"s":""]')],
  ['workshops inline', v.includes('workshop",wsCount!==1?"s":""]')],
  ['planned inline',  v.includes('planned"]}')],
  ['budgeted inline', v.includes('" budgeted"')],
  ['Due Date field',  v.includes("inp('Due Date','end_date','date')")],
  ['end_date payload', v.includes('end_date:editForm.end_date||null')],
  ['no grid-cols-4',  !v.includes('grid grid-cols-4 gap-3 bg-gray-50')],
  ['Ub count=1',      (v.match(/function Ub\(/g)||[]).length===1],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
