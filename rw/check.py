import inspect


class ProtectorMeta(type):
    def __new__(mcs, cls_name, bases, dct):
        is_base_class = bases == (ProtectorBase, )
        ret = type.__new__(mcs, cls_name, bases, dct)
        check_overwrite = getattr(ret, '_check_overwrite', {})
        for name, overwrite in check_overwrite.items():
            func, overwrite_file, overwrite_lino = overwrite
            if name in dct and func != dct[name]:
                # this function is defined in this class and the
                # overwrite protection is defined is set in a base class
                # so we check if @overwrite was used on it
                if not getattr(dct[name], '_overwrite', False):
                    raise OverwriteException(cls_name, func, func.__doc__, overwrite_file, overwrite_lino)
        return ret


class ProtectorBase(object):
    pass


class Protector(ProtectorBase):
    __metaclass__ = ProtectorMeta


class OverwriteException(BaseException):
    def __init__(self, cls_name, func_name, func_doc, overwrite_file, overwrite_lino):
        self.cls_name = cls_name
        self.func_name = func_name
        self.func_doc = ''
        if func_doc:
            self.func_doc = '\n'.join('\t' + line for line in func_doc.split('\n'))
        self.overwrite_file = overwrite_file
        self.overwrite_lino = overwrite_lino

    def __str__(self):
        return """Function {5} is overwrite protected

{3} line {4}
\tMarks this function to be overwritten by subclasses only explicitly.

If you are sure you want to overwrite {0}.{1}, doc:
{2}

add the @rw.check.overwrite decorator to explictly overwrite this method""".format(
        self.cls_name, self.func_name.__name__, self.func_doc, self.overwrite_file, self.overwrite_lino, self.func_name)


def overwrite(func):
    func._overwrite = True
    return func


def overwrite_protected(func):
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe, 2)[1]
    cls_locals = calframe[0].f_locals
    cls_locals.setdefault('_check_overwrite', {})
    cls_locals['_check_overwrite'][func.__name__] = (func, calframe[1], calframe[2])
    return func

