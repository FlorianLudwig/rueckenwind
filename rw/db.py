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
import numbers
from copy import copy
import bson
from motor import Op

from tornado import gen
from tornado.concurrent import return_future

db = None

__all__ = ['Entity']


class Cursor(object):
    def __init__(self, query, user_callback=None):
        self.user_callback = user_callback
        self.col_cls = query.col_cls
        col = getattr(db, query.col_cls._name)
        print 'query', col, query._filters
        self.db_cursor = col.find(query._filters, sort=query._sort, limit=query._limit)
        self.db_cursor.to_list(callback=self.on_response)

    def on_response(self, response, error):
        assert not error
        self.user_callback([self.col_cls(**e) for e in response])


class Query(object):
    def __init__(self, col, filters=None, sort=None, limit=0, start=0):
        self.col_cls = col
        self._sort = sort
        if db:
            self.col = getattr(db, col._name)
        self._filters = filters if filters else {}
        self._limit = limit
        self._start = start

    def __getitem__(self, slice):
        if isinstance(slice, numbers.Number):
            return Query(self.col_cls, self._filters, self.sort,
                         limit=1, start=slice)
        elif slice.step is None \
          and isinstance(slice.start, numbers.Number)\
          and isinstance(slice.stop, numbers.Number)\
          and slice.stop > slice.start:
            return Query(self.col_cls, self._filters, self._sort,
                         limit=slice.stop - slice.start, start=slice.start)
        else:
            raise AttributeError('Slice indecies must be integers, step (= {}) must not be set'
                                 ' and start (= {}) must be higher than stop (= {})'.format(
                                 slice.step, repr(slice.start), repr(slice.stop)
            ))

    def find(self, *args, **kwargs):
        filters = copy(self._filters)
        filters.update(kwargs)
        if args:
            assert len(args) == 1
            filters.update(args[0])
        return Query(self.col_cls, filters, self._sort, self._limit)

    def sort(self, sort):
        return Query(self.col_cls, self._filters, sort, self._limit)

    @return_future
    def to_list(self, callback):
        Cursor(self, callback)

    @return_future
    def first(self, callback):
        self._limit = 1
        Cursor(self, callback)

    @gen.coroutine
    def find_one(self):
        ret = yield Op(self.col.find_one, self._filters, sort=self._sort, limit=self._limit)
        if ret:
            raise gen.Return(self.col_cls(**ret))
        else:
            raise gen.Return(None)

    def get(self, value, user_callback):
        def callback(elements, error):
            if elements:
                user_callback(elements[0])
            else:
                user_callback(None)
        self.col.find({'_id': value}, callback=callback)


class NoDefaultValue(object):
    pass


class Field(property):
    def __init__(self, type, default=NoDefaultValue):
        # print 'init property', self, type
        super(Field, self).__init__(self.get_value, self.set_value)
        self.name = None
        self.type = type
        self.default = default

    def get_value(self, entity):
        if self.name in entity:
            value = entity[self.name]
        elif self.default is not NoDefaultValue:
            entity[self.name] = value = copy(self.default)
        else:
            raise ValueError('Value not found for "{}"'.format(self.name))
        if not isinstance(value, self.type):
            entity[self.name] = self.type(value)
        return entity[self.name]

    def set_value(self, entity, value):
        entity[self.name] = value

    def __repr__(self):
        return '<Field %i>' % self.name


# TODO
class List(Field):
    pass


# TODO
class Reference(Field):
    pass


class DocumentMeta(type):
    def __new__(mcs, name, bases, dct):
        ret = type.__new__(mcs, name, bases, dct)

        ret._id_name = '_id'
        for key, value in dct.items():
            if isinstance(value, Field):
                field = getattr(ret, key)
                field.name = key

        if bases != (dict,):
            ret._name = name.lower()
            # ret.query = Query(ret)

        return ret


class Document(dict):
    """Base type for mapped classes.

    It is a regular dict, with a little different construction behaviour plus
    one new class method `create` to create a new entry in a collection and
    a new method `delete` to delete an entry.

    Additionally there is a `query` attribute on `Entity` subclasses for


    Example::
         class Fruits(rw.db.Document):
             kind = rw.db.Field(unicode)

         Fuits.find(kind='banana').all()

    Warning: Never use "callback" as key."""
    __metaclass__ = DocumentMeta

    def __init__(self, **kwargs):
        cls = self.__class__
        for field in dir(cls):
            cls_obj = getattr(cls, field)
            if isinstance(cls_obj, Field) and cls_obj.default is not NoDefaultValue:
                getattr(self, field)
        self.update(kwargs)

    # def __getitem__(self, key):
    #     return dict.__getitem__(self, key)
    #
    # def __setitem__(self, key, value):
    #     if key == self._id_name:
    #         dict.__setitem__(self, '_id', value)
    #     else:
    #         dict.__setitem__(self, key, value)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                            ' '.join('%s=%s' % item for item in self.items()))

    def insert(self):
        """Save entry in collection (updates or creates)

        returns Future"""
        return Op(getattr(db, self._name).insert, self)

    def sync_db(self):
        """update entry in collection (updates or creates)

        returns Future"""
        return Op(getattr(db, self._name).update, {'_id': self['_id']}, self)

    @gen.coroutine
    def remove(self, callback=None):
        return getattr(db, self._name).remove(self, callback=callback)

    @classmethod
    def find(cls, *args, **kwargs):
        query = Query(cls)
        return query.find(*args, **kwargs)

    @classmethod
    def by_id(cls, _id):
        if isinstance(_id, basestring):
            _id = bson.ObjectId(_id)
        return Query(cls).find(_id=_id).find_one()

    @property
    def _motor_collection(self):
        return getattr(db, self._name)


class SubDocument(Document):
    pass


class Unicode(Field):
    pass


def using_options(name=None, tablename=None):
    if tablename:
        # elxir compatibility
        name = tablename
    print name


def extract_model(fileobj, keywords, comment_tags, options):
    """Extract messages from rw models

    :param fileobj: the file-like object the messages should be extracted
                    from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: ``iterator``
    """
    import ast, _ast
    print 'extract model', fileobj, keywords, comment_tags, options
    code = ast.parse(fileobj.read()).body
    for statement in code:
        if isinstance(statement, _ast.ClassDef):
            print 'cls', dir(statement)
            for base in statement.bases:
                cls_name = statement.name
                if base.id in ('Document', 'db.Document', 'rw.db.Document'):
                    for line in statement.body:
                        if isinstance(line, _ast.Assign):
                            for name in line.targets:
                                msg = 'model.{}.{}'.format(cls_name, name.id)
                                yield (name.lineno,
                                       'gettext',
                                       msg.format('1', name.id),
                                       ''
                                       )
                                yield (name.lineno,
                                       'gettext',
                                       msg + '-Description',
                                       ''
                                )
                            print line.value
                            print dir(line)
                        # yield (base.lineno)
