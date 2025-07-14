#!/bin/bash
# Fix hostname resolution issues

echo "Fixing hostname resolution..."

# Get current hostname
HOSTNAME=$(hostname)
echo "Current hostname: $HOSTNAME"

# Check if hostname is in /etc/hosts
if ! grep -q "127.0.1.1.*$HOSTNAME" /etc/hosts; then
    echo "Adding hostname to /etc/hosts..."
    echo "127.0.1.1 $HOSTNAME" | sudo tee -a /etc/hosts
else
    echo "Hostname already in /etc/hosts"
fi

# Verify the fix
echo "Testing hostname resolution..."
if nslookup $HOSTNAME > /dev/null 2>&1 || grep -q "$HOSTNAME" /etc/hosts; then
    echo "✓ Hostname resolution fixed"
else
    echo "⚠ Hostname resolution may still have issues"
fi
