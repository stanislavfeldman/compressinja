# -*- coding: utf-8 -*-
"""
    A Jinja2 extension that eliminates useless whitespace at template
    compilation time without extra overhead.

    :copyright: (c) 2011 by Armin Ronacher and Feldman Stanislav.
    :license: BSD, see LICENSE for more details.
"""
import re
from jinja2.ext import Extension
from jinja2.lexer import Token, describe_token
from jinja2 import TemplateSyntaxError


_TAG_RE = re.compile(r'(?:<(/?)(!?[a-zA-Z0-9_-]+)\s*|(>\s*))(?s)')
_WS_NORMALIZE_RE = re.compile(r'[ \t\r\n]+')


class StreamProcessContext(object):
    '''Context which stores state information while lexing a document.'''
    # pylint: disable=too-few-public-methods

    def __init__(self, stream):
        self.stream = stream
        self.token = None
        self.stack = []

    def fail(self, message):
        '''Reraise errors as TemplateSyntaxErrors.'''
        raise TemplateSyntaxError(message, self.token.lineno,
                                  self.stream.name, self.stream.filename)

class HtmlCompressor(Extension):
    '''
    Compressor for a Jinja template which removes all excess spaces similar to
    an HTML minifier.
    '''
    # pylint: disable=abstract-method
    isolated_elements = set(('script', 'style', 'noscript', 'textarea', 'pre'))
    void_elements = set(('br', 'img', 'area', 'hr', 'param', 'input',
                         'embed', 'col'))
    block_elements = set(('div', 'p', 'form', 'ul', 'ol', 'li', 'td', 'th',
                          'dl', 'dt', 'dd', 'blockquote', 'h1', 'h2', 'h3',
                          'h4', 'h5', 'h6', 'title'))
    breaking_rules = {
        'p': set(('div', 'p', 'form', 'ul', 'ol', 'li', 'table', 'tr',
                  'tbody', 'thead', 'tfoot', 'td', 'th', 'dl', 'dt', 'dd',
                  'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6')),
        'li': set(('li')),
        'td': set(('td', 'th', 'tr', 'tbody', 'thead', 'tfoot')),
        'th': set(('td', 'th', 'tr', 'tbody', 'thead', 'tfoot')),
        'tr': set(('tr', 'tbody', 'thead', 'tfoot')),
        'tbody': set(('tbody', 'thead', 'tfoot')),
        'thead': set(('tbody', 'thead', 'tfoot')),
        'tfoot': set(('tbody', 'thead', 'tfoot')),
        'dd': set(('dl', 'dt', 'dd')),
        'dt': set(('dl', 'dt', 'dd')),
    }

    def is_isolated(self, stack):
        '''Test if the currently opened tags include a preformatted tag.'''
        for tag in reversed(stack):
            if tag in self.isolated_elements:
                return True
        return False

    def is_block(self, stack):
        '''Test if the currently opened tags include a block tag.'''
        for tag in reversed(stack):
            if tag in self.block_elements:
                return True
        return False

    def is_breaking(self, tag, other_tag):
        '''Test if an implicit tag closure is required.'''
        breaking = self.breaking_rules.get(other_tag)
        return breaking and tag in breaking

    def enter_tag(self, tag, ctx):
        '''Add a tag to the stack.'''
        # Implicitly close any conflicting tags
        while ctx.stack and self.is_breaking(tag, ctx.stack[-1]):
            self.leave_tag(ctx.stack[-1], ctx)
        # Add the tag (as long as it isn't a self-closing tag)
        if tag not in self.void_elements and not tag.startswith('!'):
            ctx.stack.append(tag)

    def leave_tag(self, tag, ctx):
        '''Remove a tag from the stack.'''
        if not ctx.stack:
            # All tags are already closed
            ctx.fail('Tried to leave "%s" but something closed '
                     'it already' % tag)

        if tag == ctx.stack[-1]:
            # Simple case, tag is on top of the stack
            ctx.stack.pop()
            return

        # Implicit closures
        for idx, other_tag in enumerate(reversed(ctx.stack)):
            if other_tag == tag:
                # Remove all tags "on top" of the closed one
                for _ in xrange(idx + 1):
                    ctx.stack.pop()
            elif not self.breaking_rules.get(other_tag):
                # Tags closed in the incorrect order
                break

    def normalize(self, ctx):
        # False warning because of the embedded functions
        # pylint: disable=too-many-branches
        '''Minify a set of HTML data.'''
        def in_tag():
            '''Detect if we are currently in a tag.'''
            inside = False
            for text in output_buffer:
                for char in text:
                    if char == '<':
                        inside = True
                    elif char == '>':
                        inside = False
            return inside

        def write_data(value):
            '''Compress and add data the output buffer.'''
            if not self.is_isolated(ctx.stack):
                # Normalise if we aren't in a preformatted tag
                if not self.is_block(ctx.stack) and not in_tag():
                    # Strip all whitespace outside blocks
                    value = _WS_NORMALIZE_RE.sub('', value)
                else:
                    # Strip duplicates but leave a space placeholder
                    value = _WS_NORMALIZE_RE.sub(' ', value)
                    if not self.is_block(ctx.stack):
                        value = value.replace('> ', '>')
            output_buffer.append(value)

        pos = 0
        output_buffer = []
        for match in _TAG_RE.finditer(ctx.token.value):
            closes, tag, sole = match.groups()
            preamble = ctx.token.value[pos:match.start()]
            write_data(preamble)
            if sole:
                write_data(sole)
            else:
                output_buffer.append(match.group())
                (closes and self.leave_tag or self.enter_tag)(tag, ctx)
            pos = match.end()

        write_data(ctx.token.value[pos:])
        return u''.join(output_buffer)

    def filter_stream(self, stream):
        '''Process all elements in a lexed string.'''
        ctx = StreamProcessContext(stream)
        for token in stream:
            if token.type != 'data':
                # Don't process Jinja tags
                yield token
                continue
            ctx.token = token
            value = self.normalize(ctx)
            yield Token(token.lineno, 'data', value)


class SelectiveHtmlCompressor(HtmlCompressor):
    '''
    Compressor for a Jinja template which removes all excess spaces similar to
    an HTML minifier within {% strip %} and {% endstrip %} tags.
    '''
    # pylint: disable=abstract-method

    def filter_stream(self, stream):
        '''Process all elements in a lexed string between strip tags.'''
        ctx = StreamProcessContext(stream)
        strip_depth = 0
        while 1:
            if stream.current.type == 'block_begin':
                if stream.look().test('name:strip') or \
                   stream.look().test('name:endstrip'):
                    stream.skip()
                    if stream.current.value == 'strip':
                        strip_depth += 1
                    else:
                        strip_depth -= 1
                        if strip_depth < 0:
                            ctx.fail('Unexpected tag endstrip')
                    stream.skip()
                    if stream.current.type != 'block_end':
                        ctx.fail('expected end of block, got %s' %
                                 describe_token(stream.current))
                    stream.skip()
            if strip_depth > 0 and stream.current.type == 'data':
                ctx.token = stream.current
                value = self.normalize(ctx)
                yield Token(stream.current.lineno, 'data', value)
            else:
                yield stream.current
            stream.next()
