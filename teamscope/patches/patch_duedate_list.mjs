/**
 * @file patch_duedate_list.mjs
 *
 * @description
 * Adds a "Due Date" column to the deliverables list view and wires the
 * `end_date` field into every relevant editing surface:
 *
 *   1. **Column header** -- Inserts a "Due Date" header between "Business Days"
 *      and "Status" in the `qb` component's list header row.
 *
 *   2. **Row cell** -- Renders `ta(e.end_date)` (formatted date) in each `Hb`
 *      deliverable row between the Business Days and Status columns.
 *
 *   3. **Wb inline edit form** -- Adds a `<input type="date">` for `end_date`
 *      right after the Business Days number input so users can edit the due
 *      date inline without opening the side panel.
 *
 *   4. **Vb side panel** -- Adds the same date field to the Vb
 *      create/edit deliverable side panel (if the pattern is found).
 *
 *   5. **Bulk apply** -- Extends the bulk-update handler in `qb` to pass
 *      `end_date` when a due date is specified in the bulk form.
 *
 * @components
 *   - **qb** (deliverables list view container / header)
 *   - **Hb** (deliverable row component)
 *   - **Wb** (inline edit form, expanded under a row)
 *   - **Vb** (side-panel create/edit form)
 *
 * @strategy
 *   Uses string indexOf + slice for positional insertions (Wb field injection)
 *   and simple string replace for header / cell / bulk-apply modifications.
 *   Verification checks confirm every expected fragment is present.
 */

import { readFileSync, writeFileSync } from 'fs';

/** Load the full bundle for text-level patching. */
let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ─── 1. Add Due Date column header in qb ─────────────────────────────────────
//
// The header row in qb renders columns as fixed-width spans. We insert a
// 20-character-wide "Due Date" span between "Business Days" and "Status".

/** Original header fragment: Business Days followed immediately by Status. */
const oldHeaders = `s.jsx("span",{className:"w-16 text-right shrink-0",children:"Business Days"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"})`;

/** New header fragment with Due Date inserted in between. */
const newHeaders = `s.jsx("span",{className:"w-16 text-right shrink-0",children:"Business Days"}),s.jsx("span",{className:"w-20 text-right shrink-0",children:"Due Date"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"})`;

if (!c.includes(oldHeaders)) { console.error('Cannot find column headers'); process.exit(1); }
c = c.replace(oldHeaders, newHeaders);
console.log('✓ Added Due Date column header');

// ─── 2. Add Due Date cell in each Hb row ─────────────────────────────────────
//
// In the Hb row component, each field is rendered as a fixed-width span.
// We insert a new span displaying `ta(e.end_date)` (the formatted date)
// right after the Business Days span and before the Bb status select.

/** Anchor: the Business Days cell immediately followed by the Bb status component. */
const oldBizDays = `s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-16 text-right",title:"Business Days",children:mo(e.business_days,"")}),s.jsx(Bb,{status:e.status`;

/** New fragment: Business Days cell + Due Date cell + Bb status. */
const newBizDays = `s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-16 text-right",title:"Business Days",children:mo(e.business_days,"")}),s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-20 text-right",title:"Due Date",children:ta(e.end_date)}),s.jsx(Bb,{status:e.status`;

if (!c.includes(oldBizDays)) { console.error('Cannot find business days cell'); process.exit(1); }
c = c.replace(oldBizDays, newBizDays);
console.log('✓ Added Due Date cell in row');

// ─── 3. Add end_date date input to the Wb inline edit form ───────────────────
//
// Wb is the inline-edit form that expands below a row when the user clicks
// "Edit". We locate the Business Days `<input type="number">` inside Wb and
// inject a "Due Date" `<input type="date">` field immediately after it.
//
// Because Wb may contain multiple similar patterns, we first find the start
// of the Wb function and search within a bounded slice.

/** Locate the Wb function definition. */
const wbIdx = c.indexOf('function Wb(');
if (wbIdx < 0) { console.error('Cannot find Wb'); process.exit(1); }

// Confirm that the `business_days` key exists inside Wb's body.
const wbChunk = c.slice(wbIdx, wbIdx + 5000);
const bizDaysEdit = wbChunk.indexOf('"business_days"');
if (bizDaysEdit < 0) { console.error('Cannot find business_days in Wb'); process.exit(1); }

console.log('Wb business_days context found');

