# Implementation Summary: Minimum UEFA Constraint

## Status: PARTIALLY COMPLETE

### What We've Done ✅

1. **Created Implementation Plan** (`PLAN_UEFA_MIN_CONSTRAINT.md`)
   - Comprehensive 6-phase plan
   - Timeline estimates
   - Risk assessment

2. **Created Pipeline Script** (`pipeline_full_regen.sh`)
   - Automated end-to-end regeneration
   - Backups old data
   - Runs tests, simulation, stats, screenshots
   - Validates final output

3. **Updated Validation** (`validate_seed.py`)
   - Added minimum UEFA check (min 1 per group)
   - Updated success criteria display
   - Tested on seed 2000 - correctly identifies violations

4. **Created Test Suite** (`tests/test_min_uefa_constraint.py`)
   - Unit tests for constraint validation
   - Integration test for full draw
   - Tests UEFA playoff counting

5. **Added Core Constraint Logic** (`wc_draw/draw.py`)
   - Added `_check_min_uefa_constraint()` function
   - Implements lookahead logic to prevent blocking UEFA placement
   - Integrated into `eligible_for_group()` function
   - Added `remaining_uefa` calculation in main loop

6. **Validated Existing Data**
   - Scanned all 50,000 seeds
   - Found 61,988 violations (~62k groups without UEFA)
   - This constraint will significantly impact draw success rate

### What Remains ⏳

1. **Complete draw.py updates**
   - Need to update `compute_eligible()` function calls
   - Need to pass `remaining_uefa` to backtracking solver
   - Consider simplifying by making remaining_uefa optional with smart default

2. **Run Tests**
   - Execute: `make test`
   - Fix any failing tests
   - Ensure new constraint works correctly

3. **Small Batch Test** (RECOMMENDED BEFORE FULL RUN)
   - Run 1,000 seeds to check success rate
   - Command: `python -m wc_draw.cli draw --seed-scan 0 1000 --fifa-official-constraints --output test_1000.jsonl`
   - Validate results
   - Adjust constraint logic if needed

4. **Full Simulation**
   - Run 50,000 seeds (2-3 hours)
   - Use pipeline script or manual command

5. **Regenerate Artifacts**
   - Statistics files
   - Screenshots (all 3 viewers)

### Current Code State

**draw.py Changes:**
- ✅ Added `_check_min_uefa_constraint()` helper function
- ✅ Updated `eligible_for_group()` signature to accept `remaining_uefa`
- ✅ Added `remaining_uefa` calculation in main placement loop
- ✅ Updated main eligible_for_group calls in placement logic
- ⏸️ Need to update `compute_eligible()` function
- ⏸️ Need to update backtracking solver calls

**Constraint Logic:**
```python
def _check_min_uefa_constraint(
    team: Team, grp_teams: List[Team], remaining_uefa: int, remaining_slots: int
) -> bool:
    # If placing a UEFA team, always OK
    if team.confederation.startswith("UEFA") or "|" in team.confederation:
        return True
    
    # Check if group already has a UEFA team
    has_uefa = any(t.confederation.startswith("UEFA") or "|" in (t.confederation or "") 
                   for t in grp_teams)
    if has_uefa:
        return True
    
    # Group doesn't have UEFA yet - apply restrictions
    if team.pot == 4:  # Last pot
        return False  # Can't place non-UEFA in pot 4 if no UEFA yet
    
    if remaining_slots <= 1:  # Would be last slot
        return False
    
    return True  # Allow, assuming UEFA will come later
```

### Next Immediate Steps

**Option A: Complete Implementation (Recommended)**
1. Simplify `remaining_uefa` handling - make it truly optional
2. Update `compute_eligible()` to calculate remaining_uefa
3. Run `make test`
4. Run small batch test (1000 seeds)
5. If success rate > 80%, proceed to full run

**Option B: Test Current State**
1. Run `make test` to see what breaks
2. Fix only critical issues
3. Run small batch immediately
4. Assess if constraint is too restrictive

**Option C: Simplify Constraint (If needed)**
1. Only enforce in pot 4 (strict)
2. Loosen lookahead logic
3. Accept some risk of violations

### Key Decisions Needed

1. **Success Rate Tolerance**: What minimum success rate is acceptable?
   - Current: ~100% (no min UEFA constraint)
   - Expected: 60-90% with constraint?
   - If too low, may need to adjust logic

2. **Constraint Strictness**: How aggressive should lookahead be?
   - Current: Block non-UEFA in pot 2/3 if group might fill without UEFA
   - Could relax: Only enforce in pot 4
   - Trade-off: Strictness vs. success rate

3. **Fallback Strategy**: If constraint causes too many failures?
   - Option: Allow constraint violations in fallback mode
   - Option: Adjust pot ordering to prioritize UEFA placement
   - Option: Pre-distribute UEFA teams to ensure coverage

### Files Modified

- `PLAN_UEFA_MIN_CONSTRAINT.md` - New
- `pipeline_full_regen.sh` - New (executable)
- `validate_seed.py` - Modified (min UEFA check)
- `tests/test_min_uefa_constraint.py` - New
- `wc_draw/draw.py` - Modified (constraint logic, partially complete)

### Commands Ready to Execute

```bash
# Test current state
make test

# Small batch test
python -m wc_draw.cli draw --seed-scan 0 1000 \\
  --fifa-official-constraints --output test_1000.jsonl

# Validate sample
python validate_seed.py 2004 test_1000.jsonl

# Full pipeline (when ready)
./pipeline_full_regen.sh 50000
```

### Estimated Completion Time

- Finish draw.py updates: 30 min
- Test and debug: 30-60 min
- Small batch test: 5-10 min
- Full simulation: 2-3 hours
- Total remaining: ~3-4 hours

## Recommendation

**PAUSE and decide on approach:**
1. Complete Option A for robust implementation, or
2. Test current state with Option B to assess constraint impact, or
3. Simplify with Option C if constraint proves too restrictive

The constraint is significant (62k violations in current data), so understanding its impact before full run is critical.
