#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

mdbook build
netlify deploy --prod
