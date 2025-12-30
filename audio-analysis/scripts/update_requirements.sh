#!/bin/bash
set -e

requirement_dir=$(pwd)/audio-analysis/requirements

echo "Updating requirement files with hashes..."

pip install pip-tools
pip-compile --generate-hashes --strip-extras $requirement_dir/base.in -o $requirement_dir/base.txt
pip-compile --generate-hashes --strip-extras $requirement_dir/local.in -o $requirement_dir/local.txt
pip-compile --generate-hashes --strip-extras $requirement_dir/production.in -o $requirement_dir/production.txt

echo "Requirements updated with latest hashes!"
echo "Don't forget to commit the updated .txt files"