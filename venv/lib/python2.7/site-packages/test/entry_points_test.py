import pkg_resources

def test_entry_points_01():
    count = 0
    for entry_point in pkg_resources.iter_entry_points('ofs.backend'):
        backend = entry_point.load()
        print entry_point.name, backend
        count += 1
    assert count >= 4

