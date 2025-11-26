# City Probability Analysis

## Overview

This system calculates the probability that each team will play at least one group stage match in each host city, based on:

1. **FIFA Position Mappings** - How pot numbers map to group positions (e.g., Pot 3 → Position A2 in Group A)
2. **Match Schedules** - Which positions play which matches in each group
3. **Venue Assignments** - Which cities host which matches
4. **Group Distributions** - Probability of each team being drawn into each group (from 50k simulations)

## Key Files

### Code Modules

- **`wc_draw/city_probabilities.py`** - Core calculation logic
  - `parse_group_stage_details()` - Parses group-stage-details file
  - `calculate_pot_city_probabilities()` - Calculates city probs for (group, pot) combo
  - `build_complete_city_probability_map()` - Precomputes all 48 (group, pot) mappings
  - `calculate_team_city_probabilities()` - Weights by group distribution
  - `calculate_all_teams_city_probabilities()` - Processes all teams

- **`wc_draw/group_positions.py`** - FIFA position mappings (already existed)
  - `get_position_for_pot(group, pot)` - Returns position number (1-4)
  - Three distinct patterns across 12 groups

### Scripts

- **`scripts/calculate_all_city_probabilities.py`** - Main calculator script
  - Loads FIFA stats from `fifa_official_stats.json`
  - Parses `group-stage-details` file
  - Outputs `team_city_probabilities.json` and `.csv`

### Data Files

- **Input Files:**
  - `group-stage-details` - Match schedules and venues for all groups
  - `fifa_official_stats.json` - Team group distributions from 50k draws

- **Output Files:**
  - `team_city_probabilities.json` - Nested dict: `{team: {city: probability}}`
  - `team_city_probabilities.csv` - Matrix format (teams × cities)

### Notebooks

- **`notebooks/city_probability_visualization.ipynb`** - Visualization examples
  - Top 4 seeds city probabilities
  - Scotland deep dive
  - City popularity heatmap
  - Summary statistics

## How It Works

### Host Groups (A, B, D)

For host groups, the match schedule explicitly assigns positions to matches:

**Example: Group A**
- Position A1 (Mexico) plays Match 1, 28, 53
- Position A2 (Pot 3) plays Match 1, 25, 54
- Position A3 (Pot 2) plays Match 2, 28, 54
- Position A4 (Pot 4) plays Match 2, 25, 53

Each position has **100% probability** of playing their 3 assigned matches.

Cities are determined by match venues:
- Match 1: Mexico City
- Match 25: Atlanta
- Match 54: Monterrey

So Position A2 has:
- Mexico City: 100%
- Atlanta: 100%
- Monterrey: 100%

### Non-Host Groups (C, E-L)

For non-host groups, matches are assigned to positions in pairs. Each position plays one match from each of 3 pairs:

**Example: Group C (6 matches)**
- Pair 1: Match 5 (Boston) or Match 7 (New York) - 50% each
- Pair 2: Match 29 (Philadelphia) or Match 30 (Boston) - 50% each
- Pair 3: Match 49 (Miami) or Match 50 (Atlanta) - 50% each

Each position plays exactly 3 matches, but which specific match from each pair is not predetermined.

**City probabilities** are calculated as "at least 1 match in this city":
- P(visit city) = 1 - P(avoid city in all 3 matches)
- P(avoid city) = product of (1 - match_probability) for all matches in that city

**Example:** Group C, Position C4 (Pot 3), Boston
- Match 5 in Boston: 50% chance
- Match 30 in Boston: 50% chance
- P(visit Boston) = 1 - (1-0.5) × (1-0.5) = 1 - 0.25 = **75%**

### Team-Level Calculation

Once we have city probabilities for each (group, pot) combination, we weight by the team's group distribution:

**Example: Scotland (Pot 3)**

```
Group A: 9.08% probability → A2 position → {Mexico: 100%, Atlanta: 100%, Monterrey: 100%}
Group B: 9.01% probability → B3 position → {Toronto: 100%, Vancouver: 100%, Seattle: 100%}
Group C: 8.18% probability → C4 position → {Boston: 75%, New York: 75%, Philadelphia: 50%, ...}
...

Overall Boston probability:
  = 0% × 0.0908 (Group A)
  + 0% × 0.0901 (Group B)  
  + 75% × 0.0818 (Group C)
  + ... (other groups)
  = 16.09%
```

## FIFA Position Mappings

The key insight is that **position ≠ pot** in most groups:

