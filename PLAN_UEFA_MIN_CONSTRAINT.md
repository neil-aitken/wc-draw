# Plan: Implement UEFA Minimum 1 Per Group Constraint

## Issue
FIFA official rules require **at least one UEFA team per group**. Currently only enforcing:
- Max 2 UEFA teams per group ✓
- Max 1 non-UEFA confederation per group ✓
- **Missing: Min 1 UEFA team per group** ❌

## Impact Analysis

### Current State
- 16 UEFA teams total (12 direct + 4 playoff paths)
- 12 groups
- Theoretically possible for a group to have 0 UEFA teams (though rare)

### Validation Check
Need to verify if any seeds in `seed_scan_fifa_official.jsonl` violate this rule.

## Implementation Plan

### Phase 1: Validation & Testing (30 min)
1. **Check existing data** - Scan all 50,000 seeds for violations
2. **Create validation script** - Add min UEFA check to `validate_seed.py`
3. **Write unit tests** - Add test cases in `tests/test_uefa_constraints.py`
   - Test: Group with 0 UEFA teams should fail
   - Test: All groups with >= 1 UEFA team should pass
   - Test: Integration with existing max 2 UEFA constraint

### Phase 2: Core Logic Update (45 min)
4. **Update `wc_draw/draw.py`**
   - Add `_check_min_uefa_per_group()` function
   - Integrate into `_can_place_team()` logic
   - Handle during Pot 2/3/4 placement
   - Consider lookahead: if placing non-UEFA would leave no UEFA slots, block it
5. **Update constraint documentation** in code comments

### Phase 3: Re-simulation (2-3 hours)
6. **Run draw simulation**
   ```bash
   python -m wc_draw.cli draw --seed-scan 0 50000 \
     --fifa-official-constraints \
     --output seed_scan_fifa_official_v2.jsonl
   ```
7. **Compare success rates** - Check if constraint significantly reduces valid draws

### Phase 4: Statistics Regeneration (30 min)
8. **Regenerate all statistics**
   ```bash
   python calculate_draw_statistics.py seed_scan_fifa_official_v2.jsonl
   python calculate_all_city_probabilities.py
   ```
9. **Verify changes** - Compare old vs new statistics

### Phase 5: Screenshots & Artifacts (45 min)
10. **Regenerate screenshots**
    ```bash
    cd screenshots && python capture_screenshots.py
    ```
11. **Backup old data** - Move old JSONL and stats to `backup/` folder
12. **Update documentation** - Note constraint addition in README.md

### Phase 6: Pipeline Automation (1 hour)
13. **Create `pipeline_full_regen.sh`** script to automate:
    - Run tests
    - Run draw simulation
    - Regenerate statistics
    - Regenerate screenshots
    - Create backup
    - Validation checks

## Files to Modify

### Core Logic
- `wc_draw/draw.py` - Add min UEFA constraint check
- `wc_draw/draw.py` - Update `_can_place_team()` lookahead logic

### Testing
- `tests/test_uefa_constraints.py` - New test file or extend existing
- `tests/test_draw.py` - Add integration tests

### Scripts
- `validate_seed.py` - Add min UEFA check
- `pipeline_full_regen.sh` - **NEW** automation script

### Documentation
- `README.md` - Document new constraint
- `CONTEXT.md` - Update constraint list

## Risk Assessment

### Low Risk
- Adding constraint is backwards compatible (only makes draws more restrictive)
- Existing valid draws may become invalid, but that's expected

### Medium Risk
- Success rate may drop if constraint is very restrictive
- May need fallback strategy adjustments

### Mitigation
- Run small test batch (1000 seeds) first to check success rate
- Keep old JSONL file as backup
- Can revert if constraint causes major issues

## Success Criteria
- [ ] All tests pass
- [ ] No seeds in new JSONL violate min UEFA rule
- [ ] Success rate remains > 90%
- [ ] Statistics reflect new constraint
- [ ] Screenshots regenerated with new data
- [ ] Pipeline script works end-to-end

## Estimated Timeline
- **Total: 5-6 hours**
- Can be done in stages with validation points

## Command Sequence (Quick Reference)
```bash
# 1. Add validation check to existing seeds
python validate_all_seeds.py  # Create this script

# 2. Run tests
make test

# 3. Run small batch test
python -m wc_draw.cli draw --seed-scan 0 1000 --fifa-official-constraints

# 4. Run full simulation
python -m wc_draw.cli draw --seed-scan 0 50000 --fifa-official-constraints \
  --output seed_scan_fifa_official_v2.jsonl

# 5. Regenerate stats
python calculate_draw_statistics.py seed_scan_fifa_official_v2.jsonl
python calculate_all_city_probabilities.py

# 6. Regenerate screenshots
cd screenshots && python capture_screenshots.py

# 7. Or use pipeline script
./pipeline_full_regen.sh
```

## Next Steps
1. ✅ Create this plan document
2. ⏭️ Validate existing seeds for violations
3. ⏭️ Implement constraint in draw logic
4. ⏭️ Write tests
5. ⏭️ Run small batch test
6. ⏭️ Run full simulation
7. ⏭️ Regenerate artifacts
8. ⏭️ Create pipeline script
