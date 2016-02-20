# encoding: utf-8
from future.standard_library import install_aliases
install_aliases()

import io
import re
import os
from urllib.parse import unquote_plus
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound, HTTPFound
from pyramid.response import Response
from pygments import highlight
from pygments.filters import Filter
from pygments import token
from pygments.lexer import RegexLexer
from pygments.lexers import get_lexer_for_filename
from pygments.formatters.svg import SvgFormatter, escape_html
from .git import Symbolic
from .interfaces import IGitFetcher

def extract_callouts(code):
    callouts = []
    result = []
    for l, line in enumerate(re.split(ur'\r\n|\n|\r', code)):
        g = re.search(ur'\s+<---+\s*\((\d+)\)\s*$', line)
        if g is not None:
            line = line[:-len(g.group(0))]
            callouts.append((l, g.group(1)))
        result.append(line)
    return u'\n'.join(result), callouts


class CalloutMarker(unicode):
    def __init__(self, *args, **kwargs):
        self.callouts = kwargs.pop('callouts')

    def __repr__(self):
        return '<%r>%s' % (self.callouts, super(CalloutMarker, self).__repr__())

    def __new__(cls, *args, **kwargs):
        return super(CalloutMarker, cls).__new__(cls, *args)


class CalloutSpecifier(Filter):
    INVALID_CALLOUT = (None, None)

    def __init__(self, **options):
        callouts = options.pop('callouts')
        super(CalloutSpecifier, self).__init__(**options)
        self.callouts = callouts

    def filter(self, lexer, stream):
        last = None
        l = 0
        ci = iter(self.callouts)
        next_callout = next(ci, self.INVALID_CALLOUT)
        callouts = None
        for t, i in stream:
            lines = i.split('\n')
            callouts = None
            for _ in range(0, len(lines) - 1):
                if l == next_callout[0]:
                    if callouts is None:
                        callouts = []
                    callouts.append(next_callout[1])
                    next_callout = next(ci, self.INVALID_CALLOUT)
                l += 1
            if callouts:
                i = CalloutMarker(i, callouts=callouts)
            yield t, i


