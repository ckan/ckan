from ckan.types import Context, DataDict


def show_logs(context: Context, data_dict: DataDict):
    return {"success": False}

def get_auth_functions():
    return {
        "show_logs": show_logs,
    }
