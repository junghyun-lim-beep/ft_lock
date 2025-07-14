# FT Lock - Linux Screen Saver with Authentication

A secure screen locker for Ubuntu 22.04 with lightdm integration that uses Linux account information for authentication.

## Features

- **PAM Authentication**: Uses Linux account credentials
- **Fullscreen Lock**: Prevents desktop access
- **Virtual Terminal Protection**: Disables Ctrl+Alt+F1-F12 switching
- **Screensaver Mode**: Automatic locking after inactivity
- **Failed Attempt Protection**: Temporary lockout after max attempts
- **System Integration**: Works with lightdm and Ubuntu 22.04

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
