# FT Lock - Linux Screen Saver with Authentication

A secure screen locker for Ubuntu 22.04 with lightdm integration that uses Linux account information for authentication.

## ✨ Features

### 🔒 **Enhanced Security**
- **Advanced Key Blocking**: Blocks all system shortcuts (Super+A, Alt+Tab, Ctrl+Alt+F1-F12, etc.)
- **Special Character Support**: Full password support including `/`, `@`, `#`, `$` and other symbols
- **Real 5-Minute Lockout**: Actual 5-minute lockout after 3 failed attempts with countdown timer
- **Enhanced Input Grabbing**: Continuous focus maintenance and input capture
- **VT Switching Protection**: Prevents virtual terminal switching through keyboard shortcuts

### 🎨 **UI Improvements**
- **Centered Interface**: Password input dialog positioned at screen center
- **Real-time Clock**: Live time display with seconds (HH:MM:SS format)
- **Auto-generated Background**: Beautiful gradient background image creation
- **Improved Layout**: Better spacing and modern styling
- **Status Messages**: Clear feedback for authentication attempts

### 🧪 **Testing Features**
- **Test Mode**: `test_lock_screen.py` with PAM authentication support
- **'test' Password**: Quick testing with bypass password (test mode only)
- **Component Testing**: `--test` flag for system verification

## Features

- **PAM Authentication**: Uses Linux account credentials + enhanced security
- **Fullscreen Lock**: Prevents desktop access with advanced key blocking
- **System Shortcut Protection**: Blocks Super, Alt, and Ctrl key combinations
- **Screensaver Mode**: Automatic locking after inactivity
- **Failed Attempt Protection**: 5-minute lockout with real-time countdown
- **Real-time Display**: Live clock and date updates
- **Cross-platform Build**: Docker-based compilation for consistent results

## Requirements

- Ubuntu 22.04 (or compatible)
- Python 3.8+
- lightdm display manager
- PAM authentication system

## Installation

1. **Quick Install**:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

2. **Manual Install**:
   ```bash
   # Install system dependencies
   sudo apt update
   sudo apt install python3 python3-pip python3-pam python3-tk
   
   # Install Python dependencies
   pip3 install -r requirements.txt
   
   # Make executable
   chmod +x ft_lock.py
   ```

3. **Build Executable (Docker)**:
   ```bash
   # Prerequisites: Docker installed and running
   
   # Build Linux executable using Docker
   ./make_install.sh
   
   # Results:
   # - dist/ft-lock (Linux executable)
   # - ft-lock-release/ (distribution package) 
   # - ft-lock-linux-YYYYMMDD.tar.gz (release archive)
   ```

## Usage

### Basic Usage
```bash
# Lock screen immediately
./ft_lock.py --lock

# Start screensaver with 5-minute timeout
./ft_lock.py --screensaver 5

# Show help
./ft_lock.py --help
```

### Integration Options

1. **Keyboard Shortcut**: 
   - Go to Settings → Keyboard → Custom Shortcuts
   - Add: `Command: /path/to/ft_lock.py --lock`
   - Assign to Ctrl+Alt+L

2. **Screensaver Service**:
   ```bash
   # Enable automatic screensaver
   systemctl --user enable ft-lock-screensaver@$USER.service
   systemctl --user start ft-lock-screensaver@$USER.service
   ```

3. **Desktop Entry**:
   - Application will appear in applications menu after installation

## Security Features

- **PAM Integration**: Uses system authentication
- **Input Grabbing**: Prevents bypassing with other applications
- **VT Switching Block**: Disables virtual terminal access
- **Attempt Limiting**: 5-minute lockout after 3 failed attempts
- **Session Validation**: Checks active user sessions

## Configuration

Edit `ft_lock.py` to customize:
- `max_attempts`: Maximum login attempts (default: 3)
- Timeout duration for screensaver mode
- UI appearance and colors
- Security restrictions

## Troubleshooting

1. **Permission Issues**:
   ```bash
   # Ensure proper permissions for PAM
   sudo usermod -a -G shadow $USER
   ```

2. **PAM Authentication Fails**:
   ```bash
   # Test PAM module
   python3 -c "import pam; p=pam.pam(); print(p.authenticate('$USER', 'password'))"
   ```

3. **Virtual Terminal Issues**:
   ```bash
   # Reset VT if needed
   sudo chvt 7
   ```

## Compatibility

- **Tested on**: Ubuntu 22.04 LTS
- **Display Managers**: lightdm, gdm3
- **Desktop Environments**: GNOME, KDE, XFCE, LXDE

## Security Notes

- Run with appropriate user permissions
- Ensure PAM is properly configured
- Test thoroughly before production use
- Consider using with fail2ban for additional security

## License

Open source - modify as needed for your environment.

## Contributing

Feel free to submit issues and feature requests.
