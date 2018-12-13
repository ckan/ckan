import pkg_resources 

def get_impl(name):
    for ep in pkg_resources.iter_entry_points("ofs.backend", name.strip().lower()):
        return ep.load()
