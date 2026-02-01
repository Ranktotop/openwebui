#!/usr/bin/env bash
# Manual Docker Build and Push Script (Docker Hub)
# Builds GPU and/or CPU variants if their Dockerfiles exist.

set -euo pipefail

# ---------- logging (jetzt auf STDERR!) ----------
log_info()    { printf '[INFO] %s\n' "$1" >&2; }
log_warning() { printf '[WARNING] %s\n' "$1" >&2; }
log_error()   { printf '[ERROR] %s\n' "$1" >&2; }

# ---------- Configuration ----------
IMG_VERSION="0.0.01"                          
TAG_BASE="gptresearcher-pipeline-queue-server"                        
SUBDIR=".docker/gptresearcher/pipeline/queueserver"
REPO_NAME="openwebui"                     

# Enable faster builds (optional)
export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"

# ---------- CLI / Defaults ----------
DEFAULT_ANSWER=""  # akzeptiert 'y' oder 'n'

print_usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  -d, --default-answer [y|n]   Überschreib-Entscheidung ohne Rückfrage treffen.
  -h, --help                   Diese Hilfe anzeigen.

Beispiel:
  $(basename "$0") --default-answer y
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --default-answer=*)
        DEFAULT_ANSWER="${1#*=}"
        shift
        ;;
      -d|--default-answer)
        [[ $# -ge 2 ]] || { log_error "Option $1 erfordert ein Argument [y|n]"; exit 2; }
        DEFAULT_ANSWER="$2"
        shift 2
        ;;
      -h|--help)
        print_usage
        exit 0
        ;;
      *)
        log_warning "Unbekannte Option ignoriert: $1"
        shift
        ;;
    esac
  done

  if [[ -n "$DEFAULT_ANSWER" ]]; then
    # trim & validieren
    DEFAULT_ANSWER="$(printf '%s' "$DEFAULT_ANSWER" | tr -d ' \t\r\n')"
    case "$DEFAULT_ANSWER" in
      y|Y) DEFAULT_ANSWER="y" ;;
      n|N) DEFAULT_ANSWER="n" ;;
      *)
        log_error "--default-answer erwartet 'y' oder 'n', erhalten: '$DEFAULT_ANSWER'"
        exit 2
        ;;
    esac
    log_info "Default-Antwort für Überschreiben: '$DEFAULT_ANSWER'"
  fi
}


# ---------- Helpers ----------
sanitize_ref() {
  # schneidet CR und umgebende Whitespaces ab
  printf '%s' "$1" | tr -d '\r' | sed -e 's/^[[:space:]]\+//' -e 's/[[:space:]]\+$//'
}

# ---------- Project root detection ----------
find_project_root() {
  # 1) Respektiere vorgesetztes ROOT_DIR
  if [[ -n "${ROOT_DIR:-}" && -d "$ROOT_DIR" ]]; then
    echo "$ROOT_DIR"
    return 0
  fi

  # 2) Git-Root
  if command -v git >/dev/null 2>&1; then
    if GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
      [[ -d "$GIT_ROOT" ]] && { echo "$GIT_ROOT"; return 0; }
    fi
  fi

  # 3) Hochlaufen bis Ordnername == $REPO_NAME
  local dir="$PWD"
  while [[ "$dir" != "/" ]]; do
    if [[ "$(basename "$dir")" == "$REPO_NAME" ]]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done

  return 1
}

ROOT_DIR="$(find_project_root)" || {
  log_error "Konnte Projektwurzel '$REPO_NAME' nicht finden. Setze ROOT_DIR manuell (export ROOT_DIR=/pfad/zu/$REPO_NAME)."
  exit 1
}
cd "$ROOT_DIR"

WORKER_DIR="$ROOT_DIR/$SUBDIR"
DOCKERFILE="$WORKER_DIR/Dockerfile"

