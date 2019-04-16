#!/usr/bin/env python3

import argparse
import os.path
import sys
from collections import namedtuple
from html import escape
from math import ceil
from textwrap import dedent


def clamp_to_byte(value):
    '''Returns the value clamped to 0..255 range.

    >>> clamp_to_byte(-1)
    0
    >>> clamp_to_byte(0)
    0
    >>> clamp_to_byte(1)
    1
    >>> clamp_to_byte(254)
    254
    >>> clamp_to_byte(255)
    255
    >>> clamp_to_byte(256)
    255
    >>> all(x == clamp_to_byte(x) for x in range(256))
    True
    '''
    return min(255, max(0, value))


def ignore_comments(f):
    for line in f:
        if line.strip() and not line.strip().startswith('#'):
            yield line


class Color:
    '''24-bit RGB color (8-bit per component)

    >>> Color(0, 0, 0) == Color('#000000')
    True
    >>> Color(0, 0, 0) != Color('#000000')
    False
    >>> Color(255, 255, 255) == Color('#FFFFFF')
    True
    >>> Color('ABCDEF') == Color('#ABCDEF')
    True
    >>> Color('#AABBCC') == Color('#ABC')
    True
    >>> Color(0, 0, 1) == Color('#000000')
    False
    >>> Color(0, 0, 1) != Color('#000000')
    True
    >>> bool(Color(0, 0, 0))
    False
    >>> bool(Color(1, 0, 0))
    True
    >>> set([Color(0, 0, 0), Color('#000')])
    {Color(0, 0, 0)}
    >>> x = Color(127, 500, -500)
    >>> (x.r, x.g, x.b)
    (127, 255, 0)
    >>> (x.rr, x.gg, x.bb)
    ('7f', 'ff', '00')
    >>> (x.RR, x.GG, x.BB)
    ('7F', 'FF', '00')
    >>> x.rrggbb
    '7fff00'
    >>> x.RRGGBB
    '7FFF00'
    >>> x.prrggbb
    '#7fff00'
    >>> x.pRRGGBB
    '#7FFF00'
    >>> x.as_gpl()
    '127 255   0'
    >>> x.as_css_rgb()
    'rgb(127, 255, 0)'
    >>> x.as_css_rgb(space='')
    'rgb(127,255,0)'
    >>> (x[0], x[1], x[2])
    (127, 255, 0)
    >>> (x['r'], x['G'], x['b'])
    (127, 255, 0)
    >>> len(x)
    3
    >>> [c * 2 for c in x]
    [254, 510, 0]
    >>> i = iter(x)
    >>> next(i)
    127
    >>> next(i)
    255
    >>> next(i)
    0
    >>> next(i)
    Traceback (most recent call last):
        ...
    StopIteration
    >>> str(x)
    '#7fff00'
    >>> repr(x)
    'Color(127, 255, 0)'
    '''

    __slots__ = ('_r', '_g', '_b')

    def __init__(self, r=None, g=None, b=None):
        '''Can be Initialized with three integers, or with a single string.
        '''
        self._r = 0
        self._g = 0
        self._b = 0

        if r is None and (g is not None or b is not None):
            raise ValueError(
                'Either pass all three parameters, or pass only one')

        if r is not None:
            if g is not None and b is None:
                raise ValueError(
                    'Either pass all three parameters, or pass only one')
            if g is None and b is not None:
                raise ValueError(
                    'Either pass all three parameters, or pass only one')
            if g is not None:  # and b is not None
                self.r = r
                self.g = g
                self.b = b
            else:
                self.set(r)

    def __str__(self):
        return self.prrggbb

    def __repr__(self):
        return 'Color({self.r}, {self.g}, {self.b})'.format(self=self)

    def __eq__(self, other):
        return self.r == other.r and self.g == other.g and self.b == other.b

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.r << 16 | self.g << 8 | self.b

    def __bool__(self):
        '''Black is false, everything else is true.

        Quite arbitrary, I know.
        '''
        return bool(self.r or self.g or self.b)

    def __len__(self):
        return 3

    def __getitem__(self, key):
        if isinstance(key, str):
            if key in 'rR':
                return self.r
            if key in 'gG':
                return self.g
            if key in 'bB':
                return self.b
            else:
                raise KeyError()
        elif isinstance(key, int):
            if key == 0:
                return self.r
            elif key == 1:
                return self.g
            elif key == 2:
                return self.b
            else:
                raise IndexError()
        else:
            raise TypeError()

    def set(self, value):
        '''Receives a single parameter and tries to auto-detect its format.
        '''
        if isinstance(value, str):
            if value.startswith('#'):
                self.prrggbb = value
            else:
                self.rrggbb = value
        else:
            raise ValueError('Unexpected value')

    def _decimal_component_property(attrname):
        return property(
            lambda self: getattr(self, attrname),
            lambda self, value: setattr(self, attrname, clamp_to_byte(int(value))),
            None,  # No deleter.
            'One RGB component as decimal integer. Upon setting,'
            ' automatically converts strings to integers, and automatically'
            ' clamps to 0..255 range.')

    r = _decimal_component_property('_r')
    g = _decimal_component_property('_g')
    b = _decimal_component_property('_b')

    def _hex_component_property(attrname, upper_or_lower):
        return property(
            lambda self: ('{0:02' + upper_or_lower + '}').format(getattr(self, attrname)),
            lambda self, value: setattr(self, attrname, clamp_to_byte(int(value, base=16))),
            None,  # No deleter.
            'One RGB component as hexadecimal. Automatically clamps to'
            ' 00..FF range.')

    rr = _hex_component_property('_r', 'x')
    gg = _hex_component_property('_g', 'x')
    bb = _hex_component_property('_b', 'x')

    RR = _hex_component_property('_r', 'X')
    GG = _hex_component_property('_g', 'X')
    BB = _hex_component_property('_b', 'X')

    @property
    def rrggbb(self):
        '''The color as rrggbb hexadecimal string.'''
        return ''.join([self.rr, self.gg, self.bb])

    @rrggbb.setter
    def rrggbb(self, value):
        original_value = value
        if len(value) == 3:
            value = value[0] + value[0] + value[1] + value[1] + value[2] + value[2]
        if len(value) == 6:
            self.rr = value[0:2]
            self.gg = value[2:4]
            self.bb = value[4:6]
        else:
            raise ValueError('Expected RRGGBB or RGB hex string but found {0!r}'.format(original_value))

    @property
    def RRGGBB(self):
        '''The color as RRGGBB hexadecimal string.'''
        return ''.join([self.RR, self.GG, self.BB])

    @RRGGBB.setter
    def RRGGBB(self, value):
        self.rrggbb = value

    @property
    def prrggbb(self):
        '''The color as #rrggbb hexadecimal string.'''
        return '#' + self.rrggbb

    @prrggbb.setter
    def prrggbb(self, value):
        if value.startswith('#'):
            self.rrggbb = value[1:]
        else:
            raise ValueError(
                'Expected #RRGGBB string but found {0!r}'.format(value))

    @property
    def pRRGGBB(self):
        '''The color as #RRGGBB hexadecimal string.'''
        return '#' + self.RRGGBB

    @pRRGGBB.setter
    def pRRGGBB(self, value):
        self.prrggbb = value

    def as_gpl(self):
        '''Returns the string representation as in *.gpl GIMP Palette.
        '''
        return '{self.r:>3d} {self.g:>3d} {self.b:>3d}'.format(self=self)

    def as_css_rgb(self, space=' '):
        '''Returns the string representation as CSS rgb() function.

        http://www.w3.org/TR/css3-color/#rgb-color
        https://developer.mozilla.org/en-US/docs/Web/CSS/color_value#rgb()
        '''
        return 'rgb({self.r},{space}{self.g},{space}{self.b})'.format(self=self, space=space)


