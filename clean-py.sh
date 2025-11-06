#! /bin/bash

set -o errexit

echo "Run clean up python"
find . -type f -name "*.pyc" | xargs rm -fr
find . -type d -name __pycache__ | xargs rm -fr
find . -type f -name .DS_Store | xargs rm -fr