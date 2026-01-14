#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Rocky System - Rollback Mechanism
# Story: RAF-022
# Target: Safe rollback to previous working state
#
# Usage: ./rollback.sh [checkpoint_name]

set -e

ROXY_HOME="${HOME}/.roxy"
BACKUP_DIR="${ROXY_HOME}/backups"
CHECKPOINT_DIR="${BACKUP_DIR}/checkpoints"
CURRENT_LINK="${BACKUP_DIR}/current"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[ROXY]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[ROXY]${NC} $1"
}

log_error() {
    echo -e "${RED}[ROXY]${NC} $1"
}

# Create checkpoint
create_checkpoint() {
    local name="${1:-$(date +%Y%m%d_%H%M%S)}"
    local checkpoint="${CHECKPOINT_DIR}/${name}"

    mkdir -p "${CHECKPOINT_DIR}"

    log_info "Creating checkpoint: ${name}"

    # Create checkpoint directory
    mkdir -p "${checkpoint}"

    # Backup critical files
    cp -a "${ROXY_HOME}/config" "${checkpoint}/" 2>/dev/null || true
    cp -a "${ROXY_HOME}/data" "${checkpoint}/" 2>/dev/null || true

    # Backup service status
    systemctl --user is-active roxy.service > "${checkpoint}/service_status" 2>/dev/null || echo "unknown"

    # Save git state if applicable
    if [ -d "${ROXY_HOME}/.git" ]; then
        git -C "${ROXY_HOME}" rev-parse HEAD > "${checkpoint}/git_commit" 2>/dev/null || true
    fi

    # Create manifest
    cat > "${checkpoint}/manifest.json" << EOF
{
    "name": "${name}",
    "created": "$(date -Iseconds)",
    "roxy_version": "1.0.0",
    "files": $(find "${checkpoint}" -type f | wc -l)
}
EOF

    # Update current link
    ln -sfn "${checkpoint}" "${CURRENT_LINK}"

    log_info "Checkpoint created: ${checkpoint}"
    echo "${name}"
}

