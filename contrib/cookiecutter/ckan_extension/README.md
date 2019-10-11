# CKAN Extension Template

[Cookiecutter](https://github.com/audreyr/cookiecutter) for creating a [CKAN](https://github.com/ckan/ckan) extension skeleton.

## Getting Started

Install Cookiecutter:
```sh
$pip install cookiecutter
```

Generate the skeleton:
```sh
$ cookiecutter https://github.com/f-osorio/cookiecutter-ckan-extension.git
```

Cookiecutter will prompt you for the following information to generate the skeleton:
```no-highlight
project: name of the project - MUST begin with "ckanext-"
keywords: associated with the project
description: of the project
author: of the project
author_email: 
github_user_name: GitHub user or organization name
```

Additionally, it will display the following which should not be changed:
```no-highlight
project_shortname
plugin_class_name 
```

Consult [CKAN documentation](https://docs.ckan.org/en/latest/extensions/tutorial.html) for creating an extension.
