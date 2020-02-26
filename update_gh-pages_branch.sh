#!/bin/sh

set -ex

./make_index_html.sh index_new.html

git checkout gh-pages
mv index_new.html index.html

if ! git diff --exit-code --quiet ; then
	git add index.html
	git commit -m 'auto-updating index.html'
fi

git checkout master

# Removing write permission to prevent Gimp from accidentally updating these
# palettes and deleting the comments in them.
chmod -w palettes/*.gpl

echo 'To upload all branches: git push --all'
