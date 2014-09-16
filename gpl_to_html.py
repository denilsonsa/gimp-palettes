#!/usr/bin/env python3

import argparse
import sys
from collections import namedtuple
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

    @classmethod
    def new_from_filename(cls, filename):
        with open(filename) as f:
            return cls.new_from_file(f, filename=filename)

    @classmethod
    def new_from_file(cls, f, filename=None):
        pal = cls()

        if filename:
            pal.filename = filename

        header_magic = next(f)
        assert header_magic.strip() == 'GIMP Palette'

        header_name = next(f)
        assert header_name.startswith('Name:')
        pal.name = header_name.partition('Name:')[2].strip()

        header_columns = next(f)
        assert header_columns.startswith('Columns:')
        pal.columns = int(header_columns.partition('Columns:')[2].strip())

        for line in f:
            line = line.strip()
            if line.startswith('#'):
                pal.comments.append(line[1:].strip())
            else:
                r, g, b, name = line.strip().split(maxsplit=3)
                pal.colors.append(NamedColor(
                    r=int(r),
                    g=int(g),
                    b=int(b),
                    name=name.strip()
                ))

        return pal


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
    margin: 0;
    padding: 0;
    font-family: "Roboto", "Helvetica", "Arial", sans-serif;
    font-size: 12px;
}
.palettes {
    text-align: center;
}
@media (min-width: 432px) {
    .palettes {
        -webkit-columns: 216px;
        columns: 216px;  /* 192px + 2*8px of margin + 2*4px of padding */
        -webkit-column-gap: 0px;
        column-gap: 0px;
    }
}

.palette {
    display: inline-block;
    vertical-align: top;
    width: 192px;
    margin: 8px;
    padding: 4px;
    background: white;
    box-shadow: 0 2px 8px silver;
}
.palette h1,
.palette p{
    font: inherit;
    font-size: 1em;
    margin: 0;
    margin-bottom: 1ex;
    text-align: center;
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

.info {
    white-space: pre-wrap;
}
</style>
</head>
<body>

<p>TODO:
<ul>
<li>Add some styling to the fieldset (probably change it to another element). Should stay always visible (position: fixed), maybe on the right. Not sure yet about smaller screens.</li>
<li>Remove comments from the div. Probably add them as data attributes.</li>
<li>Remove the link, or move the link to the title.</li>
</ul>
</p>

<fieldset>
<label><input type="checkbox" id="toggle_border_checkbox"> Border</label>
<div class="info" id="info_over"></div>
<div class="info" id="info_click"></div>
</fieldset>

<script>
function toggle_border(ev) {
    var elem = document.getElementById('palettes');
    if (document.getElementById('toggle_border_checkbox').checked) {
        elem.classList.add('with-border');
    } else {
        elem.classList.remove('with-border');
    }
}
document.getElementById('toggle_border_checkbox').addEventListener(
    'change', toggle_border);
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
    document.getElementById(info_id).textContent = target.title;
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
        <div class="palette">
            <h1 class="name">{pal.name}</h1>
            <p class="filename"><a href="{pal.filename}">{pal.filename}</a></p>
            {comments}
            <table class="colors">{colors}</table>
        </div>
    ''').strip().format(
        pal=pal,
        comments='\n'.join(
            '<p class="comment">{0}</p>'.format(comment)
            for comment in pal.comments
        ),
        colors=''.join(
            '<tr>{line}</tr>'.format(line=''.join(
                dedent('''\
                    <td
                    class="color"
                    style="background-color:{color.prrggbb}"
                    title="{color.name}
                    {color.pRRGGBB}
                    {color.r}, {color.g}, {color.b}"
                    ></td>
                ''').strip().format(color=color)
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

    for f in options.palettes:
        pal = GimpPalette.new_from_file(f, filename=f.name)
        f.close()
        options.output.write(
            palette_to_html(pal))
        # from pprint import pprint
        # pprint(pal.filename)
        # pprint(pal.name)
        # pprint(pal.columns)
        # pprint(pal.comments)
        # pprint(pal.colors)

    options.output.write(HTML_SUFFIX)
    options.output.close()


if __name__ == '__main__':
    main()
