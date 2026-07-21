# CI fix for PR #9439

Changes:

- Added `changes/9439.bugfix` describing the tracking export row fix.
- Renamed `ckanext/tracking/tests.py` to `ckanext/tracking/test_tracking.py` without changing test contents.

Validation:

- Targeted Docker pytest: 16 passed.
- Docker split collection: all 12 groups passed; the renamed module appeared in multiple groups.
- `towncrier check`: passed.
- `git diff --check`: passed.

Commit: `85e5e6ff266040a7ceacaee2be581484a12ec570` (`Fix tracking export changelog and test discovery`)

Push: successful, without force, to `fork/fix-9437-tracking-export-viewcount`.

Residual risk: full remote CI and Codecov still need to complete on GitHub; local split collection confirms the tracking tests are assigned to shards.