class CalloutRenderingSvgFormatter(SvgFormatter):
    def format_unencoded(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.

        For our implementation we put all lines in their own 'line group'.
        """
        x = self.xoffset
        y = self.yoffset
        if not self.nowrap:
            if self.encoding:
                outfile.write('<?xml version="1.0" encoding="%s"?>\n' %
                              self.encoding)
            else:
                outfile.write('<?xml version="1.0"?>\n')
            outfile.write('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" '
                          '"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/'
                          'svg10.dtd">\n')
            outfile.write('<svg xmlns="http://www.w3.org/2000/svg">\n')
            outfile.write('<g font-family="%s" font-size="%s">\n' %
                          (self.fontfamily, self.fontsize))
        state = 0
        for ttype, value in tokensource:
            style = self._get_style(ttype)
            tspan = style and '<tspan' + style + '>' or ''
            tspanend = tspan and '</tspan>' or ''
            if isinstance(value, CalloutMarker):
                callouts = value.callouts
            else:
                callouts = []
            value = escape_html(value)
            if self.spacehack:
                value = value.expandtabs().replace(' ', '&#160;')
            parts = value.split('\n')
            for i, part in enumerate(parts):
                if i > 0:
                    if callouts:
                        callout = callouts.pop(0)
                        outfile.write(u'<tspan dx="2em" style="%(callout_style)s">−−−−−−− </tspan><tspan style="%(callout_style)s" text-anchor="middle">⬤</tspan><tspan dx="-1.75ex" text-anchor="middle" style="fill:#ffffff">%(callout)s</tspan>' % dict(callout=callout, callout_style=self.options['callout_style']))
                    if state != 0:
                        outfile.write('</text>')
                    y += self.ystep
                    state = 0
                if state == 0:
                    outfile.write('<text x="%s" y="%s" xml:space="preserve">' % (x, y))
                    state = 1
                outfile.write(tspan + part + tspanend)
        if state != 0:
            outfile.write('</text>')
        if not self.nowrap:
            outfile.write('</g></svg>\n')


class PlainTextLexer(RegexLexer):
    name = 'Plain Text'
    aliases = ['text']
    filenames = ['*.txt']

    tokens = {
        'root': [
            (r'\s+', token.Whitespace),
            (r'\S+', token.Text),
            ]
        }

def generate_image(filename, code, callouts):
    options = dict(
        stripnl=False,
        filters=[
            CalloutSpecifier(callouts=callouts),
            ]
        )
    try:
        lexer = get_lexer_for_filename(filename, **options)
    except:
        lexer = PlainTextLexer(**options)
    retval = highlight(
        code,
        lexer=lexer,
        formatter=CalloutRenderingSvgFormatter(
            callout_style='fill:#888;stroke:none'
            )
        )
    if isinstance(retval, str):
        retval = unicode(retval)
    return Response(
        status=200,
        content_type='image/svg+xml',
        charset='utf-8',
        text=retval
        )


@view_config(route_name='generate', request_method='POST')
def generate(context, request):
    filename = request.matchdict['filename_part']
    code = unquote_plus(request.text)
    code, callouts = extract_callouts(code)
    return generate_image(filename, code, callouts)


def sanitize_path(path):
    r = []
    first = True
    ends_with_sep = False
    for c in path.split(u'/'):
        if c == u'':
            if first:
                r.append(c)
            else:
                ends_with_sep = True
        elif c == u'..':
            r.pop()
            ends_with_sep = False
        elif c != u'.':
            r.append(c)
            ends_with_sep = False
        first = False
    if ends_with_sep:
        r.append(u'')
    return u'/'.join(r)


REPO_URL_PATH_SEPARATOR = u'/+/'


@view_config(route_name='fetch')
def fetch(context, request):
    repo_url_and_path = request.matchdict['repo_url_and_path']
    try:
        repo_url_and_path = repo_url_and_path[0] + u'//' + u'/'.join(repo_url_and_path[1:])
    except IndexError:
        raise HTTPNotFound()
    repo_url, path = repo_url_and_path.split(REPO_URL_PATH_SEPARATOR, 2)
    path = sanitize_path(path)
    g = re.match(ur'(.*)/([^/]+)$', repo_url)
    if g is None:
        raise HTTPNotFound()
    repo_url = g.group(1)
    ref = g.group(2)
    git_fetcher = request.registry.queryUtility(IGitFetcher)
    try:
        r = git_fetcher.fetch(repo_url, ref)
    except Symbolic as e:
        raise HTTPFound(request.route_path('fetch', repo_url_and_path=repo_url + u'/' + e.args[0] + REPO_URL_PATH_SEPARATOR + path, _query=request.query_string))
    except Exception:
        raise HTTPNotFound()
    abs_path = os.path.join(r.working_dir, path)
    if not os.path.exists(abs_path):
        raise HTTPNotFound()
    encoding = request.params.get('encoding')
    code_lines = [l.rstrip(u'\r\n \t') for l in io.open(abs_path, encoding=(encoding or 'utf-8'))]
    line_range = request.params.get('l')
    if line_range is not None:
        start_line, end_line = line_range.split(u'-', 2)
        try:
            if start_line == u'':
                start_line = 0
            else:
                start_line = int(start_line) - 1
                if start_line < 0 or start_line >= len(code_lines):
                    start_line = None
        except ValueError:
            start_line = None
        if start_line is None:
            raise HTTPBadRequest(u'Invalid start line number') 
        try:
            if end_line == u'':
                end_line = -1
            else:
                end_line = int(end_line)
                if end_line < start_line + 1 or end_line > len(code_lines):
                    end_line = None
        except ValueError:
            end_line = None
        if end_line is None:
            raise HTTPBadRequest(u'Invalid end line number') 
        code_lines = code_lines[start_line:end_line]
    else:
        start_line = 0
        end_line = len(code_lines)
    code = u'\n'.join(code_lines)
    callouts = []
    for k, v in request.params.items():
        g = re.match(ur'\[([^]]+)\]', k)
        if g is not None:
            i = g.group(1)
            try:
                l = int(v) - 1
            except ValueError:
                l = None 
            if l is None or l < start_line or l >= end_line:
                raise HTTPBadRequest(u'Invalid line number: %s' % l)
            callouts.append((l - start_line, i))
    callouts = sorted(callouts, key=lambda x: x[0])
    return generate_image(path, code, callouts)

