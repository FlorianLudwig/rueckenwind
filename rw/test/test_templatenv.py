from rw.www import RequestHandler, RequestSubHandler, generate_routing, mount
from tornado import httpserver, web


def gen_handler(handler_cls, method, path):
    req = httpserver.HTTPRequest(method, path, remote_ip='127.0.0.1')
    return handler_cls(web.Application(), req)


class Something(RequestSubHandler):
    pass


class Config(RequestSubHandler):
    something = mount('/something', Something)


class User(RequestHandler):
    config = mount('/config', Config)


class Root(RequestHandler):
    user = mount('/user', User)





def check_handlervars(test, main_handler, root_handler):
    test_handler = gen_handler(test, 'GET', '/')
    assert test_handler['handler'] == test_handler
    assert test_handler['main_handler'] == main_handler
    assert test_handler['root_handler'] == root_handler


def test_handlervars():
    """Within the template env there must always be the variables:
        * handler
        * main_handler
        * root_handler"""
    generate_routing(Root)
    check_handlervars(Root, Root, Root)
    check_handlervars(User, User, Root)
    check_handlervars(Config, User, Root)
    check_handlervars(Something, User, Root)