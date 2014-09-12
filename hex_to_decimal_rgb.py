#!/usr/bin/env python3
#
# Replaces colors in #fff or #ffffff notation with three integers: 255 255 255
# Useful to generate a Gimp palette based on list of colors in hex notation.

import re
import sys


def hex_to_rgb(value):
    if len(value) == 3:
        value = value[0] * 2 + value[1] * 2 + value[2] * 2
    return ' '.join(str(x) for x in (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    ))


for line in sys.stdin.readlines():
    line = re.sub(
        r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})',
        lambda match: hex_to_rgb(match.group(1)),
        line)
    print(line.strip())
