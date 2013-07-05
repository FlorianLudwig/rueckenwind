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
    def __init__(self, query):
        self.col_cls = query.col_cls
        col = getattr(db, query.col_cls._name)
        self.db_cursor = col.find(query._filters, sort=query._sort, limit=query._limit)

    @gen.coroutine
    def to_list(self):
        data = yield Op(self.db_cursor.to_list)
        raise gen.Return([self.col_cls(**e) for e in data])

    @gen.coroutine
    def next(self):
        ret = yield self.db_cursor.fetch_next
        if ret:
            raise gen.Return(self.col_cls(**self.db_cursor.next_object()))
        else:
            raise gen.Return(None)

    def skip(self, skip):
        self.db_cursor.skip(skip)
        return self


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

    def to_list(self):
        return Cursor(self).to_list()

    def cursor(self):
        return Cursor(self)

    @gen.coroutine
    def first(self):
        result = yield self.limit(1).to_list()
        raise gen.Return(result[0] if result else None)

    @gen.coroutine
    def count(self):
        col = getattr(db, self.col_cls._name)
        ret = yield Op(col.find(self._filters, sort=self._sort, limit=self._limit).count)
        raise gen.Return(ret)

    def limit(self, limit):
        return Query(self.col_cls, self._filters, self._sort, limit)

    @gen.coroutine
    def find_one(self, *args, **kwargs):
        filters = copy(self._filters)
        filters.update(kwargs)
        if args:
            assert len(args) == 1
            filters.update(args[0])
        ret = yield Op(self.col.find_one, filters, sort=self._sort, limit=self._limit)
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


class TypeCastException(Exception):
    def __init__(self, name, value, typ, e):
        self.type = typ
        self.name = name
        self.value = value
        self.e = str(e)

    def __str__(self):
        return 'TypeCastException on Attrbute {1}:\n' \
               'Cannot cast value {2} to type {0}\n' \
               'Cast Exception was:\n' \
               '{3}'.format(
            repr(self.type),
            self.name,
            repr(self.value),
            self.e
        )


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
            # try:
		     #    entity[self.name] = self.type(value)
            # except TypeCastException as e:
            #     raise e
            # except BaseException as e:
		     #    raise TypeCastException(self.name, value, self.type, e)
        return entity[self.name]

    def set_value(self, entity, value):
        entity[self.name] = value

    def __repr__(self):
        return '<Field %s>' % self.name


def Vector(typ):
    """Generate a Vector class that casts all elements to specified type"""
    class VectorClass(list):
        def __init__(self, values=None):
            if values:
                casted_values = [typ(v) for v in values]
                # casted_values = []
                # try:
                #     for i, value in enumerate(values):
                #         casted_values.append(typ(value))
                # except BaseException as e:
                #     raise TypeCastException(str(i), value, typ, e)

                list.__init__(self, casted_values)

        def _check_type(self, value):
            if not isinstance(value, typ):
                raise ValueError('Vector({}) does not accept items of type {}'.format(
                    repr(typ), repr(type(value))
                ))

        def __setitem__(self, key, value):
            self._check_type(value)
            list.__setitem__(self, key, value)

        def append(self, p_object):
            self._check_type(p_object)
            list.append(self, p_object)

        def extend(self, iterable):
            iterable = list(iterable)
            for value in iterable:
                self._check_type(value)
            list.extend(self, iterable)

    return VectorClass


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

        if bases != (dict,) and '_name' not in dct:
            ret._name = name.lower()
            # ret.query = Query(ret)

        return ret



class DocumentBase(dict):
    __metaclass__ = DocumentMeta


class SubDocument(DocumentBase):
    pass


class Document(DocumentBase):
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

    _id = Field(bson.ObjectId)

    def __init__(self, *args, **kwargs):
        if len(args) > 2:
            raise AttributeError()
        elif len(args) == 1:
            kwargs.update(args[0])
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
    def find_one(cls, *args, **kwargs):
        query = Query(cls)
        return query.find_one(*args, **kwargs)

    @classmethod
    def by_id(cls, _id):
        if not isinstance(_id, cls._id.type):
            _id = cls._id.type(_id)
        return Query(cls).find(_id=_id).find_one()

    @property
    def _motor_collection(self):
        return getattr(db, self._name)


class Unicode(Field):
    pass


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
    code = ast.parse(fileobj.read()).body
    for statement in code:
        if isinstance(statement, _ast.ClassDef):
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
                        # yield (base.lineno)
