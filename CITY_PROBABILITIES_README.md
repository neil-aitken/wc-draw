# City Visit Probability Analysis

## Overview

Calculate the probability that each team will play **at least one group stage match** in each of the 16 host cities, based on FIFA's official draw constraints and 50,000 simulated draws.

## Quick Start

### Generate Probabilities

```bash
python3 scripts/calculate_all_city_probabilities.py
```

**Outputs:**
- `team_city_probabilities.json` - Full data (48 teams × 16 cities)
- `team_city_probabilities.csv` - Spreadsheet format

### View Results

```bash
# Scotland's top 5 cities
python3 -c "
import json
scotland = json.load(open('team_city_probabilities.json'))['Scotland']
for city, prob in sorted(scotland.items(), key=lambda x: -x[1])[:5]:
    print(f'{city}: {prob:.2f}%')
"

# Open CSV in Excel/Numbers
open team_city_probabilities.csv
```

### Visualize

```bash
jupyter notebook notebooks/city_probability_visualization.ipynb
```

## Sample Results

### Scotland (Pot 3)
1. San Francisco: 24.33%
2. Atlanta: 23.36%
3. Houston: 18.30%
4. Philadelphia: 18.14%
5. New York: 18.10%

### Top 4 Seeds
- **Spain** → Houston (24.06%)
- **Argentina** → Houston (24.16%)
- **France** → Houston (24.08%)
- **England** → Houston (23.89%)

## How It Works

The system accounts for:

1. **FIFA Position Mappings** - Pot ≠ Position in most groups
   - Example: Pot 3 → Position A2 in Group A (not A3)

2. **Match Assignments**
   - Host groups (A, B, D): Fixed matches per position (100%)
   - Non-host groups (C, E-L): Match pairs (50% each)

3. **Group Distributions** - From 50k FIFA-compliant draws
   - Top 4 separation constraints
   - Uneven distributions result from FIFA rules

4. **"At Least 1" Calculation**
   - P(visit city) = 1 - P(avoid all matches in city)
   - Handles multiple matches in same city

## Documentation

- **Quick Start:** `docs/CITY_PROBABILITY_QUICKSTART.md`
- **Technical Details:** `docs/CITY_PROBABILITY_ANALYSIS.md`
- **Full Summary:** `CITY_PROBABILITIES_SUMMARY.md`

## API Usage

```python
from wc_draw.city_probabilities import (
    build_complete_city_probability_map,
    calculate_team_city_probabilities
)

# Build map (do once)
city_map = build_complete_city_probability_map()

# Calculate for Scotland (Pot 3)
scotland_groups = {"A": 9.08, "B": 9.01, ...}
city_probs = calculate_team_city_probabilities(scotland_groups, 3, city_map)

print(f"San Francisco: {city_probs['san-francisco']:.2f}%")
```

## Tests

```bash
pytest tests/test_city_probabilities.py -v
```

**13 tests covering:**
- Group stage parsing
- Position calculations
- Pot-to-position mapping
- Probability aggregation
- Real-world validation

All tests passing ✓

## Files

```
wc_draw/city_probabilities.py           # Core module
scripts/calculate_all_city_probabilities.py  # Generator
notebooks/city_probability_visualization.ipynb  # Charts
tests/test_city_probabilities.py         # Tests
docs/CITY_PROBABILITY_*.md               # Documentation
```

## Key Insights

### Most Popular Cities (Average)
1. Philadelphia: 18.75%
2. New York: 18.75%
3. Houston: 18.75%
4. Atlanta: 18.60%
5. Toronto: 18.43%

### Least Popular Cities
1. Mexico City: 10.42% (locked to host groups)
2. Monterrey: 10.74% (locked to host groups)
3. Guadalajara: 14.26%

### Highest Variance (Unevenness)
1. Los Angeles: σ = 14.44%
2. Mexico City: σ = 14.13%
3. Vancouver: σ = 13.87%

High variance indicates FIFA constraints cause very different probabilities for different teams.

## Integration

This system builds on:
- `wc_draw/group_positions.py` - FIFA position mappings
- `fifa_official_stats.json` - 50k draw simulations
- `group-stage-details` - Match schedules

## Next Steps

Potential enhancements:
- Knockout stage probabilities
- Total expected matches per city
- Travel distance analysis
- Interactive map visualization

## Questions?

See documentation:
- `docs/CITY_PROBABILITY_QUICKSTART.md` - Examples and usage
- `docs/CITY_PROBABILITY_ANALYSIS.md` - Technical deep dive
