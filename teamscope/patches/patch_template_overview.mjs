/**
 * @file patch_template_overview.mjs
 *
 * Replaces the ww (template overview card) component with an enhanced version
 * that adds:
 *   - Workshop template awareness: shows workshop count and workshop pills
 *   - A stats bar with deliverable count, workshop count, and planned hours
 *     (combining deliverable hours and workshop duration hours)
 *   - Deliverable type breakdown (e.g., "3x control_family, 2x narrative")
 *   - Workshop template pills with calendar emoji and optional duration
 *
 * Target component: ww (the collapsible card rendered for each template in
 * the template list view).
 *
 * Search/replace strategy:
 *   1. Locates the ww function by searching for "function ww({template:".
 *   2. Uses brace-counting to find the end of the function body (matching
 *      the outermost opening and closing braces).
 *   3. Slices out the old ww and inserts the new version.
 *   4. Verifies the new stat helper and workshop-related code are present.
 */

import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

// ── Find the ww function boundaries ────────────────────────────────────────
// Search for the exact declaration string used by the bundler.
const wwStart = c.indexOf('function ww({template:');
if (wwStart < 0) { console.error('Cannot find ww'); process.exit(1); }

/**
 * Find the end of ww by brace-counting.  We start at wwStart and track
 * depth: increment on '{', decrement on '}'.  When depth returns to 0,
 * we've found the matching closing brace of the function body.
 */
let depth = 0, i = wwStart;
while (i < c.length) {
  if (c[i] === '{') depth++;
  if (c[i] === '}') { depth--; if (depth === 0) { i++; break; } }
  i++;
}
const wwEnd = i;
console.log('ww found at', wwStart, '-', wwEnd, 'len=', wwEnd - wwStart);

/**
 * New ww component.
 *
 * Props:
 *   - template (e)            : the template object with deliverable_templates
 *                                and workshop_templates arrays
 *   - frameworks (t)          : all frameworks (for badge rendering)
 *   - expanded (n)            : whether the card body is expanded
 *   - onToggle (r)            : callback to toggle expanded state
 *   - onEdit (a)              : callback to edit the template
 *   - onDelete (l)            : callback to delete the template
 *   - onAddDeliverable (o)    : callback to add a deliverable template
 *   - onEditDeliverable (i)   : callback to edit a deliverable template
 *   - onDeleteDeliverable (u) : callback to delete a deliverable template
 *
 * Computed values:
 *   - m         : count of deliverable templates
 *   - wsCount   : count of workshop templates
 *   - totalHrs  : sum of (flat_hours + qa_hours) across all deliverable templates
 *   - wsHrs     : sum of duration_hours across all workshop templates
 *   - totalPlanned : totalHrs + wsHrs (combined planned hours)
 *   - byType    : object mapping deliverable_type -> count (for type breakdown)
 *
 * The stat() helper renders a centered stat card with a large value, label,
 * and optional subtitle.
 *
 * External dependencies:
 *   - Du : chevron-down icon (expanded state)
 *   - El : chevron-right icon (collapsed state)
 *   - On : pencil/edit icon
 *   - Me : trash/delete icon
 */
