#!/bin/bash
# FT Lock Installation Script for Ubuntu 22.04

echo "Installing FT Lock dependencies..."

# Update package list
sudo apt update

# Install required system packages
sudo apt install -y python3 python3-pip python3-pam python3-tk

# Install Python dependencies
pip3 install -r requirements.txt

# Make ft_lock.py executable
chmod +x ft_lock.py

# Create desktop entry for easy access
cat > ~/.local/share/applications/ft-lock.desktop << EOF
[Desktop Entry]
Name=FT Lock
Comment=Linux Screen Saver with Authentication
Exec=$(pwd)/ft_lock.py --lock
Icon=system-lock-screen
Terminal=false
Type=Application
Categories=System;Security;
EOF

# Create systemd service for screensaver mode (optional)
sudo tee /etc/systemd/system/ft-lock-screensaver.service > /dev/null << EOF
[Unit]
Description=FT Lock Screensaver Service
After=graphical-session.target

[Service]
Type=simple
User=%i
ExecStart=$(pwd)/ft_lock.py --screensaver 10
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

echo "Installation complete!"
echo ""
echo "Usage:"
echo "  ./ft_lock.py --lock           # Lock screen immediately"
echo "  ./ft_lock.py --screensaver 5  # Start screensaver (5 min timeout)"
echo "  ./ft_lock.py --help           # Show help"
echo ""
echo "To enable screensaver service:"
echo "  systemctl --user enable ft-lock-screensaver@$USER.service"
echo "  systemctl --user start ft-lock-screensaver@$USER.service"
