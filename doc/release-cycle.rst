=============
Release Cycle
=============

In order to ensure that our releases are stable and backwards compatible, we
follow a strict release process. There are two kinds of releases:

Point releases (e.g 1.8)
------------------------

These will be branched from master at a certain point (we aim to do a point
release roughly every two or three months). There will be a period of three
weeks until the actual release. During the first two weeks changes would be
allowed  to stabilize the code, update i18n etc. During the last week only
critical bug fixes will be allowed. Point releases are merged back into master
after the actual release.

Point point releases (e.g 1.8.1)
--------------------------------

These are branched from every point release and *must not* break compatibility:

- No DB migrations or schema changes
- No function interface changes
- No plugin interface changes
- No new dependencies
- No big refactorings or new features on critical parts of the code
- Point point releases are not merged back into master, and all changes must be
  cherry-picked from master.
- Point point releases are released as needed depending on the severity of the
  bugs fixed. They will be distributed via the same apt repository as their
  parent release.

Allowed optimizations and small features in point point releases are somewhat
open to interpretation. In any case, the release manager (or another single
developer designated by him) has the final say on what is merged into release
branches.

Both core and external supported extensions need to be tested before the
release (during the two week period after branching and before the final
freeze). These supported extensions need to defined as soon as possible. 