class NamedColor(Color):
    __slots__ = ('name',)

    def __init__(self, name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

    def __repr__(self):
        return 'NamedColor({self.r}, {self.g}, {self.b}, name={self.name!r})'.format(self=self)


class GimpPalette:
    def __init__(self):
        self.name = ''
        self.filename = ''
        self.columns = 0
        self.comments = []
        self.colors = []

    def __repr__(self):
        return '<GimpPalette {0.name!r}, {1} colors over {0.columns} columns, {2} comments, loaded from {0.filename!r}>'.format(self, len(self.colors), len(self.comments))

    def __str__(self):
        return 'GimpPalette {0.name}'.format(self)

    @classmethod
    def new_from_filename(cls, filename):
        with open(filename) as f:
            return cls.new_from_file(f, filename=filename)

    @classmethod
    def new_from_file(cls, f, filename=None):
        pal = cls()

        if filename:
            pal.filename = filename

        lineno = 1
        header_magic = next(f)
        assert header_magic.strip() == 'GIMP Palette', '{0}: Incorrect header at the first line'.format(filename)

        for line in f:
            lineno += 1
            if line.startswith('Name:'):
                pal.name = line.partition('Name:')[2].strip()
            elif line.startswith('Columns:'):
                pal.columns = int(line.partition('Columns:')[2].strip())
            elif line.startswith('Channels:'):
                # Present in Aseprite palette, ignored here.
                pass
            else:
                line = line.strip()
                if line.startswith('#'):
                    pal.comments.append(line[1:].strip())
                elif line:
                    splitted = line.split(maxsplit=3)
                    if len(splitted) == 3:
                        splitted.append('Untitled')
                    assert len(splitted) == 4, 'Invalid line at {0}:{1}'.format(filename, lineno)

                    r, g, b, name = splitted
                    pal.colors.append(NamedColor(
                        r=int(r),
                        g=int(g),
                        b=int(b),
                        name=name.strip()
                    ))

        if pal.name == '':
            pal.name = os.path.basename(filename)

        return pal

    def how_many_unique_colors(self):
        return len(set(c for c in self.colors))


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generates an HTML page from GIMP palettes',
        epilog='This script reads one or more *.gpl files and builds an HTML'
        ' page with demonstrations of all those palettes. Think of it as a'
        ' quick preview of multiple palettes at once.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-t', '--test',
        action='store_true',
        dest='run_tests',
        help='Run the self-test (doctest) of this script'
    )
    parser.add_argument(
        '-o', '--output',
        type=argparse.FileType('w'),
        default='-',
        help='Output HTML file'
    )
    parser.add_argument(
        'palettes',
        type=argparse.FileType('r'),
        nargs='*',
        help='GIMP Palette files (*.gpl)'
    )
    options = parser.parse_args()
    return options


