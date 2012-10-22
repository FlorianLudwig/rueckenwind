"""rw.db provides a simple database ORM for mongodb

Example::

    from rw.www import RequestHandler, get, post
    import motor
    import rw.db
    from tornado import gen

    connection = motor.MotorConnection(max_pool_size=10, max_concurrent=20).open_sync()
    rw.db.db = connection.test


    class User(rw.db.Entity):
        name = rw.db.Field(unicode)
        email = rw.db.Field(unicode)


    class Main(RequestHandler):
        @gen.engine
        @get('/')
        def index(self):
            self['users'] = yield gen.Task(User.query.filter_by(name='2').all)
            self.finish(template='index.html')

"""

from copy import copy

db = None

__all__ = ['Entity']


class Cursor(object):
    def __init__(self, query, user_callback=None):
        self.user_callback = user_callback
        self.col_cls = query.col_cls
        col = getattr(db, query.col_cls._name)
        self.db_cursor = col.find(query._filters, sort=query._sort, limit=query._limit)
        self.db_cursor.to_list(callback=self.on_response)

    def on_response(self, response, error):
        assert not error
        self.user_callback([self.col_cls(**e) for e in response])


class Query(object):
    def __init__(self, col, filters=None, sort=None, limit=0):
        self.col_cls = col
        self._sort = sort
        if db:
            self.col = getattr(db, col._name)
        self._filters = filters if filters else {}
        self._limit = limit

    def filter_by(self, **kwargs):
        filters = copy(self._filters)
        filters.update(kwargs)
        return Query(self.col_cls, filters, self._sort, self._limit)

    def sort(self, sort):
        return Query(self.col_cls, self._filters, sort, self._limit)

    def all(self, callback):
        Cursor(self, callback)

    def first(self, callback):
        self._limit = 1
        Cursor(self, callback)

    def get(self, value, user_callback):
        def callback(elements, error):
            if elements:
                user_callback(elements[0])
            else:
                user_callback(None)
        self.col.find({'_id': value}, callback=callback)


class Field(property):
    def __init__(self, type, _id=False):
        # print 'init property', self, type
        super(Field, self).__init__(self.get_value, self.set_value)
        self.name = None
        self.is_id = _id

    def get_value(self, entity):
        if self.is_id:
            return entity['_id']
        else:
            return entity[self.name]

    def set_value(self, entity, value):
        if self.is_id:
            entity['_id'] = value
        else:
            entity[self.name] = value

    def __repr__(self):
        return '<Field %i>' % self.name


class EntityMeta(type):
    def __new__(cls, name, bases, dct):
        ret = type.__new__(cls, name, bases, dct)

        ret._id_name = '_id'
        for key, value in dct.items():
            if isinstance(value, Field):
                field = getattr(ret, key)
                field.name = key
                if field.is_id:
                    if ret._id_name == '_id':
                        ret._id_name = key
                    else:
                        raise AttributeError('Two fields with _id=True %s, %s'
                                             % (ret._id_name, value))

        if bases != (dict,):
            ret._name = name.lower()
            ret.query = Query(ret)

        return ret


class Entity(dict):
    """Base type for mapped classes.

    It is a regular dict, with a little different construction behaviour plus
    one new class method `create` to create a new entry in a collection and
    a new method `delete` to delete an entry.

    Additionally there is a `query` attribute on `Entity` subclasses for


    Example::
         class Fruits(rw.db.Entity):
             kind = rw.db.Field(unicode)

         Fuits.query.filter_by(kind='banana').all()

    Warning: Never use "callback" as key."""
    __metaclass__ = EntityMeta

    def __init__(self, **kwargs):
        self.col = getattr(db, self._name)
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self[key] = value
        super(dict, self).__init__()

    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        if key == self._id_name:
            dict.__setitem__(self, '_id', value)
        else:
            dict.__setitem__(self, key, value)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                            ' '.join('%s=%s' % item for item in self.items()))

    def save(self, callback=None):
        """Save entry in collection (updates or creates)

        Warning: Never use "callback" as key."""
        def inner_callback(*args, **kwargs):
            if not callback is None:
                callback(*args, **kwargs)
        self.col.save(self, callback=inner_callback)  # TODO callback

    def delete(self):
        self.col.delete(self)


class Unicode(Field):
    pass


def using_options(name=None, tablename=None):
    if tablename:
        # elxir compatibility
        name = tablename
    print name
