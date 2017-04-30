# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# $Id$
"""

A simple Solr client for python.


Features
--------
 * Supports Solr 1.2+
 * Supports http/https and SSL client-side certificates
 * Uses persistent HTTP connections by default
 * Properly converts to/from Solr data types, including datetime objects
 * Supports both querying and update commands (add, delete)
 * Requires Python 2.3+


Connections
-----------
`SolrConnection` can be passed in the following parameters.
Only `url` is required,.

    url -- URI pointing to the Solr instance. Examples:

        http://localhost:8080/solr
        https://solr-server/solr

        Your python install must be compiled with SSL support for the
        https:// schemes to work. (Most pre-packaged pythons are.)

    persistent -- Keep a persistent HTTP connection open.
        Defaults to true.

    timeout -- Timeout, in seconds, for the server to response.
        By default, use the python default timeout (of none?)
        NOTE: This changes the python-wide timeout.

    ssl_key, ssl_cert -- If using client-side key files for
        SSL authentication,  these should be, respectively,
        your PEM key file and certificate file
        
    http_user, http_pass -- If given, include HTTP Basic authentication 
        in all request headers.

Once created, a connection object has the following public methods:

    query(q, fields=None, highlight=None,
          score=True, sort=None, **params)

            q -- the query string.

            fields -- optional list of fields to include. It can be either
                a string in the format that Solr expects ('id,f1,f2'), or
                a python list/tuple of field names.   Defaults to returning
                all fields. ("*")

            score -- boolean indicating whether "score" should be included
                in the field list.  Note that if you explicitly list
                "score" in your fields value, then this parameter is
                effectively ignored.  Defaults to true.

            highlight -- indicates whether highlighting should be included.
                `highlight` can either be `False`, indicating "No" (the
                default),  `True`, incidating to highlight any fields
                included in "fields", or a list of field names.

            sort -- list of fields to sort by.

            Any parameters available to Solr 'select' calls can also be
            passed in as named parameters (e.g., fq='...', rows=20, etc).

            Many Solr parameters are in a dotted notation (e.g.,
            `hl.simple.post`).  For such parameters, replace the dots with
            underscores when calling this method. (e.g.,
            hl_simple_post='</pre'>)

            Returns a Response object

    add(**params)

            Add a document.  Pass in all document fields as
            keyword parameters:

                add(id='foo', notes='bar')

            You must "commit" for the addition to be saved.

    add_many(lst)

            Add a series of documents at once.  Pass in a list of
            dictionaries, where each dictionary is a mapping of document
            fields:

                add_many( [ {'id': 'foo1', 'notes': 'foo'},
                            {'id': 'foo2', 'notes': 'w00t'} ] )

            You must "commit" for the addition to be saved.

    delete(id)

            Delete a document by id.

            You must "commit" for the deletion to be saved.

    delete_many(lst)

            Delete a series of documents.  Pass in a list of ids.

            You must "commit" for the deletion to be saved.

    delete_query(query)

            Delete any documents returned by issuing a query.

            You must "commit" for the deletion to be saved.


    commit(wait_flush=True, wait_searcher=True)

            Issue a commit command.

    optimize(wait_flush=True, wait_searcher=True)

            Issue an optimize command.

    raw_query(**params)

            Send a query command (unprocessed by this library) to
            the Solr server. The resulting text is returned un-parsed.

                raw_query(q='id:1', wt='python', indent='on')

            Many Solr parameters are in a dotted notation (e.g.,
            `hl.simple.post`).  For such parameters, replace the dots with
            underscores when calling this method. (e.g.,
            hl_simple_post='</pre'>)

    close()
            Close the underlying HTTP(S) connection.


Query Responses
---------------

    Calls to connection.query() return a Response object.

    Response objects always have the following properties:

        results -- A list of matching documents. Each document will be a
            dict of field values.

        results.start -- An integer indicating the starting # of documents

        results.numFound -- An integer indicating the total # of matches.

        results.maxScore -- An integer indicating the maximum score assigned
                            to a document. Takes into account all of documents
                            found by the query, not only the current batch.

        header -- A dict containing any responseHeaders.  Usually:

            header['params'] -- dictionary of original parameters used to
                        create this response set.

            header['QTime'] -- time spent on the query

            header['status'] -- status code.

            See Solr documentation for other/typical return values.
            This may be settable at the Solr-level in your config files.


        next_batch() -- If only a partial set of matches were returned
            (by default, 10 documents at a time), then calling
            .next_batch() will return a new Response object containing
            the next set of matching documents. Returns None if no
            more matches.

            This works by re-issuing the same query to the backend server,
            with a new 'start' value.

        previous_batch() -- Same as next_batch, but return the previous
            set of matches.  Returns None if this is the first batch.

    Response objects also support __len__ and iteration. So, the following
    shortcuts work:

        responses = connection.query('q=foo')
        print len(responses)
        for document in responses:
            print document['id'], document['score']


    If you pass in `highlight` to the SolrConnection.query call,
    then the response object will also have a "highlighting" property,
    which will be a dictionary.


Quick examples on use:
----------------------

Example showing basic connection/transactions

    >>> from solr import *
    >>> c = SolrConnection('http://localhost:8983/solr')
    >>> c.add(id='500', name='python test doc', inStock=True)
    >>> c.delete('123')
    >>> c.commit()


Examples showing the search wrapper

    >>> response = c.query('test', rows=20)
    >>> print response.results.start
     0
    >>> for match in response:
    ...     print match['id'],
      0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19
    >>> response = response.next_batch()
    >>> print response.results.start
     20

Enter a raw query, without processing the returned HTML contents.

    >>> print c.raw_query(q='id:[* TO *]', wt='python', rows='10')

"""
import sys
import socket
import http.client
import urllib.parse
import codecs
import urllib.request, urllib.parse, urllib.error
import datetime
import logging
from io import StringIO
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from xml.sax.saxutils import escape, quoteattr
from xml.dom.minidom import parseString
from .util import MultiDict
import collections

