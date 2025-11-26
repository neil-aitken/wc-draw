#!/bin/bash
#
# Check progress of seed scan
#

OUTPUT_FILE="seed_scan_fifa_official.jsonl"

if [ ! -f "$OUTPUT_FILE" ]; then
    echo "No output file found yet. Simulation may not have started."
    exit 0
fi

TOTAL=$(wc -l < "$OUTPUT_FILE")
SUCCESS=$(grep -c '"success": true' "$OUTPUT_FILE" || echo 0)
FAILED=$(grep -c '"success": false' "$OUTPUT_FILE" || echo 0)

SUCCESS_RATE=0
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.2f\", ($SUCCESS / $TOTAL) * 100}")
fi

echo "=========================================="
echo "Seed Scan Progress"
echo "=========================================="
echo "Seeds processed: $TOTAL"
echo "Successful:      $SUCCESS"
echo "Failed:          $FAILED"
echo "Success rate:    ${SUCCESS_RATE}%"
echo "=========================================="

# Show last few lines of file to see most recent seed
echo ""
echo "Recent seeds:"
tail -n 5 "$OUTPUT_FILE" | jq -r '"Seed \(.seed): \(if .success then "✓" else "✗" end)"' 2>/dev/null || tail -n 5 "$OUTPUT_FILE"
