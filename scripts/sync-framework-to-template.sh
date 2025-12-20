#!/bin/bash
# Sync framework/ to template/.framework/framework/
# This ensures the product template has the latest framework code
# Structure: .framework/framework/ allows PYTHONPATH=.framework with "import framework"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/framework"
TARGET_DIR="$ROOT_DIR/template/.framework/framework"

# Check for dry-run flag
DRY_RUN=""
if [ "$1" = "--dry-run" ] || [ "$1" = "-n" ]; then
    DRY_RUN="--dry-run"
    echo "🔍 DRY RUN MODE - No changes will be made"
    echo ""
fi

echo "Syncing framework/ to template/.framework/framework/..."

# Create target directory if it doesn't exist (unless dry-run)
if [ -z "$DRY_RUN" ]; then
    mkdir -p "$TARGET_DIR"
fi

# Use rsync to sync files (delete removes files not in source)
rsync -av --delete $DRY_RUN "$SOURCE_DIR/" "$TARGET_DIR/"

if [ -n "$DRY_RUN" ]; then
    echo ""
    echo "✅ Dry run completed. Run without --dry-run to apply changes."
else
    echo "✅ Framework synced successfully"
    echo "   Source: $SOURCE_DIR"
    echo "   Target: $TARGET_DIR"
fi
