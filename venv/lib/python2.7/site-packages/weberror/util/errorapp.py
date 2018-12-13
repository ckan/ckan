"""
This simple application creates errors
"""

def error_app(environ, start_response):
    environ['errorapp.item'] = 1
    raise_error()

def raise_error():
    if 1 == 1:
        raise Exception('This is an exception')
    else:
        do_stuff()

def make_error_app(global_conf):
    return error_app
