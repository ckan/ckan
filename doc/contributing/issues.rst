================
Reporting issues
================

If you've found a bug in CKAN, open a new issue on CKAN's `GitHub Issues`_ (try
searching first to see if there's already an issue for your bug).

.. _GitHub Issues: https://github.com/ckan/ckan/issues

If you can fix the bug yourself, please
:doc:`send a pull request <pull-requests>`!

Do not use an issue to ask how to do something - for that use `StackOverflow
with the 'ckan' tag <https://stackoverflow.com/questions/tagged/ckan>`_.

Do not use an issue to suggest an significant change to CKAN - instead create
an issue at https://github.com/ckan/ideas-and-roadmap.


Writing a good issue
====================

* Describe what went wrong
* Say what you were doing when it went wrong
* If in doubt, provide detailed steps for someone else to recreate the problem.
* A screenshot is often helpful
* If it is a 500 error / ServerError / exception then it's essential to supply
  the full stack trace provided in the CKAN log.

Issues process
==============

The CKAN Technical Team reviews new issues twice a week. They aim to assign
someone on the Team to take responsibility for it. These are the sorts of
actions to expect:

* If it is a serious bug and the person who raised it won't fix it then the
  Technical Team will aim to create a fix.

* A feature that you plan to code shortly will be happily discussed. It's often
  good to get the team's support for a feature before writing lots of code. You
  can then quote the issue number in the commit messages and branch name.
  (Larger changes or suggestions by non-contributers are better discussed on
  https://github.com/ckan/ideas-and-roadmap instead)

* Features may be marked "Good for Contribution" which means the Team is happy
  to see this happen, but the Team are not offering to do it.

Old issues
==========

If an issue has little activity for 12 months then it should be closed. If
someone is still keen for it to happen then they should comment, re-open it and
push it forward.
