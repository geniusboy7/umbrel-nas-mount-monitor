#!/bin/sh
# These two plain-text files exist only in the local Umbrel app-data directory.
config_dir="${UMBREL_ROOT}/app-data/geniusnas-monitor/data"
parent_file="${config_dir}/nas-parent-path"
source_file="${config_dir}/expected-source"

if [ ! -r "$parent_file" ] || [ ! -r "$source_file" ]; then
  echo "NAS Mount Monitor: local configuration files are missing" >&2
  return 1
fi

IFS= read -r GENIUSNAS_PARENT_PATH < "$parent_file"
IFS= read -r GENIUSNAS_EXPECTED_SOURCE < "$source_file"

# Limit the bind to one NAS parent under Umbrel's network storage directory.
case "$GENIUSNAS_PARENT_PATH" in
  "${UMBREL_ROOT}/network/"*) ;;
  *) echo "NAS Mount Monitor: invalid NAS parent" >&2; return 1 ;;
esac
case "${GENIUSNAS_PARENT_PATH#"${UMBREL_ROOT}/network/"}" in
  ""|*/*) echo "NAS Mount Monitor: NAS parent must be one directory" >&2; return 1 ;;
esac
if [ ! -d "$GENIUSNAS_PARENT_PATH" ]; then
  echo "NAS Mount Monitor: NAS parent does not exist" >&2
  return 1
fi
case "$GENIUSNAS_EXPECTED_SOURCE" in
  //?*/Media) ;;
  *) echo "NAS Mount Monitor: invalid expected CIFS source" >&2; return 1 ;;
esac

export GENIUSNAS_PARENT_PATH GENIUSNAS_EXPECTED_SOURCE
