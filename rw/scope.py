from tornado import gen, concurrent, stack_context
import contextlib
import functools

import inspect

NOT_PROVIDED = object()
current_scope = None


class Scope(dict):
    def __init__(self, **kwargs):
        super(Scope, self).__init__(**kwargs)
        self._provider = {}
        self.parent = None

    def provider(self, key, provider):
        self._provider[key] = provider

    def get(self, key, default=NOT_PROVIDED):
        if not key in self:
            if key in self._provider:
                self[key] = self._provider[key]()
                del self._provider[key]
            elif default is not NOT_PROVIDED:
                return default
            elif self.parent is not None:
                return self.parent.get(key, default)
            else:
                raise IndexError('No value for "{}" stored and no default given'.format(key))
        return self[key]

    def __call__(self):
        return stack_context.StackContext(functools.partial(set_context, self))


@contextlib.contextmanager
def set_context(scope):
    global current_scope
    if current_scope is not None:
        scope.parent = current_scope
    current_scope = scope
    yield
    current_scope = current_scope.parent


def inject(fn):
    arg_spec = inspect.getargspec(fn)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if len(args) < len(arg_spec.args):
            # possible injection
            missing_args = set(arg_spec.args[len(args):])
            for key in missing_args:
                if key not in kwargs:
                    kwargs[key] = current_scope.get(key)
        return fn(*args, **kwargs)
    return wrapper