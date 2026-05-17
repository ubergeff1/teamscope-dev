/**
 * @file patch_due_dates_cols.mjs
 *
 * @description
 * Adds two new phase-level due-date columns -- "Consult Due" and "QA Due" --
 * to the deliverables list view. These columns display the `end_date` of the
 * `draft` and `qa` phase records attached to each deliverable.
 *
 *   1. **Column headers** -- Inserts "Consult Due" and "QA Due" header spans
 *      between the existing "Due Date" and "Status" headers in `qb`.
 *
 *   2. **Phase extraction** -- Adds local variables `_draftPhase` and
 *      `_qaPhase` inside the `Hb` row component, extracted from the
 *      deliverable's `phases` array using `phase_type` matching.
 *
 *   3. **Row cells** -- Renders two new `ta()`-formatted date cells in each
 *      `Hb` row, positioned between the overall Due Date cell and the
 *      Status selector.
 *
 * @components
 *   - **qb** (deliverables list header)
 *   - **Hb** (deliverable row component)
 *
 * @strategy
 *   Uses indexOf-based search to find exact string anchors, then replaces
 *   them with extended versions containing the new columns. Phase variable
 *   declarations are appended to an existing variable-declaration line
 *   inside Hb.
 */

import { readFileSync, writeFileSync } from 'fs';

/** Load the full bundle for patching. */
let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ─── 1. Add column headers in qb ─────────────────────────────────────────────
//
// Insert "Consult Due" (w-20) and "QA Due" (w-20) header spans between the
// existing "Due Date" header and the "Status" header.

/** The existing header pair: Due Date then Status. */
const oldHeaderDueDate = `s.jsx("span",{className:"w-20 text-right shrink-0",children:"Due Date"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"})`;

if (!c.includes(oldHeaderDueDate)) {
  console.error('Cannot find Due Date + Status headers');
  process.exit(1);
}

/** Extended header list with the two new columns inserted. */
const newHeaders = `s.jsx("span",{className:"w-20 text-right shrink-0",children:"Due Date"}),s.jsx("span",{className:"w-20 text-right shrink-0",children:"Consult Due"}),s.jsx("span",{className:"w-20 text-right shrink-0",children:"QA Due"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"})`;

c = c.replace(oldHeaderDueDate, newHeaders);
console.log('✓ Added Consult Due / QA Due headers');

// ─── 2. Extract phase objects inside Hb ──────────────────────────────────────
//
// Hb already has a line that looks up the QA consultant:
//   `const d=e.qa_consultant_id?n.get(e.qa_consultant_id):null;`
//
// We append two new `const` declarations that find the `draft` and `qa`
// phase objects from the deliverable's `phases` array. These are used
// later to render the phase due-date cells.

const hbStart = c.indexOf('function Hb(');
const hbChunk = c.slice(hbStart, hbStart + 500);

/** Anchor: the last variable declaration line before the JSX return. */
const oldVarEnd = `const d=e.qa_consultant_id?n.get(e.qa_consultant_id):null;`;
const hbVarIdx = c.indexOf(oldVarEnd, hbStart);
if (hbVarIdx < 0) { console.error('Cannot find Hb variable declarations'); process.exit(1); }

/**
 * Extended declarations: `_draftPhase` and `_qaPhase` are extracted via
 * Array.find on the phases array, guarded with a fallback to `[]` in case
 * the deliverable has no phases loaded.
 */
const newVarEnd = `const d=e.qa_consultant_id?n.get(e.qa_consultant_id):null;const _draftPhase=(e.phases||[]).find(ph=>ph.phase_type==='draft');const _qaPhase=(e.phases||[]).find(ph=>ph.phase_type==='qa');`;

c = c.replace(oldVarEnd, newVarEnd);
console.log('✓ Added phase date extraction');

// ─── 3. Add the two date cells in the Hb row ────────────────────────────────
//
// In the row JSX, we locate the transition from the overall end_date cell
// to the Bb status component and insert two new cells in between:
//   - Consultant Due: `_draftPhase.end_date`
//   - QA Due: `_qaPhase.end_date`

/** Anchor: end of the overall Due Date cell, right before the status select. */
const oldEndDateCell = `ta(e.end_date)}),s.jsx(Bb,{status:e.status`;
if (!c.includes(oldEndDateCell)) { console.error('Cannot find end_date cell'); process.exit(1); }

/**
 * Two new cells rendered with `ta()` (date formatter). Each uses a ternary
 * to safely handle cases where the phase object doesn't exist.
 */
const newEndDateCells = `ta(e.end_date)}),s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-20 text-right",title:"Consultant Due Date",children:ta(_draftPhase?_draftPhase.end_date:null)}),s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-20 text-right",title:"QA Due Date",children:ta(_qaPhase?_qaPhase.end_date:null)}),s.jsx(Bb,{status:e.status`;

c = c.replace(oldEndDateCell, newEndDateCells);
console.log('✓ Added Consult Due / QA Due cells');

// ─── Write and verify ────────────────────────────────────────────────────────

writeFileSync('/home/coder/teamscope_v3.js', c);

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['Consult Due header', v.includes('"Consult Due"')],
  ['QA Due header',      v.includes('"QA Due"')],
  ['draft phase extract',v.includes("phase_type==='draft'")],
  ['qa phase extract',   v.includes("phase_type==='qa'")],
  ['draft due cell',     v.includes('_draftPhase?_draftPhase.end_date:null')],
  ['qa due cell',        v.includes('_qaPhase?_qaPhase.end_date:null')],
  ['Hb intact',          v.includes('function Hb(')],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
