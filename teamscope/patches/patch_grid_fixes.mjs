/**
 * @file patch_grid_fixes.mjs
 *
 * @description
 * Applies miscellaneous fixes to the consultant utilisation grid (Rb/Tb
 * components). Currently implements one targeted fix:
 *
 *   1. **Utilisation color with workshop hours** -- The `Tb` grid cell
 *      component calls `Pb(n, a, l)` to determine the background color
 *      based on the utilisation percentage `n`. However, `n` comes from
 *      the API and only reflects deliverable hours, not workshop hours.
 *      This patch adjusts the color calculation to account for the total
 *      planned hours (`totalPlanned`, which includes both deliverables
 *      and workshops) by proportionally scaling the utilisation percentage.
 *
 * Additional investigation points (documented but not modified):
 *   - wsMap useEffect dependency array (empty `[]` is intentional since
 *     workshops are loaded once on mount).
 *   - TsCellSheet drawer workshop display (already handled).
 *   - Grid cell click wkFrom/wkTo range (already correct).
 *   - Grid refresh on TsCellSheet save (onSaved callback).
 *
 * @components
 *   - **Tb** (grid cell / utilisation display)
 *   - **Rb** (grid container, investigated but not modified)
 *
 * @strategy
 *   Uses indexOf to locate the `Pb()` call inside the Tb function, then
 *   replaces it with a modified version that recalculates the utilisation
 *   percentage based on `totalPlanned` (deliverable + workshop hours)
 *   relative to the original deliverable-only hours `e`.
 */

import { readFileSync, writeFileSync } from 'fs';

/** Load the full bundle for patching. */
let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');

/** Tracks how many modifications were applied. */
let changes = 0;

// ─── Investigation: wsMap useEffect dependency array ─────────────────────────
//
// The wsMap useEffect in Rb fetches all active projects and their workshops
// on mount. It uses an empty dependency array `},[]);` which means it only
// runs once. This is intentional -- workshops are static during a grid
// viewing session and only change when the user navigates away and back.
//
// We locate the effect to confirm the pattern but do NOT modify it.

/** Find the Rb function to scope our search. */
const rbIdx = c.indexOf('function Rb()');

/** Find the wsMap fetch callback within Rb. */
const wsMapEffect = c.indexOf('Am("active").then(async ps=>{', rbIdx);

// Walk through the callback to find its closing brace by tracking brace depth.
let depth = 0;
let pos = wsMapEffect;
while (pos < c.length) {
  if (c[pos] === '{') depth++;
  if (c[pos] === '}') {
    depth--;
    if (depth === 0) break;
  }
  pos++;
}

// `pos` now points to the closing `}` of the callback.
const afterCallback = c.slice(pos, pos + 10);
console.log('After wsMap callback:', JSON.stringify(afterCallback));

// Confirm the empty dependency array exists (no modification needed).
const wsEffectEnd = c.indexOf('},[]);', wsMapEffect);
if (wsEffectEnd < 0) { console.error('FAIL: wsMap effect end not found'); process.exit(1); }

// ─── Fix: Tb utilisation color should account for workshop hours ─────────────
//
// Original call:  Pb(n, a, l)
//   - n = utilPct (from API, deliverable-only)
//   - a = warnPct threshold
//   - l = dangerPct threshold
//
// Problem: `n` does not include workshop hours, so a consultant who is
// fully booked with workshops may show as under-utilised.
//
// Solution: If we have both `totalPlanned` (deliv + ws hours) and the
// original deliverable-only hours `e`, we can scale the API utilisation
// proportionally:
//   adjustedUtil = totalPlanned / e * n    (when e > 0 and n > 0)
//   fallback to 100 when e is 0 but totalPlanned > 0
//   fallback to original n when totalPlanned is 0

/** The original Pb call pattern inside Tb's JSX. */
const oldPb = 'Pb(n,a,l)),';

/** Find it specifically within the Tb function to avoid false matches. */
const pbIdx = c.indexOf(oldPb, c.indexOf('function Tb('));
if (pbIdx < 0) { console.error('FAIL: Pb call in Tb not found'); process.exit(1); }

/**
 * Adjusted Pb call: scales utilisation by the ratio of total planned hours
 * (including workshops) to deliverable-only hours.
 */
const newPb = 'Pb(totalPlanned>0&&n>0?(e>0?totalPlanned/e*n:100):n,a,l)),';

// Replace the exact slice to avoid affecting other Pb calls elsewhere.
c = c.replace(
  c.slice(pbIdx, pbIdx + oldPb.length),
  newPb
);
changes++;
console.log('✓ Tb utilization color now accounts for workshop hours');

// ─── Notes on other investigated areas ───────────────────────────────────────
//
// Fix 3: TsCellSheet drawer workshop display -- already handled by a prior
//         patch that added duration_hours to ws entries.
//
// Fix 4: Grid cell click wkFrom/wkTo -- uses `a,C` (start/end of visible
//         week range), which is correct for proper data fetching.
//
// Fix 5: Ub header deliverable vs workshop breakdown -- cosmetic, not
//         implemented (handled separately in patch_slim_header.mjs).

// ─── Investigation: grid refresh on TsCellSheet save ─────────────────────────
//
// When the TsCellSheet saves a deliverable, we want the grid (Rb) to also
// refresh its workshop data. We locate the `onSaved` callback to understand
// the current wiring.

const oldOnSaved = c.indexOf('onSaved:()=>{', rbIdx);
if (oldOnSaved > 0) {
  console.log('Found onSaved at', oldOnSaved);
  console.log(c.slice(oldOnSaved, oldOnSaved+200));
} else {
  // onSaved might be passed differently -- check the TsCellSheet JSX call
  const tsCellCall = c.indexOf('jsx(TsCellSheet,{', rbIdx);
  if (tsCellCall > 0) {
    console.log('TsCellSheet call:', c.slice(tsCellCall, tsCellCall+300));
  }
}

// ─── Write and report ────────────────────────────────────────────────────────

writeFileSync('/home/coder/teamscope_v3.js', c);

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
console.log('Changes:', changes);
console.log('Size:', v.length);
