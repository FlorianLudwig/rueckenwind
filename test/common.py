def generate_route_func(name):
    def f(x):
        return x

    f.__name__ = name
    return f


def generate_handler_func(route_func, path, name=None):
    if name is None:
        name = route_func.__name__ + '_' + {'/': 'index'}[path]
    f = generate_route_func(name)
    return route_func(path)(f)