# List checkpoints
list_checkpoints() {
    log_info "Available checkpoints:"
    echo ""

    if [ ! -d "${CHECKPOINT_DIR}" ]; then
        log_warn "No checkpoints found"
        return
    fi

    for checkpoint in "${CHECKPOINT_DIR}"/*; do
        if [ -d "${checkpoint}" ]; then
            name=$(basename "${checkpoint}")
            manifest="${checkpoint}/manifest.json"

            if [ -f "${manifest}" ]; then
                created=$(grep -o '"created": "[^"]*"' "${manifest}" | cut -d'"' -f4)
                echo "  ${name} (${created})"
            else
                echo "  ${name}"
            fi
        fi
    done
    echo ""

    # Show current
    if [ -L "${CURRENT_LINK}" ]; then
        current=$(basename "$(readlink "${CURRENT_LINK}")")
        log_info "Current checkpoint: ${current}"
    fi
}

# Rollback to checkpoint
rollback_to() {
    local name="$1"
    local checkpoint="${CHECKPOINT_DIR}/${name}"

    if [ ! -d "${checkpoint}" ]; then
        log_error "Checkpoint not found: ${name}"
        list_checkpoints
        exit 1
    fi

    log_warn "Rolling back to checkpoint: ${name}"
    log_warn "This will overwrite current configuration!"

    # Confirm
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi

    # Stop services
    log_info "Stopping ROXY services..."
    systemctl --user stop roxy.service 2>/dev/null || true
    systemctl --user stop roxy-brain.service 2>/dev/null || true
    systemctl --user stop roxy-audio.service 2>/dev/null || true

    # Create safety backup before rollback
    log_info "Creating safety backup..."
    create_checkpoint "pre_rollback_$(date +%Y%m%d_%H%M%S)" > /dev/null

    # Restore files
    log_info "Restoring configuration..."
    if [ -d "${checkpoint}/config" ]; then
        rm -rf "${ROXY_HOME}/config"
        cp -a "${checkpoint}/config" "${ROXY_HOME}/"
    fi

    if [ -d "${checkpoint}/data" ]; then
        rm -rf "${ROXY_HOME}/data"
        cp -a "${checkpoint}/data" "${ROXY_HOME}/"
    fi

    # Restore git commit if tracked
    if [ -f "${checkpoint}/git_commit" ] && [ -d "${ROXY_HOME}/.git" ]; then
        commit=$(cat "${checkpoint}/git_commit")
        log_info "Restoring git state: ${commit}"
        git -C "${ROXY_HOME}" checkout "${commit}" 2>/dev/null || log_warn "Git restore failed"
    fi

    # Update current link
    ln -sfn "${checkpoint}" "${CURRENT_LINK}"

    # Restart services
    log_info "Restarting ROXY services..."
    systemctl --user start roxy-brain.service 2>/dev/null || true
    sleep 1
    systemctl --user start roxy.service 2>/dev/null || true

    log_info "Rollback complete!"
}

# Rollback to previous
rollback_previous() {
    if [ ! -L "${CURRENT_LINK}" ]; then
        log_error "No current checkpoint set"
        exit 1
    fi

    current=$(basename "$(readlink "${CURRENT_LINK}")")

    # Find previous checkpoint
    previous=""
    for checkpoint in "${CHECKPOINT_DIR}"/*; do
        name=$(basename "${checkpoint}")
        if [ "${name}" == "${current}" ]; then
            break
        fi
        previous="${name}"
    done

    if [ -z "${previous}" ]; then
        log_error "No previous checkpoint found"
        exit 1
    fi

    rollback_to "${previous}"
}

# Clean old checkpoints
clean_checkpoints() {
    local keep="${1:-5}"

    log_info "Cleaning old checkpoints (keeping ${keep})..."

    # Get sorted list of checkpoints
    checkpoints=($(ls -1t "${CHECKPOINT_DIR}" 2>/dev/null))

    # Delete old ones
    count=0
    for checkpoint in "${checkpoints[@]}"; do
        count=$((count + 1))
        if [ ${count} -gt ${keep} ]; then
            log_info "Removing: ${checkpoint}"
            rm -rf "${CHECKPOINT_DIR}/${checkpoint}"
        fi
    done

    log_info "Cleanup complete"
}

# Verify checkpoint
verify_checkpoint() {
    local name="$1"
    local checkpoint="${CHECKPOINT_DIR}/${name}"

    if [ ! -d "${checkpoint}" ]; then
        log_error "Checkpoint not found: ${name}"
        exit 1
    fi

    log_info "Verifying checkpoint: ${name}"

    errors=0

    # Check manifest
    if [ ! -f "${checkpoint}/manifest.json" ]; then
        log_warn "Missing manifest.json"
        errors=$((errors + 1))
    fi

    # Check config
    if [ ! -d "${checkpoint}/config" ]; then
        log_warn "Missing config directory"
        errors=$((errors + 1))
    fi

    # Check data
    if [ ! -d "${checkpoint}/data" ]; then
        log_warn "Missing data directory"
        errors=$((errors + 1))
    fi

    if [ ${errors} -eq 0 ]; then
        log_info "Checkpoint verified: OK"
    else
        log_error "Checkpoint has ${errors} issues"
    fi
}

# Show usage
usage() {
    echo "ROXY Rollback Manager"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  create [name]      Create a new checkpoint"
    echo "  list               List all checkpoints"
    echo "  rollback <name>    Rollback to a specific checkpoint"
    echo "  previous           Rollback to previous checkpoint"
    echo "  clean [keep]       Remove old checkpoints (default: keep 5)"
    echo "  verify <name>      Verify checkpoint integrity"
    echo ""
    echo "Examples:"
    echo "  $0 create before_update"
    echo "  $0 rollback 20260104_120000"
    echo "  $0 previous"
    echo "  $0 clean 10"
}

# Main
case "${1:-}" in
    create)
        create_checkpoint "${2:-}"
        ;;
    list)
        list_checkpoints
        ;;
    rollback)
        if [ -z "${2:-}" ]; then
            log_error "Checkpoint name required"
            usage
            exit 1
        fi
        rollback_to "$2"
        ;;
    previous)
        rollback_previous
        ;;
    clean)
        clean_checkpoints "${2:-5}"
        ;;
    verify)
        if [ -z "${2:-}" ]; then
            log_error "Checkpoint name required"
            exit 1
        fi
        verify_checkpoint "$2"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac