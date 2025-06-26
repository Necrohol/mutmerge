#!/bin/bash
# mutmerge - Shell wrapper for the MutMerge Python script
#
# Usage examples:
#   mutmerge firefox                    # Test all Firefox variants
#   mutmerge --stats                    # Show build statistics  
#   mutmerge --chroot /path/to/chroot   # Use chroot environment
#   mutmerge --docker                   # Use Docker for builds

set -euo pipefail

# Default paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUTMERGE_SCRIPT="${SCRIPT_DIR}/mutmerge.py"
CONFIG_FILE="packages.toml"
DATABASE_FILE="mutmerge.db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    if ! command -v emerge &> /dev/null; then
        missing_deps+=("emerge (Portage)")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

# Setup environment
setup_environment() {
    # Ensure FEATURES includes binpkg-multi-instance
    if [[ -z "${FEATURES:-}" ]]; then
        export FEATURES="binpkg-multi-instance"
    elif [[ ! "$FEATURES" =~ binpkg-multi-instance ]]; then
        export FEATURES="$FEATURES binpkg-multi-instance"
    fi
    
    # Create necessary directories
    mkdir -p "$(dirname "$DATABASE_FILE")"
    
    # Check if we're running as root (needed for emerge)
    if [[ $EUID -ne 0 ]] && [[ ! "${USE_DOCKER:-}" == "true" ]] && [[ -z "${CHROOT_PATH:-}" ]]; then
        warning "Not running as root. Consider using --docker or --chroot for safer testing."
    fi
}

# Show usage information
show_usage() {
    cat << EOF
MutMerge - Mutating Emerge Wrapper

USAGE:
    mutmerge [OPTIONS] [PACKAGE]

OPTIONS:
    -c, --config FILE       Configuration file (default: packages.toml)
    -d, --database FILE     SQLite database file (default: mutmerge.db)
    -m, --max-variants NUM  Maximum variants per package (default: 50)
    --chroot PATH           Use chroot environment for building
    --docker                Use Docker for building
    --stats [PACKAGE]       Show build statistics
    --list-packages         List configured packages
    --clean-db              Clean database of old entries
    --export-results FILE   Export results to JSON file
    -h, --help              Show this help message

EXAMPLES:
    # Test all variants of Firefox
    mutmerge firefox
    
    # Test all packages with max 25 variants each
    mutmerge --max-variants 25
    
    # Use chroot for safer testing
    mutmerge --chroot /mnt/gentoo firefox
    
    # Use Docker for testing
    mutmerge --docker
    
    # Show statistics for VLC
    mutmerge --stats vlc
    
    # Export all results to JSON
    mutmerge --export-results results.json

CONFIGURATION:
    Create a packages.toml file with package definitions:
    
    [packages.firefox]
    USE1 = "pulseaudio alsa"
    USE2 = "pulseaudio -alsa"
    USE3 = "-pulseaudio alsa"

For more information, see the documentation.
EOF
}

# List configured packages
list_packages() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    log "Configured packages in $CONFIG_FILE:"
    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from mutmerge import ConfigManager
try:
    config = ConfigManager('$CONFIG_FILE')
    packages = config.get_packages()
    for pkg in sorted(packages.keys()):
        print(f'  • {pkg}')
    print(f'\\nTotal: {len(packages)} packages')
except Exception as e:
    print(f'Error reading config: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Clean old database entries
clean_database() {
    if [[ ! -f "$DATABASE_FILE" ]]; then
        warning "Database file not found: $DATABASE_FILE"
        return
    fi
    
    log "Cleaning old database entries..."
    python3 -c "
import sqlite3
import time

conn = sqlite3.connect('$DATABASE_FILE')
cursor = conn.cursor()

# Remove entries older than 30 days
cutoff = int(time.time()) - (30 * 24 * 60 * 60)
cursor.execute('DELETE FROM builds WHERE timestamp < ?', (cutoff,))
cursor.execute('DELETE FROM skip_combinations WHERE timestamp < ?', (cutoff,))

removed = cursor.rowcount
conn.commit()
conn.close()

print(f'Removed {removed} old entries')
"
    success "Database cleaned"
}

# Export results to JSON
export_results() {
    local output_file="$1"
    
    if [[ ! -f "$DATABASE_FILE" ]]; then
        error "Database file not found: $DATABASE_FILE"
        exit 1
    fi
    
    log "Exporting results to $output_file..."
    python3 -c "
import sqlite3
import json
import sys

try:
    conn = sqlite3.connect('$DATABASE_FILE')
    cursor = conn.cursor()
    
    # Get all builds
    cursor.execute('''
        SELECT package, use_flags, status, timestamp, build_time, error_log, binary_path
        FROM builds ORDER BY timestamp DESC
    ''')
    
    builds = []
    for row in cursor.fetchall():
        builds.append({
            'package