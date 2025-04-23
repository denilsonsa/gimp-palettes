#!/bin/sh

filename="$1"

if [ -z "${filename}" ] ; then
	echo "Usage: ./make_index_html.sh index.html"
	exit 1
fi

set -ex

./gpl_to_html.py palettes/*.gpl \
	| sed 's|\(href="\)\(palettes/[^"]*\.gpl"\)|\1https://raw.githubusercontent.com/denilsonsa/gimp-palettes/master/\2|g' \
	| sed 's|\(</head>\)|<script data-goatcounter="https://denilsonsa.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>\n\1|' \
	| sed 's|\(<body[^>]*>.*\)|\1\n<h1 style="text-align:center">Palettes for GIMP, Inkscape, Calligra/Krita, MyPaint, Aseprite, Drawpile... <a href="https://github.com/denilsonsa/gimp-palettes" style="text-decoration:none">https://github.com/denilsonsa/gimp-palettes</a></h1>\n|' \
	> "${filename}"
