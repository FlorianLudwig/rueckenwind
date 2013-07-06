import collections


def encode_dict(data):
    if isinstance(data, unicode):
        return data.encode('utf-8')
    elif isinstance(data, basestring):
        return data
    elif isinstance(data, collections.Mapping):
        return dict(map(encode_dict, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(encode_dict, data))
    else:
        return data