import ckan.plugins.toolkit as tk

__all__ = ['{{cookiecutter.project_shortname}}_get_sum']


def {{cookiecutter.project_shortname}}_get_sum(context, data_dict):
    tk.check_access('{{cookiecutter.project_shortname}}_get_sum', context, data_dict)
    left, right = tk.get_or_bust(data_dict, ['left', 'right'])
    try:
        result = tk.asint(left) + tk.asint(right)
    except ValueError as e:
        raise tk.ValidationError(e)
    return {
        'left': left,
        'right': right,
        'sum': result
    }


def get_actions():
    return {
        '{{cookiecutter.project_shortname}}_get_sum': {{cookiecutter.project_shortname}}_get_sum,
    }
