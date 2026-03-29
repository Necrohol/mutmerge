#!/bin/bash
# fix-binhost.sh - Run on Debian/Alpine VPS
# Supports both modern .gpkg and legacy .tbz2 (XPAK)

BASE_DIR="/var/www/binhost"
ARCHES=("amd64" "arm64" "riscv64")

for ARCH in "${ARCHES[@]}"; do
    TARGET="$BASE_DIR/$ARCH"
    [ -d "$TARGET" ] || continue
    cd "$TARGET" || continue
    
    TEMP_PACKAGES=$(mktemp)
    echo ">>> Indexing $ARCH..."

    # 1. Header
    echo "TIMESTAMP: $(date +%s)" > "$TEMP_PACKAGES"
    echo "PACKAGES: $(find . -maxdepth 1 \( -name "*.gpkg" -o -name "*.tbz2" \) | wc -l)" >> "$TEMP_PACKAGES"
    echo "" >> "$TEMP_PACKAGES"

    # 2. Metadata Extraction Loop
    for pkg in *.{gpkg,tbz2}; do
        [ -e "$pkg" ] || continue
        
        if [[ "$pkg" == *.gpkg ]]; then
            # Modern GPKG: Tar -> metadata.tar.gz -> Packages
            tar -xOf "$pkg" metadata.tar.gz 2>/dev/null | tar -xzOf - Packages >> "$TEMP_PACKAGES"
        else
            # Legacy TBZ2: XPAK metadata is at the end. 
            # On non-Gentoo, we can use 'python3' (usually present) to 
            # safely grab the 'Packages' block from the XPAK trailer.
            python3 -c "
import sys
with open('$pkg', 'rb') as f:
    data = f.read()
    start = data.rfind(b'STOP') # End of Bzip2 / Start of XPAK
    if start != -1:
        xpak = data[start:]
        # Look for the internal 'Packages' marker in XPAK
        pkg_start = xpak.find(b'Packages')
        if pkg_start != -1:
            sys.stdout.buffer.write(xpak[pkg_start:].split(b'\0')[0])
" >> "$TEMP_PACKAGES"
        fi
        echo "" >> "$TEMP_PACKAGES" # Delimiter
    done

    # 3. Finalize
    rm -f Packages Packages.gz
    mv "$TEMP_PACKAGES" Packages
    gzip -9 -c Packages > Packages.gz
    echo ">>> Done $ARCH."
done