// Locate the Business Days input element within Wb specifically.
const wbBizPattern = `"Business Days"}),s.jsx("input",{type:"number"`;
const wbBizIdx = c.indexOf(wbBizPattern, wbIdx);
if (wbBizIdx < 0) { console.error('Cannot find Wb business_days input'); process.exit(1); }

// Walk forward from the Business Days input to find its enclosing `]})`
// (the closing of the wrapper div for that field).
let searchPos = wbBizIdx + wbBizPattern.length;
const nextFieldOrEnd = c.indexOf(']})', searchPos);
const endOfBizField = nextFieldOrEnd + 3; // include `]})`

/**
 * The new Due Date field to inject.
 * Uses `r.end_date` for state (Wb's edit state object) and `l` as the
 * field-change helper that calls `setState`.
 */
const insertPoint = endOfBizField;
const dueDateField = `,s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs text-gray-500 mb-1",children:"Due Date"}),s.jsx("input",{type:"date",value:r.end_date??"",onChange:h=>l("end_date",h.target.value||null),className:De})]})`;

// Splice the due-date field into the source right after the Business Days field.
c = c.slice(0, insertPoint) + dueDateField + c.slice(insertPoint);
console.log('✓ Added Due Date to Wb inline edit');

// ─── 4. Note on Wb save behaviour ───────────────────────────────────────────
//
// Wb passes its entire edit-state object `r` to the `onSave` callback.
// Since `r` starts as a shallow copy of the deliverable, `end_date` is
// already present if the API returned it. The new field writes back into
// `r`, so no additional payload wiring is needed here -- the parent (qb)
// handles serialisation.

// ─── 5. Add Due Date to the Vb side panel (create/edit deliverable) ──────────
//
// Vb is the slide-over panel for creating or editing a deliverable.
// The same approach: find the Business Days input, then inject a Due Date
// field right after it.

const vbIdx = c.indexOf('function Vb(');
if (vbIdx < 0) { console.error('Cannot find Vb'); process.exit(1); }

const vbBizPattern = `"Business Days"}),s.jsx("input",{type:"number"`;
const vbBizIdx = c.indexOf(vbBizPattern, vbIdx);
if (vbBizIdx < 0) {
  // Vb may have been restructured by a prior patch; skip gracefully.
  console.log('⚠ Vb business_days field not found, skipping');
} else {
  const vbNextField = c.indexOf(']})', vbBizIdx + vbBizPattern.length);
  const vbInsert = vbNextField + 3;

  /**
   * Due Date field for Vb. Uses `l.end_date` for state and `c` as the
   * field-change handler (Vb's local naming differs from Wb).
   */
  const vbDueDateField = `,s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Due Date"}),s.jsx("input",{type:"date",value:l.end_date??"",onChange:g=>c("end_date",g.target.value||null),className:Je})]})`;
  c = c.slice(0, vbInsert) + vbDueDateField + c.slice(vbInsert);
  console.log('✓ Added Due Date to Vb side panel');
}

// ─── 6. Add end_date to bulk apply in qb ─────────────────────────────────────
//
// The bulk-apply handler iterates selected deliverables and builds a
// partial-update object `_`. We extend it to include `end_date` when the
// user has specified a due date in the bulk form (`h.dueDate`).

const oldBulkDays = `h.days&&(_.business_days=Number(h.days)),`;
if (c.includes(oldBulkDays)) {
  c = c.replace(oldBulkDays, `h.days&&(_.business_days=Number(h.days)),h.dueDate&&(_.end_date=h.dueDate||null),`);
  console.log('✓ Added end_date to bulk apply');
}

// ─── Write patched bundle ────────────────────────────────────────────────────

writeFileSync('/home/coder/teamscope_v3.js', c);

// ─── Verification ────────────────────────────────────────────────────────────
//
// Re-read and assert every expected fragment exists; exit non-zero on failure.

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['Due Date header',    v.includes('"Due Date"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"')],
  ['Due Date cell',      v.includes('ta(e.end_date)}),s.jsx(Bb')],
  ['Due Date in Wb',     v.includes('"Due Date"}),s.jsx("input",{type:"date",value:r.end_date')],
  ['Hb intact',          v.includes('function Hb(')],
  ['qb intact',          v.includes('function qb(')],
  ['Wb intact',          v.includes('function Wb(')],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
