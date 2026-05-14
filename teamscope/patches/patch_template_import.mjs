import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// 1. Add importing state to Nw component
// Current: function Nw(){const e=St(),[t,n]=b.useState([]),[r,a]=b.useState([]),[l,o]=b.useState(new Set),[i,u]=b.useState(null),[c,p]=b.useState(!1);
const oldNwState = 'function Nw(){const e=St(),[t,n]=b.useState([]),[r,a]=b.useState([]),[l,o]=b.useState(new Set),[i,u]=b.useState(null),[c,p]=b.useState(!1);';
const newNwState = `function Nw(){const e=St(),[t,n]=b.useState([]),[r,a]=b.useState([]),[l,o]=b.useState(new Set),[i,u]=b.useState(null),[c,p]=b.useState(!1);const[importing,setImporting]=b.useState(!1);const[importErr,setImportErr]=b.useState(null);const fileRef=b.useRef(null);
  async function handleImport(ev){
    const file=ev.target.files&&ev.target.files[0];
    if(!file)return;
    ev.target.value='';
    setImporting(!0);setImportErr(null);
    try{
      const fd=new FormData();fd.append('file',file);
      await H.post('/templates/import-excel',fd,{headers:{'Content-Type':'multipart/form-data'}});
      await m();
    }catch(err){
      const msg=err?.response?.data?.detail||'Import failed';
      setImportErr(msg);
      setTimeout(()=>setImportErr(null),5000);
    }finally{setImporting(!1);}
  }
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

// 2. Replace the single "New Template" button with button group
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

// 3. Add error banner after the header div (before t.length===0)
const oldAfterHeader = `t.length===0?`;
const idx = c.indexOf(oldAfterHeader, c.indexOf('function Nw()'));
if (idx < 0) {
  console.error('Cannot find t.length===0 check');
  process.exit(1);
}
const newAfterHeader = `importErr&&s.jsx("div",{className:"mb-3 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400",children:importErr}),t.length===0?`;
c = c.slice(0, idx) + newAfterHeader + c.slice(idx + oldAfterHeader.length);
console.log('✓ Added error banner');

writeFileSync('/home/coder/teamscope_v3.js', c);

// verify
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['handleImport',     v.includes('async function handleImport')],
  ['handleDownload',   v.includes('function handleDownload()')],
  ['fileRef',          v.includes('fileRef=b.useRef(null)')],
  ['Download button',  v.includes('Download Template')],
  ['Import button',    v.includes('Import Template')],
  ['import-excel API', v.includes("'/templates/import-excel'")],
  ['excel-template API', v.includes("'/templates/excel-template'")],
  ['error banner',     v.includes('importErr&&s.jsx')],
  ['W1 icon',          v.includes('s.jsx(W1,{size:14})')],
  ['Qm icon',          v.includes('s.jsx(Qm,{size:14})')],
  ['Nw count=1',       (v.match(/function Nw\(\)/g)||[]).length===1],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
