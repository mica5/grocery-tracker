import falcon
import os
import sys
import urllib
import subprocess
from dateutil import parser

import jinja2

this_dir = os.path.dirname(os.path.abspath(__file__))
def log(message):
    with open(os.path.join(this_dir, 'logs.txt'), 'a') as fa:
        print(message, file=fa)
sys.path.insert(0, this_dir)

from helpers import load_keys


class HTTPSResource(object):
    """docstring for HTTPSResource"""
    reload_templates = True
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(this_dir, 'templates')))

    keydict = load_keys()

    def __init__(self, *args, **kwargs):
        super(HTTPSResource, self).__init__(*args, **kwargs)
        # self.https = os.environ['HTTPS'].lower() == 'true'
        self.https = True

    def on_get(self, req, resp):

        if self.https and req.scheme.lower() == 'http':
            raise falcon.HTTPMovedPermanently(
                req.url.replace('http', 'https', 1)
            )
        if req.params.get('key', None) not in self.keydict:
            raise falcon.HTTPUnauthorized()

    @staticmethod
    def get_key_param_str(req):
        key = req.params.get('key', None)
        key = 'key={}'.format(key) if key else ''
        return key

    @staticmethod
    def parse_post_data(req):
        raw = req.bounded_stream.read().decode()
        raw = raw.replace('+', ' ')
        data = dict()
        for d in raw.split('&'):
            try:
                k, v = d.split('=')
            except:
                msg = "couldn't parse '{}'".format(d)
                log(msg)
                print(msg)
                raise
            k = urllib.parse.unquote(k).replace('\\r\\n', '\n')
            v = urllib.parse.unquote(v).replace('\\r\\n', '\n')
            data[k] = v
        return data

    @staticmethod
    def _parse_time(timestr):
        time = timestr.strip() or None
        if time:
            time = subprocess.check_output('date -d"{}"'.format(time), shell=True).decode().strip()
            time = parser.parse(time)
        return time


class RootResource(HTTPSResource):
    def on_get(self, req, resp):
        super(RootResource, self).on_get(req, resp)
        resp.content_type = falcon.MEDIA_HTML
        resp.body = """
            <html><head>
            <meta http-equiv="Refresh" content="1; url=index.html?{key}">
            </head><body>
            Redirecting in 1 second...
            </body></html>
        """.format(
            key=self.get_key_param_str(req),
        )

class IndexResource(HTTPSResource):
    def __init__(self, *args, **kwargs):
        super(IndexResource, self).__init__(*args, **kwargs)
        self.template = self._load_template()

    def on_get(self, req, resp):
        super(IndexResource, self).on_get(req, resp)
        resp.content_type = falcon.MEDIA_HTML
        key = req.params.get('key', None)
        key = 'key={}'.format(key) if key else ''

        template = self.template
        if self.reload_templates:
            template = self._load_template()

        resp.body = template.render(key=key)
        return

    @classmethod
    def _load_template(cls):
        with open(os.path.join(this_dir, 'templates/index.html'), 'r') as fr:
            template = cls.jinja_env.from_string(fr.read())
        return template


class TestResource(HTTPSResource):
    def __init__(self, *args, **kwargs):
        super(TestResource, self).__init__(*args, **kwargs)

    def on_post(self, req, resp):
        data = self.parse_post_data(req)

        resp.content_type = falcon.MEDIA_TEXT
        resp.body = str(data)
        return




api = falcon.API()

api.add_route('/', RootResource())
api.add_route('/index.html', IndexResource())
api.add_route('/test', TestResource())