def run_doctests_and_exit():
    import doctest
    failure_count, test_count = doctest.testmod(report=True)
    if failure_count:
        sys.exit(1)
    else:
        sys.exit(0)


HTML_PREFIX='''\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>GIMP palettes</title>
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
html, body {
    background: white;
    color: black;
    margin: 0;
    padding: 0;
    font-family: "Roboto", "Helvetica", "Arial", sans-serif;
    font-size: 12px;
}
.palettes {
    text-align: center;
    -moz-column-gap: 0px;
    -webkit-column-gap: 0px;
    column-gap: 0px;
    -moz-columns: 218px;
    -webkit-columns: 218px;
    columns: 218px;  /* 192px + 2*4px of padding + 2*8px of margin + 2*1px of box-shadow */
}

/* Working around Google Chrome 37 behavior
 * It insists creating a column even if there is no enough room.
 * Still this workaround is not perfect, because it does not take into account the scrollbar width.
 */
@media (max-width: 436px) {
    .palettes {
        -moz-columns: auto auto;
        -webkit-columns: auto auto;
    }
}
@media (orientation: landscape) and (max-width: 564px) {
    .fixed-panel .palettes {
        -moz-columns: auto auto;
        -webkit-columns: auto auto;
    }
}

.interactivepanel {
    background: white;
    font-size: 12px;
    line-height: 16px;
}
.interactivepanel .confcontrols label {
    padding-left: 1ex;
    white-space: nowrap;
}
.interactivepanel .confcontrols label input[type="search"] {
    width: calc(128px - 2ex);
}

.interactivepanel .confcontrols label input[type="checkbox"] {
    margin-top: 0;
    margin-bottom: 0;
    vertical-align: middle;
}

/* 346px = 192px of width + 2*4px of padding + 2*8px of margin + 2*1px of box-shadow + 128px of width */
@media (orientation: landscape) and (min-width: 346px) {
    body.fixed-panel {
        padding-right: 128px;
    }
    .fixed-panel .interactivepanel {
        position: fixed;
        top: 0;
        bottom: 0;
        right: 0;
        width: 128px;

        display: flex;
        flex-direction: column;
    }
    .fixed-panel .interactivepanel .infoboxes {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
    }
    .fixed-panel .interactivepanel .infoboxes .info {
        flex-grow: 1;
        flex-shrink: 1;
        flex-basis: 50%;  /* or 150px, or whatever value */
    }
    .fixed-panel .interactivepanel .infoboxes .info {
        border-width: 0;
        border-style: solid;
        white-space: pre-wrap;
    }
    .fixed-panel .interactivepanel .infoboxes .info#info_over {
        border-color: #808080;
        border-bottom-width: 8px;

        text-align: left;
        border-right-width: 0;
        border-left-width: 0;
        padding: 0;

        /* Vertically aligning the content */
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }
    .fixed-panel .interactivepanel .infoboxes .info#info_click {
        border-color: #C0C0C0;
        border-top-width: 8px;

        text-align: left;
        border-right-width: 0;
        border-left-width: 0;
        padding: 0;
    }
}

@media (orientation: portrait) {
    .interactivepanel {
        position: relative;
        top: 0;
        left: 0;
        right: 0;
    }
    .fixed-panel .interactivepanel {
        position: sticky;
    }
}

@media (orientation: portrait), (orientation: landscape) {
    .interactivepanel .infoboxes {
        display: flex;
        flex-direction: row;
    }
    .interactivepanel .infoboxes .info {
        flex-grow: 1;
        flex-shrink: 1;
        flex-basis: 50%;  /* or 150px, or whatever value */
        white-space: pre;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .interactivepanel .infoboxes .info#info_over {
        text-align: right;
        border-right: 8px solid #808080;
        padding-right: 8px;
    }
    .interactivepanel .infoboxes .info#info_click {
        text-align: left;
        border-left: 8px solid #C0C0C0;
        padding-left: 8px;
    }
}

.palette {
    display: inline-block;
    margin: 8px;
    vertical-align: top;
    width: 192px;
    padding: 4px;
    color: black;
    background: white;
    box-shadow: 0 2px 8px silver;
}
.palette h1,
.palette p {
    font: inherit;
    font-size: 1em;
    margin: 0;
    margin-bottom: 1ex;
    text-align: center;
}
.palette a {
    font: inherit;
    color: inherit;
    text-decoration: inherit;
}
.palette a:hover,
.palette a:focus,
.palette a:active {
    color: blue;
    text-decoration: underline;
}
.palette .properties {
    font-size: 0.875em;
    font-style: italic;
}
.palette .comment {
    font-size: 0.75em;
    word-wrap: break-word;
}
table.colors {
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 8px;
    margin: auto;
    margin-bottom: 1px;  /* for toggling .with-border without moving the elements */
}
.color {
    width: 8px;
    height: 8px;
}

.with-border table.colors,
table.colors.with-border {
    margin-bottom: 0;
}
.with-border .color {
    width: 7px;
    height: 7px;
    border: 1px solid black;
}

.search_filtered {
    display: none;
}
</style>
</head>
<body class="fixed-panel">

<aside class="interactivepanel">
<div class="confcontrols">
    <label><input type="search" id="search_field" placeholder="Search (regex)"></label>
    <label><input type="checkbox" id="toggle_border_checkbox"> Border</label>
    <label><input type="checkbox" id="toggle_fixed_checkbox" checked> Sticky panel</label>
</div>
<div class="infoboxes">
<div class="info" id="info_over">(over palette name)
(over color name)
(#RRGGBB)
(R, G, B)</div>
<div class="info" id="info_click">(clicked palette name)
(clicked color name)
(#RRGGBB)
(R, G, B)</div>
</div>
</aside>

<script>
// This function returns a function that debounces a certain event.
// Arguments:
//   event_handler             - Function (callback) to handle the event.
//   timeout_ms                - Amount of time to wait until event_handler is called.
//   unthrottled_event_handler - Function (callback) to be called on all events. (optional)
function debounce(event_handler, timeout_ms, unthrottled_event_handler) {
    var saved_event;
    var timeout_id;
    return function(ev) {
        clearTimeout(timeout_id);
        saved_event = ev;
        if (unthrottled_event_handler) {
            unthrottled_event_handler(saved_event);
        }
        timeout_id = setTimeout(event_handler, timeout_ms, saved_event);
    };
}

function matches_search_text_for_palette(palette_elem, search_re) {
    for (var child_elem of palette_elem.querySelectorAll('.name, .properties, .comment')) {
        var text = child_elem.textContent.trim();
        if (search_re.test(text)) {
            return true;
        }
    }
    return false;
}
// Event handler to filter all palettes based on the input field.
function filter_palettes(ev) {
    var search_field = ev.target;
    var search_text = search_field.value;
    var search_re;
    try {
        search_re = new RegExp(search_text, 'i');
    } catch(error) {
        search_field.setCustomValidity(error.message);
        search_field.reportValidity();
        return;
    }
    search_field.setCustomValidity('');
    var palettes = document.querySelectorAll('#palettes .palette');
    for (var palette of palettes) {
        palette.classList.toggle(
            'search_filtered',
            !matches_search_text_for_palette(palette, search_re)
        );
    }
}
function clear_form_validity(ev) {
    ev.target.setCustomValidity('');
}
function toggle_class_based_on_checkbox(checkbox, classname, elem) {
    elem.classList.toggle(classname, checkbox.checked);
}
function toggle_border(ev) {
    toggle_class_based_on_checkbox(ev.target, 'with-border', document.getElementById('palettes'));
}
function toggle_fixed(ev) {
    toggle_class_based_on_checkbox(ev.target, 'fixed-panel', document.body);
}

document.getElementById('search_field').addEventListener('input', debounce(filter_palettes, 500, clear_form_validity));
document.getElementById('toggle_border_checkbox').addEventListener('change', toggle_border);
document.getElementById('toggle_fixed_checkbox').addEventListener('change', toggle_fixed);

window.addEventListener('load', function(ev) {
    document.getElementById('search_field').dispatchEvent(new Event('input'));
    document.getElementById('toggle_border_checkbox').dispatchEvent(new Event('change'));
    document.getElementById('toggle_fixed_checkbox').dispatchEvent(new Event('change'));
});
</script>

<div class="palettes" id="palettes">
'''


