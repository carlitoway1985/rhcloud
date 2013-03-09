#!/usr/bin/env python
# encoding: utf8

import datetime, time, re, sys, os, os.path, glob
from pprint import pprint, pformat
from urllib import quote
from fnmatch import fnmatch
import bottle
from bottle import (route, run, default_app, 
    request, response, redirect,
    Bottle, static_file, 
    jinja2_template as template, html_escape)

rel_path = lambda x: os.path.join(os.path.realpath(os.path.dirname(__file__)), x)

bottle.TEMPLATE_PATH.append(rel_path('templates'))


static_app = Bottle()
SITE_STATIC_FILES = '|'.join(map(re.escape, [
    'favicon.ico',
    'robots.txt'
]))
@static_app.route('/<filename:path>')
#@static_app.route('/<filename:re:.*(%s)' % SITE_STATIC_FILES)
def server_static(filename):
    return static_file(filename, root='static')

dict_app = Bottle()
dict_app.hostnames = ['def.est.im', '*.def.est.im']

@route('/name/<name>')
def nameindex(name='Stranger'):
    return '<strong>Hello, %s!</strong>' % name

@dict_app.route('/')
@dict_app.route('/<query>')
def index(query=''):
    q = request.query.get('q', '')
    if q:
        return redirect('/%s' % quote(q), code=301)
    return template('index.html', query=query.decode('utf8', 'replace'), req=request.query)

@dict_app.route('/robots.txt')
def robots():
    response.content_type = 'text/plain'
    return """
Sitemap: http://%s/sitemap.xml

User-agent: *
Disallow: /:status
""".strip() % dict_app.hostnames[0]

@dict_app.route('/sitemap.xml')
def sitemap():
    response.content_type = 'text/xml'
    recent_words_xml = '\n'.join([
        ('  <url><loc>http://def.est.im/%s</loc>'
        '<changefreq>monthly</changefreq>'
        '<lastmod>%s</lastmod></url>') % (x, y) for x, y in [
            ('hello', '2013-02-28'),
            ('world', '2013-02-28'),
        ]
    ])
    return """
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>http://def.est.im/</loc><changefreq>hourly</changefreq><lastmod>%s</lastmod></url>
%s
</urlset>
""".strip() % (datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:01:01Z'), recent_words_xml,)
# datetime.date.today().isoformat()

tools_app = Bottle()
tools_app.hostnames = ['t.est.im', '*.t.est.im']


@tools_app.route('/ip<ext:re:\.?\w*>')
def ip(ext):
    "Client IP address"
    return request.environ.get('REMOTE_ADDR', '')

@tools_app.route('/ua<ext:re:\.?\w*>')
def user_agent(ext):
    "Client User-agent"
    return request.environ.get('HTTP_USER_AGENT', '')

@tools_app.route('/uid<ext:re:\.?\w*>', group='test')
def uid_tool(ext):
    return 'uid inter lookup tool.'

@tools_app.route('/echo<ext:re:\.?\w*>')
def echo_headers(ext):
    response.content_type = 'text/plain'
    return pformat(request.environ)


@tools_app.route('/h<ext:re:\.?\w*>')
def http_headers(ext):
    response.content_type = 'text/plain'
    return '\r\n'.join(['%s:\t%s' % (k, v) for k, v in request.environ.iteritems() if k.lower().startswith('http_')])

@tools_app.route('/robots.txt')
def robots():
    response.content_type = 'text/plain'
    return """
User-agent: *
Disallow: /:status

Sitemap: http://%s/sitemap.xml
""".strip() % tools_app.hostnames[0] 

@tools_app.route('/')
def index():
    tools = [{
        'path': tools_app.router.build(x.rule, ext=''), 
        'name': x.callback.__name__.replace('_', ' '), 
        'desc': x.callback.__doc__ or ''} for x in tools_app.routes 
        if x.rule.endswith('<ext:re:\.?\w*>')]
    return template('tools_app_index.html', tools=tools)


# @ToDo: rewrire http://bottlepy.org/docs/dev/_modules/bottle.html
# http://bottlepy.org/docs/dev/api.html

def application(environ, start_response):
    # how to propagate static resources
    default_app().mount('/static', static_app)
    hostname = environ.get('HTTP_HOST', '').lower()
    all_apps = [tools_app, dict_app]+default_app
    for app in all_apps:
        """
        https://github.com/defnull/bottle/blob/0.11.6/bottle.py#L3226
        default_app() will be the the last registered BottlePy App
        iteration ends at default_app()
        """
        hostnames = getattr(app, 'hostnames', [])
        # print hostname, hostnames, all_apps
        if filter(lambda x:fnmatch(hostname, x), hostnames):
            return app(environ, start_response)
    return default_app()(environ, start_response)


if '__main__' == __name__:
    try:
        import readline, rlcompleter; readline.parse_and_bind("tab: complete")
    except:
        pass

    DEV_APP = dict_app # dict_app
    if getattr(DEV_APP, 'hostnames', None):
        DEV_APP.hostnames.extend(['10.*', '127.*', '192.*'])
    else:
        DEV_APP.hostnames = ['10.*', '127.*', '192.*']
    DEV_APP.mount('/static', static_app)

    __import__('BaseHTTPServer').BaseHTTPRequestHandler.address_string = lambda x:x.client_address[0]
    from django.utils import autoreload
    def dev_server():
        run(application, host='0.0.0.0', port=8002, debug=True)
    autoreload.main(dev_server)
