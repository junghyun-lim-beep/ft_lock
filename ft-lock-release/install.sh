#!/bin/bash
echo "Installing FT Lock system dependencies..."

# 필수: PAM 라이브러리 설치
sudo apt update
sudo apt install -y python3-pam

# 실행 권한 부여
chmod +x ft-lock

# 선택: 데스크톱 항목 생성
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/ft-lock.desktop << EOD
[Desktop Entry]
Name=FT Lock
Comment=Linux Screen Saver with Authentication
Exec=$(pwd)/ft-lock --lock
Icon=system-lock-screen
Terminal=false
Type=Application
Categories=System;Security;
EOD

echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  ./ft-lock --lock           # Lock screen immediately"
echo "  ./ft-lock --screensaver 5  # Start screensaver (5 min timeout)"
echo "  ./ft-lock --test           # Test components"
echo "  ./ft-lock --help           # Show help"