HTML_SUFFIX='''
</div>

<script>
function mouse_over_or_click_handler(target, info_id) {
    if (!target.classList.contains('color')) {
        return;
    }
    var palette_elem = target.parentNode;
    while (palette_elem && !palette_elem.classList.contains('palette')) {
        palette_elem = palette_elem.parentNode;
    }
    var name = palette_elem.querySelector('.name').textContent;

    var info_elem = document.getElementById(info_id);
    info_elem.textContent = name + '\\n' + target.title;
    info_elem.style.borderColor = target.style.backgroundColor;
}
function mouse_over_handler(ev) {
    return mouse_over_or_click_handler(ev.target, 'info_over');
}
function mouse_click_handler(ev) {
    return mouse_over_or_click_handler(ev.target, 'info_click');
}
document.getElementById('palettes').addEventListener(
    'mouseover', mouse_over_handler);
document.getElementById('palettes').addEventListener(
    'click', mouse_click_handler);
</script>

</body>
</html>
'''


def palette_to_html(pal):
    # This function is a bit ugly just because I wanted to write it as a single
    # statement, just for fun.
    return dedent('''\
        <article class="palette">
            <h1 class="name"><a href="{filename}">{name}</a></h1>
            <p class="properties">{cols}x{rows} ({len} colors, {len_unique} unique)</p>
            {comments}
            <table class="colors">{colors}</table>
        </article>
    ''').strip().format(
        filename=escape(pal.filename),
        name=escape(pal.name),
        cols=pal.columns,
        rows=(ceil(len(pal.colors) / (pal.columns or 16))),
        len=len(pal.colors),
        len_unique=pal.how_many_unique_colors(),
        comments='\n'.join(
            '<p class="comment">{0}</p>'.format(escape(comment))
            for comment in pal.comments
        ),
        colors=''.join(
            '<tr>{line}</tr>'.format(line=''.join(
                dedent('''\
                    <td
                    class="color"
                    style="background-color:{color.prrggbb}"
                    title="{name}
                    {color.pRRGGBB}
                    {color.r}, {color.g}, {color.b}"
                    ></td>
                ''').strip().format(
                    name=escape(color.name),
                    color=color
                )
                for color in pal.colors[offset:offset + (pal.columns or 16)]
            )) for offset in range(0, len(pal.colors), pal.columns or 16)
        ),
    )


def main():
    options = parse_args()

    if options.run_tests:
        run_doctests_and_exit()

    # TODO: Print error if len(options.palettes) == 0.

    options.output.write(HTML_PREFIX)

    palettes = []

    for f in options.palettes:
        pal = GimpPalette.new_from_file(f, filename=f.name)
        f.close()
        palettes.append(pal)

    palettes.sort(key=lambda pal: pal.name.lower())

    for pal in palettes:
        options.output.write(palette_to_html(pal))

    options.output.write(HTML_SUFFIX)
    options.output.close()


if __name__ == '__main__':
    main()
