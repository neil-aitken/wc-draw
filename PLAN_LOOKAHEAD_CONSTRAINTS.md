# Plan: Eliminate Fallback Orderings with Lookahead Constraints

## Problem Statement

Currently, 30% of draws fail the standard pot ordering (1→2→3→4) and require a fallback ordering like [2,4,3]. This creates systematic bias:
- Scotland/Norway are ~9% more likely to be with Argentina/Brazil in fallback draws
- This is not how FIFA actually conducts the draw

## Goal

Implement proper lookahead logic so that **every draw succeeds with pot ordering 1→2→3→4**, by excluding groups that would cause a deadlock before they're selected.

---

## Phase 1: Analysis & Understanding (Research)

### Step 1.1: Document Current Deadlock Scenarios
- [ ] Analyze the 15,171 fallback draws to understand WHY standard ordering fails
- [ ] Categorize the constraint violations that cause deadlocks
- [ ] Identify patterns (e.g., which pot/team combinations cause issues)

### Step 1.2: Map All Constraints

**Current explicit constraints:**

1. **Max 2 UEFA teams per group** - Self-explanatory

2. **Max 1 team per non-UEFA confederation per group** - This means:
   - Max 1 AFC team per group
   - Max 1 CAF team per group
   - Max 1 CONMEBOL team per group
   - Max 1 CONCACAF team per group
   - Max 1 OFC team per group
   - (UEFA is the exception - can have up to 2)
   - Note: A group will have 2-3 non-UEFA teams, but they must each be from DIFFERENT confederations

3. **Min 1 UEFA team per group** - Every group needs at least one European team

4. **No two teams from same pot in one group** - Standard pot distribution

5. **Host nations in fixed groups** - Mexico (Group A), Canada (Group B), USA (Group D)

6. **Top 4 bracket separation** - Spain/Argentina/France/England distributed across bracket quadrants

**Emergent constraints (to validate in Step 1.3):**

7. **Inter Path 1 landing spot** - Must have at least 1 group available for Inter Path 1
8. **Inter Path 2 landing spot** - Must have at least 1 group available for Inter Path 2  
9. **Non-European Pot 1 diversity** - Specific requirements for the 5 non-UEFA pot 1 groups

### Step 1.3: Validate Expert's Emergent Constraints

**Inter Path 1 Constraint:**
- Inter Path 1 playoff contains teams from: **CAF | OFC | CONCACAF** (DR Congo, New Caledonia, Jamaica)
- Therefore Inter Path 1 CANNOT go into any group that already has a CAF, OFC, or CONCACAF team
- **Requirement**: At end of Pot 3, there must be at least 1 group containing ONLY teams from UEFA, CONMEBOL, or AFC
- This is the "landing spot" for Inter Path 1

**Inter Path 2 Constraint:**
- Inter Path 2 playoff contains teams from: **AFC | CONMEBOL | CONCACAF** (Iraq, Bolivia, Suriname)
- Therefore Inter Path 2 CANNOT go into any group that already has an AFC, CONMEBOL, or CONCACAF team
- **Requirement**: At end of Pot 3, there must be at least 1 group with exactly 2 UEFA teams + 1 CAF team (and no AFC/CONMEBOL/CONCACAF)
- This is the only valid configuration for Inter Path 2

**Non-European Pot 1 Diversity Constraint:**
- The 5 groups with non-UEFA Pot 1 teams are: Argentina, Brazil, Mexico, Canada, USA groups
- **Requirement**: Before Pot 4 starts, these 5 groups must collectively contain at least:
  - 1 UEFA team (satisfied by min-1-UEFA rule)
  - 1 AFC team
  - 1 CAF team
- This ensures Pot 4 teams have valid landing spots

**Validation Tasks:**
- [x] Verify Inter Path 1 candidates: Confirmed `CAF | OFC | CONCACAF` (DR Congo, New Caledonia, Jamaica)
- [x] Verify Inter Path 2 candidates: Confirmed `AFC | CONMEBOL | CONCACAF` (Iraq, Bolivia, Suriname)
- [x] Check teams.csv for actual confederation strings - DONE
- [ ] Confirm these constraints are mathematically necessary for feasibility

---

## Phase 2: Design Lookahead System

### Step 2.1: Define Lookahead Check Function
```python
def would_cause_deadlock(team, group, current_state, remaining_teams) -> bool:
    """
    Return True if placing `team` in `group` would make it impossible
    to place all remaining teams.
    """
```

Key checks:
1. **UEFA distribution feasibility**: Can remaining UEFA teams fill the min-1-per-group requirement?
2. **Confederation feasibility**: Can remaining non-UEFA teams be distributed without exceeding max-1?
3. **Inter Path 1 feasibility**: Will there be a valid landing spot (UEFA/CONMEBOL/AFC only group)?
4. **Inter Path 2 feasibility**: Will there be a valid landing spot (2 UEFA + 1 CAF group)?
5. **Pot slot feasibility**: Will each remaining pot have valid placements?

