/**
 * @file patch_tb_rollup.mjs
 *
 * Replaces the Tb (table-cell badge) component so that deliverable pills
 * and workshop pills are merged into unified per-project pills.
 *
 * Before this patch, Tb rendered two separate sections:
 *   1. Deliverable pills (one per project, showing project name + hours)
 *   2. Workshop pills (separate, with a calendar emoji)
 *
 * After this patch, Tb merges both into a single list of "pills" keyed by
 * project name.  Each pill shows the project name, hours (if any), and a
 * calendar emoji (if the project has workshops that week).
 *
 * Target component: Tb (the badge/pill renderer inside each grid cell of the
 * resource-planning table).
 *
 * Search/replace strategy:
 *   1. Defines the exact old Tb function source as a search string (oldTb).
 *   2. Defines the new merged-pill version (newTb).
 *   3. Uses string .replace() for a direct swap.
 *   4. Verifies the merge-map logic and pill rendering are present.
 */

import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

/**
 * oldTb: the exact source of the previous Tb component.
 * This string must match character-for-character in the bundle.
 * Key identifying features:
 *   - It renders deliverable pills and workshop pills as separate sections
 *   - Uses `hasWs=ws&&ws.length>0` to conditionally render workshop section
 *   - Workshop pills use opacity:0.85 and a calendar emoji prefix
 */
const oldTb = `function Tb({planned:e,actual:t,utilPct:n,projects:r,warnPct:a,dangerPct:l,workshops:ws}){const hasWs=ws&&ws.length>0;return s.jsx("div",{className:Q("min-w-[140px] px-2 py-1.5 text-xs rounded select-none transition-colors",Pb(n,a,l)),children:(e>0||hasWs)?s.jsxs(s.Fragment,{children:[e>0&&s.jsxs("div",{className:"flex items-baseline justify-between gap-2 mb-1.5",children:[s.jsxs("span",{className:"font-semibold tabular-nums",children:[e,"h"]}),t>0&&s.jsxs("span",{className:"opacity-60 tabular-nums text-[10px]",children:[t,"h actual"]}),s.jsxs("span",{className:"opacity-60 tabular-nums",children:[n.toFixed(0),"%"]})]}),e>0&&s.jsx("div",{className:"space-y-0.5 mb-0.5",children:r.map((o,i)=>s.jsxs("div",{className:"flex items-center justify-between gap-1 px-1.5 py-0.5 rounded-full text-white text-[10px] font-medium",style:{backgroundColor:o.color},children:[s.jsx("span",{className:"truncate",style:{maxWidth:72},children:o.project_name}),s.jsxs("span",{className:"shrink-0 font-semibold",children:[o.hours,"h"]})]},i))}),hasWs&&s.jsx("div",{className:"space-y-0.5",children:ws.map((o,i)=>s.jsx("div",{className:"flex items-center gap-1 px-1.5 py-0.5 rounded text-white text-[10px] font-medium truncate",style:{backgroundColor:o.color,opacity:.85},children:"\uD83D\uDCC5 "+o.name},i))})]}):s.jsx("div",{className:"opacity-30 text-center py-1",children:"\u2014"})})}\n`;

/**
 * newTb: the merged-pill version of Tb.
 *
 * Instead of rendering deliverables and workshops separately, it:
 *   1. Builds a project map (pm) keyed by project name
 *   2. For each deliverable project, stores {name, color, hours, ws:[]}
 *   3. For each workshop, either appends to an existing project entry
 *      or creates a new one with hours:0
 *   4. Renders a single list of pills, each showing:
 *      - Project name (truncated to 80px)
 *      - Hours badge (if hours > 0)
 *      - Calendar emoji (if the project has workshops)
 */
const newTb = `function Tb({planned:e,actual:t,utilPct:n,projects:r,warnPct:a,dangerPct:l,workshops:ws}){const pm={};for(const p of(r||[])){pm[p.project_name]={name:p.project_name,color:p.color,hours:p.hours,ws:[]};}for(const w of(ws||[])){if(pm[w.proj_name])pm[w.proj_name].ws.push(w.name);else pm[w.proj_name]={name:w.proj_name,color:w.color,hours:0,ws:[w.name]};}const pills=Object.values(pm);const hasPills=pills.length>0;return s.jsx("div",{className:Q("min-w-[140px] px-2 py-1.5 text-xs rounded select-none transition-colors",Pb(n,a,l)),children:hasPills?s.jsxs(s.Fragment,{children:[e>0&&s.jsxs("div",{className:"flex items-baseline justify-between gap-2 mb-1.5",children:[s.jsxs("span",{className:"font-semibold tabular-nums",children:[e,"h"]}),t>0&&s.jsxs("span",{className:"opacity-60 tabular-nums text-[10px]",children:[t,"h actual"]}),s.jsxs("span",{className:"opacity-60 tabular-nums",children:[n.toFixed(0),"%"]})]}),s.jsx("div",{className:"space-y-0.5",children:pills.map((o,i)=>s.jsxs("div",{className:"flex items-center gap-1 px-1.5 py-0.5 rounded-full text-white text-[10px] font-medium",style:{backgroundColor:o.color},children:[s.jsx("span",{className:"truncate flex-1",style:{maxWidth:80},children:o.name}),o.hours>0&&s.jsx("span",{className:"shrink-0 font-semibold",children:o.hours+"h"}),o.ws.length>0&&s.jsx("span",{className:"shrink-0 opacity-80",children:"\uD83D\uDCC5"})]},i))})]}):s.jsx("div",{className:"opacity-30 text-center py-1",children:"\u2014"})})}\n`;

// ── Apply replacement ──────────────────────────────────────────────────────
// Direct string replacement - oldTb must match exactly in the bundle.
if (!c.includes(oldTb)) { console.error('oldTb not found'); process.exit(1); }
c = c.replace(oldTb, newTb);
writeFileSync('/home/coder/teamscope_v3.js', c);

// ── Verify ─────────────────────────────────────────────────────────────────
// Confirm the new merge-map approach is in place and surrounding code intact.
const checks = [
  /* The project merge-map that combines deliverables + workshops */
  ['merged pm map',        c.includes('const pm={};')],
  /* Single unified pill rendering loop */
  ['single pill loop',     c.includes('pills.map((o,i)')],
  /* Calendar emoji shown when a project has workshops */
  ['workshop emoji pill',  c.includes('o.ws.length>0')],
  /* Hours badge conditionally shown */
  ['hours in merged pill', c.includes('o.hours>0&&')],
  /* Rb must still exist (next function boundary after Tb) */
  ['Rb present',           c.includes('function Rb()')],
];
let ok = true;
for (const [n,p] of checks) { console.log((p?'✓':'✗')+' '+n); if(!p) ok=false; }
console.log('Size:', c.length);
process.exit(ok ? 0 : 1);
