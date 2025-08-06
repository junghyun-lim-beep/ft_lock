#!/bin/bash
echo "🐧 Building FT Lock for Ubuntu 22.04..."

# Docker가 설치되어 있는지 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

echo "📂 Current directory: $(pwd)"
echo "📁 Files to build:"
ls -la *.py images/ 2>/dev/null || echo "⚠️  Some files missing"

echo ""
echo "🔨 Starting Docker build..."

# 기존 빌드 파일 정리
echo "🧹 Cleaning previous build files..."
rm -rf dist/ build/ *.spec __pycache__/ *.pyc
echo "   ✅ Previous build files cleaned"

docker run --rm -v $(pwd):/workspace -w /workspace ubuntu:22.04 bash -c "
    set -e
    
    echo '🌍 Step 1: Setting timezone (non-interactive)...'
    export DEBIAN_FRONTEND=noninteractive
    export TZ=Asia/Seoul
    ln -snf /usr/share/zoneinfo/\$TZ /etc/localtime && echo \$TZ > /etc/timezone
    
    echo '📦 Step 2: Updating package repositories...'
    apt-get update
    
    echo '📦 Step 3: Installing system packages...'
    apt-get install -y python3 python3-pip python3-venv python3-pam python3-tk python3-dev build-essential
    
    echo '🔍 Step 4: Verifying Python installation...'
    python3 --version
    pip3 --version
    
    echo '🐍 Step 5: Installing Python packages...'
    echo '   Installing pyinstaller...'
    pip3 install pyinstaller
    
    echo '   Installing pillow...'
    pip3 install pillow
    
    echo '   Installing python-pam...'
    pip3 install python-pam
    
    echo '   Installing psutil...'
    pip3 install psutil
    
    echo '   Installing six...'
    pip3 install six
    
    # echo '   Verifying pam import...'
    # python3 -c \"import pam; print('PAM module working')\" || echo \"PAM import failed\"
    
    echo '🎨 Step 6: Creating background image...'
    python3 create_background.py
    if [ -f 'images/lock_background.png' ]; then
        echo '   ✅ Background image created successfully'
    else
        echo '   ⚠️  Background image not created, continuing...'
    fi
    
    echo '⚙️  Step 7: Building Linux executable...'
    echo '   This may take 2-3 minutes...'
    if [ -f 'images/lock_background.png' ]; then
        pyinstaller --onefile --name 'ft-lock' \
            --add-data 'images:images' \
            --hidden-import=six \
            --hidden-import=pam \
            --hidden-import=psutil \
            --hidden-import=PIL \
            --hidden-import=PIL.Image \
            --hidden-import=PIL.ImageTk \
            --hidden-import=PIL.ImageDraw \
            --hidden-import=tkinter \
            --hidden-import=tkinter.ttk \
            --hidden-import=tkinter.messagebox \
            ft_lock.py --distpath /workspace/dist
    else
        pyinstaller --onefile --name 'ft-lock' \
            --hidden-import=six \
            --hidden-import=pam \
            --hidden-import=psutil \
            --hidden-import=PIL \
            --hidden-import=PIL.Image \
            --hidden-import=PIL.ImageTk \
            --hidden-import=tkinter \
            --hidden-import=tkinter.ttk \
            --hidden-import=tkinter.messagebox \
            ft_lock.py --distpath /workspace/dist
    fi
    
    echo '🔧 Step 8: Setting file permissions...'
    chmod +x /workspace/dist/ft-lock
    
    chown \$(stat -c '%u:%g' /workspace) /workspace/dist/ft-lock
    
    echo '🧹 Step 9: Cleaning build artifacts...'
    rm -rf build/ *.spec __pycache__/ *.pyc
    
    echo '✅ All build steps completed!'
"

echo ""
echo "=================================================="

# 빌드 결과 확인 및 배포 패키지 생성
if [ -f "dist/ft-lock" ]; then
    echo "🎉 BUILD SUCCESSFUL!"
    echo ""
    echo "📍 Executable: $(pwd)/dist/ft-lock"
    echo "📏 Size: $(ls -lh dist/ft-lock | awk '{print $5}')"
    echo "🗓️  Built: $(date)"
    echo ""
    
    # 배포 패키지 자동 생성
    echo "📦 Creating distribution package..."
    
    # 배포 디렉토리 생성
    rm -rf ft-lock-release/
    mkdir -p ft-lock-release
    
    # 필요한 파일들 복사
    cp dist/ft-lock ft-lock-release/
    
    # 이미지 폴더가 있으면 복사
    if [ -d "images" ]; then
        cp -r images ft-lock-release/
        echo "   ✅ Images included"
    fi
    
    # README 파일이 있으면 복사
    if [ -f "README.md" ]; then
        cp README.md ft-lock-release/
        echo "   ✅ README included"
    fi
    
    # 간소화된 설치 스크립트 생성
    cat > ft-lock-release/install.sh << 'INSTALL_EOF'
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
INSTALL_EOF
    
    chmod +x ft-lock-release/install.sh
    echo "   ✅ Install script created"
    
    # 압축 파일 생성
    tar -czf ft-lock-linux-$(date +%Y%m%d).tar.gz ft-lock-release/
    echo "   ✅ Archive created: ft-lock-linux-$(date +%Y%m%d).tar.gz"
    
    echo ""
    echo "📋 Distribution package contents:"
    ls -la ft-lock-release/
    
    echo ""
    echo "🚀 Ready for distribution!"
    echo "   📦 Package: ft-lock-linux-$(date +%Y%m%d).tar.gz"
    echo "   📁 Directory: ft-lock-release/"
    echo ""
    echo "🔄 To deploy on Ubuntu machine:"
    echo "   1. Transfer: scp ft-lock-linux-$(date +%Y%m%d).tar.gz user@ubuntu:~/"
    echo "   2. Extract: tar -xzf ft-lock-linux-$(date +%Y%m%d).tar.gz"
    echo "   3. Install: cd ft-lock-release && ./install.sh"
    echo "   4. Run: ./ft-lock --lock"
    
    echo ""
    echo "🧹 Cleaning temporary files..."
    rm -rf build/ *.spec __pycache__/ *.pyc 2>/dev/null
    echo "   ✅ Temporary files cleaned"
    
else
    echo "❌ BUILD FAILED!"
    echo ""
    echo "🧹 Cleaning failed build artifacts..."
    rm -rf dist/ build/ *.spec __pycache__/ *.pyc 2>/dev/null
fi

echo ""
echo "🏁 Process completed!"