### Step 2.2: Design State Tracking

Track at each decision point:
- Groups with 0, 1, 2 UEFA teams
- Groups with each non-UEFA confederation (AFC, CAF, CONMEBOL, CONCACAF, OFC)
- Groups that are valid Inter Path 1 landing spots (no CAF/OFC/CONCACAF)
- Groups that are valid Inter Path 2 landing spots (2 UEFA + 1 CAF only)
- Remaining teams per pot per confederation

### Step 2.3: Define Specific Lookahead Rules

**Rule L1: UEFA Minimum Feasibility**
```
Before placing non-UEFA team in group G:
- Count groups that will have 0 UEFA teams after all placements in current pot
- Count remaining UEFA teams in future pots
- If remaining_uefa_teams < groups_needing_uefa → REJECT this placement
```

**Rule L2: Inter Path 1 Feasibility**
```
When drawing Pot 2 or Pot 3:
- Count groups that contain NO teams from CAF, OFC, or CONCACAF
- If placing team would reduce this count to 0 → REJECT
- Must preserve at least 1 "clean" group for Inter Path 1
```

**Rule L3: Inter Path 2 Feasibility**
```
When drawing Pot 2 or Pot 3:
- Count groups that have exactly (2 UEFA + 1 CAF) or could reach that state
- A valid Inter Path 2 group needs: 2 UEFA, 1 CAF, 0 AFC/CONMEBOL/CONCACAF
- If placing team would eliminate all potential Inter Path 2 landing spots → REJECT
```

**Rule L4: Non-European Pot 1 Group Diversity**
```
When drawing Pot 3 for non-UEFA Pot 1 groups (Argentina, Brazil, Mexico, Canada, USA):
- Track if these 5 groups collectively have: ≥1 AFC, ≥1 CAF
- If a placement would make it impossible to achieve this before Pot 4 → REJECT
```

**Rule L5: General Confederation Feasibility**
```
Before any placement:
- For each remaining team, verify at least 1 valid group exists
- If any team would have 0 valid groups after this placement → REJECT
```

---

## Phase 3: Implementation

### Step 3.1: Create Lookahead Module
- [ ] New file: `wc_draw/lookahead.py`
- [ ] Implement state tracking class
- [ ] Implement each feasibility rule (L1-L5)
- [ ] Unit tests for each lookahead rule

### Step 3.2: Integrate into `eligible_for_group()`
- [ ] Add lookahead check after basic constraint check
- [ ] Pass draw state to eligibility function
- [ ] Ensure lookahead is efficient (avoid exponential blowup)

### Step 3.3: Remove Fallback Orderings
- [ ] Remove `alternate_orderings` logic from `run_full_draw()`
- [ ] Keep only standard 1→2→3→4 ordering
- [ ] Ensure 100% success rate without fallbacks

### Step 3.4: Update Backtracking Solver
- [ ] Integrate lookahead into backtracking pruning
- [ ] Should rarely/never be needed if lookahead is correct

---

## Phase 4: Validation

### Step 4.1: Test Lookahead Correctness
- [ ] Run 1,000 seed test - should be 100% success, 0 fallbacks
- [ ] Verify all constraints are satisfied
- [ ] Compare statistics with fallback version

### Step 4.2: Verify Bias Elimination

**Scotland/Norway vs Non-European Pot 1 Teams:**
The key validation is that Scotland and Norway (Pot 3 UEFA teams) should have:
- **Almost equal probability** of landing in ANY of the 5 non-European Pot 1 groups
- They will still have some probability of landing in UEFA Pot 1 groups (Spain, France, England, Germany, Netherlands, Belgium, Portugal)
- But among the non-UEFA Pot 1 groups, they should be ~equally distributed

Example expected distribution for Scotland/Norway:
- ~11% each for Argentina, Brazil, Mexico, Canada, USA (total ~55%)
- ~6-7% each for the 7 UEFA Pot 1 groups (total ~45%)
- Currently biased: higher % for Argentina/Brazil due to fallback ordering

**Pot 2 vs Pot 3 UEFA Teams with Argentina/Brazil:**
The expert's claim is that Pot 2 UEFA teams (Austria, Croatia, Switzerland) should be MORE likely to end up with Argentina/Brazil than Pot 3 UEFA teams (Scotland, Norway).

Reasoning:
- Pot 2 has 3 CONMEBOL teams (Colombia, Uruguay, Paraguay) 
- These CONMEBOL teams CANNOT go with Argentina/Brazil (max 1 CONMEBOL per group)
- So Pot 2 UEFA teams have relatively more opportunities for Argentina/Brazil groups
- Pot 3 has no such restriction pushing UEFA teams toward Argentina/Brazil

