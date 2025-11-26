#!/bin/bash
#
# Full Regeneration Pipeline
# Runs complete draw simulation and regenerates all derived artifacts
#
# Usage: ./pipeline_full_regen.sh [num_seeds]
#

set -e  # Exit on any error

NUM_SEEDS=${1:-50000}
OUTPUT_FILE="seed_scan_fifa_official.jsonl"
BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "World Cup Draw - Full Regeneration Pipeline"
echo "=========================================="
echo "Num seeds: $NUM_SEEDS"
echo "Output: $OUTPUT_FILE"
echo ""

# Step 1: Run tests
echo "Step 1/7: Running tests..."
make test
if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Aborting pipeline."
    exit 1
fi
echo "✅ Tests passed"
echo ""

# Step 2: Backup existing data
if [ -f "$OUTPUT_FILE" ]; then
    echo "Step 2/7: Backing up existing data..."
    mkdir -p "$BACKUP_DIR"
    cp "$OUTPUT_FILE" "$BACKUP_DIR/"
    cp draw_stats.json "$BACKUP_DIR/" 2>/dev/null || true
    cp fifa_official_stats.json "$BACKUP_DIR/" 2>/dev/null || true
    cp team_city_probabilities.json "$BACKUP_DIR/" 2>/dev/null || true
    # Remove old file so script starts fresh (not append mode)
    rm "$OUTPUT_FILE"
    echo "✅ Backup created at $BACKUP_DIR (old file removed)"
else
    echo "Step 2/7: No existing data to backup"
fi
echo ""

# Step 3: Run draw simulation
echo "Step 3/7: Running draw simulation ($NUM_SEEDS seeds)..."
echo "This will take several hours..."
python scripts/seed_scan_large.py \
    --start 0 \
    --end $NUM_SEEDS \
    --workers 8 \
    --fifa-official-constraints \
    --output "$OUTPUT_FILE"

if [ $? -ne 0 ]; then
    echo "❌ Draw simulation failed!"
    exit 1
fi

# Count successes
SUCCESS_COUNT=$(grep '"success": true' "$OUTPUT_FILE" | wc -l)
echo "✅ Draw simulation complete: $SUCCESS_COUNT/$NUM_SEEDS successful draws"
echo ""

# Step 4: Validate a sample seed
echo "Step 4/7: Validating sample seed (2004)..."
python validate_seed.py 2004
echo "✅ Validation passed"
echo ""

# Step 5: Regenerate statistics
echo "Step 5/7: Regenerating draw statistics..."
python calculate_draw_statistics.py "$OUTPUT_FILE"
if [ $? -ne 0 ]; then
    echo "❌ Statistics generation failed!"
    exit 1
fi
echo "✅ Statistics regenerated"
echo ""

echo "Step 5b/7: Regenerating city probabilities..."
python calculate_all_city_probabilities.py
if [ $? -ne 0 ]; then
    echo "❌ City probabilities generation failed!"
    exit 1
fi
echo "✅ City probabilities regenerated"
echo ""

# Step 6: Regenerate screenshots
echo "Step 6/7: Regenerating screenshots..."
cd screenshots
python capture_screenshots.py
if [ $? -ne 0 ]; then
    echo "❌ Screenshot capture failed!"
    cd ..
    exit 1
fi
cd ..
echo "✅ Screenshots regenerated"
echo ""

# Step 7: Final validation
echo "Step 7/7: Running final validation..."
echo "Checking for UEFA minimum constraint violations..."
python3 << 'PYEOF'
import json

violations = 0
total_seeds = 0

with open('seed_scan_fifa_official.jsonl', 'r') as f:
    confeds = {}
    with open('teams.csv', 'r') as csv_f:
        for line in csv_f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split(',')
            if len(parts) >= 3:
                confeds[parts[0].strip()] = parts[1].strip()
    
    for line in f:
        if not line.strip():
            continue
        total_seeds += 1
        data = json.loads(line)
        
        if not data.get('success'):
            continue
            
        groups = data.get('groups', {})
        for group_name, teams in groups.items():
            uefa_count = sum(1 for t in teams if confeds.get(t, '').startswith('UEFA'))
            if uefa_count == 0:
                violations += 1
                break

print(f"Total successful seeds: {total_seeds}")
print(f"Seeds with UEFA min violations: {violations}")

if violations > 0:
    print(f"❌ {violations} seeds still have violations!")
    exit(1)
else:
    print("✅ No violations found!")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ Final validation failed!"
    exit 1
fi

# Success summary
echo ""
echo "=========================================="
echo "✅ Pipeline Complete!"
echo "=========================================="
echo "Generated files:"
echo "  - $OUTPUT_FILE"
echo "  - draw_stats.json"
echo "  - fifa_official_stats.json"
echo "  - team_city_probabilities.json"
echo "  - screenshots/city_views/*.png"
echo "  - screenshots/group_views/*.png"
echo "  - screenshots/team_views/*.png"
if [ -d "$BACKUP_DIR" ]; then
    echo ""
    echo "Backup location: $BACKUP_DIR"
fi
echo ""
echo "Success rate: $SUCCESS_COUNT / $NUM_SEEDS"
echo "=========================================="