| Group | Pos 1 | Pos 2 | Pos 3 | Pos 4 | Pattern |
|-------|-------|-------|-------|-------|---------|
| A     | Pot 1 | **Pot 3** | Pot 2 | Pot 4 | [1,3,2,4] |
| B     | Pot 1 | **Pot 4** | Pot 3 | Pot 2 | [1,4,3,2] |
| C     | Pot 1 | Pot 2 | **Pot 4** | Pot 3 | [1,2,4,3] |
| D     | Pot 1 | **Pot 3** | Pot 2 | Pot 4 | [1,3,2,4] |
| E     | Pot 1 | **Pot 4** | Pot 3 | Pot 2 | [1,4,3,2] |
| F     | Pot 1 | Pot 2 | **Pot 4** | Pot 3 | [1,2,4,3] |
| G     | Pot 1 | **Pot 3** | Pot 2 | Pot 4 | [1,3,2,4] |
| H     | Pot 1 | **Pot 4** | Pot 3 | Pot 2 | [1,4,3,2] |
| I     | Pot 1 | Pot 2 | **Pot 4** | Pot 3 | [1,2,4,3] |
| J     | Pot 1 | **Pot 3** | Pot 2 | Pot 4 | [1,3,2,4] |
| K     | Pot 1 | **Pot 4** | Pot 3 | Pot 2 | [1,4,3,2] |
| L     | Pot 1 | Pot 2 | **Pot 4** | Pot 3 | [1,2,4,3] |

Three distinct patterns:
- **[1,3,2,4]**: Groups A, D, G, J (Pot 3 in position 2)
- **[1,4,3,2]**: Groups B, E, H, K (Pot 4 in position 2)
- **[1,2,4,3]**: Groups C, F, I, L (Pot 4 in position 3)

## Usage

### Calculate City Probabilities

```bash
cd /workspaces/wc-draw
python3 scripts/calculate_all_city_probabilities.py
```

This generates:
- `team_city_probabilities.json`
- `team_city_probabilities.csv`

### Visualize Results

Open and run `notebooks/city_probability_visualization.ipynb`

### Query in Python

```python
import json

# Load data
with open('team_city_probabilities.json') as f:
    city_probs = json.load(f)

# Get Scotland's probabilities
scotland = city_probs['Scotland']
print(f"Scotland → San Francisco: {scotland['san-francisco']:.2f}%")
print(f"Scotland → Atlanta: {scotland['atlanta']:.2f}%")

# Find most likely city for any team
team = 'Spain'
most_likely = max(city_probs[team].items(), key=lambda x: x[1])
print(f"{team}'s most likely city: {most_likely[0]} ({most_likely[1]:.2f}%)")
```

### Query in CLI

```bash
# Get all of Scotland's probabilities
python3 -c "import json; print(json.load(open('team_city_probabilities.json'))['Scotland'])"

# Find top 3 cities for a team
python3 -c "
import json
data = json.load(open('team_city_probabilities.json'))
team = 'England'
sorted_cities = sorted(data[team].items(), key=lambda x: -x[1])[:3]
for city, prob in sorted_cities:
    print(f'{city}: {prob:.2f}%')
"
```

## Sample Results

### Scotland (Pot 3)
- San Francisco: 24.33%
- Atlanta: 23.36%
- Houston: 18.30%
- Philadelphia: 18.14%
- New York: 18.10%

### Spain (Pot 1, Seed #1)
- Houston: 24.06%
- Philadelphia: 22.90%
- New York: 22.84%
- Miami: 21.90%
- Atlanta: 21.90%

### Most Popular Cities (Average)
Cities with highest average probability across all teams:
1. San Francisco: ~17%
2. Houston: ~19%
3. New York: ~19%
4. Philadelphia: ~19%
5. Atlanta: ~16%

Note: These reflect the uneven group distributions caused by FIFA's official constraints (top 4 separation, etc.)

## Technical Notes

### "At Least 1 Match" Calculation

The probabilities represent the chance of playing **at least one match** in a city, not the total number of matches.

For multiple matches in the same city with independent probabilities:
```
P(at least 1) = 1 - P(none)
P(none) = ∏(1 - p_i) for all matches i in that city
```

Example: Two 50% chances in same city
- P(at least 1) = 1 - (0.5 × 0.5) = 75%

### Hosts

Host teams (Mexico, USA, Canada) have 0% probability for non-host-group cities because they are locked into their host group and positions.

### Playoff Teams

Teams like "UEFA Playoff A" are treated as distinct entities with their own group distributions, even though we don't know which specific team they are yet.

## Limitations

1. **Group stage only** - Does not include knockout stage travel
2. **Draw simulation based** - Accuracy depends on FIFA stats quality (50k runs used)
3. **No training camps** - Doesn't include pre-tournament locations
4. **Static venue assignments** - Assumes match-to-venue mappings won't change

## Future Enhancements

Potential additions:
- Knockout stage city probabilities
- Total matches per city (not just "at least 1")
- Distance/travel burden analysis
- Time zone impact calculations
- Interactive map visualizations
