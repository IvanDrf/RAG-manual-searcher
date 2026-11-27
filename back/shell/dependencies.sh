#!/bin/sh
set -eu

uv run --locked --no-sync python -m nltk.downloader --exit-on-error -d /usr/local/share/nltk_data stopwords punkt punkt_tab
