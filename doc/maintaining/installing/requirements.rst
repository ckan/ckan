.. include:: /_latest_release.rst

============================
CKAN Requirements
============================

Before deploying CKAN, you might want to ensure your hardware meets
the minimum requirements.

For a small to medium CKAN instance, the following are recommended as
a minimum:

* 2 CPU cores
* 4 GB of RAM
* 60 GB of disk space

for each machine.

If you wish to run both frontend and backend on the same machine,
you will almost certainly want to use 4(+) CPU cores.

You do not want to be constrained by disk IO, often a case with budget
hosting providers (`iostat -x -m 10 100` may be useful -- but ignore
the first few lines)
