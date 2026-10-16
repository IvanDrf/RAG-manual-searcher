#!/bin/sh
set -e 

echo "Install deps for nltk"
uv run -m nltk.downloader punkt_tab
uv run -m nltk.downloader stopwords