__version__ = "0.9.5"

__all__ = ['SolrException', 'Solr', 'SolrConnection',
           'Response', 'SearchHandler']

_python_version = sys.version_info[0]+(sys.version_info[1]/10.0)

# ===================================================================
# Exceptions
# ===================================================================
class SolrException(Exception):
    """An exception thrown by solr connections.

    Detailed information is provided in attributes of the exception object.
    """

    httpcode = 400
    """HTTP response code from Solr."""

    reason = None
    """Error message from the HTTP response sent by Solr."""

    body = None
    """Response body returned by Solr.

    This can contain much more information about the error, including
    tracebacks from the Java runtime.
    """

    def __init__(self, httpcode, reason=None, body=None):
        self.httpcode = httpcode
        self.reason = reason
        self.body = body

    def __repr__(self):
        return 'HTTP code=%s, Reason=%s, body=%s' % (
                    self.httpcode, self.reason, self.body)

    def __str__(self):
        return 'HTTP code=%s, reason=%s' % (self.httpcode, self.reason)


# Decorator (used below)

def committing(function=None):

    def wrapper(self, *args, **kw):
        commit = kw.pop("commit", False)
        optimize = kw.pop("optimize", False)
        query = {}
        if commit or optimize:
            if optimize:
                query["optimize"] = "true"
            elif commit:
                query["commit"] = "true"
            wait_searcher = kw.pop("wait_searcher", True)
            wait_flush = kw.pop("wait_flush", True)
            if not wait_searcher:
                query["waitSearcher"] = "false"
            if not wait_flush:
                query["waitFlush"] = "false"
                query["waitSearcher"] = "false"
        elif "wait_flush" in kw:
            raise TypeError(
                "wait_flush cannot be specified without commit or optimize")
        elif "wait_searcher" in kw:
            raise TypeError(
                "wait_searcher cannot be specified without commit or optimize")
        content = function(self, *args, **kw)
        if content:
            return self._update(content, query)
        # If there's nothing to do (no content), should we issue a
        # commit/optimize if those are requested by the options?

    wrapper.__doc__ = function.__doc__
    wrapper.__name__ = function.__name__
    return wrapper


# ===================================================================
# Connection Objects
# ===================================================================

