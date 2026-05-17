/**
 * @file patch_grid_ws_hours.mjs
 *
 * @description
 * Enhances the consultant utilisation grid to display workshop hours
 * alongside deliverable hours. Three main changes:
 *
 *   1. **wsMap entry augmentation** -- When building the per-consultant,
 *      per-week workshop map (`wsM`), each entry now includes a numeric
 *      `hours` field parsed from `w.duration_hours`. This allows
 *      downstream components to sum workshop hours per cell.
 *
 *   2. **Tb cell component rewrite** -- The grid cell component (`Tb`) is
 *      completely rewritten to:
 *        - Merge deliverable project data with workshop data into a single
 *          `pills` array (keyed by project name).
 *        - Compute `totalPlanned = deliverableHours + workshopHours`.
 *        - Render per-project pills with combined hours and a calendar
 *          emoji for projects that have workshops in that week.
 *        - Show an overall header with total hours, actual hours, and
 *          utilisation percentage.
 *
 *   3. **TsCellSheet workshop entries** -- Adds `duration_hours` to the
 *      workshop list entries in the TsCellSheet drawer so the side panel
 *      can also display workshop hour information.
 *
 * @components
 *   - **Rb** (grid container -- wsMap build logic)
 *   - **Tb** (grid cell / utilisation display -- full rewrite)
 *   - **TsCellSheet** (deliverable side-panel drawer)
 *
 * @strategy
 *   - wsMap push: simple string replacement to add the `hours` property.
 *   - Tb rewrite: locates function boundaries (`function Tb(` to
 *     `\nfunction TsCellSheet(`) and replaces the entire function body.
 *   - TsCellSheet ws push: simple string replacement to add `duration_hours`.
 */

import { readFileSync, writeFileSync } from 'fs';

/** Load the full bundle for patching. */
let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ═══════════════════════════════════════════════════════════════════════════════
// 1. Add `hours` to wsMap entries
// ═══════════════════════════════════════════════════════════════════════════════
//
// The wsMap is built inside an effect in Rb. For each workshop, it pushes
// an entry per consultant per week. The original entry only has `name`,
// `proj_name`, and `color`. We add `hours` so Tb can compute total
// workshop hours per cell.

/** Original push call: entry without hours. */
const oldPush = 'wsM[cc.id][wk].push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed"});';

/** New push call: entry with `hours` parsed from `duration_hours`. */
const newPush = 'wsM[cc.id][wk].push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed",hours:parseFloat(w.duration_hours||0)});';

if (!c.includes(oldPush)) { console.error('FAIL: wsMap push'); process.exit(1); }
c = c.replace(oldPush, newPush);
console.log('✓ Added hours to wsMap entries');

// ═══════════════════════════════════════════════════════════════════════════════
// 2. Rewrite the Tb grid cell component
// ═══════════════════════════════════════════════════════════════════════════════
//
// The original Tb only displays deliverable hours. The new version:
//
//   a) Accepts a new `workshops` (aliased `ws`) prop with the week's
//      workshop entries for this consultant.
//
//   b) Builds a merged `pm` (project map) keyed by project name. Each
//      entry tracks: deliverable hours, workshop hours, workshop names,
//      and project color.
//
//   c) Computes `totalPlanned = deliverableHours + totalWsHrs`.
//
//   d) Renders:
//      - A header line with total hours, actual hours, and util %.
//      - Per-project "pills" (colored rounded-full bars) showing the
//        project name, combined hours, and a calendar emoji if the
//        project has workshops that week.
//      - An em-dash placeholder if no data is present.

/** Start of the old Tb function definition. */
const tbStart = c.indexOf('function Tb({planned:e,');

/** End boundary: the next function definition (TsCellSheet). */
const tbEnd = c.indexOf('\nfunction TsCellSheet(');

if (tbStart < 0 || tbEnd < 0) { console.error('FAIL: Tb bounds', tbStart, tbEnd); process.exit(1); }

/**
 * Complete replacement for the Tb component.
 *
 * Props:
 *   - planned (e): total deliverable hours for this cell
 *   - actual (t): actual logged hours
 *   - utilPct (n): utilisation percentage from the API
 *   - projects (r): array of { project_name, color, hours } for deliverables
 *   - warnPct (a): yellow threshold percentage
 *   - dangerPct (l): red threshold percentage
 *   - workshops (ws): array of { name, proj_name, color, hours } for workshops
 */
