#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 install|update" >&2
  exit 1
}

[ $# -eq 1 ] || usage

case "$1" in
  install | update)
    echo "$1: not implemented yet" >&2
    exit 1
    ;;
  *) usage ;;
esac