class Solr:

    def __init__(self, url,
                 persistent=True,
                 timeout=None,
                 ssl_key=None,
                 ssl_cert=None,
                 http_user=None,
                 http_pass=None,
                 post_headers={},
                 max_retries=3,
                 debug=False):

        """
            url -- URI pointing to the Solr instance. Examples:

                http://localhost:8080/solr
                https://solr-server/solr

                Your python install must be compiled with SSL support for the
                https:// schemes to work. (Most pre-packaged pythons are.)

            persistent -- Keep a persistent HTTP connection open.
                Defaults to true

            timeout -- Timeout, in seconds, for the server to response.
                By default, use the python default timeout (of none?)

            ssl_key, ssl_cert -- If using client-side key files for
                SSL authentication,  these should be, respectively,
                your PEM key file and certificate file.

            http_user, http_pass -- If given, include HTTP Basic authentication 
                in all request headers.

        """

        self.scheme, self.host, self.path = urllib.parse.urlparse(url, 'http')[:3]
        self.url = url

        assert self.scheme in ('http','https')

        self.persistent = persistent
        self.reconnects = 0
        self.timeout = timeout
        self.ssl_key = ssl_key
        self.ssl_cert = ssl_cert
        self.max_retries = int(max_retries)

        assert self.max_retries >= 0

        kwargs = {}

        if self.timeout and _python_version >= 2.6 and _python_version < 3:
            kwargs['timeout'] = self.timeout

        if self.scheme == 'https':
            self.conn = http.client.HTTPSConnection(self.host,
                   key_file=ssl_key, cert_file=ssl_cert, **kwargs)
        else:
            self.conn = http.client.HTTPConnection(self.host, **kwargs)

        self.response_version = 2.2
        self.encoder = codecs.getencoder('utf-8')

        # Responses from Solr will always be in UTF-8
        self.decoder = codecs.getdecoder('utf-8')

        # Set timeout, if applicable.
        if self.timeout and _python_version < 2.6:
            self.conn.connect()
            if self.scheme == 'http':
                self.conn.sock.settimeout(self.timeout)
            elif self.scheme == 'https':
                self.conn.sock.sock.settimeout(self.timeout)

        self.xmlheaders = {'Content-Type': 'text/xml; charset=utf-8'}
        self.xmlheaders.update(post_headers)
        if not self.persistent:
            self.xmlheaders['Connection'] = 'close'

        self.form_headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
        
        if http_user is not None and http_pass is not None:
            http_auth = http_user + ':' + http_pass
            http_auth = 'Basic ' + http_auth.encode('base64').strip()
            self.auth_headers = {'Authorization': http_auth}
        else:
            self.auth_headers = {}
        
        if not self.persistent:
            self.form_headers['Connection'] = 'close'

        self.debug = debug
        self.select = SearchHandler(self, "/select")
        self.add = Updater(self).add
        self.add_many = Updater(self).add_many

    def close(self):
        """Close the underlying HTTP(S) connection."""
        self.conn.close()


    # Update interface.

    def updater(self, **field_ops):
        """
        Create an updater which can modify documents.

        For example, to update document ID 1 by setting its 'price' field to
        105 and incremending its 'num_updates' field by 1:
        >>> ops = solr.UpdateOps
        >>> updater = conn.updater(price=ops.SET, num_updates=opts.INC)
        >>> updater.add(id=1, price=105, num_updates=1)
        """
        return Updater(self, field_ops)

    @committing
    def delete(self, id=None, ids=None, queries=None):
        """
        Delete documents by ids or queries.

        Any or all of `id`, `ids`, or `queries` may be given; all
        provided will be used.  If none are provided, no request will be
        sent to Solr.

        `id` is a single value for the schema's unique id field.  `ids`
        is an iterable of unique ids.

        `queries` is an iterable of standard-syntax queries.
        Supports commit-control arguments.
        """
        return self._delete(id=id, ids=ids, queries=queries)

    @committing
    def delete_many(self, ids):
        """
        Delete documents using an iterable of ids.

        This is equivalent to ``delete(ids=[ids])``.
        Supports commit-control arguments.
        """
        return self._delete(ids=ids)

    @committing
    def delete_query(self, query):
        """
        Delete all documents identified by a query.

        This is equivalent to ``delete(queries=[query])``.
        Supports commit-control arguments.
        """
        return self._delete(queries=[query])

    def commit(self, wait_flush=True, wait_searcher=True, _optimize=False):
        """
        Issue a commit command to the Solr server.

        `wait_flush` and `wait_searcher` have the same interpretations as
        the like-name `commit-control arguments`_.

        """
        return self._commit("commit", wait_flush, wait_searcher)

    def optimize(self, wait_flush=True, wait_searcher=True):
        """
        Issue an optimize command to the Solr server.

        `wait_flush` and `wait_searcher` have the same interpretations as
        the like-name `commit-control arguments`_.

        """
        return self._commit("optimize", wait_flush, wait_searcher)

    def _commit(self, verb, wait_flush, wait_searcher):
        if not wait_searcher:  #just handle deviations from the default
            if not wait_flush:
                options = 'waitFlush="false" waitSearcher="false"'
            else:
                options = 'waitSearcher="false"'
        else:
            options = ''
        xstr = '<%s %s/>' % (verb, options)
        return self._update(xstr)

    # Helper methods.

    def _update(self, request, query=None):
        selector = '%s/update%s' % (self.path, qs_from_items(query))
        rsp, data = self._post(selector, request, self.xmlheaders)

        # Detect old-style error response (HTTP response code
        # of 200 with a non-zero status).
        starts = data.startswith
        if starts(b'<result status="') and not starts(b'<result status="0"'):
            data = self.decoder(data)[0]
            parsed = parseString(data)
            status = parsed.documentElement.getAttribute('status')
            if status != 0:
                reason = parsed.documentElement.firstChild.nodeValue
                raise SolrException(rsp.status, reason)
        return data

    def _delete(self, id=None, ids=None, queries=None):
        """
        Delete a specific document by id.
        """
        if not ids:
            ids = []
        if id:
            ids.insert(0, id)
        lst = []
        for id in ids:
            lst.append('<id>%s</id>\n' % escape(str(id)))
        for query in (queries or ()):
            lst.append('<query>%s</query>\n' % escape(str(query)))
        if lst:
            lst.insert(0, '<delete>\n')
            lst.append('</delete>')
            return ''.join(lst)

    def __repr__(self):
        return (
            '<%s (url=%s, persistent=%s, post_headers=%s, reconnects=%s)>'
            % (self.__class__.__name__,
               self.url, self.persistent,
               self.xmlheaders, self.reconnects))

    def _reconnect(self):
        self.reconnects += 1
        self.close()
        self.conn.connect()
        if self.timeout and _python_version < 2.6:
            if self.scheme == 'http':
                self.conn.sock.settimeout(self.timeout)
            elif self.scheme == 'https':
                self.conn.sock.sock.settimeout(self.timeout)

    def _post(self, url, body, headers):
        if self.debug:
            logging.info("solrpy request: %s" % body)

        try:
            _headers = self.auth_headers.copy()
            _headers.update(headers)
            attempts = self.max_retries + 1
            while attempts > 0:
                try:
                    self.conn.request('POST', url, body.encode('UTF-8'), _headers)
                    rsp = check_response_status(self.conn.getresponse())
                    data = rsp.read()
                    if self.debug:
                        logging.info("solrpy got response: %s" % data)
                    return rsp, data
                except (socket.error,
                        http.client.ImproperConnectionState,
                        http.client.BadStatusLine):
                        # We include BadStatusLine as they are spurious
                        # and may randomly happen on an otherwise fine
                        # Solr connection (though not often)
                    self._reconnect()
                    attempts -= 1
                    if attempts <= 0:
                        raise
        finally:
            if not self.persistent:
                self.close()