const newTb = `function Tb({planned:e,actual:t,utilPct:n,projects:r,warnPct:a,dangerPct:l,workshops:ws}){
  // Build a merged project map combining deliverable and workshop data
  const pm={};
  for(const p of(r||[])){pm[p.project_name]={name:p.project_name,color:p.color,hours:p.hours,wsHrs:0,ws:[]};}

  // Accumulate workshop hours and names into the project map
  let totalWsHrs=0;
  for(const w of(ws||[])){
    const wh=w.hours||0;
    totalWsHrs+=wh;
    if(pm[w.proj_name]){pm[w.proj_name].ws.push(w.name);pm[w.proj_name].wsHrs+=wh;}
    else pm[w.proj_name]={name:w.proj_name,color:w.color,hours:0,wsHrs:wh,ws:[w.name]};
  }

  // Convert to array for rendering
  const pills=Object.values(pm);
  const hasPills=pills.length>0;

  // Total planned = deliverable hours + workshop hours
  const totalPlanned=e+totalWsHrs;

  return s.jsx("div",{className:Q("min-w-[140px] px-2 py-1.5 text-xs rounded select-none transition-colors",Pb(n,a,l)),
    children:hasPills?s.jsxs(s.Fragment,{children:[
      /* Header: total hours, actual hours, utilisation % */
      totalPlanned>0&&s.jsxs("div",{className:"flex items-baseline justify-between gap-2 mb-1.5",children:[
        s.jsxs("span",{className:"font-semibold tabular-nums",children:[totalPlanned.toFixed(1),"h"]}),
        t>0&&s.jsxs("span",{className:"opacity-60 tabular-nums text-[10px]",children:[t,"h actual"]}),
        n>0&&s.jsxs("span",{className:"opacity-60 tabular-nums",children:[n.toFixed(0),"%"]}),
      ]}),
      /* Per-project pills with color, name, hours, and workshop indicator */
      s.jsx("div",{className:"space-y-0.5",children:pills.map((o,i)=>{
        const pillHrs=o.hours+o.wsHrs;  // Combined deliv + ws hours for this project
        return s.jsxs("div",{className:"flex items-center gap-1 px-1.5 py-0.5 rounded-full text-white text-[10px] font-medium",
          style:{backgroundColor:o.color},children:[
          s.jsx("span",{className:"truncate flex-1",style:{maxWidth:80},children:o.name}),
          pillHrs>0&&s.jsx("span",{className:"shrink-0 font-semibold",children:pillHrs.toFixed(1)+"h"}),
          o.ws.length>0&&s.jsx("span",{className:"shrink-0 opacity-80",children:"\\uD83D\\uDCC5"}),  /* Calendar emoji for ws */
        ]},i);
      })})
    ]}):s.jsx("div",{className:"opacity-30 text-center py-1",children:"\\u2014"})  /* Em-dash when empty */
  });
}
`;

// Replace the entire Tb function body (from `function Tb(` up to `\nfunction TsCellSheet(`).
c = c.slice(0, tbStart) + newTb + c.slice(tbEnd);
console.log('✓ Tb rewritten with workshop hours');

// ═══════════════════════════════════════════════════════════════════════════════
// 3. Add duration_hours to TsCellSheet workshop entries
// ═══════════════════════════════════════════════════════════════════════════════
//
// The TsCellSheet drawer shows workshops for the selected week. We add
// `duration_hours` to each entry so the drawer can display how many hours
// each workshop represents.

/** Original push in TsCellSheet's workshop list builder. */
const oldTsPush = `wsList.push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed",workshop_date:w.workshop_date,status:w.status});`;
if (c.includes(oldTsPush)) {
  /** Extended push with `duration_hours`. */
  c = c.replace(oldTsPush, `wsList.push({name:w.name,proj_name:pr.name,color:pr.color||"#7c3aed",workshop_date:w.workshop_date,status:w.status,duration_hours:w.duration_hours||0});`);
  console.log('✓ Added duration_hours to TsCellSheet ws entries');
}

// ─── Write and verify ────────────────────────────────────────────────────────

writeFileSync('/home/coder/teamscope_v3.js', c);

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  ['wsMap has hours',     v.includes('hours:parseFloat(w.duration_hours||0)')],
  ['Tb totalWsHrs',       v.includes('totalWsHrs+=wh')],
  ['Tb totalPlanned',     v.includes('totalPlanned=e+totalWsHrs')],
  ['Tb pillHrs',           v.includes('pillHrs=o.hours+o.wsHrs')],
  ['TsCellSheet intact',   v.includes('function TsCellSheet(')],
  ['Rb intact',            v.includes('function Rb(')],
];
let ok = true;
for (const [n, p] of checks) {
  console.log((p ? '✓' : '✗') + ' ' + n);
  if (!p) ok = false;
}
console.log('Size:', v.length);
process.exit(ok ? 0 : 1);
