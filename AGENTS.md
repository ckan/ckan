# AGENTS.md

CKAN is an open-source data portal platform built with Python.

## Documentation and guidelines

* Full documentation can be found in the `doc` folder or online at https://docs.ckan.org
* When using the online documentation make sure to use the one relevant to the CKAN version
  you are working on (e.g. https://docs.ckan.org/en/2.12 for CKAN 2.12, https://docs.ckan.org/en/latest/
  for the master development branch).
* Important documentation sections:
  * API guide and reference: https://docs.ckan.org/en/latest/api/index.html
  * Configuration reference: https://docs.ckan.org/en/latest/maintaining/configuration.html
  * Plugin interfaces reference: https://docs.ckan.org/en/latest/extensions/plugin-interfaces.html
* Make sure to check the contribution guidelines: https://docs.ckan.org/en/latest/contributing/index.html

## Pull request guidelines

* Do not send a PR yourself. Propose a draft PR with a summary of the changes made, which the human operator
  will edit and validate, before submitting it.
* Use the pull request template located in `.github/PULL_REQUEST_TEMPLATE.md`. Tick all relevant boxes, especially
  the one that flags the use of automated tools.
* Keep texts short. Describe the issues addressed and changes made in a small number of sentences. Keep commit
  messages short and descriptive. If available, prefix the commit message with the issue number (e.g. `[#1234] Some changes`)
* Once a PR exists, add a changelog fragment in the `changes` directory in the form `changes/{pr_number}.{type}`
  where `type` is one of `bugfix`, `feature`, `misc` or `removal`.
* Run linting and type checking commands before submitting (see sections below).

## Coding standards

* Follow existing patterns in the codebase. Before adding a new helper, validator or
  utility, check whether an equivalent already exists and reuse it.
* Comments are a code smell. Only add comments when a code side effect is likely to be surprising.
  Intent of code should be clear from its structure, function and variable names.
* Every line of code added is future technical debt. Every change is a future merge conflict.
  Limit these future costs when implementing features.
* Actions live in `ckan/logic/action/` and must have a matching auth function in
  `ckan/logic/auth/`. Validate input with schemas (`ckan/logic/schema.py`) and
  validators (`ckan/logic/validators.py`) rather than ad hoc checks.
* Action docstrings are rendered into the API reference. They document action API parameters
  and return values using sphinx format.
* Code under `ckanext` should use `ckan.plugins.toolkit` instead of importing CKAN internals directly.
* Update existing tests to cover changes. Create new tests to cover new functionality. Tests should
  be as simple and short as possible.

## Development Commands

### Testing

Always run the following commands with the custom configuration file with `--ckan-ini=test-core.ini`

```bash
# Run all tests
pytest --ckan-ini=test-core.ini

# Run tests for a specific module
pytest --ckan-ini=test-core.ini ckan/tests/logic

# Run tests for a specific file
pytest --ckan-ini=test-core.ini ckan/tests/logic/test_action.py

# Run a single test
pytest --ckan-ini=test-core.ini ckan/tests/logic/test_action.py::TestPackageShow::test_package_show

# Run tests matching a pattern
pytest --ckan-ini=test-core.ini -k "test_package"
```

### Linting and Type Checking

```bash
# Lint with Ruff (run pip install ruff first)
ruff check .

# Type check with PyRight (run npm install first)
npx pyright

# Type check a specific file
npx pyright ckan/logic/action/package.py

```
