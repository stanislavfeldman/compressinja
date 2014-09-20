# MVC web framework in Python with Gevent, Jinja2, Werkzeug

    Jinja2 extension that removes whitespace between HTML tags.

# Usage

    # all spaces will be removed
    env = Environment(extensions=['compressinja.HtmlCompressor'])

    # or some spaces
    env = Environment(extensions=['compressinja.SelectiveHtmlCompressor'])
    #in template
    {% strip %} ... {% endstrip %}

# Known "bugs"
This compressor is run during the conversion between the template and Jinja bytecode.  While this does mean it can be cached and isn't run on every page view, it also adds some serious limitations in parsing.  Basically it comes down to the beginning of tag must be intact, and not within a Jinja tag.  This makes sense after understanding that all Jinja rules are effectively ignored during the conversion.

### Bad:
    <{% if use_div %}div{% else %}span{% endif %} class="warn button"/>
### Parsed as:
    <divspan class="warn button"/>
The issue isn't that "divspan" is an unknown tag, but actually that it is parsed in chunks broken up by Jinja code, like this:

     <
     div
     span
      class="warn button"/>

Which means there is never a complete tag, so the parser can't classify it correctly.

### Okay:
    {% if use_div %}<div{% else %}<span{% endif %} class="warn button"/>
### Parsed as:
    <div<span class="warn button"/>
Although not valid HTML, the parser will understand it as if the div was a closed tag.

### Mixing preformatted tags
    {% if use_div%}<div>{% else %}<pre>{% endif %}This text will
    NOT
    be compressed{% if use_div%}</div>{% else %}</pre>{% endif %}
### Parsed as:
    <div><pre>This text will
    NOT
    be compressed</div></pre>
In this case, keep in mind that the text will not be compressed, and new lines and extra spaces will be preserved because the pre tag may be used.

If you need to use the above examples for some reason, or have more advanced code that injects HTML tags from within Jinja, and the compressor is breaking your HTML, use the SelectiveHtmlCompressor instead, and don't strip areas where the compressor is fragile.

### Bad:
    <table><{{ row_type}}><{{ header_type }}>This is header text</{{ header_type }}></{{ row_type}}></table>
### Parsed as:
    <table><><>This is header text</></></table>
### Final result:
    <table><thead><th>Thisisheadertext</th></thead></table>
Again, because the compressor had no way of knowing this would end up as a block, it stripped all spaces, leaving a confusing output.  Examples like this should be excluded using the SelectiveHtmlCompressor instead.
### Alternative:
    <table>
        {% if row_type %}<{{ row_type }}>{% else %}<thead>{% endif %}
        {% if header_type %}<{{ header_type }}>{% else %}<th>{% endif %}
        This is header text
        {% if header_type %}</{{ header_type }}>{% else %}</th>{% endif %}
        {% if row_type %}</{{ row_type }}>{% else %}</thead>{% endif %}
    </table>
Although much more verbose, providing default values allows the compressor to use those defaults to detect block boundaries and compress the text correctly, even if the defaults are never used in the actual template.  This becomes more fragile when pre tags are possible, and should be avoided in those cases.

# License
This software is licensed under the BSD License. See the license file in the top distribution directory for the full license text.

