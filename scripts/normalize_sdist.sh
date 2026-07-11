#!/usr/bin/env bash
set -euo pipefail

archive="${1:?usage: normalize_sdist.sh DIST.tar.gz}"
epoch="${SOURCE_DATE_EPOCH:-1704067200}"
stage="$(mktemp -d)"
cleanup() { rm -rf "$stage"; }
trap cleanup EXIT

gzip -dc "$archive" | tar -xf - -C "$stage"
root_name="$(find "$stage" -mindepth 1 -maxdepth 1 -type d -printf '%f\n')"
test -n "$root_name"
test "$(find "$stage" -mindepth 1 -maxdepth 1 | wc -l)" -eq 1
tmp_archive="${archive}.normalized"
tar --sort=name --mtime="@${epoch}" --owner=0 --group=0 --numeric-owner \
  --pax-option=delete=atime,delete=ctime -cf - -C "$stage" "$root_name" \
  | gzip -n -9 >"$tmp_archive"
mv "$tmp_archive" "$archive"
