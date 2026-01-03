#!/bin/bash
# Setup APFS support on Ubuntu for reading macOS drives
# Run with: sudo bash setup-apfs-linux.sh

set -e
echo "=== Installing APFS support for Linux ==="

apt-get update
apt-get install -y git cmake build-essential libfuse3-dev libbz2-dev zlib1g-dev libattr1-dev

cd /tmp
rm -rf apfs-fuse
git clone https://github.com/sgan81/apfs-fuse.git
cd apfs-fuse
git submodule update --init --recursive
mkdir -p build && cd build
cmake ..
make -j$(nproc)
make install

echo ""
echo "=== APFS-FUSE Installed ==="
echo "Mount: sudo apfs-fuse /dev/nvme0n1p2 /mnt/macos"
echo "If FileVault encrypted, you'll be prompted for password."
