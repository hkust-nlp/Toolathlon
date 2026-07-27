#!/bin/bash

# Load a host-cached image into a Kind node without asking containerd to
# import every platform referenced by a multi-architecture image index.
#
# Docker Engine 29 uses the containerd image store by default.  A host pull
# normally downloads only the host platform, while retaining the complete OCI
# index.  ``kind load docker-image`` (Kind v0.20) imports that archive with
# ``ctr images import --all-platforms`` and consequently fails when the index
# references platform or attestation blobs that are not present locally.
#
# Streaming the archive directly to the Kind node and selecting only the
# node's platform avoids that failure.  Do not add ``image save --platform``
# here: Toolathlon's task image currently ships Docker CLI 24.0.7 and talks to
# newer daemons with API v1.44, where that flag is not available.

_toolathlon_kind_node_platform() {
  local runtime=$1
  local node=$2
  local machine

  machine=$("$runtime" exec "$node" uname -m 2>/dev/null) || return 1
  case "$machine" in
    x86_64 | amd64)
      printf '%s\n' "linux/amd64"
      ;;
    aarch64 | arm64)
      printf '%s\n' "linux/arm64"
      ;;
    armv7l | armv7)
      printf '%s\n' "linux/arm/v7"
      ;;
    ppc64le | s390x | riscv64)
      printf 'linux/%s\n' "$machine"
      ;;
    *)
      printf 'Unsupported Kind node architecture: %s\n' "$machine" >&2
      return 1
      ;;
  esac
}

_toolathlon_kind_node_snapshotter() {
  local runtime=$1
  local node=$2
  local snapshotter

  snapshotter=$("$runtime" exec "$node" awk '
    /^[[:space:]]*\[plugins\."io\.containerd\.grpc\.v1\.cri"\.containerd\][[:space:]]*$/ {
      section = 1
      next
    }
    section && /^[[:space:]]*\[/ {
      section = 0
    }
    section && $1 == "snapshotter" {
      value = $3
      gsub(/"/, "", value)
      print value
      exit
    }
  ' /etc/containerd/config.toml 2>/dev/null) || return 1

  if [ -z "$snapshotter" ]; then
    printf 'Unable to determine the CRI snapshotter on Kind node: %s\n' "$node" >&2
    return 1
  fi
  printf '%s\n' "$snapshotter"
}

toolathlon_kind_load_image() {
  if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    printf 'Usage: toolathlon_kind_load_image RUNTIME CLUSTER IMAGE [PLATFORM]\n' >&2
    return 2
  fi

  local runtime=$1
  local cluster_name=$2
  local image=$3
  local platform=${4:-}
  local nodes_output
  local -a nodes=()
  local node
  local node_snapshotter
  local import_output
  local import_rc

  if ! command -v "$runtime" >/dev/null 2>&1; then
    printf 'Container runtime not found: %s\n' "$runtime" >&2
    return 1
  fi
  if ! "$runtime" image inspect "$image" >/dev/null 2>&1; then
    printf 'Host image is not available in %s: %s\n' "$runtime" "$image" >&2
    return 1
  fi
  if ! command -v kind >/dev/null 2>&1; then
    printf 'Kind command not found\n' >&2
    return 1
  fi

  nodes_output=$(KIND_EXPERIMENTAL_PROVIDER="$runtime" kind get nodes --name "$cluster_name") || {
    printf 'Unable to list nodes for Kind cluster: %s\n' "$cluster_name" >&2
    return 1
  }
  mapfile -t nodes < <(printf '%s\n' "$nodes_output" | sed '/^[[:space:]]*$/d')
  if [ "${#nodes[@]}" -eq 0 ]; then
    printf 'Kind cluster has no nodes: %s\n' "$cluster_name" >&2
    return 1
  fi

  for node in "${nodes[@]}"; do
    if ! "$runtime" inspect "$node" >/dev/null 2>&1; then
      printf 'Kind node is not available in %s: %s\n' "$runtime" "$node" >&2
      return 1
    fi

    local node_platform=$platform
    if [ -z "$node_platform" ]; then
      node_platform=$(_toolathlon_kind_node_platform "$runtime" "$node") || return 1
    fi
    node_snapshotter=$(_toolathlon_kind_node_snapshotter "$runtime" "$node") || return 1

    # Run the pipeline in a subshell with pipefail so a failed image export is
    # not hidden by a successful ``ctr`` process that merely consumed EOF.
    # Keep the save command's stderr out of the tar stream.
    import_output=$(
      set -o pipefail
      "$runtime" image save "$image" |
        "$runtime" exec -i "$node" \
          ctr --namespace=k8s.io images import \
            --platform "$node_platform" \
            --snapshotter "$node_snapshotter" \
            - 2>&1
    )
    import_rc=$?

    if [ "$import_rc" -ne 0 ]; then
      printf 'Platform-scoped import failed for %s into %s (platform=%s, snapshotter=%s, rc=%s)\n' \
        "$image" "$node" "$node_platform" "$node_snapshotter" "$import_rc" >&2
      if [ -n "$import_output" ]; then
        printf '%s\n' "$import_output" >&2
      fi
      return "$import_rc"
    fi

    if ! "$runtime" exec "$node" crictl inspecti "$image" >/dev/null 2>&1; then
      printf 'Image import completed but CRI cannot resolve %s on %s\n' \
        "$image" "$node" >&2
      return 1
    fi

    printf 'Loaded %s into %s for %s\n' "$image" "$node" "$node_platform"
  done
}
