#!/bin/sh
# Installs or updates Posture on Alpine Linux (OpenRC). Run as root.
set -eu

REPO="Norbiox/posture"
APP=/opt/posture
STATE=/var/lib/posture
LOGS=/var/log/posture
USER_NAME=posture
CONF=/etc/conf.d/posture
INIT=/etc/init.d/posture
BACKUPS_KEPT=5

usage() {
  echo "Usage: $0 install|update" >&2
  exit 1
}

die() {
  echo "error: $*" >&2
  exit 1
}

need_root() {
  [ "$(id -u)" -eq 0 ] || die "run as root"
}

latest_tag() {
  curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" |
    sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p'
}

install_packages() {
  apk add --no-cache bluez dbus curl tar tzdata
  # Alpine's uv package lags behind and cannot fetch Python 3.14, so use the official installer.
  if ! command -v uv >/dev/null 2>&1; then
    curl -fsSL https://astral.sh/uv/install.sh | UV_UNMANAGED_INSTALL=/usr/local/bin sh
  fi
}

start_bluetooth() {
  for service in dbus bluetooth; do
    rc-update add "$service" default
    rc-service "$service" status >/dev/null 2>&1 || rc-service "$service" start
  done
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if bluetoothctl list | grep -q '^Controller'; then
      return 0
    fi
    sleep 1
  done
  die "no Bluetooth adapter visible; pass the USB adapter through to the VM"
}

create_user() {
  if ! id "$USER_NAME" >/dev/null 2>&1; then
    addgroup -S "$USER_NAME"
    adduser -S -D -H -h "$STATE" -s /sbin/nologin -G "$USER_NAME" "$USER_NAME"
  fi
  getent group bluetooth >/dev/null || addgroup -S bluetooth
  # BlueZ's D-Bus policy lets the bluetooth group talk to bluetoothd.
  id -nG "$USER_NAME" | grep -qw bluetooth || adduser "$USER_NAME" bluetooth
  mkdir -p "$APP" "$STATE" "$LOGS"
  chown "$USER_NAME:$USER_NAME" "$APP" "$STATE" "$LOGS"
}

# Downloads the source tarball and the built frontend of release $1 into directory $2.
fetch_release() {
  mkdir -p "$2/frontend/dist"
  curl -fsSL "https://github.com/$REPO/archive/refs/tags/$1.tar.gz" |
    tar -xz -C "$2" --strip-components=1
  curl -fsSL "https://github.com/$REPO/releases/download/$1/posture-frontend-$1.tar.gz" |
    tar -xz -C "$2/frontend/dist"
}

# Prints the database path, honouring a POSTURE_DB override in $CONF.
db_path() {
  (
    POSTURE_DB=
    # shellcheck disable=SC1090 # the file is written by write_conf or by hand
    [ -e "$CONF" ] && . "$CONF"
    echo "${POSTURE_DB:-$STATE/posture.db}"
  )
}

# Copies the database aside while the service is stopped, labelled with the version it belonged to.
backup_db() {
  db=$(db_path)
  [ -f "$db" ] || return 0
  label=$(cat "$APP/VERSION" 2>/dev/null || echo unknown)
  # A fresh mtime, so the pruning below keeps this copy.
  cp "$db" "$db.$label.bak"
  echo "Database backed up to $db.$label.bak"
  # shellcheck disable=SC2012 # backup names are ours and contain no newlines
  ls -t "$db".*.bak | tail -n +$((BACKUPS_KEPT + 1)) | while read -r old; do rm -f "$old"; done
}

# Replaces the code in $APP with release $1. The virtualenv stays, uv sync updates it in place.
# VERSION is written last, so an interrupted run is retried by the next update.
install_release() {
  tmp=$(mktemp -d)
  fetch_release "$1" "$tmp"
  rc-service posture stop >/dev/null 2>&1 || true
  backup_db
  rm -rf "$APP/src" "$APP/frontend"
  cp -a "$tmp"/. "$APP"/
  rm -rf "$tmp"
  chown -R "$USER_NAME:$USER_NAME" "$APP"
  su -s /bin/sh "$USER_NAME" -c "cd $APP && HOME=$STATE uv sync --frozen --no-dev --python 3.14" ||
    die "installing $1 failed, Posture is stopped; fix the cause and run: $0 ${CMD:-install} again"
  echo "$1" >"$APP/VERSION"
}

write_init_script() {
  cat >"$INIT" <<'EOF'
#!/sbin/openrc-run

name="posture"
description="Posture desk controller"
supervisor=supervise-daemon
command=/opt/posture/.venv/bin/posture
command_user=posture:posture
directory=/opt/posture
respawn_delay=5
output_logger="logger -t posture"
error_logger="logger -t posture -p daemon.err"

depend() {
	need dbus bluetooth
	after net
}
EOF
  chmod 755 "$INIT"
}

# Keeps an existing file so settings made by hand survive reinstalls.
write_conf() {
  if [ -e "$CONF" ]; then
    return 0
  fi
  mac=${POSTURE_DESK_MAC:-}
  if [ -z "$mac" ]; then
    printf 'Desk Bluetooth MAC address (AA:BB:CC:DD:EE:FF): '
    read -r mac </dev/tty
  fi
  case $mac in
    [0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]) ;;
    *) die "invalid MAC address: $mac" ;;
  esac
  cat >"$CONF" <<EOF
# Environment for Posture. Every variable is documented in the README.
export POSTURE_DESK_MAC="$mac"
#export POSTURE_TZ="Europe/Warsaw"
#export POSTURE_RETRIES="5"
EOF
}

pair_desk() {
  mac=$(sed -n 's/^export POSTURE_DESK_MAC="\(.*\)"/\1/p' "$CONF")
  if bluetoothctl info "$mac" 2>/dev/null | grep -q 'Paired: yes'; then
    echo "Desk $mac is already paired."
    return 0
  fi
  echo "Hold the Desk's Bluetooth pairing button, then press Enter."
  read -r _ </dev/tty
  bluetoothctl --timeout 15 scan on >/dev/null || true
  bluetoothctl pair "$mac"
  bluetoothctl trust "$mac"
}

cmd_install() {
  need_root
  install_packages
  start_bluetooth
  create_user
  tag=$(latest_tag)
  [ -n "$tag" ] || die "could not find the latest release"
  install_release "$tag"
  write_init_script
  write_conf
  pair_desk
  rc-update add posture default
  rc-service posture restart
  echo "Posture $tag is installed and running."
}

cmd_update() {
  need_root
  [ -f "$APP/VERSION" ] || die "Posture is not installed, run: $0 install"
  current=$(cat "$APP/VERSION")
  tag=$(latest_tag)
  [ -n "$tag" ] || die "could not find the latest release"
  if [ "$tag" = "$current" ]; then
    echo "Already up to date ($current)."
    return 0
  fi
  echo "Updating $current -> $tag"
  install_release "$tag"
  write_init_script
  rc-service posture restart
  echo "Posture $tag is running."
}

[ $# -eq 1 ] || usage

CMD=$1
case "$1" in
  install) cmd_install ;;
  update) cmd_update ;;
  *) usage ;;
esac
