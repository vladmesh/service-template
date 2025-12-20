#!/bin/bash
# Sync framework/ to template/.framework/framework/
# This ensures the product template has the latest framework code

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/framework"
TARGET_DIR="$ROOT_DIR/template/.framework/framework"

echo "Syncing framework/ to template/.framework/framework/..."

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Use rsync to sync files (delete removes files not in source)
rsync -av --delete "$SOURCE_DIR/" "$TARGET_DIR/"

echo "✅ Framework synced successfully"
echo "   Source: $SOURCE_DIR"
echo "   Target: $TARGET_DIR"
