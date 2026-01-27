#!/usr/bin/env bash
# Build & Push: <namespace>/openwebui:morphik-nginx-latest
# - Prüft, ob :latest schon existiert und fragt nach Überschreiben
# - Erwartet: DOCKERHUB_USERNAME, DOCKERHUB_TOKEN, optional DOCKERHUB_ORG

set -euo pipefail

# ---------- Logging ----------
log_i(){ printf '[INFO] %s\n' "$1" >&2; }
log_w(){ printf '[WARN] %s\n' "$1" >&2; }
log_e(){ printf '[ERROR] %s\n' "$1" >&2; }

export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"

# ---------- Defaults / CLI ----------
DEFAULT_ANSWER=""

usage(){
  cat >&2 <<EOF
Usage: $(basename "$0") [--default-answer y|n] [--help]

Options:
  -d, --default-answer [y|n]   Überschreiben ohne Rückfrage.
  -h, --help                   Diese Hilfe.
EOF
}

parse_args(){
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -d|--default-answer)
        [[ $# -ge 2 ]] || { log_e "Option $1 erfordert [y|n]"; exit 2; }
        DEFAULT_ANSWER="$2"; shift 2;;
      --default-answer=*)
        DEFAULT_ANSWER="${1#*=}"; shift;;
      -h|--help) usage; exit 0;;
      *) log_w "Ignoriere unbekannte Option: $1"; shift;;
    esac
  done
  if [[ -n "$DEFAULT_ANSWER" ]]; then
    case "$DEFAULT_ANSWER" in
      y|Y) DEFAULT_ANSWER="y";;
      n|N) DEFAULT_ANSWER="n";;
      *) log_e "--default-answer erwartet 'y' oder 'n'"; exit 2;;
    esac
    log_i "Default-Antwort Überschreiben: '$DEFAULT_ANSWER'"
  fi
}

# ---------- Root finden ----------
find_root(){
  if [[ -n "${ROOT_DIR:-}" && -d "$ROOT_DIR" ]]; then echo "$ROOT_DIR"; return; fi
  if command -v git >/dev/null 2>&1; then
    if r=$(git rev-parse --show-toplevel 2>/dev/null); then
      [[ -d "$r" ]] && { echo "$r"; return; }
    fi
  fi
  echo "$PWD"
}

# ---------- Checks ----------
need_env(){
  local n="$1"
  [[ -n "${!n:-}" ]] || { log_e "$n ist nicht gesetzt!"; exit 1; }
}

ns(){
  if [[ -n "${DOCKERHUB_ORG:-}" ]]; then echo "$DOCKERHUB_ORG"; else echo "$DOCKERHUB_USERNAME"; fi
}

dockerhub_login(){
  log_i "Login bei Docker Hub…"
  echo "$DOCKERHUB_TOKEN" | docker login --username "$DOCKERHUB_USERNAME" --password-stdin >/dev/null
  log_i "Login ok."
}

confirm_overwrite_if_exists(){
  local ref="$1"
  log_i "Prüfe, ob ${ref} bereits existiert…"
  if docker manifest inspect "$ref" >/dev/null 2>&1; then
    log_w "Tag existiert bereits: $ref"
    if [[ -n "$DEFAULT_ANSWER" ]]; then
      [[ "$DEFAULT_ANSWER" == "y" ]] && { log_i "Überschreibe ohne Rückfrage."; return; }
      log_i "Kein Überschreiben (--default-answer n). Abbruch."; exit 0
    fi
    read -r -p "Vorhandenes Image überschreiben? (y/N): " ans
    [[ "$ans" =~ ^[Yy]$ ]] || { log_i "Abgebrochen."; exit 0; }
  else
    log_i "Tag nicht vorhanden. Baue neu."
  fi
}

# ---------- Main ----------
main(){
  parse_args "$@"

  need_env DOCKERHUB_USERNAME
  need_env DOCKERHUB_TOKEN

  local ROOT; ROOT="$(find_root)"
  cd "$ROOT"

  local REPO="openwebui"
  local TAG="morphik-nginx-latest"
  local DOCKERFILE="${DOCKERFILE:-$ROOT/.docker/morphik/nginx/Dockerfile}"

  [[ -f "$DOCKERFILE" ]] || { log_e "Dockerfile nicht gefunden: $DOCKERFILE"; exit 1; }

  local NS; NS="$(ns)"
  local REF="${NS}/${REPO}:${TAG}"

  log_i "Projekt-Root: $ROOT"
  log_i "Dockerfile:   $DOCKERFILE"
  log_i "Repository:   ${NS}/${REPO}"
  log_i "Tag:          ${TAG}"

  dockerhub_login
  confirm_overwrite_if_exists "$REF"

  log_i "Baue Image $REF … (das kann etwas dauern)"
  docker build \
    -f "$DOCKERFILE" \
    -t "$REF" \
    .

  log_i "Push $REF …"
  docker push "$REF"

  log_i "Fertig: $REF"
}

main "$@"
