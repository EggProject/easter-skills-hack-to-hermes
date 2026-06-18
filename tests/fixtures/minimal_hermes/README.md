# tests/fixtures/minimal_hermes — 4-anchor contract

The `seed_minimal()` function in `seed_minimal.py` materializes a 6-file
synthetic Hermes checkout under any `root: Path`. Per
`plans/09-test-strategy.md §Fixture strategy`, this fixture is the
anchor contract for migration tests: it pins the exact set of
relative paths and contents the migration scripts must read, write,
or leave untouched. Usage: `from tests.fixtures.minimal_hermes.seed_minimal
import seed_minimal, MINIMAL_HERMES_FILES`.
