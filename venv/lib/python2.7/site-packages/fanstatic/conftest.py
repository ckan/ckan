from fanstatic import set_resource_file_existence_checking

def pytest_runtest_setup(item):
    set_resource_file_existence_checking(False)

def pytest_runtest_teardown(item):
    set_resource_file_existence_checking(True)
    
    
