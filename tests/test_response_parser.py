import unittest
import solr.core
import datetime
from StringIO import StringIO

# TODO: test other value types
# TODO: test empty responses


class TestJSONResponseParser(unittest.TestCase):
    data = r'''{"responseHeader":{"status":0,"QTime":0,"params":{"q":"text:\"world\"","wt":"json","rows":"1000"}},"response":{"numFound":2,"start":0,"docs":[{"text":"hello world","timestamp":"2012-02-22T00:00:01Z","id":"someid","hits":513},{"text":"farewell world","timestamp":"2012-02-23T00:00:01Z","id":"otherid","hits":111}]}}'''
    expected_header = {u'status': 0, u'QTime': 0, u'params': {u'q': u'text:"world"', u'wt': u'json', u'rows': u'1000'}}

    def _get_response(self, parser, data=data):
        params = object()
        query = object()
        resp = parser(StringIO(data), params, query)
        self.assertIs(resp._query, query)
        self.assertIs(resp._params, params)
        self.assertEquals(resp.header, self.expected_header)
        self.assertEquals(resp.numFound, 2)
        self.assertEquals(resp.start, 0)
        self.assertEquals(len(resp.results), 2)
        for doc in resp.results:
            self.assertListEqual(sorted(doc.keys()), [u'hits', u'id', u'text', u'timestamp',])
        return resp

    def test_no_translation(self):
        resp = self._get_response(solr.core.JSONResponseParser())
        self.assertDictEqual(resp.results[0], {"text":"hello world","timestamp":"2012-02-22T00:00:01Z","id":"someid","hits":513})
        self.assertDictEqual(resp.results[1], {"text":"farewell world","timestamp":"2012-02-23T00:00:01Z","id":"otherid","hits":111})

    def test_index_path(self):
        resp = self._get_response(solr.core.JSONResponseParser([(('response', 'docs', 1, 'text',), len)]))
        self.assertDictEqual(resp.results[0], {"text":"hello world","timestamp":"2012-02-22T00:00:01Z","id":"someid","hits":513})
        self.assertDictEqual(resp.results[1], {"text":14,"timestamp":"2012-02-23T00:00:01Z","id":"otherid","hits":111})

    def test_wildcard_path(self):
        resp = self._get_response(solr.core.JSONResponseParser([(('response', 'docs', None, 'text',), len)]))
        self.assertDictEqual(resp.results[0], {"text":11,"timestamp":"2012-02-22T00:00:01Z","id":"someid","hits":513})
        self.assertDictEqual(resp.results[1], {"text":14,"timestamp":"2012-02-23T00:00:01Z","id":"otherid","hits":111})

    def test_callback_path(self):
        resp = self._get_response(solr.core.JSONResponseParser([(('response', 'docs', lambda k: k == 1, 'text',), len)]))
        self.assertDictEqual(resp.results[0], {"text":"hello world","timestamp":"2012-02-22T00:00:01Z","id":"someid","hits":513})
        self.assertDictEqual(resp.results[1], {"text":14,"timestamp":"2012-02-23T00:00:01Z","id":"otherid","hits":111})

    def test_index_leaf(self):
        resp = self._get_response(solr.core.JSONResponseParser([(('response', 'docs', 1, ), lambda x: x.__setitem__('text', 'no world') or x)]))
        self.assertDictEqual(resp.results[0], {"text":"hello world","timestamp":"2012-02-22T00:00:01Z","id":"someid","hits":513})
        self.assertDictEqual(resp.results[1], {"text":"no world","timestamp":"2012-02-23T00:00:01Z","id":"otherid","hits":111})

    def test_wildcard_leaf(self):
        resp = self._get_response(solr.core.JSONResponseParser([(('response', 'docs', None, None), lambda x: x * 2)]))
        self.assertDictEqual(resp.results[0], {"text":2*"hello world","timestamp":2*"2012-02-22T00:00:01Z","id":2*"someid","hits":2*513})
        self.assertDictEqual(resp.results[1], {"text":2*"farewell world","timestamp":2*"2012-02-23T00:00:01Z","id":2*"otherid","hits":2*111})

    def test_callback_leaf(self):
        resp = self._get_response(solr.core.JSONResponseParser([(('response', 'docs', None, lambda s: s.startswith('te')), len)]))
        self.assertDictEqual(resp.results[0], {"text":11,"timestamp":"2012-02-22T00:00:01Z","id":"someid","hits":513})
        self.assertDictEqual(resp.results[1], {"text":14,"timestamp":"2012-02-23T00:00:01Z","id":"otherid","hits":111})

    def test_translator_order(self):
        t1 = (('response', 'docs', None, 'text'), len)
        t2 = (('response', 'docs', None, 'text'), lambda x: x - 1)
        resp = self._get_response(solr.core.JSONResponseParser([t1, t2]))
        self.assertDictEqual(resp.results[0], {"text":10,"timestamp":"2012-02-22T00:00:01Z","id":"someid","hits":513})
        self.assertDictEqual(resp.results[1], {"text":13,"timestamp":"2012-02-23T00:00:01Z","id":"otherid","hits":111})
        self.assertRaises(TypeError, self._get_response, solr.core.JSONResponseParser([t2, t1]))

    def test_additional_keys(self):
        data = self.data[:-1] + ',"termVectors":"some data"}'
        resp = self._get_response(solr.core.JSONResponseParser(), data)
        self.assertEquals(resp.termVectors, u'some data')


class TestXMLResponseParser(unittest.TestCase):
    data = r'''<?xml version="1.0" encoding="UTF-8"?>
<response>
<lst name="responseHeader"><int name="status">0</int><int name="QTime">0</int><lst name="params"><str name="wt">standard</str><str name="rows">1000</str><str name="q">text:"world"</str></lst></lst><result name="response" numFound="2" start="0"><doc><str name="text">hello world</str><date name="timestamp">2012-02-22T00:00:01Z</date><str name="id">someid</str><int name="hits">513</int></doc><doc><str name="text">farewell world</str><date name="timestamp">2012-02-23T00:00:01Z</date><str name="id">otherid</str><int name="hits">111</int></doc></result>
</response>'''
    expected_header = {u'status': 0, u'QTime': 0, u'params': {u'q': u'text:"world"', u'wt': u'standard', u'rows': u'1000'}}

    def _get_response(self, parser, data=data):
        params = object()
        query = object()
        resp = parser(StringIO(data), params, query)
        self.assertIs(resp._query, query)
        self.assertIs(resp._params, params)
        self.assertEquals(resp.header, self.expected_header)
        self.assertEquals(resp.numFound, 2)
        self.assertEquals(resp.start, 0)
        self.assertEquals(len(resp.results), 2)
        for doc in resp.results:
            self.assertListEqual(sorted(doc.keys()), [u'hits', u'id', u'text', u'timestamp',])
        return resp

    def test_parser(self):
        resp = self._get_response(solr.core.parse_xml_response)
        self.assertDictEqual(resp.results[0], {"text":"hello world","timestamp":datetime.datetime(2012, 02, 22, 0, 0, 1, tzinfo=solr.core.utc),"id":"someid","hits":513})
        self.assertDictEqual(resp.results[1], {"text":"farewell world","timestamp":datetime.datetime(2012, 02, 23, 0, 0, 1, tzinfo=solr.core.utc),"id":"otherid","hits":111})

    def test_additional_keys(self):
        data = self.data[:self.data.rindex('<')] + '<lst name="termVectors"></lst>' + self.data[self.data.rindex('<'):]
        resp = self._get_response(solr.core.parse_xml_response, data)
        self.assertEquals(resp.termVectors, {})

