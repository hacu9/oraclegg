#!/bin/bash
# Release a new version of OracleGG
#
# Usage: ./scripts/release.sh 0.2.0
#
# This:
# 1. Updates the version in updater.py and pyproject.toml
# 2. Rebuilds the Windows exe
# 3. Creates a GitHub release with the zip attached
#
# Prerequisites: gh CLI installed and authenticated

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release.sh <version>"
    echo "Example: ./scripts/release.sh 0.2.0"
    exit 1
fi

echo "Releasing OracleGG v${VERSION}..."

# Update version in files
sed -i "s/^VERSION = .*/VERSION = \"${VERSION}\"/" src/oraclegg/updater.py
sed -i "s/^version = .*/version = \"${VERSION}\"/" pyproject.toml

# Commit
git add -A
git commit -m "Release v${VERSION}"
git tag "v${VERSION}"
git push && git push --tags

# Build exe on Windows
echo "Building exe..."
powershell.exe -Command "Start-Process cmd -ArgumentList '/c','cd /d C:\Users\hacu9\oraclegg_build && scripts\build_windows_exe.bat' -Wait -NoNewWindow"

# Copy .env with key
cp /tmp/env_for_dist /mnt/c/Users/hacu9/oraclegg_build/dist/OracleGG/.env 2>/dev/null || true

# Zip
powershell.exe -Command "
Remove-Item 'C:\Users\hacu9\Desktop\OracleGG.zip' -Force -ErrorAction SilentlyContinue
Compress-Archive -Path 'C:\Users\hacu9\oraclegg_build\dist\OracleGG' -DestinationPath 'C:\Users\hacu9\Desktop\OracleGG.zip' -Force
"

# Create GitHub release
echo "Creating GitHub release..."
gh release create "v${VERSION}" \
    "/mnt/c/Users/hacu9/Desktop/OracleGG.zip" \
    --title "OracleGG v${VERSION}" \
    --notes "Auto-update: existing users will be prompted to update."

echo ""
echo "Released v${VERSION}!"
echo "Friends' apps will show an update notification on next launch."