**Validation Metrics:**
- [ ] Scotland/Norway should have ~equal % for each non-UEFA Pot 1 team (Argentina ≈ Brazil ≈ Mexico ≈ Canada ≈ USA)
- [ ] Scotland/Norway should have lower % for UEFA Pot 1 teams than non-UEFA Pot 1 teams
- [ ] Austria/Croatia/Switzerland should have HIGHER % for Argentina/Brazil than Scotland/Norway do
- [ ] No systematic bias from draw ordering

### Step 4.3: Full Regeneration
- [ ] Run 50,000 seed simulation
- [ ] Regenerate statistics
- [ ] Regenerate screenshots
- [ ] Expert review of new numbers

---

## Phase 5: Optimization (if needed)

### Step 5.1: Performance Tuning
- [ ] Profile lookahead performance
- [ ] Cache feasibility calculations where possible
- [ ] Ensure draws complete in reasonable time

### Step 5.2: Edge Case Handling
- [ ] Handle seeds that are truly infeasible (should be rare/none)
- [ ] Add detailed logging for debugging

---

## Key Questions to Resolve

1. **Validate Inter Path confederations**: Confirm exact confederation strings in teams.csv

2. **Lookahead depth**: How far ahead do we need to look? 
   - Likely need to consider all remaining teams in current pot + future pots

3. **Performance**: Can we make lookahead fast enough for 50k seeds?

4. **Determinism**: Ensure same seed produces same draw (lookahead shouldn't affect randomness, only eligibility filtering)

5. **Mathematical necessity**: Are the emergent constraints (Inter Path 1/2 landing spots) always achievable, or are some seeds truly infeasible?

---

## Estimated Timeline

| Phase | Description | Time |
|-------|-------------|------|
| Phase 1 | Analysis & Understanding | 2-3 hours |
| Phase 2 | Design Lookahead System | 2-3 hours |
| Phase 3 | Implementation | 4-6 hours |
| Phase 4 | Validation | 2-3 hours |
| Phase 5 | Optimization | 1-2 hours |
| **Total** | | **11-17 hours** |

---

## Risks

1. **Complexity**: Lookahead logic can get complex and hard to debug
2. **Performance**: Deep lookahead could be slow
3. **Edge cases**: Some seeds might be truly infeasible
4. **Unintended bias**: New logic could introduce different biases

---

## Success Criteria

- [ ] **0% fallback rate** - All draws use standard 1→2→3→4 pot ordering
- [ ] **100% success rate** - All seeds produce valid draws
- [ ] **Scotland/Norway equal distribution across non-UEFA Pot 1** - Almost equal probability for each non-European Pot 1 team (e.g., ~11% each for Argentina, Brazil, Mexico, Canada, USA). Lower probability for UEFA Pot 1 teams (e.g., ~6-7% each for Spain, France, England, etc.)
- [ ] **Pot 2 > Pot 3 for Argentina/Brazil** - Austria/Croatia/Switzerland have higher probability with Argentina/Brazil than Scotland/Norway do
- [ ] **All constraints satisfied** - Min 1 UEFA, max 2 UEFA, max 1 per non-UEFA confederation, etc.
- [ ] **All tests pass**
- [ ] **Expert approval** of final statistics

---

## Progress Tracking

### Phase 1 Progress
- [ ] Step 1.1: Analyze fallback draws
- [ ] Step 1.2: Map all constraints (documented above)
- [ ] Step 1.3: Validate emergent constraints

### Phase 2 Progress
- [ ] Step 2.1: Define lookahead function
- [ ] Step 2.2: Design state tracking
- [ ] Step 2.3: Define specific rules

### Phase 3 Progress
- [ ] Step 3.1: Create lookahead module
- [ ] Step 3.2: Integrate into eligible_for_group()
- [ ] Step 3.3: Remove fallback orderings
- [ ] Step 3.4: Update backtracking solver

### Phase 4 Progress
- [ ] Step 4.1: Test lookahead correctness
- [ ] Step 4.2: Verify bias elimination
- [ ] Step 4.3: Full regeneration

### Phase 5 Progress
- [ ] Step 5.1: Performance tuning
- [ ] Step 5.2: Edge case handling

---

## Recommended Next Steps

1. **First**: Validate the Inter Path 1 and Inter Path 2 confederation strings from teams.csv
2. **Second**: Analyze WHY current draws need fallbacks - which specific placements cause deadlocks
3. **Third**: Implement simplest lookahead rule (UEFA minimum feasibility) and measure impact
4. **Fourth**: Add Inter Path feasibility rules
5. **Fifth**: Iterate until 0% fallback rate achieved

---

*Last Updated: November 26, 2025*