# ---------- Env checks ----------
check_env_vars() {
  if [[ -z "${DOCKERHUB_USERNAME:-}" ]]; then
    log_error "DOCKERHUB_USERNAME ist nicht gesetzt!"
    echo "Bitte setzen: export DOCKERHUB_USERNAME=dein-user" >&2
    exit 1
  fi
  if [[ -z "${DOCKERHUB_TOKEN:-}" ]]; then
    log_error "DOCKERHUB_TOKEN ist nicht gesetzt!"
    echo "Bitte setzen: export DOCKERHUB_TOKEN=dein-token" >&2
    exit 1
  fi
}

# Resolve Docker Hub namespace (org overrides username)
get_namespace() {
  if [[ -n "${DOCKERHUB_ORG:-}" ]]; then
    echo "$DOCKERHUB_ORG"
  else
    echo "$DOCKERHUB_USERNAME"
  fi
}

# Login to DockerHub
login_dockerhub() {
  log_info "Logging into Docker Hub..."
  if echo "$DOCKERHUB_TOKEN" | docker login --username "$DOCKERHUB_USERNAME" --password-stdin >/dev/null 2>&1; then
    log_info "Successfully logged into Docker Hub"
  else
    log_error "Failed to login to Docker Hub"
    exit 1
  fi
}

# Check if image tag already exists on Docker Hub
check_image_exists_dh() {
  local ns="$1" # Docker Hub namespace. Usually username or org
  local tag_prefix="$2"   # e.g.: gptresearcher-pipeline-queue-server-default
  local image_tag="${tag_prefix}-${IMG_VERSION}" # e.g.: gptresearcher-pipeline-queue-server-default-0.0.01
  local ref="${ns}/${REPO_NAME}:${image_tag}" # e.g.: username/openwebui:gptresearcher-pipeline-queue-server-default-0.0.01

  log_info "Checking if image version ${ref} already exists on Docker Hub..."
  if docker manifest inspect "$ref" >/dev/null 2>&1; then
    log_warning "Image version ${ref} already exists on Docker Hub"

    if [[ -n "$DEFAULT_ANSWER" ]]; then
      if [[ "$DEFAULT_ANSWER" == "y" ]]; then
        log_info "Überschreiben ohne Rückfrage (per --default-answer y)."
        return 0
      else
        log_info "Kein Überschreiben (per --default-answer n). Abbruch."
        exit 0
      fi
    fi

    read -r -p "Do you want to overwrite the existing image? (y/N): " reply
    echo >&2
    if [[ ! "$reply" =~ ^[Yy]$ ]]; then
      log_info "Aborted by user"
      exit 0
    fi
  else
    log_info "Image version ${ref} does not exist, proceeding with build"
  fi
}

# Build Docker image
build_docker_image() {
  local ns="$1"             # Docker Hub namespace. Usually username or org
  local tag_prefix="$2"     # e.g.: gptresearcher-pipeline-queue-server-default
  local dockerfile="$3"     # path to Dockerfile
  local versioned="${ns}/${REPO_NAME}:${tag_prefix}-${IMG_VERSION}" # e.g.: username/openwebui:gptresearcher-pipeline-queue-server-default-0.0.01

  log_info "Building Docker image: ${versioned}"
  log_info "Dockerfile: ${dockerfile}"
  log_info "This may take several minutes..."

  if docker build \
      --build-arg VERSION="$IMG_VERSION" \
      -t "$versioned" \
      -f "$dockerfile" .; then
    log_info "Successfully built Docker image"
    printf '%s\n' "$versioned"   # <-- einziges STDOUT dieser Funktion! 
  else
    log_error "Failed to build Docker image"
    exit 1
  fi
}

