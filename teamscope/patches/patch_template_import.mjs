/**
 * @file patch_template_import.mjs
 *
 * Adds Excel import/export functionality to the Nw (template list) component:
 *   - "Download Template" button: downloads an Excel template file from the API
 *   - "Import Template" button: uploads an Excel file to bulk-import templates
 *   - Error banner: shows import errors with auto-dismiss after 5 seconds
 *
 * Target component: Nw (the template list page that shows all templates
 * with the "New Template" button in the header).
 *
 * Search/replace strategy:
 *   This patch uses three targeted string replacements (not boundary-based
 *   slicing) to inject code at specific points within the existing Nw function:
 *
 *   1. State injection: finds the Nw state declaration block and appends
 *      new state variables (importing, importErr) plus handler functions
 *      (handleImport, handleDownload) and a file input ref.
 *
 *   2. Button injection: finds the existing "New Template" button and wraps
 *      it in a button group with Download and Import buttons added before it.
 *
 *   3. Error banner injection: finds the "t.length===0?" empty-state check
 *      and prepends an error banner that's conditionally rendered when
 *      importErr is set.
 */

import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ── Step 1: Add importing state and handler functions ──────────────────────
// The search string targets the exact sequence of useState calls at the top
// of the Nw component.  This is fragile but necessary because the minified
// bundle doesn't have named variables we can search for.
//
// New state added:
//   - importing / setImporting : tracks whether an import is in progress
//   - importErr / setImportErr : holds the error message from a failed import
//   - fileRef                  : ref to the hidden file input element
const oldNwState = 'function Nw(){const e=St(),[t,n]=b.useState([]),[r,a]=b.useState([]),[l,o]=b.useState(new Set),[i,u]=b.useState(null),[c,p]=b.useState(!1);';
const newNwState = `function Nw(){const e=St(),[t,n]=b.useState([]),[r,a]=b.useState([]),[l,o]=b.useState(new Set),[i,u]=b.useState(null),[c,p]=b.useState(!1);const[importing,setImporting]=b.useState(!1);const[importErr,setImportErr]=b.useState(null);const fileRef=b.useRef(null);
  /**
   * handleImport: triggered when the user selects an Excel file.
   * Uploads the file to POST /templates/import-excel as multipart form data,
   * then refreshes the template list.  On error, shows a message that
   * auto-dismisses after 5 seconds.
   */
  async function handleImport(ev){
    const file=ev.target.files&&ev.target.files[0];
    if(!file)return;
    /* Reset the file input so the same file can be re-selected */
    ev.target.value='';
    setImporting(!0);setImportErr(null);
    try{
      const fd=new FormData();fd.append('file',file);
      await H.post('/templates/import-excel',fd,{headers:{'Content-Type':'multipart/form-data'}});
      /* Refresh the template list after successful import (m is the fetch function) */
      await m();
    }catch(err){
      const msg=err?.response?.data?.detail||'Import failed';
      setImportErr(msg);
      /* Auto-dismiss error after 5 seconds */
      setTimeout(()=>setImportErr(null),5000);
    }finally{setImporting(!1);}
  }
  /**
   * handleDownload: downloads an Excel template file that users can fill in
   * and then import.  Creates a temporary blob URL and triggers a download
   * via a programmatically-created <a> element.
   */
  function handleDownload(){
    H.get('/templates/excel-template',{responseType:'blob'}).then(res=>{
      const url=URL.createObjectURL(res.data);
      const a=document.createElement('a');a.href=url;a.download='template_import.xlsx';document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
    });
  }`;

if (!c.includes(oldNwState)) {
  console.error('Cannot find Nw state declaration');
  process.exit(1);
}
c = c.replace(oldNwState, newNwState);
console.log('✓ Added import state and handlers');

// ── Step 2: Replace the "New Template" button with a button group ──────────
// The search string matches the exact JSX for the existing "New Template"
// button.  We wrap it in a flex container and add two new buttons before it.
//
// New buttons:
//   - Download Template: triggers handleDownload(), uses W1 (download icon)
//   - Import Template: a <label> wrapping a hidden <input type="file">,
//     uses Qm (upload icon), becomes disabled during import
const oldButton = `s.jsxs("button",{onClick:()=>e("/templates/new"),className:"flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-md",children:[s.jsx(we,{size:15})," New Template"]})`;

const newButtons = `s.jsxs("div",{className:"flex items-center gap-2",children:[
  s.jsxs("button",{onClick:handleDownload,className:"flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 text-sm font-medium rounded-md",children:[s.jsx(W1,{size:14})," Download Template"]}),
  s.jsxs("label",{className:"flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 text-sm font-medium rounded-md cursor-pointer"+(importing?" opacity-50 pointer-events-none":""),children:[s.jsx(Qm,{size:14}),importing?" Importing\u2026":" Import Template",s.jsx("input",{type:"file",accept:".xlsx,.xls",ref:fileRef,onChange:handleImport,className:"hidden"})]}),
  s.jsxs("button",{onClick:()=>e("/templates/new"),className:"flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-md",children:[s.jsx(we,{size:15})," New Template"]}),
]})`;

if (!c.includes(oldButton)) {
  console.error('Cannot find New Template button');
  process.exit(1);
}
c = c.replace(oldButton, newButtons);
console.log('✓ Added Download/Import/New buttons');

// ── Step 3: Add error banner ───────────────────────────────────────────────
// Finds the "t.length===0?" check (the empty-state conditional) within the
// Nw function and prepends an error banner div that renders when importErr
// is set.  The search starts from the Nw function declaration to avoid
// matching similar patterns elsewhere in the bundle.
const oldAfterHeader = `t.length===0?`;
const idx = c.indexOf(oldAfterHeader, c.indexOf('function Nw()'));
if (idx < 0) {
  console.error('Cannot find t.length===0 check');
  process.exit(1);
}
/** Error banner: red background with the import error message */
const newAfterHeader = `importErr&&s.jsx("div",{className:"mb-3 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400",children:importErr}),t.length===0?`;
c = c.slice(0, idx) + newAfterHeader + c.slice(idx + oldAfterHeader.length);
console.log('✓ Added error banner');

writeFileSync('/home/coder/teamscope_v3.js', c);

// ── Verify ─────────────────────────────────────────────────────────────────
// Confirm all three injection points took effect and no code was broken.
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  /* Handler functions exist */
  ['handleImport',     v.includes('async function handleImport')],
  ['handleDownload',   v.includes('function handleDownload()')],
  /* File input ref for the hidden file picker */
  ['fileRef',          v.includes('fileRef=b.useRef(null)')],
  /* Button text is present */
  ['Download button',  v.includes('Download Template')],
  ['Import button',    v.includes('Import Template')],
  /* API endpoints are correct */
  ['import-excel API', v.includes("'/templates/import-excel'")],
  ['excel-template API', v.includes("'/templates/excel-template'")],
  /* Error banner renders conditionally */
  ['error banner',     v.includes('importErr&&s.jsx')],
  /* Icon components are referenced */
  ['W1 icon',          v.includes('s.jsx(W1,{size:14})')],
  ['Qm icon',          v.includes('s.jsx(Qm,{size:14})')],
  /* Ensure exactly one Nw function exists (no duplication) */
  ['Nw count=1',       (v.match(/function Nw\(\)/g)||[]).length===1],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
