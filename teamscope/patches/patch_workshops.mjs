/**
 * @file patch_workshops.mjs
 *
 * Replaces the Jb (workshop management) component with a fully rewritten
 * version that adds:
 *   - Inline editing: clicking a row expands an inline edit form below it
 *   - Bulk operations: checkbox selection with bulk status/date update
 *   - Create panel: a side panel for creating new workshops
 *   - Delete confirmation: inline delete with a confirm() dialog
 *
 * Target component: Jb (the workshop list/table rendered on the project
 * detail page, managing workshops for a single project).
 *
 * Search/replace strategy:
 *   1. Locates the Jb function by its declaration ("function Jb(").
 *   2. Finds the end boundary by searching for "}function Zb(" - the closing
 *      brace of Jb followed by the next function declaration.
 *   3. Slices out the old Jb and inserts the new version.
 *   4. Verifies that both Jb and its successor Zb still exist.
 *
 * Props received by the new Jb:
 *   - workshops (e)   : array of workshop objects for the current project
 *   - consultants (t) : array of all consultants (for the multi-select)
 *   - onCreate (n)    : callback to create a new workshop
 *   - onUpdate (r)    : callback to update a workshop by ID
 *   - onDelete (a)    : callback to delete a workshop by ID
 *
 * Internal state:
 *   - editId / editMap       : which row is being edited and its form data
 *   - saving                 : per-row saving state (keyed by workshop ID)
 *   - selected / bulk        : checkbox selection set and bulk-edit form values
 *   - showCreate / createData: side-panel visibility and new-workshop form data
 */

import { readFileSync, writeFileSync } from 'fs';

const src = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ── Locate Jb boundaries ──────────────────────────────────────────────────
// "function Jb(" is the declaration.  "}function Zb(" marks the end of Jb's
// body (closing brace) and the start of the next function.  We add +1 to
// include the closing brace itself in the slice we're replacing.
const jbStart = src.indexOf('function Jb(');
const jbEnd   = src.indexOf('}function Zb(', jbStart) + 1;

if (jbStart < 0 || jbEnd < 1) { console.error('Could not locate Jb'); process.exit(1); }

/**
 * New Jb component.
 *
 * Layout:
 *   - Left side (flex-1): workshop table with:
 *       - Header row with count + "Add Workshop" button
 *       - Bulk action bar (shown when checkboxes are selected)
 *       - Table with columns: checkbox, Name, Date, Consultants, Status, Actions
 *       - Inline edit row that expands below the selected row
 *   - Right side (w-80): create panel (shown when "Add Workshop" is clicked)
 *
 * Key helper functions:
 *   - startEdit(g)        : copies workshop data into editMap for inline editing
 *   - cancelEdit()        : clears the edit state
 *   - updField(id,key,val): updates a single field in the edit map
 *   - saveEdit(id)        : sends the edited data to onUpdate callback
 *   - togSel/togAll       : checkbox toggle for individual/all rows
 *   - applyBulk()         : applies bulk status/date changes to all selected rows
 *   - handleCreate()      : creates a new workshop via onCreate callback
 *   - handleDelete(ev,id) : deletes a workshop after confirmation
 *
 * External dependencies:
 *   - Kb : default create-data object (initial form values)
 *   - Gb : function to convert a workshop object to edit-form format
 *   - Qb : array of valid workshop status strings
 *   - Yb : status -> CSS class mapping for status badges
 *   - Xb : multi-select consultant picker component
 *   - De : CSS class string for form inputs (used in edit/bulk forms)
 *   - Je : CSS class string for form inputs (used in create panel)
 *   - we : plus icon component
 *   - On : pencil/edit icon component
 *   - ot : close/X icon component
 *   - Me : trash/delete icon component
 *   - lt : checkmark/save icon component
 */
