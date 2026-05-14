import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ─── 1. Change stats from grid to inline row ─────────────────────────────────

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

// Find the end of the budget section (the closing of the grid div)
const statsStart = c.indexOf(oldStats);
const budgetEditEnd = c.indexOf(`s.jsx("div",{className:"text-[11px] text-gray-500 font-medium",children:"Budgeted Hours"`)
const closingAfterBudget = c.indexOf(`]}),\n      ]}),`, budgetEditEnd);

if (closingAfterBudget < 0) {
  console.error('Cannot find end of stats section');
  process.exit(1);
}

const oldFullStats = c.slice(statsStart, closingAfterBudget + `]}),\n      ]}),`.length);

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

c = c.slice(0, statsStart) + newStats + c.slice(statsStart + oldFullStats.length);
console.log('✓ Stats changed to inline');


// ─── 2. Add Due Date to TsCellSheet edit form ────────────────────────────────

// Find the edit form grid in TsCellSheet
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

writeFileSync('/home/coder/teamscope_v3.js', c);

// Verify
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
