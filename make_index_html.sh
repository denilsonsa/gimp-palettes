#!/bin/sh

set -ex

./gpl_to_html.py -o index_new.html palettes/*.gpl
sed -i 's|\(href="\)\(palettes/[^"]*\.gpl"\)|\1https://raw.githubusercontent.com/denilsonsa/gimp-palettes/master/\2|g' index_new.html
sed -i 's|\(<body[^>]*>.*\)|\1\n<h1 style="text-align:center">Palettes for GIMP\, Inkscape\, Calligra/Krita... <a href="https://github.com/denilsonsa/gimp-palettes" style="text-decoration:none">https://github.com/denilsonsa/gimp-palettes</a></h1>\n|' index_new.html

git checkout gh-pages
mv index_new.html index.html

if ! git diff --exit-code --quiet ; then
	git add index.html
	git commit -m 'auto-updating index.html'
fi

git checkout master
