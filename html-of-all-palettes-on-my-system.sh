#!/bin/bash

# This is a simple script to generate an HTML preview of all palettes on my system.

# Prefix the following line with "pudb3" to debug it.
./gpl_to_html.py -o all-palettes.html \
	$PWD/palettes/*.gpl \
	~/.gimp-2.8/palettes/web_dev.gpl \
	~/.gimp-2.8/palettes/Gimp_Palettes_by_nevit/*.gpl \
	~/.gimp-2.8/palettes/base16-gimp-palette/*.gpl \
	~/.gimp-2.8/palettes/calligra/*.gpl \
	~/.steam/steamapps/common/Aseprite/data/palettes/*.gpl \
	~/.steam/steamapps/common/Aseprite/data/extensions/*palettes/*.gpl \
	/usr/share/gimp/2.0/palettes/*.gpl \
	/usr/share/inkscape/palettes/*.gpl \
	/usr/share/mypaint/palettes/*.gpl

# I don't have Drawpile installed anymore:
# /usr/share/drawpile/drawpile/palettes/*.gpl
# /usr/share/aseprite/data/palettes/*.gpl