class SolrConnection(Solr):
    """
    Represents a Solr connection.

    Designed to work with the 2.2 response format (Solr 1.2+),
    though will likely work with 2.1 responses as well.
    """

    # Backward compatible update interfaces.

    def add(self, _commit=False, **fields):
        """
        Add or update a single document with field values given by
        keyword arguments.

        The `_commit` argument is treated specially, causing an immediate
        commit if present.  It may be specified either positionally or as
        a keyword.  If `_commit` is true, the commit will be issued as
        part of the same HTTP request to the Solr server.

        Example::

            connection.add(id="mydoc", author="Me")

        This is equialent to ``solr.Solr.add(fields, commit=_commit)``.
        """
        return Solr.add_many(self, [fields], commit=_commit)

    def add_many(self, docs, _commit=False):
        """
        Add or update multiple documents. with field values for each given
        by dictionaries in the sequence `docs`.

        The `_commit` argument is treated specially, causing an immediate
        commit if present.  It may be specified either positionally or as
        a keyword.  If `_commit` is true, the commit will be issued as
        part of the same HTTP request to the Solr server.

        Example::

            doc1 = {...}
            doc2 = {...}
            connection.add_many([doc1, doc2], _commit=True)

        This is equialent to ``solr.Solr.add_many(docs, commit=_commit)``.
        """
        return Solr.add_many(self, docs, commit=_commit)

    # Backward compatible query interfaces.

    def query(self, *args, **params):
        return self.select(*args, **params)

    def raw_query(self, **params):
        return self.select.raw(**params)


