# City Probability System - Quick Start Guide

## What is this?

This system calculates the probability that each team will play **at least one group stage match** in each of the 16 host cities, based on:
- FIFA's official position mappings (pot ≠ position in most groups)
- Match schedules and venue assignments
- 50,000 simulated draws using FIFA official constraints

## Quick Usage

### Generate City Probabilities

```bash
cd /workspaces/wc-draw
python3 scripts/calculate_all_city_probabilities.py
```

**Output files:**
- `team_city_probabilities.json` - Nested structure for programmatic use
- `team_city_probabilities.csv` - Matrix format (teams × cities) for Excel/analysis

### View Results

**Option 1: JSON (programmatic)**
```bash
# All of Scotland's probabilities
python3 -c "import json; print(json.load(open('team_city_probabilities.json'))['Scotland'])"

# Top 5 cities for any team
python3 -c "
import json
team = 'Spain'
data = json.load(open('team_city_probabilities.json'))[team]
for city, prob in sorted(data.items(), key=lambda x: -x[1])[:5]:
    print(f'{city}: {prob:.2f}%')
"
```

**Option 2: CSV (spreadsheet)**
```bash
# Open in VS Code
code team_city_probabilities.csv

# Or view in terminal
column -s, -t < team_city_probabilities.csv | less -S
```

**Option 3: Jupyter Notebook (visualizations)**
```bash
# Open the visualization notebook
jupyter notebook notebooks/city_probability_visualization.ipynb
```

## Understanding the Results

### Probability Interpretation

The numbers represent: **"What % chance does this team have of playing at least 1 match in this city?"**

**Example: Scotland**
- San Francisco: 24.33% → 24.33% chance Scotland plays 1+ matches there
- Atlanta: 23.36% → 23.36% chance Scotland plays 1+ matches there

### Why Aren't All Probabilities Equal?

The uneven distribution comes from:
1. **FIFA Top 4 Constraints** - Top seeds (Spain, Argentina, France, England) have restricted group distributions
2. **Position Mappings** - Pot 3 goes to position 2 in some groups, position 3 or 4 in others
3. **Host Groups** - Mexico, USA, Canada locked to groups A, B, D
4. **Match Pairings** - Non-host groups have 50/50 match alternatives

### City Name Normalization

Cities are normalized for consistency:
- `east-rutherford` → `new-york`
- `santa-clara` → `san-francisco`
- `inglewood` → `los-angeles`
- `zapopan` → `guadalajara`
- `guadalupe` → `monterrey`
- `foxborough` → `boston`
- `miami-gardens` → `miami`
- `arlington` → `dallas`

## Sample Results

### Top 5 Teams - Most Likely Cities

**Scotland (Pot 3)**
1. San Francisco: 24.33%
2. Atlanta: 23.36%
3. Houston: 18.30%
4. Philadelphia: 18.14%
5. New York: 18.10%

**Spain (Pot 1, #1 Seed)**
1. Houston: 24.06%
2. Philadelphia: 22.90%
3. New York: 22.84%
4. Miami: 21.90%
5. Atlanta: 21.90%

**Argentina (Pot 1, #2 Seed)**
1. Houston: 24.16%
2. Philadelphia: 22.80%
3. New York: 22.74%
4. Dallas: 22.10%
5. Miami: 21.86%

**France (Pot 1, #3 Seed)**
1. Houston: 24.08%
2. New York: 22.82%
3. Philadelphia: 22.80%
4. Dallas: 21.91%
5. Miami: 21.91%

**England (Pot 1, #4 Seed)**
1. Houston: 23.89%
2. Philadelphia: 23.10%
3. New York: 23.06%
4. Dallas: 22.02%
5. Boston: 21.94%

## How It Works (Simplified)

### Host Groups (A, B, D)

Each position has fixed matches (100% probability):

**Group A**
- Position A1 (Mexico): Matches 1, 28, 53
- Position A2 (Pot 3): Matches 1, 25, 54
- Position A3 (Pot 2): Matches 2, 28, 54
- Position A4 (Pot 4): Matches 2, 25, 53

### Non-Host Groups (C, E-L)

Matches come in pairs (50% probability each):

**Group C**
- **Pair 1**: Match 5 (Boston) OR Match 7 (New York)
- **Pair 2**: Match 29 (Philadelphia) OR Match 30 (Boston)
- **Pair 3**: Match 49 (Miami) OR Match 50 (Atlanta)

Each position plays one match from each pair.

**City probability calculation:**
- Boston: Has matches 5 (50%) and 30 (50%)
- P(play in Boston) = 1 - P(avoid both) = 1 - (0.5 × 0.5) = **75%**

### Team-Level Aggregation

Weight position probabilities by group distribution:

```
Scotland Total = 
  Group A probability × Group A position probabilities +
  Group B probability × Group B position probabilities +
  ... (all 12 groups)
```

## Common Use Cases

### 1. "Where will Scotland most likely play?"

```bash
python3 -c "
import json
scotland = json.load(open('team_city_probabilities.json'))['Scotland']
top_cities = sorted(scotland.items(), key=lambda x: -x[1])[:3]
print('Scotland most likely to play in:')
for city, prob in top_cities:
    print(f'  {city}: {prob:.2f}%')
"
```

### 2. "Which teams are most likely to visit Atlanta?"

```bash
python3 -c "
import json
all_teams = json.load(open('team_city_probabilities.json'))
atlanta_probs = [(team, probs.get('atlanta', 0)) for team, probs in all_teams.items()]
atlanta_probs.sort(key=lambda x: -x[1])
print('Teams most likely in Atlanta:')
for team, prob in atlanta_probs[:5]:
    print(f'  {team}: {prob:.2f}%')
"
```

### 3. "Compare two teams' city probabilities"

```python
import json
import pandas as pd

data = json.load(open('team_city_probabilities.json'))
df = pd.DataFrame([
    {'city': city, 'scotland': data['Scotland'][city], 'spain': data['Spain'][city]}
    for city in data['Scotland'].keys()
])
df['difference'] = df['scotland'] - df['spain']
print(df.sort_values('difference', ascending=False))
```

## Files Reference

| File | Description |
|------|-------------|
| `wc_draw/city_probabilities.py` | Core calculation module |
| `wc_draw/group_positions.py` | FIFA position mappings |
| `scripts/calculate_all_city_probabilities.py` | Main calculator script |
| `notebooks/city_probability_visualization.ipynb` | Visualization examples |
| `team_city_probabilities.json` | Output: nested dict format |
| `team_city_probabilities.csv` | Output: matrix format |
| `group-stage-details` | Input: match schedules/venues |
| `fifa_official_stats.json` | Input: group distributions |

## Documentation

For detailed technical information, see:
- `docs/CITY_PROBABILITY_ANALYSIS.md` - Complete technical documentation
- `wc_draw/city_probabilities.py` - Code documentation and examples

## Support

Questions? Check the docstrings:
```python
from wc_draw.city_probabilities import calculate_team_city_probabilities
help(calculate_team_city_probabilities)
```
