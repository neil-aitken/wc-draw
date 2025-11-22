# Project Working Context

This project follows a test-driven development (TDD) workflow. The preferred way of working is:
## Usage Instructions

Use the provided Makefile targets to run tests and linting:

- To run tests: `make test`
- To lint code: `make lint`

Agents and collaborators should use these targets for consistency.

1. **Create a failing unit test**
   - Write a test that describes the desired behavior or feature.
   - Ensure the test fails, confirming the feature is not yet implemented.

2. **Make it pass**
   - Implement the minimum code necessary to make the test pass.
   - Focus on correctness and functionality first.

3. **Make it better**
   - Refactor the code for clarity, maintainability, and performance.
   - Apply linting and style improvements.
   - Ensure all tests continue to pass after changes.

This cycle should be repeated for each new feature or bugfix to maintain code quality and reliability.

## Draw Scenarios

The project supports 3 viable scenario configurations for the World Cup draw:

1. **Baseline** (both flags off):
   - `uefa_group_winners_separated=False`
   - `uefa_playoffs_seeded=False`
   - Standard FIFA draw rules with no special constraints

2. **Playoff Seeding Only**:
   - `uefa_group_winners_separated=False`
   - `uefa_playoffs_seeded=True`
   - UEFA playoff paths assigned to pots 2-3 based on FIFA rankings
   - Reduces pot 4 constraint pressure

3. **Both Features Combined**:
   - `uefa_group_winners_separated=True`
   - `uefa_playoffs_seeded=True`
   - UEFA group winner separation constraint enforced (one winner per group)
   - Requires playoff seeding to work (moves UEFA teams out of pot 4)
   - 100% success rate with max_attempts=5000

**Note**: The combination `uefa_group_winners_separated=True` with `uefa_playoffs_seeded=False` is **impossible** due to over-constrained pot 4. With 12 UEFA group winners in 12 groups and 4 UEFA playoff paths in pot 4, the constraint cannot be satisfied. Testing confirms 0% success rate across all seeds tested.