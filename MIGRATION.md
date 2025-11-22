# Migration Guide

This guide helps you migrate an existing `teams.csv` file to the new format that supports additional features.

## What's New

The updated `teams.csv` format adds two new fields:
1. **fifa_ranking**: FIFA ranking number (integer)
2. **uefa_group_winner**: Boolean indicating UEFA qualifying group winners

These fields enable:
- Dynamic pot assignment based on FIFA rankings
- UEFA group winner separation constraint

## Migration Steps

### 1. Backup Your Current File

```bash
cp teams.csv teams.csv.backup
```

### 2. Add New Columns

Add `fifa_ranking` and `uefa_group_winner` columns to your CSV header:

**Old format:**
```csv
name,confederation,pot,host,fixed_group,allowed_confederations
```

**New format:**
```csv
name,confederation,pot,host,fixed_group,allowed_confederations,fifa_ranking,uefa_group_winner
```

### 3. Populate FIFA Rankings

Add FIFA ranking numbers for all teams. For the 2026 World Cup qualifiers:

**Pot 1 teams** (ranks 1-12):
- Spain: 1
- England: 4
- France: 2
- Argentina: 3
- Brazil: 5
- Belgium: 6
- Netherlands: 7
- Portugal: 8
- Germany: 11
- Mexico: 13
- United States: 14
- Canada: 40

**Pot 2 teams** (ranks 13-24, excluding hosts):
- Croatia: 10
- Uruguay: 15
- Switzerland: 17
- Japan: 18
- Senegal: 19
- Iran: 20
- South Korea: 22
- Denmark: 23 (example)
- etc.

**Pot 3 teams** (ranks 25-36):
- Norway: 44
- Scotland: 39
- etc.

**Pot 4 teams** (ranks 37-48):
- Cape Verde: 73
- Curacao: 79
- etc.

**Playoff paths**: Leave empty unless using playoff seeding feature. For playoff seeding:
- UEFA Playoff A: 12 (Italy's ranking)
- UEFA Playoff B: 28 (Ukraine's ranking)
- UEFA Playoff C: 25 (Slovakia's ranking)
- UEFA Playoff D: 21 (Czechia's ranking)

### 4. Mark UEFA Group Winners

Set `uefa_group_winner=true` for the 12 UEFA teams that won their qualifying groups:

- Austria
- Belgium
- Croatia
- England
- France
- Germany
- Netherlands
- Norway
- Portugal
- Scotland
- Spain
- Switzerland

All other teams should have `uefa_group_winner=false`.

**Important**: Playoff paths must always be `false` - they cannot be group winners.

### 5. Example Row Formats

**Regular team (UEFA group winner):**
```csv
Spain,UEFA,1,false,,,1,true
```

**Regular team (not a group winner):**
```csv
Italy,UEFA,2,false,,,9,false
```

**Host nation:**
```csv
Mexico,CONCACAF,1,true,A,,13,false
```

**Playoff path (no playoff seeding):**
```csv
UEFA Playoff A,UEFA | CONMEBOL,4,false,,UEFA | CONMEBOL,,false
```

**Playoff path (with playoff seeding):**
```csv
UEFA Playoff A,UEFA | CONMEBOL,4,false,,UEFA | CONMEBOL,12,false
```

Note: The `pot` field for playoff paths is ignored when playoff seeding is enabled - the pot is determined by the FIFA ranking.

## Validation

After migration, validate your file:

```bash
# Check pot counts
uv run python -m wc_draw.cli

# Try a basic draw
make draw ARGS="--seed 42"

# Try with playoff seeding
make draw ARGS="--uefa-playoffs-seeded --seed 42"

# Try with both features
make draw ARGS="--uefa-group-winners-separated --uefa-playoffs-seeded --seed 42"
```

## Common Issues

### Issue: "Missing column: fifa_ranking"

**Solution**: Ensure the CSV header includes all 8 columns in the correct order.

### Issue: "Invalid uefa_group_winner value"

**Solution**: Values must be exactly `true` or `false` (lowercase), not `True`, `FALSE`, `1`, `0`, etc.

### Issue: Draw fails with "Unable to place pot after N attempts"

**Possible causes**:
1. Using `--uefa-group-winners-separated` without `--uefa-playoffs-seeded` (impossible)
2. Incorrect number of UEFA group winners (should be exactly 12)
3. Too many teams with the same confederation in a pot

**Solutions**:
- Always use both flags together for the UEFA constraint
- Verify exactly 12 teams have `uefa_group_winner=true`
- Check confederation distribution in pots

### Issue: Playoff path assigned to wrong pot

**Solution**: When using playoff seeding, the `pot` column for playoff paths is ignored. The pot is determined by the `fifa_ranking` value. Make sure the ranking is correct.

## Backward Compatibility

The new format is **not** backward compatible with older versions of the code that don't expect these columns.

If you need to use an old version:
1. Keep your backup: `teams.csv.backup`
2. Remove the last two columns when needed:
   ```bash
   cut -d',' -f1-6 teams.csv > teams_old_format.csv
   ```

## Testing Your Migration

Run the test suite to ensure everything works:

```bash
make test
```

Expected output:
- 36 tests passed
- 2 tests skipped (UEFA constraint tests without playoff seeding)

If tests fail, check:
1. CSV format is correct (8 columns, proper quotes for names with commas)
2. All boolean values are lowercase `true`/`false`
3. FIFA rankings are integers (no decimals or text)
4. Exactly 12 UEFA group winners marked

## Need Help?

If you encounter issues during migration:

1. Check the example `teams.csv` in the repository
2. Validate CSV syntax with: `python3 -c "import csv; list(csv.DictReader(open('teams.csv')))"`
3. Review error messages - they usually indicate which row/field has issues
4. Compare your file structure with the examples in this guide

## Summary

Required changes:
- ✅ Add `fifa_ranking` column (integer, empty for non-seeded playoff paths)
- ✅ Add `uefa_group_winner` column (boolean: `true` or `false`)
- ✅ Mark exactly 12 UEFA group winners as `true`
- ✅ All playoff paths must have `uefa_group_winner=false`
- ✅ Test with `make draw` to verify

Optional enhancements:
- Add FIFA rankings to all teams for potential future features
- Add FIFA rankings to playoff paths if using playoff seeding feature
