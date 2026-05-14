import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// 1. Add Due Date column header in qb
const oldHeaders = `s.jsx("span",{className:"w-16 text-right shrink-0",children:"Business Days"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"})`;
const newHeaders = `s.jsx("span",{className:"w-16 text-right shrink-0",children:"Business Days"}),s.jsx("span",{className:"w-20 text-right shrink-0",children:"Due Date"}),s.jsx("span",{className:"w-28 text-right shrink-0",children:"Status"})`;

if (!c.includes(oldHeaders)) { console.error('Cannot find column headers'); process.exit(1); }
c = c.replace(oldHeaders, newHeaders);
console.log('✓ Added Due Date column header');

// 2. Add due date cell in Hb row - after Business Days, before status select
const oldBizDays = `s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-16 text-right",title:"Business Days",children:mo(e.business_days,"")}),s.jsx(Bb,{status:e.status`;
const newBizDays = `s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-16 text-right",title:"Business Days",children:mo(e.business_days,"")}),s.jsx("span",{className:"text-xs text-gray-500 shrink-0 tabular-nums w-20 text-right",title:"Due Date",children:ta(e.end_date)}),s.jsx(Bb,{status:e.status`;

if (!c.includes(oldBizDays)) { console.error('Cannot find business days cell'); process.exit(1); }
c = c.replace(oldBizDays, newBizDays);
console.log('✓ Added Due Date cell in row');

// 3. Find the Wb inline edit form and add due date field
// First let's find Wb
const wbIdx = c.indexOf('function Wb(');
if (wbIdx < 0) { console.error('Cannot find Wb'); process.exit(1); }

// Find the business_days field in Wb
const wbChunk = c.slice(wbIdx, wbIdx + 5000);
const bizDaysEdit = wbChunk.indexOf('"business_days"');
if (bizDaysEdit < 0) { console.error('Cannot find business_days in Wb'); process.exit(1); }

// Show context around it
console.log('Wb business_days context found');

// Find the business_days input in Wb to add end_date after it
// Look for pattern: business_days input followed by next field
const wbBizPattern = `"Business Days"}),s.jsx("input",{type:"number"`;
const wbBizIdx = c.indexOf(wbBizPattern, wbIdx);
if (wbBizIdx < 0) { console.error('Cannot find Wb business_days input'); process.exit(1); }

// Find the end of this field group (the closing ]}) of the div)
let searchPos = wbBizIdx + wbBizPattern.length;
// Find the next s.jsxs("div" which starts the next field, or the closing of the grid
const nextFieldOrEnd = c.indexOf(']})', searchPos);
const endOfBizField = nextFieldOrEnd + 3; // include ]})

// Insert due date field after business_days field
const insertPoint = endOfBizField;
const dueDateField = `,s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs text-gray-500 mb-1",children:"Due Date"}),s.jsx("input",{type:"date",value:r.end_date??"",onChange:h=>l("end_date",h.target.value||null),className:De})]})`;

c = c.slice(0, insertPoint) + dueDateField + c.slice(insertPoint);
console.log('✓ Added Due Date to Wb inline edit');

// 4. Also need to ensure Wb sends end_date in its save payload
// Find the Wb save handler - look for the onSave call
const wbSaveIdx = c.indexOf('onSave', wbIdx);
// Actually Wb's inline edit data is managed differently - let me check
// The Wb component passes its edit state to onSave
// The edit state r starts from the deliverable, so end_date should already be there
// But we need to make sure the bulk save in qb also handles end_date

// 5. Add Due Date to the Vb side panel (create/edit deliverable)
const vbIdx = c.indexOf('function Vb(');
if (vbIdx < 0) { console.error('Cannot find Vb'); process.exit(1); }

// Find business_days field in Vb
const vbBizPattern = `"Business Days"}),s.jsx("input",{type:"number"`;
const vbBizIdx = c.indexOf(vbBizPattern, vbIdx);
if (vbBizIdx < 0) {
  console.log('⚠ Vb business_days field not found, skipping');
} else {
  const vbNextField = c.indexOf(']})', vbBizIdx + vbBizPattern.length);
  const vbInsert = vbNextField + 3;
  const vbDueDateField = `,s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Due Date"}),s.jsx("input",{type:"date",value:l.end_date??"",onChange:g=>c("end_date",g.target.value||null),className:Je})]})`;
  c = c.slice(0, vbInsert) + vbDueDateField + c.slice(vbInsert);
  console.log('✓ Added Due Date to Vb side panel');
}

// 6. Add end_date to bulk apply in qb
const oldBulkDays = `h.days&&(_.business_days=Number(h.days)),`;
if (c.includes(oldBulkDays)) {
  c = c.replace(oldBulkDays, `h.days&&(_.business_days=Number(h.days)),h.dueDate&&(_.end_date=h.dueDate||null),`);
  console.log('✓ Added end_date to bulk apply');
}

writeFileSync('/home/coder/teamscope_v3.js', c);

// Verify
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
