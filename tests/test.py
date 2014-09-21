# -*- coding: utf-8 -*-
'''
.. module:: compressinja.test.test
    :synopsis: Test cases for compressinja.html modules.
'''
import unittest
from jinja2 import Environment, TemplateSyntaxError


def html_compress(template_text, params=None):
    '''
    Wrap given template_text in a Jinja environment with the
    HtmlCompressor enabled and return rendered text.
    '''
    params = params or {}
    env = Environment(
        extensions=['compressinja.HtmlCompressor'],
    )
    template = env.from_string(template_text)
    return template.render(params)


class TestHtmlCompressor(unittest.TestCase):
    # pylint: disable=too-many-public-methods
    '''Test cases for compressinja.HtmlCompress.'''

    def test_basic(self):
        '''Verify the compressor can process HTML.'''
        self.assertEqual(
            html_compress('<p></p>'),
            '<p></p>',
        )

    def test_preserve_spaces(self):
        '''Verify the compressor preserves spaces in blocks.'''
        self.assertEqual(
            html_compress('<p>This has spaces.</p>'),
            '<p>This has spaces.</p>',
        )

    def test_strip_whitespace(self):
        '''Verify the compressor removes extra whitespace in blocks.'''
        self.assertEqual(
            html_compress('<div>\n\r\t<p>test</p> </div>'),
            '<div> <p>test</p> </div>',
        )

    def test_whitespace_pre(self):
        '''Verify the compressor doesn't touch whitespace in pre tags.'''
        self.assertEqual(
            html_compress('<pre>\n\t </pre>'),
            '<pre>\n\t </pre>',
        )

    def test_prefix_space(self):
        '''Verify the compressor keeps space within blocks (prefix).'''
        self.assertEqual(
            html_compress('<p>Test <a href="#">link</a></p>'),
            '<p>Test <a href="#">link</a></p>',
        )

    def test_suffix_space(self):
        '''Verify the compressor keeps space within blocks (suffix).'''
        self.assertEqual(
            html_compress('<p><a href="#">link</a> test</p>'),
            '<p><a href="#">link</a> test</p>',
        )

    def test_whitespace_outside_blocks(self):
        '''Verify the compressor strips all spaces between blocks.'''
        self.assertEqual(
            html_compress('<p>test</p>\n\t <p>text</p>'),
            '<p>test</p><p>text</p>'
        )

    def test_self_closing(self):
        '''Verify the compressor can handle self-closing tags.'''
        self.assertEqual(
            html_compress('<p>test <br /> text</p>'),
            '<p>test <br /> text</p>',
        )

    def test_invalid_tags(self):
        '''Verify the compressor raises errors with duplicate close tags.'''
        self.assertRaises(
            TemplateSyntaxError,
            html_compress,
            '<div></div></div>',
        )

    def test_implicit_tags(self):
        '''Verify the compressor handles implicitly closed tags.'''
        self.assertEqual(
            html_compress('<ul><li> te st <li> te st2 </ul>'),
            '<ul><li> te st <li> te st2 </ul>',
        )
        self.assertEqual(
            html_compress('<th>test<td>test2'),
            '<th>test<td>test2',
        )

    def test_misordered_tags(self):
        '''Verify the compressor handles tags with incorrect order.'''
        self.assertEqual(
            html_compress('<p><div></p></div>'),
            '<p><div></p></div>',
        )

    def test_properties(self):
        '''Verify the compressor handles properties.'''
        self.assertEqual(
            html_compress('<div class="test    tag"></div>'),
            '<div class="test tag"></div>'
        )

    def test_jinja_tags(self):
        '''Verify jinja tags aren't modified.'''
        self.assertEqual(
            html_compress(
                '<div class="test {{ test }}"></div>',
                {'test': 'test2'}
            ),
            '<div class="test test2"></div>'
        )

    def test_table_tags(self):
        '''Verify outer table tags don't preserve spaces.'''
        self.assertEqual(
            html_compress(('<table> <tbody> <tr> <td> space '
                           '</td> </tr> </tbody> </table>')),
            '<table><tbody><tr><td> space </td></tr></tbody></table>',
        )

    def test_mixed_tags(self):
        '''Verify stripping whitespace around Jinja tags works.'''
        self.assertEqual(
            html_compress('<table><tbody> {{ "<tr>" }} <td></td>'),
            '<table><tbody><tr><td></td>',
        )

    def test_properties_non_block(self):
        '''Verify properties aren't stripped outside block tags.'''
        self.assertEqual(
            html_compress('<table class="1 2"> <tbody class="2 3">'),
            '<table class="1 2"><tbody class="2 3">'
        )

    def test_broken_pre_tags(self):
        '''
        Verify pre tags aren't respected from Jinja.

        This is a limitation of the compressor, and is not considered a bug
        even though the output is "wrong".
        '''
        self.assertEqual(
            html_compress('{{ "<pre>" }}\n\t {{ "</pre>" }}'),
            '<pre></pre>',
        )

    def test_broken_block_tags(self):
        '''
        Verify block tags aren't respected from Jinja.

        This is a limitation of the compressor, and is not considered a bug
        even though the output is "wrong".
        '''
        self.assertEqual(
            html_compress('{{ "<p>" }} stripping spaces {{ "</p>" }}'),
            '<p>strippingspaces</p>',
        )

    def test_broken_properties(self):
        '''
        Verify property spacing isn't respected with Jinja tags.

        This is a limitation of the compressor, and is not considered a bug
        even though the output is "wrong".
        '''
        self.assertEqual(
            html_compress('{{ "<div" }} class="1 2 3">{{ "</div>" }}'),
            '<divclass="123"></div>',
        )

    def test_broken_mixed_pre_tags(self):
        '''
        Verify pre tags aren't respected from Jinja.

        This is a limitation of the compressor, and is not considered a bug
        even though the output is "wrong".
        '''
        self.assertEqual(
            html_compress(('<{% if false %}div{% else %}pre{% endif %}>\n\t '
                           '</{% if false %}div{% else %}pre{% endif %}>')),
            '<pre></pre>',
        )

    def test_injected_tags(self):
        '''
        Verify injects tags aren't respected from Jinja.

        This is a limitation of the compressor, and is not considered a bug
        even though the output is "wrong".
        '''
        self.assertEqual(
            html_compress(
                ('<table><{{ row_type}}><{{ header_type }}>This is header text'
                 '</{{ header_type }}></{{ row_type}}></table>'),
                params={'row_type': 'thead', 'header_type': 'th'},
            ),
            '<table><thead><th>Thisisheadertext</th></thead></table>',
        )

    def test_partial_mixed_tags(self):
        '''Verify partially injected tags work correctly.'''
        self.assertEqual(
            html_compress(('{% if true %}<table{% else %}<table class="1"'
                           '{% endif %}>This should be compressed')),
            '<table>Thisshouldbecompressed',
        )

    def test_fixed_tags(self):
        '''Verify alternative tag implementation works.'''
        self.assertEqual(
            html_compress(('{% if true %}<pre>{% endif %}\n\t '
                           '{% if true %}</pre>{% endif %}')),
            '<pre>\n\t </pre>',
        )
        self.assertEqual(
            html_compress(('{% if true %}<p>{% endif %} not stripping '
                           'spaces {% if true %}</p>{% endif %}')),
            '<p> not stripping spaces </p>',
        )
        self.assertEqual(
            html_compress(('{% if true %}<div{% endif %} class="1 2 3">'
                           '</div>')),
            '<div class="1 2 3"></div>',
        )
        self.assertEqual(
            html_compress(('{% if true %}<pre{% else %}<div{% endif %}>\n\t '
                           '{% if true %}</pre{% else %}</div{% endif %}>')),
            '<pre>\n\t </pre>',
        )
        self.assertEqual(
            html_compress(
                ('<table>'
                 '{% if row_type %}<{{ row_type }}>{% else %}'
                    '<thead>{% endif %}'
                 '{% if header_type %}<{{ header_type }}>{% else %}'
                    '<th>{% endif %}'
                 'This is header text'
                 '{% if header_type %}</{{ header_type }}>{% else %}'
                    '</th>{% endif %}'
                 '{% if row_type %}</{{ row_type }}>{% else %}'
                    '</thead>{% endif %}'
                 '</table>'),
                params={'row_type': 'thead', 'header_type': 'th'},
            ),
            '<table><thead><th>This is header text</th></thead></table>',
        )

    def test_doctype(self):
        '''Verify !DOCTYPE tags are preserved.'''
        self.assertEqual(
            html_compress('<!DOCTYPE html><html></html>'),
            '<!DOCTYPE html><html></html>',
        )
