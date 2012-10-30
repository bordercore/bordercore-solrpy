
class MultipleValueError(ValueError):
    pass

class MultiDict(dict):
    """
    A dict variant which stores multiple values for each key.

    It aims to provide an interface identical to a standard dict for the case
    where each key has at most one value. Otherwise:
    * __getitem__, get, and setdefault return the last value entered for a key
    * pop(k) and getone(k) may raise MultipleValueError if k corresponds to more than one value
    * additional "*list" methods are provided to handle multi-valued keys
    """

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __repr__(self):
        return 'm{%s}' % ', '.join('%r: %r' % (k, v) for k, v in self.iteritems())

    def copy(self):
        raise NotImplementedError()

    def additem(self, key, value):
        super(MultiDict, self).setdefault(key, []).append(value)

    def __setitem__(self, key, value):
        super(MultiDict, self).__setitem__(key, [value])

    def setdefault(self, key, value):
        return super(MultiDict, self).setdefault(key, [value])[-1]

    def update(self, *args, **kwargs):
        if args:
            if len(args) > 1:
                raise TypeError('Expected at most one positional argument')
            obj = args[0]
            if hasattr(obj, 'iteritems'):
                obj = obj.iteritems()
            elif hasattr(obj, 'items'):
                obj = obj.items()
            for k, v in obj:
                self.additem(k, v)
        for k, v in kwargs.items():
            self.additem(k, v)

    def __getitem__(self, key):
        list_ = super(MultiDict, self).__getitem__(key)
        try:
            return list_[-1]
        except IndexError:
            raise KeyError('%r resulted in an empty list' % key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def getone(self, key, default=None):
        list_ = super(MultiDict, self).get(key, (default,))
        if len(list_) > 1:
            raise MultipleValueError('Key %r has more than one value' % key)
        return list_[-1]

    def getlist(self, key, default=[]):
        return super(MultiDict, self).get(key, default)

    def pop(self, key, default=None):
        try:
            list_ = super(MultiDict, self).pop(key)
        except KeyError:
            return default
        if len(list_) > 1:
            raise MultipleValueError('Key %r has more than one value' % key)
        return list_[0]

    def poplist(self, key, default=[]):
        return super(MultiDict, self).pop(key, default)

    def popitem(self):
        k, list_ = super(MultiDict, self).popitem()
        v = list_.pop()
        if list_:
            super(MultiDict, self).__setitem__(k, list_)
        return k, v

    def iteritems(self):
        for k, list_ in super(MultiDict, self).iteritems():
            for v in list_:
                yield k, v

    def itervalues(self):
        for list_ in super(MultiDict, self).itervalues():
            for v in list_:
                yield v

    def items(self):
        return list(self.iteritems())

    def values(self):
        return list(self.itervalues())
