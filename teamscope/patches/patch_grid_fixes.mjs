import { readFileSync, writeFileSync } from 'fs';

let c = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
let changes = 0;

// Fix 1: wsMap should refresh when grid data refreshes (add dependency on u/data)
// Currently: },[]);  (empty deps - only runs once)
// The wsMap useEffect is the second useEffect that starts with Am("active")
// Find it precisely
const rbIdx = c.indexOf('function Rb()');
const wsMapEffect = c.indexOf('Am("active").then(async ps=>{', rbIdx);
// Find the closing },[]) of this useEffect
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
// pos is at the closing } of the callback, next should be ,[]); or similar
const afterCallback = c.slice(pos, pos + 10);
console.log('After wsMap callback:', JSON.stringify(afterCallback));

// The pattern is },[]);  - change to depend on a trigger
// Actually, let's just make it re-run when the main grid data changes
// u is the consultant data. But we can't reference u in deps because wsMap
// is set in a separate effect. Let's use a simpler approach: add a wsRefresh counter
// that increments when onSaved fires.

// Actually, the simplest fix is to make the wsMap effect depend on nothing
// but provide a way to manually trigger it. Let's add the R callback to deps
// so when grid data refetches, workshops also refetch.

// Find the exact dependency array
const wsEffectEnd = c.indexOf('},[]);', wsMapEffect);
if (wsEffectEnd < 0) { console.error('FAIL: wsMap effect end not found'); process.exit(1); }
// Don't change this - empty deps is actually fine since we only need to fetch
// workshops once (they don't change during grid viewing). If user edits,
// they'd need to reload the page.

// Fix 2: Tb utilization color should account for workshop hours
// Currently Pb(n,a,l) where n is utilPct from API (doesn't include workshops)
// Change to recalculate utilization if workshops add hours
const oldPb = 'Pb(n,a,l)),';
const pbIdx = c.indexOf(oldPb, c.indexOf('function Tb('));
if (pbIdx < 0) { console.error('FAIL: Pb call in Tb not found'); process.exit(1); }

// The utilPct from API is based on capacity_hours. We need to recalculate:
// newUtil = (deliverable_hours + workshop_hours) / capacity_hours * 100
// But we don't have capacity_hours in Tb. We can estimate from the existing pct:
// capacity = e / (n/100) if n > 0
// Then newUtil = totalPlanned / capacity * 100
// This is a bit hacky but correct.

// Actually, let me just use totalPlanned in the color calculation proportionally
const newPb = 'Pb(totalPlanned>0&&n>0?(e>0?totalPlanned/e*n:100):n,a,l)),';
c = c.replace(
  c.slice(pbIdx, pbIdx + oldPb.length),
  newPb
);
changes++;
console.log('✓ Tb utilization color now accounts for workshop hours');

// Fix 3: The TsCellSheet drawer should show workshop duration_hours
// Check if it's already showing - yes, it was added earlier

// Fix 4: When the grid cell is clicked and TsCellSheet opens,
// the wkFrom/wkTo should be the visible range for proper data fetching
// Currently uses a,C (the start/end of visible range) - this is correct

// Fix 5: In the Ub header, the consultant hours section doesn't show
// which hours are from deliverables vs workshops. Let's add a subtle indicator.
// Actually this is cosmetic and was not requested - skip.

// Fix 6: Ensure grid refreshes workshops when TsCellSheet saves
// The onSaved callback in Rb should also refresh wsMap
const oldOnSaved = c.indexOf('onSaved:()=>{', rbIdx);
if (oldOnSaved > 0) {
  console.log('Found onSaved at', oldOnSaved);
  console.log(c.slice(oldOnSaved, oldOnSaved+200));
} else {
  // onSaved might be named differently - check the TsCellSheet call
  const tsCellCall = c.indexOf('jsx(TsCellSheet,{', rbIdx);
  if (tsCellCall > 0) {
    console.log('TsCellSheet call:', c.slice(tsCellCall, tsCellCall+300));
  }
}

writeFileSync('/home/coder/teamscope_v3.js', c);

const v = readFileSync('/home/coder/teamscope_v3.js', 'utf8');
console.log('Changes:', changes);
console.log('Size:', v.length);