class UpdateOps(object):
    SET = 'set'
    INC = INCREMENT = 'inc'
    ADD = APPEND = 'add'


class Updater(object):
    class FieldFormatter(dict):
        def set_updater(self, name, op):
            self[name] = ('<field name=%s update=%s>%%s</field>' %
                    (quoteattr(name), quoteattr(op))).__mod__

        def __getitem__(self, name):
            try:
                return dict.__getitem__(self, name)
            except KeyError:
                # Default
                return ('<field name=%s>%%s</field>' % quoteattr(name)).__mod__

    def __init__(self, conn, field_ops={}):
        self.conn = conn
        self._update = conn._update
        self.field_formatters = self.__class__.FieldFormatter()
        for name, op in list(field_ops.items()):
            self.field_formatters.set_updater(name, op)

    def add(self, doc):
        """
        Add a document to the Solr server.  Document fields
        should be specified as arguments to this function

        Example::

            doc = {"id": "mydoc", "author": "Me"}
            connection.add(doc)

        Supports commit-control arguments.
        """
        return self.add_many((doc,))

    @committing
    def add_many(self, docs):
        """
        Add several documents to the Solr server.

        `docs`
            An iterable of document dictionaries.

        Supports commit-control arguments.
        """
        lst = ['<add>']
        for doc in docs:
            self.__add(lst, doc)
        lst.append('</add>')
        return ''.join(lst)

    @committing
    def __add(self, lst, fields):
        lst.append('<doc>')
        for field, value in list(fields.items()):
            # Handle multi-valued fields if values
            # is passed in as a list/tuple
            if not isinstance(value, (list, tuple, set)):
                values = [value]
            else:
                values = value

            for value in values:
                # ignore values that are not defined
                if value == None:
                    continue
                # Do some basic data conversion
                if isinstance(value, datetime.datetime):
                    value = utc_to_string(value)
                elif isinstance(value, datetime.date):
                    value = datetime.datetime.combine(
                        value, datetime.time(tzinfo=UTC()))
                    value = utc_to_string(value)
                elif isinstance(value, bool):
                    value = value and 'true' or 'false'

                lst.append(self.field_formatters[field](escape(str(value))))
        lst.append('</doc>')



class SearchHandler(object):

    def __init__(self, conn, relpath="/select", arg_separator="_", parse_response=None):
        self.conn = conn
        self.selector = conn.path + relpath
        self.arg_separator = arg_separator
        # NB: parse_response.wt should be set as appropriate, and parse_response(file_like, params, query) returns a Response object
        self.parse_response = parse_response or parse_xml_response

    def __call__(self, q=None, fields=None, highlight=None,
                 score=True, sort=None, sort_order="asc", **params):
        """
        q is the query string.

        fields is an optional list of fields to include. It can
        be either a string in the format that SOLR expects, or
        a python list/tuple of field names.   Defaults to
        all fields. ("*")

        score indicates whether "score" should be included
        in the field list.  Note that if you explicitly list
        "score" in your fields value, then score is
        effectively ignored.  Defaults to true.

        highlight indicates whether highlighting should be included.
        highlight can either be False, indicating "No" (the default),
        a list of fields in the same format as "fields" or True, indicating
        to highlight any fields included in "fields". If True and no "fields"
        are given, raise a ValueError.

        sort is a list of fields to sort by. See "fields" for
        formatting. Each sort element can have be in the form
        "fieldname asc|desc" as specified by SOLR specs.

        sort_order is the backward compatible way to add the same ordering
        to all the sort field when it is not specified.

        Optional parameters can also be passed in.  Many SOLR
        parameters are in a dotted notation (e.g., hl.simple.post).
        For such parameters, replace the dots with underscores when
        calling this method. (e.g., hl_simple_post='</pre'>)

        Returns a Response instance.
        """
        # Optional parameters with '_' instead of '.' will be converted
        # later by raw_query().

        if highlight:
            params['hl'] = 'true'
            if not isinstance(highlight, (bool, int, float)):
                if not isinstance(highlight, str):
                    highlight = ",".join(highlight)
                params['hl_fl'] = highlight
            else:
                if not fields:
                    raise ValueError("highlight is True and no fields were given")
                elif isinstance(fields, str):
                    params['hl_fl'] = [fields]
                else:
                    params['hl_fl'] = ",".join(fields)

        if q is not None:
            params['q'] = q

        if fields:
            if not isinstance(fields, str):
                fields = ",".join(fields)
        if not fields:
            fields = '*'

        if sort:
            if not sort_order or sort_order not in ("asc", "desc"):
                raise ValueError("sort_order must be 'asc' or 'desc'")
            if isinstance(sort, str):
                sort = [ f.strip() for f in sort.split(",") ]
            sorting = []
            for e in sort:
                if not (e.endswith("asc") or e.endswith("desc")):
                    sorting.append("%s %s" % (e, sort_order))
                else:
                    sorting.append(e)
            sort = ",".join(sorting)
            params['sort'] = sort

        if score and not 'score' in fields.replace(',',' ').split():
            fields += ',score'

        params['fl'] = fields
        params['version'] = self.conn.response_version
        params['wt'] = self.parse_response.wt

        data = self.raw(**params)
        return self.parse_response(StringIO(data.decode('UTF-8')),  params, self)

    def raw(self, **params):
        """
        Issue a query against a SOLR server.

        Return the raw result.  No pre-processing or post-processing
        happens to either input parameters or responses.
        """
        # Clean up optional parameters to match SOLR spec.
        query = []
        to_str = lambda s: s.encode('utf-8') if isinstance(s, str) else s
        for key, value in list(params.items()):
            key = key.replace(self.arg_separator, '.')
            if isinstance(value, (list, tuple)):
                query.extend([(key, to_str(v)) for v in value])
            else:
                query.append((key, to_str(value)))
        request = urllib.parse.urlencode(query, doseq=True)
        rsp, data = self.conn._post(self.selector, request, self.conn.form_headers)
        return data