const newJb = `function Jb({workshops:e,consultants:t,onCreate:n,onUpdate:r,onDelete:a}){
  /* Inline-edit state: editId tracks which row is expanded, editMap holds form data */
  const[editId,setEditId]=b.useState(null),[editMap,setEditMap]=b.useState({}),[saving,setSav]=b.useState({});
  /* Bulk selection: a Set of selected workshop IDs */
  const[selected,setSel]=b.useState(new Set());
  /* Bulk edit form values (status and date) */
  const[bulk,setBulk]=b.useState({status:"",workshop_date:""});
  const[bulkApplying,setBulkApp]=b.useState(!1);
  /* Create panel state */
  const[showCreate,setShowCreate]=b.useState(!1);
  const[createData,setCData]=b.useState({...Kb});
  const[creating,setCreating]=b.useState(!1);

  /** Check if all workshops are selected (for the header checkbox) */
  const allSelected=e.length>0&&e.every(g=>selected.has(g.id));
  /** Check if any bulk field has a value (to enable/disable the Apply button) */
  const anyBulk=!!(bulk.status||bulk.workshop_date);

  /** Copy workshop data into the edit map and set it as the active edit row */
  function startEdit(g){setEditId(g.id);setEditMap(m=>({...m,[g.id]:Gb(g)}));}
  /** Clear the edit state to collapse the inline edit row */
  function cancelEdit(){setEditId(null);}
  /** Update a single field in the edit map for a given workshop ID */
  function updField(id,key,val){setEditMap(m=>({...m,[id]:{...m[id],[key]:val}}));}
  /** Save the edited workshop via the onUpdate callback, then collapse the row */
  async function saveEdit(id){
    const d=editMap[id];if(!d)return;
    setSav(s=>({...s,[id]:!0}));
    try{await r(id,{name:d.name,workshop_date:d.workshop_date||null,status:d.status,consultant_ids:d.consultant_ids});setEditId(null);}
    finally{setSav(s=>({...s,[id]:!1}));}
  }
  /** Toggle a single row's checkbox */
  function togSel(id,chk){setSel(s=>{const ns=new Set(s);chk?ns.add(id):ns.delete(id);return ns;});}
  /** Toggle all rows' checkboxes */
  function togAll(chk){setSel(chk?new Set(e.map(g=>g.id)):new Set());}
  /**
   * Apply bulk edits to all selected workshops.
   * Iterates over selected IDs, builds a patch payload preserving existing
   * values for fields not being bulk-edited, then calls onUpdate for each.
   */
  async function applyBulk(){
    if(!selected.size)return;
    setBulkApp(!0);
    try{
      for(const id of selected){
        const w=e.find(g=>g.id===id);if(!w)continue;
        const patch={name:w.name,consultant_ids:w.consultants.map(c=>c.id)};
        if(bulk.status)patch.status=bulk.status;
        if(bulk.workshop_date)patch.workshop_date=bulk.workshop_date;
        await r(id,patch);
      }
      setBulk({status:"",workshop_date:""});setSel(new Set());
    }finally{setBulkApp(!1);}
  }
  /** Create a new workshop via the onCreate callback, then reset the form */
  async function handleCreate(){
    setCreating(!0);
    try{await n({...createData,workshop_date:createData.workshop_date||null});setShowCreate(!1);setCData({...Kb});}
    finally{setCreating(!1);}
  }
  /** Delete a workshop after showing a confirmation dialog */
  async function handleDelete(ev,id){ev.stopPropagation();confirm("Delete this workshop?")&&await a(id);}

  /* ── Render ─────────────────────────────────────────────────────────────── */
  return s.jsxs("div",{className:"flex gap-6",children:[
    /* Left side: workshop table */
    s.jsxs("div",{className:"flex-1 min-w-0",children:[
      /* Header: workshop count + Add Workshop button */
      s.jsxs("div",{className:"flex justify-between items-center mb-3",children:[
        s.jsxs("p",{className:"text-sm text-gray-500",children:[e.length," workshop",e.length!==1?"s":""]}),
        s.jsxs("button",{onClick:()=>{setShowCreate(v=>!v);setEditId(null);},className:"flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-md",children:[s.jsx(we,{size:14})," Add Workshop"]}),
      ]}),
      /* Bulk action bar: shown when at least one checkbox is selected */
      selected.size>0&&s.jsxs("div",{className:"mb-3 p-3 rounded-lg border bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",children:[
        s.jsxs("p",{className:"text-xs font-medium text-blue-700 dark:text-blue-300 mb-2",children:["Apply to ",selected.size," selected workshop",selected.size!==1?"s":""]}),
        s.jsxs("div",{className:"flex flex-wrap items-end gap-2",children:[
          /* Bulk status dropdown */
          s.jsxs("div",{children:[
            s.jsx("label",{className:"block text-[10px] text-gray-500 mb-1",children:"Status"}),
            s.jsxs("select",{value:bulk.status,onChange:ev=>setBulk(v=>({...v,status:ev.target.value})),className:De,children:[
              s.jsx("option",{value:"",children:"— unchanged —"}),
              Qb.map(st=>s.jsx("option",{value:st,children:st.replace(/_/g," ")},st)),
            ]}),
          ]}),
          /* Bulk date picker */
          s.jsxs("div",{children:[
            s.jsx("label",{className:"block text-[10px] text-gray-500 mb-1",children:"Date"}),
            s.jsx("input",{type:"date",value:bulk.workshop_date,onChange:ev=>setBulk(v=>({...v,workshop_date:ev.target.value})),className:De}),
          ]}),
          s.jsx("button",{onClick:applyBulk,disabled:bulkApplying||!anyBulk,className:"px-3 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white text-xs font-medium rounded-md",children:bulkApplying?"Applying\u2026":"Apply"}),
          s.jsx("button",{onClick:()=>setBulk({status:"",workshop_date:""}),className:"px-2 py-1.5 text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md",children:"Reset"}),
        ]}),
      ]}),
      /* Workshop table or empty state */
      e.length===0
        ?s.jsx("div",{className:"text-center py-12 text-gray-400 text-sm",children:"No workshops scheduled."})
        :s.jsx("div",{className:"bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden",children:
          s.jsxs("table",{className:"w-full text-sm",children:[
            /* Table header with select-all checkbox */
            s.jsx("thead",{className:"bg-gray-50 dark:bg-gray-800",children:
              s.jsxs("tr",{children:[
                s.jsx("th",{className:"px-3 py-2.5 w-8",children:s.jsx("input",{type:"checkbox",checked:allSelected,onChange:ev=>togAll(ev.target.checked),className:"w-4 h-4 rounded border-gray-300"})}),
                s.jsx("th",{className:"px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide",children:"Name"}),
                s.jsx("th",{className:"px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide",children:"Date"}),
                s.jsx("th",{className:"px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide",children:"Consultants"}),
                s.jsx("th",{className:"px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide",children:"Status"}),
                s.jsx("th",{className:"px-4 py-2.5 w-16"}),
              ]}),
            }),
            /* Table body: each workshop gets a data row + optional inline edit row */
            s.jsx("tbody",{className:"divide-y divide-gray-100 dark:divide-gray-800",children:
              e.map(g=>{
                const isEd=editId===g.id,ed=editMap[g.id]||{},isSav=!!saving[g.id];
                return s.jsxs(b.Fragment,{children:[
                  /* Data row: checkbox, name, date, consultant pills, status badge, action buttons */
                  s.jsxs("tr",{className:Q("hover:bg-gray-50 dark:hover:bg-gray-800/50",isEd&&"bg-blue-50/50 dark:bg-blue-900/10"),children:[
                    s.jsx("td",{className:"px-3 py-3",children:s.jsx("input",{type:"checkbox",checked:selected.has(g.id),onChange:ev=>togSel(g.id,ev.target.checked),className:"w-4 h-4 rounded border-gray-300"})}),
                    s.jsx("td",{className:"px-4 py-3 font-medium text-gray-900 dark:text-gray-100",children:g.name}),
                    s.jsx("td",{className:"px-4 py-3 text-gray-500",children:g.workshop_date??"—"}),
                    /* Consultant pills: colored rounded badges with consultant name */
                    s.jsx("td",{className:"px-4 py-3",children:g.consultants.length>0
                      ?s.jsx("div",{className:"flex flex-wrap gap-1",children:g.consultants.map(v=>s.jsx("span",{className:"inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium text-white",style:{backgroundColor:v.color},children:v.name},v.id))})
                      :s.jsx("span",{className:"text-gray-400",children:"—"}),
                    }),
                    /* Status badge using the Yb class map */
                    s.jsx("td",{className:"px-4 py-3",children:s.jsx("span",{className:Q("px-2 py-0.5 rounded text-xs font-medium",Yb[g.status]),children:g.status.replace(/_/g," ")})}),
                    /* Action buttons: edit toggle + delete */
                    s.jsx("td",{className:"px-4 py-3",children:s.jsxs("div",{className:"flex items-center justify-end gap-1",children:[
                      s.jsx("button",{onClick:()=>isEd?cancelEdit():startEdit(g),className:"p-1 text-gray-400 hover:text-brand-600 transition-colors",children:s.jsx(isEd?ot:On,{size:13})}),
                      s.jsx("button",{onClick:ev=>handleDelete(ev,g.id),className:"p-1 text-gray-400 hover:text-red-600 transition-colors",children:s.jsx(Me,{size:13})}),
                    ]})}),
                  ]},g.id+"-r"),
                  /**
                   * Inline edit row: only rendered when this row is being edited (isEd).
                   * Spans all 6 columns with a form grid containing:
                   *   - Name (full width), Date, Status, Consultants (multi-select via Xb),
                   *     Save + Cancel buttons
                   */
                  isEd&&s.jsx("tr",{children:s.jsx("td",{colSpan:6,className:"px-4 pb-4 pt-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50",children:
                    s.jsxs("div",{className:"grid grid-cols-2 sm:grid-cols-4 gap-3",children:[
                      s.jsxs("div",{className:"col-span-2 sm:col-span-4",children:[
                        s.jsx("label",{className:"block text-[10px] font-medium text-gray-500 mb-1",children:"Name *"}),
                        s.jsx("input",{type:"text",value:ed.name??"",onChange:ev=>updField(g.id,"name",ev.target.value),className:De,autoFocus:!0}),
                      ]}),
                      s.jsxs("div",{children:[
                        s.jsx("label",{className:"block text-[10px] font-medium text-gray-500 mb-1",children:"Date"}),
                        s.jsx("input",{type:"date",value:ed.workshop_date??"",onChange:ev=>updField(g.id,"workshop_date",ev.target.value||null),className:De}),
                      ]}),
                      s.jsxs("div",{children:[
                        s.jsx("label",{className:"block text-[10px] font-medium text-gray-500 mb-1",children:"Status"}),
                        s.jsxs("select",{value:ed.status??"scheduled",onChange:ev=>updField(g.id,"status",ev.target.value),className:De,children:[
                          Qb.map(st=>s.jsx("option",{value:st,children:st.replace(/_/g," ")},st)),
                        ]}),
                      ]}),
                      s.jsxs("div",{className:"col-span-2",children:[
                        s.jsx("label",{className:"block text-[10px] font-medium text-gray-500 mb-2",children:"Consultants"}),
                        s.jsx(Xb,{selected:ed.consultant_ids??[],allConsultants:t,onChange:ids=>updField(g.id,"consultant_ids",ids)}),
                      ]}),
                      /* Save and Cancel buttons for the inline edit */
                      s.jsxs("div",{className:"col-span-2 sm:col-span-4 flex gap-2 pt-1",children:[
                        s.jsxs("button",{onClick:()=>saveEdit(g.id),disabled:isSav||!ed.name,className:"flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white text-xs font-medium rounded-md",children:[s.jsx(lt,{size:13})," ",isSav?"Saving\u2026":"Save"]}),
                        s.jsx("button",{onClick:cancelEdit,className:"px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md",children:"Cancel"}),
                      ]}),
                    ]}),
                  })},g.id+"-e"),
                ]},g.id);
              })
            }),
          ]}),
        }),
    ]}),
    /**
     * Right side: Create Workshop panel.
     * Only shown when showCreate is true (toggled by "Add Workshop" button).
     * Contains form fields for name, date, status, and consultant multi-select.
     * Uses Je CSS class for inputs (slightly different styling from edit form).
     */
    showCreate&&s.jsxs("div",{className:"w-80 shrink-0 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5 h-fit",children:[
      s.jsxs("div",{className:"flex items-center justify-between mb-4",children:[
        s.jsx("h2",{className:"text-sm font-semibold text-gray-900 dark:text-gray-100",children:"New Workshop"}),
        s.jsx("button",{onClick:()=>setShowCreate(!1),className:"text-gray-400 hover:text-gray-600",children:s.jsx(ot,{size:14})}),
      ]}),
      s.jsxs("div",{className:"space-y-3",children:[
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Name *"}),s.jsx("input",{type:"text",value:createData.name,onChange:ev=>setCData(d=>({...d,name:ev.target.value})),className:Je,autoFocus:!0})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Date"}),s.jsx("input",{type:"date",value:createData.workshop_date??"",onChange:ev=>setCData(d=>({...d,workshop_date:ev.target.value||null})),className:Je})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-1",children:"Status"}),s.jsxs("select",{value:createData.status,onChange:ev=>setCData(d=>({...d,status:ev.target.value})),className:Je,children:[Qb.map(st=>s.jsx("option",{value:st,children:st.replace(/_/g," ")},st))]})]}),
        s.jsxs("div",{children:[s.jsx("label",{className:"block text-xs font-medium text-gray-500 mb-2",children:"Consultants"}),s.jsx(Xb,{selected:createData.consultant_ids,allConsultants:t,onChange:ids=>setCData(d=>({...d,consultant_ids:ids}))})]}),
      ]}),
      /* Create panel footer: Save + Cancel buttons */
      s.jsxs("div",{className:"mt-4 flex gap-2",children:[
        s.jsxs("button",{onClick:handleCreate,disabled:creating||!createData.name,className:"flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white text-sm font-medium rounded-md",children:[s.jsx(lt,{size:13})," ",creating?"Saving\u2026":"Save"]}),
        s.jsx("button",{onClick:()=>setShowCreate(!1),className:"px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md",children:"Cancel"}),
      ]}),
    ]}),
  ]});
}`;

