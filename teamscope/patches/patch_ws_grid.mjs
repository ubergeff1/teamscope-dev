/**
 * @file patch_ws_grid.mjs
 *
 * Adds workshop data to the resource-planning grid by:
 *   1. Adding a `wsMap` state variable to the grid component that maps
 *      consultant_id -> week_start -> [workshop objects]
 *   2. Injecting a useEffect that fetches all active projects' workshops,
 *      indexes them by consultant and week, and stores in wsMap
 *   3. Passing the relevant workshops to each Tb (cell badge) component
 *   4. Replacing the Tb component itself to support a `workshops` prop
 *      (renders workshop pills below deliverable pills)
 *
 * Target components:
 *   - The main grid/table component (unnamed/minified) that renders the
 *     resource-planning view with consultants as rows and weeks as columns
 *   - Tb (the cell badge component) - replaced with a version that renders
 *     workshop pills alongside deliverable pills
 *
 * Search/replace strategy:
 *   Uses four targeted string replacements to inject code at precise locations
 *   in the minified bundle, plus one boundary-based slice to replace Tb entirely.
 */

import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ── Step 1: Add wsMap state ────────────────────────────────────────────────
// Targets the state declaration block in the grid component.  The search
// string matches the end of a sequence of useState calls.  We append a new
// useState for wsMap (a nested object: {consultantId: {weekStart: [workshops]}}).
c = c.replace(
  '[w,E]=b.useState(!1),[D,j]=b.useState(null),[Xc,setXc]=b.useState(null),',
  '[w,E]=b.useState(!1),[D,j]=b.useState(null),[Xc,setXc]=b.useState(null),[wsMap,setWsMap]=b.useState({}),'
);

// ── Step 2: Add workshop fetch useEffect ───────────────────────────────────
// This useEffect runs once on mount (empty deps) and builds the wsMap:
//   - Am("active") fetches all active projects
//   - hd(pr.id) fetches workshops for each project
//   - For each workshop with a date, it computes the week-start using Vr(Nd(...))
//   - Indexes by consultant ID and week-start so Tb can look up workshops
//     for any (consultant, week) cell
//
// Note: the three closing braces "}}}catch" close:
//   1. The inner for-of loop over consultants
//   2. The outer for-of loop over workshops
//   3. The try block
const wsFetch = 'b.useEffect(()=>{Am("active").then(async ps=>{const wsM={};await Promise.all(ps.map(async pr=>{try{const wsList=await hd(pr.id);for(const w of wsList){if(!w.workshop_date)continue;const wk=Vr(Nd(new Date(w.workshop_date+"T12:00:00")));for(const cc of w.consultants){if(!wsM[cc.id])wsM[cc.id]={};if(!wsM[cc.id][wk])wsM[cc.id][wk]=[];wsM[cc.id][wk].push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed"});}}}catch(ex){}}));setWsMap(wsM);}).catch(()=>{});},[]);';

// Insert the useEffect just before the "function W(" declaration, which is
// the next function inside the grid component.  The search string includes
// the preceding useEffect that fetches projects and consultants, ensuring
// we inject in the right location.
c = c.replace(
  ']),b.useEffect(()=>{Promise.all([Am(),_l()]).then(([T,L])=>{y(T),v(L)})},[]);function W(',
  `]),b.useEffect(()=>{Promise.all([Am(),_l()]).then(([T,L])=>{y(T),v(L)})},[]);${wsFetch}function W(`
);

// ── Step 3: Pass workshops to each Tb cell ─────────────────────────────────
// The existing Tb call passes planned_hours, actual_hours, utilPct, projects,
// warnPct, and dangerPct.  We add a `workshops` prop that looks up the
// current consultant (T.consultant_id) and week (L) in the wsMap.
// Falls back to an empty array if no workshops exist for that cell.
c = c.replace(
  'jsx(Tb,{planned:G.planned_hours,actual:G.actual_hours,utilPct:G.utilization_pct,projects:G.projects,warnPct:t,dangerPct:n})',
  'jsx(Tb,{planned:G.planned_hours,actual:G.actual_hours,utilPct:G.utilization_pct,projects:G.projects,warnPct:t,dangerPct:n,workshops:(wsMap[T.consultant_id]||{})[L]||[]})'
);

