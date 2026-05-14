import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// 1. Add column headers in qb - after "Due Date", before "Status"
const oldHeaderDueDate = `s.jsx("span",{className:"w-20 text-right shrink-0",children:"Due Date"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"})`;

if (!c.includes(oldHeaderDueDate)) {
  console.error('Cannot find Due Date + Status headers');
  process.exit(1);
}

const newHeaders = `s.jsx("span",{className:"w-20 text-right shrink-0",children:"Due Date"}),s.jsx("span",{className:"w-20 text-right shrink-0",children:"Consult Due"}),s.jsx("span",{className:"w-20 text-right shrink-0",children:"QA Due"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"})`;

c = c.replace(oldHeaderDueDate, newHeaders);
console.log('✓ Added Consult Due / QA Due headers');

// 2. In Hb component, compute phase dates and add cells
// Find the Hb function and add phase date extraction
const hbStart = c.indexOf('function Hb(');
const hbChunk = c.slice(hbStart, hbStart + 500);

// Add phase date extraction after the existing variable declarations
// Current: const d=e.qa_consultant_id?n.get(e.qa_consultant_id):null;
const oldVarEnd = `const d=e.qa_consultant_id?n.get(e.qa_consultant_id):null;`;
const hbVarIdx = c.indexOf(oldVarEnd, hbStart);
if (hbVarIdx < 0) { console.error('Cannot find Hb variable declarations'); process.exit(1); }

const newVarEnd = `const d=e.qa_consultant_id?n.get(e.qa_consultant_id):null;const _draftPhase=(e.phases||[]).find(ph=>ph.phase_type==='draft');const _qaPhase=(e.phases||[]).find(ph=>ph.phase_type==='qa');`;

c = c.replace(oldVarEnd, newVarEnd);
console.log('✓ Added phase date extraction');

// 3. Add the two date cells in the row - after end_date cell, before status
const oldEndDateCell = `ta(e.end_date)}),s.jsx(Bb,{status:e.status`;
if (!c.includes(oldEndDateCell)) { console.error('Cannot find end_date cell'); process.exit(1); }

const newEndDateCells = `ta(e.end_date)}),s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-20 text-right",title:"Consultant Due Date",children:ta(_draftPhase?_draftPhase.end_date:null)}),s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-20 text-right",title:"QA Due Date",children:ta(_qaPhase?_qaPhase.end_date:null)}),s.jsx(Bb,{status:e.status`;

c = c.replace(oldEndDateCell, newEndDateCells);
console.log('✓ Added Consult Due / QA Due cells');

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