const newWw = `function ww({template:e,frameworks:t,expanded:n,onToggle:r,onEdit:a,onDelete:l,onAddDeliverable:o,onEditDeliverable:i,onDeleteDeliverable:u}){
  /* Look up the framework and impact level for badge rendering */
  const c=t.find(x=>x.id===e.framework_id),p=c==null?void 0:c.impact_levels.find(x=>x.id===e.impact_level_id);
  /* Count deliverables and workshops */
  const m=e.deliverable_templates.length;
  const wsCount=(e.workshop_templates||[]).length;
  /* Sum deliverable hours (flat + QA) */
  const totalHrs=e.deliverable_templates.reduce((acc,d)=>acc+(d.default_flat_hours||0)+(d.default_qa_hours||0),0);
  /* Sum workshop duration hours */
  const wsHrs=(e.workshop_templates||[]).reduce((acc,w)=>acc+(w.duration_hours||0),0);
  /* Combined planned hours for the stats bar */
  const totalPlanned=totalHrs+wsHrs;
  /**
   * Build a type breakdown map: e.g., { control_family: 3, narrative: 2 }
   * Used to render type pills in the expanded card body.
   */
  const byType={};
  e.deliverable_templates.forEach(d=>{const tp=d.deliverable_type||'other';byType[tp]=(byType[tp]||0)+1;});

  /**
   * stat: helper that renders a single stat card with centered layout.
   * @param {string} label - Stat label (e.g., "Deliverables")
   * @param {string|number} value - The main stat value
   * @param {string} [sub] - Optional subtitle line
   */
  const stat=(label,value,sub)=>s.jsxs('div',{className:'flex flex-col items-center px-4 py-2',children:[
    s.jsx('div',{className:'text-lg font-bold text-gray-900 dark:text-gray-100 tabular-nums',children:value}),
    s.jsx('div',{className:'text-[11px] text-gray-500 font-medium',children:label}),
    sub&&s.jsx('div',{className:'text-[10px] text-gray-400 mt-0.5',children:sub}),
  ]});

  return s.jsxs("div",{className:"bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden",children:[
    /* Card header: expand/collapse toggle, template name, framework/impact badges, action buttons */
    s.jsxs("div",{className:"flex items-center gap-3 px-4 py-3",children:[
      /* Toggle button: switches between chevron-down (Du) and chevron-right (El) */
      s.jsx("button",{onClick:r,className:"text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors",children:n?s.jsx(Du,{size:16}):s.jsx(El,{size:16})}),
      s.jsxs("div",{className:"flex-1 min-w-0",children:[
        s.jsxs("div",{className:"flex items-center gap-2 flex-wrap",children:[
          s.jsx("h3",{className:"font-semibold text-gray-900 dark:text-gray-100 text-sm",children:e.name}),
          /* Framework badge (if a framework is assigned) */
          c&&s.jsx("span",{className:"px-1.5 py-0.5 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400 text-[10px] font-medium rounded",children:c.name}),
          /* Impact level badge (if an impact level is assigned) */
          p&&s.jsx("span",{className:"px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-[10px] rounded",children:p.name}),
          /* Deliverable count badge */
          s.jsxs("span",{className:"px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 text-[10px] rounded",children:[m," deliverable",m!==1?"s":""]})
        ]}),
        /* Template description (truncated) */
        e.description&&s.jsx("p",{className:"text-xs text-gray-500 mt-0.5 truncate",children:e.description})
      ]}),
      /* Edit and Delete action buttons */
      s.jsxs("div",{className:"flex gap-1 shrink-0",children:[
        s.jsx("button",{onClick:a,className:"p-1.5 text-gray-400 hover:text-brand-600 transition-colors rounded hover:bg-gray-100 dark:hover:bg-gray-800",children:s.jsx(On,{size:14})}),
        s.jsx("button",{onClick:l,className:"p-1.5 text-gray-400 hover:text-red-600 transition-colors rounded hover:bg-gray-100 dark:hover:bg-gray-800",children:s.jsx(Me,{size:14})})
      ]})
    ]}),
    /* Expanded card body: stats bar, type breakdown, and workshop pills */
    n&&s.jsx("div",{className:"border-t border-gray-100 dark:border-gray-800 px-4 py-3",children:
      s.jsxs("div",{className:"space-y-3",children:[
        /* Stats bar: Deliverables count, Workshops count, Planned Hours total */
        s.jsxs("div",{className:"flex items-center justify-around bg-gray-50 dark:bg-gray-800/50 rounded-lg py-2",children:[
          stat('Deliverables',m),
          stat('Workshops',wsCount),
          /* Show breakdown subtitle when both deliverable and workshop hours exist */
          stat('Planned Hours',totalPlanned>0?totalPlanned+'h':'\\u2014',totalHrs>0&&wsHrs>0?totalHrs+'h deliv + '+wsHrs+'h ws':null),
        ]}),
        /* Deliverable type breakdown pills (e.g., "3x control_family") */
        Object.keys(byType).length>0&&s.jsxs("div",{className:"flex flex-wrap gap-1.5",children:[
          s.jsx("span",{className:"text-[11px] text-gray-400 font-medium mr-1 self-center",children:"Types:"}),
          ...Object.entries(byType).map(([tp,cnt])=>s.jsxs("span",{className:"px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-[11px] text-gray-600 dark:text-gray-400 font-medium",children:[cnt,"\\xd7 ",tp.replace(/_/g,' ')]},tp)),
        ]}),
        /* Workshop template pills with calendar emoji and optional duration */
        (e.workshop_templates||[]).length>0&&s.jsxs("div",{className:"flex flex-wrap gap-1.5",children:[
          s.jsx("span",{className:"text-[11px] text-gray-400 font-medium mr-1 self-center",children:"Workshops:"}),
          ...(e.workshop_templates||[]).map((w,wi)=>s.jsxs("span",{className:"px-2 py-0.5 rounded-full text-[11px] font-medium",style:{backgroundColor:'#f5f3ff',color:'#7c3aed'},children:["\\uD83D\\uDCC5 ",w.name,w.duration_hours?' ('+w.duration_hours+'h)':'']},wi)),
        ]}),
      ]})
    }),
  ]});
}`;

// ── Apply replacement ──────────────────────────────────────────────────────
// Slice out the old ww (from wwStart to wwEnd) and insert the new version.
c = c.slice(0, wwStart) + newWw + c.slice(wwEnd);
writeFileSync('/home/coder/teamscope_v3.js', c);

// ── Verify ─────────────────────────────────────────────────────────────────
const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
const checks = [
  /* Core function exists */
  ['ww function exists',     v.includes('function ww({template:')],
  /* stat() helper is used for the stats bar */
  ['stat helper',            v.includes("stat('Deliverables'")],
  /* Workshop count stat */
  ['workshop count',         v.includes("stat('Workshops',wsCount)")],
  /* Planned hours stat with combined total */
  ['planned hours',          v.includes("stat('Planned Hours'")],
  /* Type breakdown pills use Object.entries */
  ['byType breakdown',       v.includes('Object.entries(byType)')],
  /* Workshop pills reference workshop_templates */
  ['workshop pills',         v.includes('workshop_templates||[]')],
  /* Ensure exactly one ww function exists */
  ['ww count=1',             (v.match(/function ww\(/g)||[]).length===1],
  /* Nw (the next component) must still exist */
  ['Nw present',             v.includes('function Nw(')],
];
let ok=true;
for(const[n,p] of checks){console.log((p?'\\u2713':'\\u2717')+' '+n);if(!p)ok=false;}
console.log('Size:',v.length);
process.exit(ok?0:1);
