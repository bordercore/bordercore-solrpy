
from solr.core import JSONResponseParser, SearchHandler

__all__ = ['TermVectorHandler']


class TermData(object):
    __slots__ = 'tf df tf_idf offsets position'.split()

    def __init__(self, tf=None, df=None, tf_idf=None, offsets=None, position=None):
        self.tf = tf
        self.df = df
        self.tf_idf = tf_idf
        self.offsets = offsets
        self.position = position

    def __repr__(self):
        return '{0}({1!r}, {2!r})'.format(self.__class__.__name__, self.tf, self.df)


def _parse_named_list(data):
    it = iter(data)
    while True:
        k = it.next()
        try:
            v = it.next()
        except StopIteration:
            raise ValueError('Odd number of elements in named list!')
        yield k, v


def named_list_to_dict(data):
    return dict(_parse_named_list(data))


def parse_term_vector_data(data):
    res = {}
    for k, v in _parse_named_list(data):
        if k == 'tf-idf':
            k = 'tf_idf'
        if k == 'offsets':
            v = slice(v[1], v[3])
        res[k] = v
    return TermData(**res)


def _translate_tv_response(obj):
    obj = named_list_to_dict(obj)
    obj['docs'] = docs = []
    for k, v in obj.items():
        if k.startswith('doc-'):
            docs.append(named_list_to_dict(obj.pop(k)))
    return obj


class TermVectorResponseParser(JSONResponseParser):
    TRANSLATORS = [
        (('termVectors',), _translate_tv_response),
        (('termVectors', 'docs', None, lambda x: x != 'uniqueKey'), named_list_to_dict),
        (('termVectors', 'docs', None, lambda x: x != 'uniqueKey', None), parse_term_vector_data),
    ]

    def __init__(self, extra_translators=[]):
        JSONResponseParser.__init__(self, self.TRANSLATORS + list(extra_translators))


class TermVectorHandler(SearchHandler):

    def __init__(self, conn, relpath="/tvrh", arg_separator="_", parse_response=TermVectorResponseParser()):
        super(TermVectorHandler, self).__init__(conn, relpath, arg_separator, parse_response)

    def __call__(self, q=None, fields='id', tv_fields=None, **params):
        """
        Argumens are as for SearchHandler, however fields defaults to 'id', and
        tv_fields can be a list of fields where tv.all applies, or a dict from
        field name (or None to use query fields) to a TermVectorOptions object.
        """
        if hasattr(tv_fields, 'items'):
            for field, opts in tv_fields.items():
                params.update(opts.to_params())
        else:
            if tv_fields is not None:
                if not isinstance(tv_fields, basestring):
                    tv_fields = ','.join(tv_fields)
                params['tv.fl'] = tv_fields
            params['tv.all'] = 'true'
        return super(TermVectorHandler, self).__call__(q, fields=fields, **params)


class TermVectorOptions(object):
    __slots__ = ('tf', 'df', 'tf_idf', 'offsets', 'positions')

    def __init__(self, tf=False, df=False, tf_idf=False, offsets=False, positions=False):
        if tf_idf is True:
            tf = df = True
        self.tf = tf
        self.df = df
        self.tf_idf = tf_idf
        self.offsets = offsets
        self.positions = positions

    def to_params(self, field=None):
        if field == '*':
            field = None
        if field is None:
            fmt = 'tv.{opt}'
        else:
            fmt = 'f.{field}.tv.{opt}'
        res = dict((fmt.format(field, opt), 'true') for opt in self.__slots__ if getattr(self, opt))
        if len(res) == len(self.__slots__):
            return {fmt.format(field, 'all'), 'true'}
        return res

TermVectorOptions.ALL = TermVectorOptions(*[True for slot in TermVectorOptions.__slots__])