# Tag & Push Docker image to Docker Hub
push_docker_image() {
  local versioned_raw="$1" # e.g.: username/openwebui:gptresearcher-pipeline-queue-server-default-0.0.01
  local ns="$2" # Docker Hub namespace. Usually username or org
  local tag_prefix="$3"   # e.g.: gptresearcher-pipeline-queue-server-default

  local versioned
  versioned="$(sanitize_ref "$versioned_raw")" # e.g.: username/openwebui:gptresearcher-pipeline-queue-server-default-0.0.01

  local latest="${ns}/${REPO_NAME}:${tag_prefix}-latest" # e.g.: username/openwebui:gptresearcher-pipeline-queue-server-default-latest

  log_info "Pushing versioned Docker image: $versioned"
  docker push "$versioned" || { log_error "Failed to push versioned image"; exit 1; }
  log_info "Successfully pushed versioned image"

  log_info "Tagging and pushing as ${tag_prefix}-latest..."
  docker tag "$versioned" "$latest"
  docker push "$latest" || { log_error "Failed to push latest image"; exit 1; }
  log_info "Successfully pushed latest image"
}

# Cleanup local images
cleanup_images() {
  local ns="$1" # Docker Hub namespace. Usually username or org
  local tag_prefix="$2"  # e.g.: gptresearcher-pipeline-queue-server-default
  local versioned="${ns}/${REPO_NAME}:${tag_prefix}-${IMG_VERSION}" # e.g.: username/openwebui:gptresearcher-pipeline-queue-server-default-0.0.01
  local latest="${ns}/${REPO_NAME}:${tag_prefix}-latest" # e.g.: username/openwebui:gptresearcher-pipeline-queue-server-default-latest

  log_info "Cleaning up local Docker images..."
  docker rmi "$versioned" 2>/dev/null || true
  docker rmi "$latest" 2>/dev/null || true
  log_info "Cleanup completed"
}

# Build+Push for a single variant (gpu/cpu)
build_and_push_variant() {
  local variant="$1"         # e.g.: "default"
  local dockerfile="$2"      # path to Dockerfile
  local ns="$3"              # Docker Hub namespace. Usually username or org

  local tag_prefix="${TAG_BASE}-${variant}" # e.g.: gptresearcher-pipeline-queue-server-default

  log_info "----- Processing variant: ${variant} > $tag_prefix-----"
  check_image_exists_dh "$ns" "$tag_prefix"

  local versioned_image
  versioned_image="$(build_docker_image "$ns" "$tag_prefix" "$dockerfile")"  # nur Ref kommt zurück -> e.g.: username/openwebui:gptresearcher-pipeline-queue-server-default-0.0.01
  push_docker_image "$versioned_image" "$ns" "$tag_prefix"
  cleanup_images "$ns" "$tag_prefix"
  log_info "----- Completed variant: ${variant} > $tag_prefix -----"
}

# Main execution
main() {
  parse_args "$@"

  log_info "Starting manual Docker build and push for $TAG_BASE" # e.g.: gptresearcher-pipeline-queue-server
  log_info "Image version: $IMG_VERSION" # e.g.: 0.0.01
  log_info "Repository: $REPO_NAME" # e.g.: openwebui
  log_info "Projekt-Root: $ROOT_DIR"

  # Determine which variants to build
  local variants=()
  if [[ -f "$DOCKERFILE" ]]; then
    variants+=("") # "default" variant
    log_info "Found Dockerfile: $DOCKERFILE"
  else
    log_warning "Dockerfile not found: $DOCKERFILE"
  fi
  if [[ ${#variants[@]} -eq 0 ]]; then
    log_error "No Dockerfiles found. Nothing to build."
    exit 1
  fi

  check_env_vars
  login_dockerhub

  local NS
  NS="$(get_namespace)"
  log_info "Docker Hub namespace: $NS" # usually username or org

  for v in "${variants[@]}"; do
    if [[ "$v" == "default" ]]; then
      build_and_push_variant "default" "$DOCKERFILE" "$NS"
    fi
  done

  log_info "Successfully completed Docker build and push!"
  for v in "${variants[@]}"; do
    log_info "Versioned image: ${NS}/${REPO_NAME}:${TAG_BASE}-${v}-${IMG_VERSION}"
    log_info "Latest image:    ${NS}/${REPO_NAME}:${TAG_BASE}-${v}-latest"
  done
}

main "$@"