// ── Step 4: Replace the Tb component ───────────────────────────────────────
// Find Tb's boundaries: starts at "function Tb(" and ends just before
// "function TsCellSheet(" (the next top-level function in the bundle).
const tbStart = c.indexOf('function Tb(');
const tbEnd   = c.indexOf('\nfunction TsCellSheet(');

/**
 * New Tb component: accepts a `workshops` prop (ws) in addition to the
 * existing props.  Renders:
 *   - A header row with planned hours, actual hours, and utilization %
 *   - Deliverable pills (one per project, showing project name + hours)
 *   - Workshop pills (calendar emoji + workshop name, with reduced opacity)
 *   - An em-dash placeholder if the cell has no data
 *
 * Uses Pb() for background color based on utilization thresholds (warn/danger).
 */
const newTb = 'function Tb({planned:e,actual:t,utilPct:n,projects:r,warnPct:a,dangerPct:l,workshops:ws}){const hasWs=ws&&ws.length>0;return s.jsx("div",{className:Q("min-w-[140px] px-2 py-1.5 text-xs rounded select-none transition-colors",Pb(n,a,l)),children:(e>0||hasWs)?s.jsxs(s.Fragment,{children:[e>0&&s.jsxs("div",{className:"flex items-baseline justify-between gap-2 mb-1.5",children:[s.jsxs("span",{className:"font-semibold tabular-nums",children:[e,"h"]}),t>0&&s.jsxs("span",{className:"opacity-60 tabular-nums text-[10px]",children:[t,"h actual"]}),s.jsxs("span",{className:"opacity-60 tabular-nums",children:[n.toFixed(0),"%"]})]}),e>0&&s.jsx("div",{className:"space-y-0.5 mb-0.5",children:r.map((o,i)=>s.jsxs("div",{className:"flex items-center justify-between gap-1 px-1.5 py-0.5 rounded-full text-white text-[10px] font-medium",style:{backgroundColor:o.color},children:[s.jsx("span",{className:"truncate",style:{maxWidth:72},children:o.project_name}),s.jsxs("span",{className:"shrink-0 font-semibold",children:[o.hours,"h"]})]},i))}),hasWs&&s.jsx("div",{className:"space-y-0.5",children:ws.map((o,i)=>s.jsx("div",{className:"flex items-center gap-1 px-1.5 py-0.5 rounded text-white text-[10px] font-medium truncate",style:{backgroundColor:o.color,opacity:.85},children:"\uD83D\uDCC5 "+o.name},i))})]}):s.jsx("div",{className:"opacity-30 text-center py-1",children:"\u2014"})})}\n';

// Slice out the old Tb and insert the new one
c = c.slice(0, tbStart) + newTb + c.slice(tbEnd);

writeFileSync('/home/coder/teamscope_v3.js', c);

// ── Verify ─────────────────────────────────────────────────────────────────
// Confirm all four injection points took effect and surrounding code is intact.
const checks = [
  /* Step 1: wsMap state was injected */
  ['wsMap state',            c.includes('wsMap,setWsMap]=b.useState({})')],
  /* Step 2: workshop fetch effect builds the wsM index */
  ['workshop fetch (wsM)',   c.includes('const wsM={}')],
  /* The three closing braces pattern confirms correct nesting */
  ['three closing braces',   c.includes('}}}catch(ex){')],
  /* Step 3: workshops prop is passed to Tb using wsMap lookup */
  ['workshops passed to Tb', c.includes('workshops:(wsMap[T.consultant_id]')],
  /* Step 4: new Tb renders workshop pills conditionally */
  ['Tb renders workshops',   c.includes('hasWs=ws&&ws.length>0')],
  /* Surrounding functions must still exist */
  ['Rb still present',       c.includes('function Rb()')],
  ['TsCellSheet present',    c.includes('function TsCellSheet(')],
];
let ok = true;
for (const [name, pass] of checks) {
  console.log((pass ? '✓' : '✗') + ' ' + name);
  if (!pass) ok = false;
}
console.log('Size:', c.length);
process.exit(ok ? 0 : 1);
