# Contributing to CKAN

Thanks for wanting to help build CKAN. As a community-led project we welcome
all kinds of contributions.

The full documentation for contributing to CKAN (whether code, bug reports, translations,
documentation, etc.) can be found in our contributing guidelines:

https://docs.ckan.org/en/latest/contributing/

## Pull Requests

* Please mark the relevant boxes in the Pull Request template.
* The pull request description should be written by a human. Keep pull request descriptions
  concise, provide information about the CKAN version you are using and any relevant traceback
  details.
* Keep the pull request focused on a single feature or fix, use clear and descriptive commit
  messages.
* Unless suggested by a maintainer, please send all pull requests against the `master` branch.
  You should flag in the pull request description what CKAN version(s) are affected by your
  patch. The reviewer will backport the fix to the appropriate branches.
* Provide new tests or update existing ones to cover the proposed functionality.


## AI Usage

* Use of AI-assisted tools is allowed, but the human operator remains responsible for any
  submissions, and must be prepared to explain or discuss any part of it. All submissions in the form
  of pull requests, issues or comments should be made by the human operator, not directly by the agent
  or tool.
* Flag non-trivial use of an AI tool in the appropriate box of the pull request template.
* Please do not add your tool as a co-author of the commits you send (e.g. the `claude` user).
* AI tools tend to be overly verbose. In pull requests and issues, review and edit any generated
  text yourself rather than copying the generated text. In code, avoid unnecessary comments or
  overly descriptive docstrings. Explanations about code choices should go in the commit history.
* Point your tool to the `AGENTS.md` file located at the root of this repository for agent specific
  instructions.