// ── Apply replacement ──────────────────────────────────────────────────────
// Splice old Jb out and insert new Jb, preserving everything before jbStart
// and everything from jbEnd onward (which starts with "function Zb(").
const patched = src.slice(0, jbStart) + newJb + src.slice(jbEnd);
writeFileSync('/home/coder/teamscope_v3.js', patched);

// ── Verify ─────────────────────────────────────────────────────────────────
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  /* Core component exists */
  ['Jb present',            v.includes('function Jb(')],
  /* Next function boundary preserved */
  ['Zb still present',      v.includes('function Zb(')],
  /* Inline edit row uses a keyed Fragment with "-e" suffix */
  ['inline edit row',       v.includes('g.id+"-e"')],
  /* Bulk selection checkboxes */
  ['checkboxes',            v.includes('togAll')],
  /* Bulk apply functionality */
  ['bulk apply',            v.includes('applyBulk')],
  /* Create panel */
  ['Create panel',          v.includes('showCreate')],
  /* Save handler for inline edits */
  ['saveEdit',              v.includes('saveEdit')],
  /* Ensure exactly one Jb function exists */
  ['single Jb',             (v.match(/function Jb\(/g)||[]).length === 1],
];
let ok = true;
for (const [n,p] of checks) { console.log((p?'✓':'✗')+' '+n); if(!p) ok=false; }
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
