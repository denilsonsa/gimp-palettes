#!/usr/bin/env python3
#
# Reads a GPL palette file from stdin, outputs the palette with the colors
# sorted. First all grayscale colors, then sorted by hue and lightness.

from colorsys import rgb_to_hls
import re
import sys


colors = []
for line in sys.stdin.readlines():
    if match := re.match(r"^\s*([0-9]{,3})\s+([0-9]{,3})\s+([0-9]{,3})\s*", line):
        h, l, s = rgb_to_hls(
            int(match.group(1)) / 255,
            int(match.group(2)) / 255,
            int(match.group(3)) / 255,
        )
        colors.append((s != 0, h, l, s, line))
    else:
        sys.stdout.write(line)

for row in sorted(colors):
    line = row[-1]
    sys.stdout.write(line)
