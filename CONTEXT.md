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