# ===================================================================
# Response objects
# ===================================================================
class Response(object):
    """
    A container class for a

    A Response object will have the following properties:

          header -- a dict containing any responseHeader values

          results -- a list of matching documents. Each list item will
              be a dict.
    """
    def __init__(self):
        # These are set in ResponseContentHandler.endElement()
        self.header = {}
        self.results = []

        # These are set by parse_xml_response().
        # Used only if .next_batch()/previous_batch() is called
        self._query = None
        self._params = {}

    def _set_params(self, params, query):
        self._query = query
        self._params = params or {}

    def _set_numFound(self, value):
        self._numFound = int(value)

    def _get_numFound(self):
        return self._numFound

    def _del_numFound(self):
        del self._numFound

    numFound = property(_get_numFound, _set_numFound, _del_numFound)

    def _set_start(self, value):
        self._start = int(value)

    def _get_start(self):
        return self._start

    def _del_start(self):
        del self._start

    start = property(_get_start, _set_start, _del_start)

    def _set_maxScore(self, value):
        self._maxScore = float(value)

    def _get_maxScore(self):
        return self._maxScore

    def _del_maxScore(self):
        del self._maxScore

    maxScore = property(_get_maxScore, _set_maxScore, _del_maxScore)

    def __len__(self):
        """
        Return the number of matching documents contained in this set.
        """
        return len(self.results)

    def __iter__(self):
        """
        Return an iterator of matching documents.
        """
        return iter(self.results)

    def next_batch(self):
        """
        Load the next set of matches.

        By default, Solr returns 10 at a time.
        """
        try:
            start = int(self.results.start)
        except AttributeError:
            start = 0

        start += len(self.results)
        params = dict(self._params)
        params['start'] = start
        q = params['q']
        del params['q']
        return self._query(q, **params)

    def previous_batch(self):
        """
        Return the previous set of matches
        """
        try:
            start = int(self.results.start)
        except AttributeError:
            start = 0

        if not start:
            return None

        rows = int(self.header.get('rows', len(self.results)))
        start = max(0, start - rows)
        params = dict(self._params)
        params['start'] = start
        params['rows'] = rows
        q = params['q']
        del params['q']
        return self._query(q, **params)


