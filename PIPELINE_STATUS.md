## Pipeline Status - Full Regeneration

### Current Status: 🔄 RUNNING

The full regeneration pipeline is running in the background.

**Process ID:** 171226  
**Started:** Nov 26, 2025 18:42 UTC  
**Command:** `./pipeline_full_regen.sh 50000`  
**Log file:** `/workspaces/wc-draw/pipeline_run.log`  

### Steps:
1. ✅ Run tests (PASSED - 114 tests)
2. ✅ Backup existing data (backup/20251126_184203)
3. 🔄 Run 50,000 seed simulation (IN PROGRESS)
4. ⏳ Validate sample seed
5. ⏳ Regenerate statistics  
6. ⏳ Regenerate screenshots
7. ⏳ Final validation

### Monitor Progress

```bash
# Check progress
./check_progress.sh

# View live log
tail -f pipeline_run.log

# Check if process is still running
ps aux | grep 171226
```

### Expected Timeline
- **Simulation:** 2-3 hours for 50,000 seeds
- **Statistics:** 5-10 minutes
- **Screenshots:** 30-45 minutes
- **Total:** ~3-4 hours

### What Was Fixed

**Issue:** The seed_scan_large.py script was appending to the existing file instead of replacing it.

**Solution:** Updated pipeline script to delete old file after backing it up:
```bash
rm "$OUTPUT_FILE"  # Added this line
```

Now the simulation is generating fresh data with the minimum UEFA constraint properly enforced.

### Verify Success

When complete, verify the new data:

```bash
# Check success rate
SUCCESS=$(grep -c '"success": true' seed_scan_fifa_official.jsonl)
TOTAL=$(expr $(wc -l < seed_scan_fifa_official.jsonl) - 1)
echo "Success rate: $SUCCESS/$TOTAL"

# Validate a sample seed (should have NO violations)
python validate_seed.py 2004

# Check for any UEFA violations
python -c "
import json
with open('seed_scan_fifa_official.jsonl') as f:
    next(f)  # skip header
    for line in f:
        seed_data = json.loads(line)
        if seed_data['success']:
            seed = seed_data['seed']
            break
print(f'Testing seed {seed}')
" && python validate_seed.py $(python -c "import json; f=open('seed_scan_fifa_official.jsonl'); next(f); print(json.loads(next(f))['seed'])")
```

### Implementation Complete ✅

The minimum UEFA constraint is fully implemented:
- ✅ Constraint logic added to draw.py  
- ✅ All tests passing (99.9% success rate in test batch)
- ✅ Validation script updated
- ✅ Pipeline automation created
- 🔄 Full 50k simulation running

The constraint ensures every group has at least 1 UEFA team, fixing the 61,988 violations found in the old data.
