#!/bin/sh

./gpl_to_html.py -o index.html palettes/*.gpl
sed -i 's,\(href="\)\(palettes/[^"]*\.gpl"\),\1https://raw.githubusercontent.com/denilsonsa/gimp-palettes/master/\2,g' index.html
sed -i 's,\(<body[^>]*>.*\),\1\n<h1 style="text-align:center"><a href="https://github.com/denilsonsa/gimp-palettes" style="text-decoration:none">https://github.com/denilsonsa/gimp-palettes</a></h1>\n,' index.html
