# FIFA Draw Migration Plan

## Overview

Migrate from **MRV (Minimum Remaining Values)** heuristic to **FIFA "First Eligible Group"** procedure.

**Current Behavior (MRV):**
- Teams with fewest eligible groups are drawn first
- Placed in random eligible group

**FIFA Procedure:**
- Teams drawn randomly from pot
- Placed into lowest-numbered eligible group (A→L order)

---

## Phase 1: Core Algorithm Change

- [x] **Step 1.1: Create `draw_pot_fifa_style` function**
  - Remove MRV sorting logic
  - Shuffle pot teams, iterate in shuffled order
  - For each team: find eligible groups, sort alphabetically, place in first eligible
  - Return failure if no eligible group exists

- [ ] **Step 1.2: Update pot 3 special handling**
  - Remove MRV priority for CAF teams
  - CAF preference may become a lookahead constraint instead

- [ ] **Step 1.3: Update `draw_pot1_with_separation`**
  - Shuffle teams, place each in lowest eligible group respecting quadrant rules
  - Higher risk since top-4 constraints are hard to satisfy with random order

---

## Phase 2: Baseline Testing (No New Lookahead)

- [x] **Step 2.1: Create feature flag for draw style**
  - Added `fifa_style: bool = False` to `LookaheadConfig`
  - Keep MRV as fallback while testing

- [x] **Step 2.2: Test baseline with existing L3, L6-L9 lookahead**
  - Run 1000+ seeds with FIFA-style draw + current lookahead
  - **Results: 530/1000 = 53.0% success rate**
  - Failure distribution:
    - Pot 2: 64 failures
    - Pot 3: 267 failures (most common)
    - Pot 4: 139 failures

- [x] **Step 2.3: Document failure modes**
  - **CONFED_LIMIT (408 blocks)**: Teams drawn late have no valid groups
    - Most affected: Jordan (pot 4, AFC), Paraguay (pot 3, CONMEBOL)
    - Root cause: Limited confederation slots fill up before constrained teams drawn
  - **L3 (78 blocks)**: Inter Path 2 protection too aggressive
  - **L9 (54 blocks)**: CAF slot reservation too aggressive
  - Teams that get stuck most:
    - Jordan (AFC, pot 4): 49 times
    - Paraguay (CONMEBOL, pot 3): 43 times
    - Qatar, Uzbekistan, Saudi Arabia (AFC pot 3): 24-29 times
    - Colombia, Uruguay, Ecuador (CONMEBOL pot 2): 9-14 times

---

## Phase 3: New Lookahead Constraints (if needed)

- [x] **Step 3.1: L10 - Confederation slots reservation**
  - Implemented: reserves slots for CONMEBOL and AFC teams
  - Improved success from 53% to 68%
  - Pot 2 failures dropped from 64 to 5

- [x] **Step 3.2: L11 - IP2/CONMEBOL combined protection**
  - During pot 2: ensure at least 2 groups remain that are both:
    - CONMEBOL-free (for Paraguay in pot 3)
    - IP2-valid (UEFA pot 1 + CAF/UEFA pot 2)
  - Implemented and working (68% success rate maintained)
  - Pot 3 extension attempted but caused MORE failures (reverted)

- [ ] **Step 3.3: Investigate pot 3 failures further**
  - 188 pot 3 failures remain
  - Constrained teams (AFC=90, CAF=101, CONMEBOL=61) getting stuck
  - Random draw order fundamentally conflicts with MRV approach
  - **May be unavoidable with FIFA-style draw**

- [ ] **Step 3.4: Investigate pot 4 failures**
  - 127 pot 4 failures remain
  - L3 (Inter Path 2) and L9 (CAF slots) blocking

### Current Status (After L11)
- **Success Rate: 68.0%** (stable)
- **Failures by pot:**
  - Pot 1: 0 (top-4 separation working)
  - Pot 2: 5 (minimal)
  - Pot 3: 188 (main issue)
  - Pot 4: 127

### Fundamental Limitation Discovered

**The core problem:** FIFA-style draw uses random team order within each pot, but some teams (Paraguay - only CONMEBOL in pot 3) have very few valid groups. When drawn late in the random order, their groups may already be taken.

**MRV vs FIFA-style:**
- MRV: Draws most-constrained teams first → always finds a solution
- FIFA-style: Random order → sometimes constrained teams get stuck

**Example (Seed 47):**
- Paraguay is CONMEBOL, pot 3 only has 1 CONMEBOL team
- After pot 2, 7 groups are CONMEBOL-free
- Pot 3 has 8 other teams (4 AFC, 5 CAF) that can go to CONMEBOL-free groups
- If Paraguay is drawn late (position 9-12), other teams fill the CONMEBOL-free groups
- Paraguay gets stuck

**Potential Solutions:**
1. **Accept lower success rate** - 68% may be acceptable for FIFA-style
2. **Backtracking** - If draw fails, retry with different random seed
3. **Constrained random order** - Shuffle but draw constrained teams first
4. **Hybrid approach** - Use MRV for most-constrained teams, random for rest

---

## Phase 4: Performance Optimization

- [ ] **Step 4.1: Simplify eligibility checking**
  - Can stop at first eligible (since we always take lowest)

- [ ] **Step 4.2: Review lookahead constraint efficiency**
  - Some constraints may be simplified with deterministic placement

---

## Phase 5: Code Cleanup & Testing

- [ ] **Step 5.1: Remove MRV-specific code**
  - Remove `team_options` sorting logic
  - Remove pot-3 special ordering

- [ ] **Step 5.2: Update/add unit tests**
  - Test deterministic group selection
  - Test random team order within pot

- [ ] **Step 5.3: Integration testing**
  - Run 10,000+ seeds to confirm stable success rate

---

## Phase 6: Documentation

- [ ] **Step 6.1: Update docstrings and comments**

- [ ] **Step 6.2: Update README and CONTEXT.md**

---

## Risk Assessment

| Change | Risk Level | Mitigation |
|--------|-----------|------------|
| Remove MRV from pot 2-4 | Medium | New lookahead constraints |
| Remove MRV from pot 1 (top-4) | High | L11 group reservation |
| Deterministic group selection | Low | Simplifies testing |
| New lookahead constraints | Medium | Extensive testing per constraint |

---

## Execution Log

### Phase 1.1 - Create `draw_pot_fifa_style`
- **Status:** Complete
- **Notes:** Implemented and tested

### Phase 2.1 - Add feature flag
- **Status:** Complete
- **Notes:** `fifa_style: bool` added to `LookaheadConfig`

### Phase 2.2 - Baseline testing
- **Status:** Complete
- **Notes:** 53% success rate baseline established

### Phase 3.1 - L10 confederation reservation
- **Status:** Complete
- **Notes:** Improved success rate to 68%

### Phase 3.2 - L11 IP2/CONMEBOL combined
- **Status:** Complete
- **Notes:** Implemented pot-2 only version. Pot-3 extension caused more failures, reverted.

### Current Milestone
- **68% success rate** with FIFA-style draw (vs 100% with MRV)
- Remaining 32% failures appear inherent to random draw order
- Decision point: Accept 68% or explore alternative approaches (backtracking, hybrid)