# ===================================================================
# JSON parsing support
# ===================================================================
class JSONResponseParser(object):
    """
    Solr servers may produce JSON more efficiently than XML; however, it loses some type information.
    In order to re-parse types, a JSONResponseParser may be constructed with a set of translators: callbacks conditioned on paths of object/array keys/indexes.

    Each translator consists of a path to find values requiring translation, and function returning the translation for each value.
    Translators are applied in order in separate passes over the decoded object.
    Each path is a list/tuple where each element is one of:
    * None to match any object attribute or array index;
    * a string to match a particular object attribute;
    * an int to match a particular array index; or
    * a function which evaluates True given keys to descend.

    For example:
        translators = [
            (('response', 'docs', None, 'timestamp'), utc_from_string)
        ]

    would parse the 'timestamp' fields in a query response into datetime objects.

        translators = [
            (('response', 'docs', None, re.compile('_dt$').search), utc_from_string)
        ]

    would parse all fields named '*_dt' into datetime objects.
    """
    wt = 'json'

    def __init__(self, translators=[], load_json=None):
        self._translators = [(self.compile_path(path), cb) for path, cb in translators]
        if load_json is None:
            import json
            load_json = json.load
        self._load_json = load_json

    @classmethod
    def compile_path(cls, path):
        res = []
        for component in reversed(path):
            if component is None:
                res.append(cls.Wildcard())
            elif isinstance(component, collections.Callable):
                res.append(cls.Matcher(component))
            else:
                res.append(cls.Attribute(component))
        return tuple(res)

    class PathComponent(object):
        list_types = (list, tuple)

        def values(self, obj):
            for k, v in self.items(obj):
                yield v

        def items(self, obj):
            if hasattr(obj, 'items'):
                return list(obj.items())
            elif isinstance(obj, self.list_types):
                return enumerate(obj)
            return ()

    class Wildcard(PathComponent):
        def values(self, obj):
            if hasattr(obj, 'values'):
                return list(obj.values())
            elif isinstance(obj, self.list_types):
                return obj
            return ()

    class Attribute(PathComponent):
        def __init__(self, val):
            self.val = val

        def values(self, obj):
            try:
                yield obj[self.val]
            except (KeyError, IndexError, TypeError):
                return

        def items(self, obj):
            try:
                yield self.val, obj[self.val]
            except (KeyError, IndexError, TypeError):
                return

    class Matcher(PathComponent):
        def __init__(self, cb):
            self.cb = cb

        def items(self, obj):
            for k, v in JSONResponseParser.PathComponent.items(self, obj):
                if self.cb(k):
                    yield k, v

    def _translate(self, objects, cpath, callback):
        ind = len(cpath) - 1
        while ind:
            new_objects = []
            component = cpath[ind]
            for obj in objects:
                new_objects.extend(component.values(obj))
            objects = new_objects
            ind -= 1
        for obj in objects:
            for key, val in cpath[ind].items(obj):
                obj[key] = callback(val)

    def translate(self, *objects):
        for translator in self._translators:
            self._translate(objects, *translator)

    def __call__(self, data, params=None, query=None):
        obj = self._load_json(data)
        self.translate(obj)
        if not obj:
            return
        response = Response()
        response._set_params(params, query)
        response.header = obj.pop('responseHeader', None)
        result_data = obj.pop('response', {})
        response.results = result_data.pop('docs', [])
        # note cannot use response.__dict__.update due to use of property in Response
        for k, v in list(result_data.items()) + list(obj.items()):
            if k != 'name':
                setattr(response, k, v)
        return response


# ===================================================================
# xml parsing support
# ===================================================================
def parse_xml_response(data, params, query):
    """
    Parse the XML results of a /select call.
    """
    parser = make_parser()
    handler = ResponseContentHandler()
    parser.setContentHandler(handler)
    parser.parse(data)
    if handler.stack[0].children:
        response = handler.stack[0].children[0].final
        response._set_params(params, query)
        return response
    else:
        return None
parse_xml_response.wt = 'standard'


class ResponseContentHandler(ContentHandler):
    """
    ContentHandler for the XML results of a /select call.
    (Versions 2.2 (and possibly 2.1))
    """
    def __init__(self):
        self.stack = [Node(None, {})]
        self.in_tree = False

    def startElement(self, name, attrs):
        if not self.in_tree:
            if name != 'response':
                raise SolrException(
                    "Unknown XML response from server: <%s ..." % (
                        name))
            self.in_tree = True

        element = Node(name, attrs)

        # Keep track of new node
        self.stack.append(element)

        # Keep track of children
        self.stack[-2].children.append(element)

    def characters (self, ch):
        self.stack[-1].chars.append(ch)

    def endElement(self, name):
        node = self.stack.pop()

        name = node.name
        value = "".join(node.chars)

        if name == 'int':
            node.final = int(value.strip())

        elif name == 'str':
            node.final = value

        elif name == 'null':
            node.final = None

        elif name == 'long':
            node.final = int(value.strip())

        elif name == 'bool':
            node.final = value.strip().lower().startswith('t')

        elif name == 'date':
             node.final = utc_from_string(value.strip())

        elif name in ('float','double', 'status','QTime'):
            node.final = float(value.strip())

        elif name == 'response':
            node.final = response = Response()
            for child in node.children:
                name = child.attrs.get('name', child.name)
                if name == 'responseHeader':
                    name = 'header'
                elif child.name == 'result':
                    name = 'results'
                    for attr_name in child.attrs.getNames():
                        # We already know it is a response
                        if attr_name != "name":
                            setattr(response, attr_name, child.attrs.get(attr_name))

                setattr(response, name, child.final)

        elif name == 'doc':
            node.final = dict(
                    [(cnode.attrs['name'], cnode.final)
                        for cnode in node.children])

        elif name == 'lst':
            node.final = MultiDict(
                    [(cnode.attrs['name'], cnode.final)
                        for cnode in node.children])

        elif name in ('arr',):
            node.final = [cnode.final for cnode in node.children]

        elif name == 'result':
            node.final = Results([cnode.final for cnode in node.children])


        elif name in ('responseHeader',):
            node.final = dict([(cnode.name, cnode.final)
                        for cnode in node.children])
        else:
            raise SolrException("Unknown tag: %s" % name)

        for attr, val in list(node.attrs.items()):
            if attr != 'name':
                setattr(node.final, attr, val)


class Results(list):
    """
    Convenience class containing <result> items
    """
    pass


class Node(object):
    """
    A temporary object used in XML processing. Not seen by end user.
    """
    __slots__ = ('chars', 'name', 'attrs', 'final', 'children')

    def __init__(self, name, attrs):
        """
        Final will eventually be the "final" representation of
        this node, whether an int, list, dict, etc.
        """
        self.chars = []
        self.name = name
        self.attrs = attrs
        self.final = None
        self.children = []

    def __repr__(self):
        return '<%s val="%s" %s>' % (
            self.name,
            "".join(self.chars).strip(),
            ' '.join(['%s="%s"' % (attr, val)
                            for attr, val in list(self.attrs.items())]))


# ===================================================================
# Misc utils
# ===================================================================
def check_response_status(response):
    if response.status != 200:
        ex = SolrException(response.status, response.reason)
        try:
            ex.body = response.read()
        except:
            pass
        raise ex
    return response


# -------------------------------------------------------------------
# Datetime extensions to parse/generate Solr date formats
# -------------------------------------------------------------------
# A UTC class, for parsing Solr's returned dates.
class UTC(datetime.tzinfo):
    """
    UTC timezone.
    """
    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


utc = UTC()

def utc_to_string(value):
    """
    Convert datetimes to the subset of ISO 8601 that Solr expects.
    """
    value = value.astimezone(utc).isoformat()
    if '+' in value:
        value = value.split('+')[0]
    value += 'Z'
    return value

def utc_from_string(value):
    """
    Parse a string representing an ISO 8601 date.
    Note: this doesn't process the entire ISO 8601 standard,
    onle the specific format Solr promises to generate.
    """
    try:
        if not value.endswith('Z') and value[10] == 'T':
            raise ValueError(value)
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        hour = int(value[11:13])
        minute = int(value[14:16])
        microseconds = int(float(value[17:-1]) * 1000000.0)
        second, microsecond = divmod(microseconds, 1000000)
        return datetime.datetime(year, month, day, hour,
            minute, second, microsecond, utc)
    except ValueError:
        raise ValueError ("'%s' is not a valid ISO 8601 Solr date" % value)

def qs_from_items(query):
    # This deals with lists of values since multiple filter queries can
    # be used for a single request.
    qs = ''
    if query:
        sep = '?'
        for k, v in list(query.items()):
            k = urllib.parse.quote(k)
            if isinstance(v, str):
                v = [v]
            for s in v:
                qs += "%s%s=%s" % (sep, k, urllib.parse.quote_plus(s))
                sep = '&'
    return qs
