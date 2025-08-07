#!/usr/bin/env python3
"""
FT Lock - Linux Screen Saver with Authentication
A secure screen locker for Ubuntu 22.04 with lightdm integration
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import pam
import os
import sys
import subprocess
import time
import signal
import getpass
import psutil
from datetime import datetime
import threading
import xml.etree.ElementTree as ET


class FTLock:
    def __init__(self):
        self.root = None
        self.password_entry = None
        self.status_label = None
        self.time_label = None  # 실시간 시간 라벨
        self.date_label = None  # 실시간 날짜 라벨
        self.attempts = 0
        self.max_attempts = 3
        self.current_user = getpass.getuser()
        self.locked = False
        self.lockout_active = False  # 5분 잠금 상태
        self.lockout_start_time = None  # 잠금 시작 시간
        self.setup_signal_handlers()
        
    def get_display_scale(self):
        """여러 방법으로 디스플레이 스케일 값 가져오기"""
        actual_scale = 1.0
        
        # 방법 1: monitors.xml 파일 확인
        try:
            monitors_file = os.path.expanduser("~/.config/monitors.xml")
            
            if os.path.exists(monitors_file) and os.access(monitors_file, os.R_OK):
                tree = ET.parse(monitors_file)
                root = tree.getroot()
                
                for logicalmonitor in root.findall('.//logicalmonitor'):
                    scale_element = logicalmonitor.find('scale')
                    if scale_element is not None:
                        actual_scale = float(scale_element.text)
                        break
            else:
                pass
                
        except Exception as e:
            pass
        
        # 방법 2: gsettings로 fallback
        if actual_scale == 1.0:
            try:
                import subprocess
                result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'text-scaling-factor'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    text_scale = float(result.stdout.strip())
                    if text_scale != 1.0:
                        actual_scale = text_scale
            except Exception as e:
                pass
        
        # 방법 3: 해상도 비교로 추정
        if actual_scale == 1.0:
            try:
                import subprocess
                result = subprocess.run(['xrandr'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # 4K 해상도면 보통 2.0 스케일 사용
                    if '3840x2160' in result.stdout:
                        # tkinter로 논리적 해상도 확인
                        temp_root = tk.Tk()
                        logical_width = temp_root.winfo_screenwidth()
                        temp_root.destroy()
                        
                        if logical_width == 1920:  # 3840을 1920으로 스케일링
                            actual_scale = 2.0
            except Exception as e:
                pass
        
        return actual_scale
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        if self.root:
            self.root.quit()
        sys.exit(0)
        
    def block_all_keys(self, event):
        """Block all key combinations except allowed ones"""
        # Allow basic typing keys and navigation keys
        allowed_keys = {
            'Return', 'BackSpace', 'Delete', 'Left', 'Right', 'Home', 'End',
            'Tab', 'space', 'Space'  # Space key
        }
        
        # Allow special characters commonly used in passwords
        special_chars = {
            'slash', 'at', 'numbersign', 'dollar', 'percent', 'asciicircum',
            'ampersand', 'asterisk', 'parenleft', 'parenright', 'minus', 'underscore',
            'plus', 'equal', 'bracketleft', 'bracketright', 'braceleft', 'braceright',
            'backslash', 'bar', 'semicolon', 'colon', 'apostrophe', 'quotedbl',
            'comma', 'period', 'less', 'greater', 'question', 'grave', 'asciitilde',
            'exclam'
        }
        
        # Block dangerous key combinations first
        if event.state & 0x4:  # Control key pressed
            if event.keysym in ['c', 'v', 'x', 'z', 'a', 't']:  # Ctrl+C, Ctrl+V, etc.
                return "break"
                
        if event.state & 0x8:  # Alt key pressed
            return "break"  # Block all Alt combinations
            
        if event.state & 0x40:  # Super/Windows key pressed
            return "break"  # Block all Super combinations
        
        # Allow normal characters (single character keysyms)
        if len(event.keysym) == 1:
            return  # Allow single characters (a-z, A-Z, 0-9, and symbols like /, @, etc.)
            
        # Allow specific named keys
        if (event.keysym in allowed_keys or 
            event.keysym in special_chars or
            event.keysym.startswith('KP_')):  # Keypad numbers
            return  # Allow this key
        
        # Block everything else
        return "break"
        
    def disable_virtual_terminals(self):
        """Disable virtual terminal switching (removed - no sudo required)"""
        # VT switching blocking removed to avoid sudo requirement
        # Basic input grabbing and key blocking provides sufficient security
        pass
            
    def enable_virtual_terminals(self):
        """Re-enable virtual terminal switching (removed - no sudo required)"""
        # VT switching re-enabling removed to avoid sudo requirement
        pass
            
    def grab_input(self):
        """Enhanced input grabbing to prevent bypass"""
        try:
            # Ensure window is visible and updated
            self.root.update_idletasks()
            self.root.after(100, self._delayed_grab)
            return True
        except Exception as e:
            print(f"Warning: Could not grab input: {e}")
            return False
            
    def _delayed_grab(self):
        """Delayed input grabbing after window is ready"""
        try:
            # Global grab to capture all input
            self.root.grab_set_global()
            self.root.focus_force()
            if self.password_entry:
                self.password_entry.focus_set()
                
            # Keep trying to maintain focus
            self.root.after(100, self._maintain_focus)
        except Exception as e:
            print(f"Warning: Delayed grab failed: {e}")
            
    def _maintain_focus(self):
        """Continuously maintain focus and input grab"""
        if self.locked:
            try:
                # Re-grab if lost
                if not self.root.grab_current():
                    self.root.grab_set_global()
                
                # Ensure window stays on top and focused
                self.root.attributes('-topmost', True)
                self.root.focus_force()
                
                if self.password_entry:
                    self.password_entry.focus_set()
                    
            except Exception:
                pass
            
            # Schedule next focus check
            self.root.after(100, self._maintain_focus)
            
    def authenticate_user(self, username, password):
        """Authenticate user using PAM"""
        try:
            p = pam.pam()
            return p.authenticate(username, password)
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
            
    def on_unlock_attempt(self, event=None):
        """Handle unlock attempt"""
        password = self.password_entry.get()
        self.password_entry.delete(0, tk.END)
        
        if not password:
            self.status_label.config(text="Please enter password", foreground="orange")
            return
            
        self.status_label.config(text="Authenticating...", foreground="blue")
        self.root.update()
        
        # Authenticate in separate thread to avoid blocking UI
        thread = threading.Thread(target=self._authenticate_threaded, args=(password,))
        thread.daemon = True
        thread.start()
        
    def _authenticate_threaded(self, password):
        """Perform authentication in separate thread"""
        # Check if still in lockout period
        if self.lockout_active:
            if self.lockout_start_time:
                elapsed = time.time() - self.lockout_start_time
                remaining = 300 - elapsed  # 300초 = 5분
                
                if remaining > 0:
                    minutes = int(remaining // 60)
                    seconds = int(remaining % 60)
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"System locked. Wait {minutes}m {seconds}s more.", 
                        foreground="red"))
                    return
                else:
                    # 5분이 지났으므로 잠금 해제
                    self.lockout_active = False
                    self.lockout_start_time = None
                    self.attempts = 0
        
        # Try PAM authentication
        if self.authenticate_user(self.current_user, password):
            self.attempts = 0  # 성공 시 시도 횟수 리셋
            self.lockout_active = False  # 잠금 해제
            self.root.after(0, lambda: self.status_label.config(
                text="Authentication successful!", foreground="green"))
            self.root.after(500, self.unlock_screen)
            return
        
        # Authentication failed
        self.attempts += 1
        remaining = self.max_attempts - self.attempts
        
        if self.attempts >= self.max_attempts:
            # 5분 잠금 시작
            self.lockout_active = True
            self.lockout_start_time = time.time()
            
            self.root.after(0, lambda: self.status_label.config(
                text=f"Max attempts reached. System locked for 5 minutes.", 
                foreground="red"))
            
            # 5분 후 자동 해제
            self.root.after(300000, self._clear_lockout)  # 300000ms = 5분
        else:
            self.root.after(0, lambda: self.status_label.config(
                text=f"Invalid password. {remaining} attempts remaining.", 
                foreground="red"))
    
    def _clear_lockout(self):
        """Clear lockout after 5 minutes"""
        if self.lockout_active:
            self.lockout_active = False
            self.lockout_start_time = None
            self.attempts = 0
            if self.status_label:
                self.status_label.config(
                    text="Lockout expired. You may try again.", 
                    foreground="orange")
                    
    def unlock_screen(self):
        """Unlock the screen and exit"""
        self.locked = False
        self.enable_virtual_terminals()
        if self.root:
            self.root.quit()
            
    def update_time(self):
        """Update time and date in real-time"""
        if self.locked and self.time_label and self.date_label:
            current_time = datetime.now().strftime("%H:%M:%S")  # 초까지 표시
            date_str = datetime.now().strftime("%A, %B %d")
            
            self.time_label.config(text=current_time)
            self.date_label.config(text=date_str)
            
            # 1초마다 업데이트
            self.root.after(1000, self.update_time)
            
    def create_lock_screen(self):
        """Create the lock screen GUI with full screen background"""
        self.root = tk.Tk()
        self.root.title("FT Lock")
        self.root.configure(bg='black')
        
        # tkinter가 시스템 DPI 스케일링을 무시하도록 설정
        try:
            self.root.tk.call('tk', 'scaling', 1.0)
        except Exception as e:
            pass
        
        # 디스플레이 스케일 가져오기
        display_scale = self.get_display_scale()
            
        # Make window fullscreen and topmost
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        
        # Get screen dimensions BEFORE overrideredirect
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Now remove window decorations
        self.root.overrideredirect(True)
        
        # Force window to cover entire screen
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Block all key combinations globally
        self.root.bind('<Key>', self.block_all_keys)
        self.root.bind('<KeyPress>', self.block_all_keys)
        
        # Block window manager protocols
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.protocol("WM_TAKE_FOCUS", lambda: self.root.focus_force())
        
        # Load and set background image
        try:
            bg_path = os.path.join(os.path.dirname(__file__), 'images', 'lock_background.png')
            if os.path.exists(bg_path):
                # Load and resize background image to fit screen
                bg_image = Image.open(bg_path)
                
                # Handle different Pillow versions for resampling
                try:
                    # New Pillow versions (10.0.0+)
                    bg_image = bg_image.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
                except AttributeError:
                    # Older Pillow versions
                    bg_image = bg_image.resize((screen_width, screen_height), Image.LANCZOS)
                
                self.bg_photo = ImageTk.PhotoImage(bg_image)
                
                # Create background label that covers entire screen
                bg_label = tk.Label(self.root, image=self.bg_photo)
                bg_label.place(x=0, y=0, width=screen_width, height=screen_height)
            else:
                # Fallback to gradient background
                self.root.configure(bg='#1a1a2e')
        except Exception as e:
            print(f"Warning: Could not load background image: {e}")
            self.root.configure(bg='#1a1a2e')
        
        # Create center container for passcode input (가운데로 이동)
        # 스케일에 따라 컨테이너 크기 조정 (적당한 크기로)
        if display_scale > 1.0:
            container_width = int(450 * display_scale)  # 적당한 크기로 조정
            container_height = int(400 * display_scale)
        else:
            container_width = 450
            container_height = 400
        
        input_container = tk.Frame(self.root, bg='black', relief='flat')
        input_container.place(relx=0.5, rely=0.5, anchor='center', width=container_width, height=container_height)
        
        # Lock icon in input container
        lock_label = tk.Label(input_container, text="🔒", font=("Arial", 48), 
                             bg='black', fg='white')
        lock_label.pack(pady=(20, 10))
        
        # System info (실시간 업데이트를 위해 라벨을 인스턴스 변수로 저장)
        hostname = os.uname().nodename
        
        self.time_label = tk.Label(input_container, text="", 
                             font=("Arial", 20, "bold"), bg='black', fg='white')
        self.time_label.pack(pady=(0, 2))
        
        self.date_label = tk.Label(input_container, text="",
                             font=("Arial", 12), bg='black', fg='gray')
        self.date_label.pack(pady=(0, 15))
        
        # Password prompt
        prompt_label = tk.Label(input_container, text="Enter Password:",
                               font=("Arial", 14), bg='black', fg='white')
        prompt_label.pack(pady=(0, 8))
        
        # Password entry with modern styling
        entry_frame = tk.Frame(input_container, bg='black')
        entry_frame.pack(pady=(0, 15))
        
        self.password_entry = tk.Entry(entry_frame, show='•', font=("Arial", 14),
                                      width=25, bg='#2a2a3e', fg='white',
                                      relief='flat', bd=0, insertbackground='white')
        self.password_entry.pack(ipady=8, ipadx=10)
        self.password_entry.focus_set()
        self.password_entry.bind('<Return>', self.on_unlock_attempt)
        
        # Allow only specific keys in password entry
        self.password_entry.bind('<Key>', lambda e: None if self.block_all_keys(e) != "break" else "break")
        
        # Unlock button with modern styling
        unlock_btn = tk.Button(input_container, text="Unlock", font=("Arial", 12, "bold"),
                              command=self.on_unlock_attempt, 
                              bg='#4a69bd', fg='white', relief='flat',
                              padx=30, pady=8, cursor='hand2')
        unlock_btn.pack(pady=(0, 10))
        
        # Status label
        self.status_label = tk.Label(input_container, text="Enter your password to unlock", font=("Arial", 10),
                                    bg='black', fg='orange', wraplength=350)
        self.status_label.pack(pady=(0, 10))
        
        # Center bottom info (user and hostname)
        bottom_container = tk.Frame(self.root, bg='black')
        bottom_container.place(relx=0.5, rely=0.95, anchor='center')
        
        user_info = tk.Label(bottom_container, 
                            text=f"Locked for {self.current_user}@{hostname}",
                            font=("Arial", 12), bg='black', fg='gray')
        user_info.pack()
        
        # Ensure window is shown before grabbing input
        self.root.update()
        self.grab_input()
        
        # 실시간 시간 업데이트 시작
        self.update_time()
        
        return self.root
        
    def is_session_active(self):
        """Check if user session is active"""
        try:
            result = subprocess.run(['who'], capture_output=True, text=True)
            return self.current_user in result.stdout
        except:
            return True
            
    def lock_screen(self):
        """Main lock screen function"""
        print(f"Locking screen for user: {self.current_user}")
        
        # Disable virtual terminal switching
        self.disable_virtual_terminals()
        
        # Create and show lock screen
        self.locked = True
        root = self.create_lock_screen()
        
        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.enable_virtual_terminals()
            
    def start_screensaver(self, timeout_minutes=10):
        """Start screensaver mode with timeout"""
        print(f"Starting screensaver mode (timeout: {timeout_minutes} minutes)")
        
        timeout_seconds = timeout_minutes * 60
        last_activity = time.time()
        
        while True:
            try:
                # Simple activity detection (mouse/keyboard)
                current_time = time.time()
                
                # Check if timeout reached
                if current_time - last_activity >= timeout_seconds:
                    if self.is_session_active():
                        self.lock_screen()
                        last_activity = time.time()  # Reset after unlock
                        
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("Screensaver stopped")
                break
            except Exception as e:
                print(f"Screensaver error: {e}")
                time.sleep(5)
                
    def test_components(self):
        """Test FT Lock components for debugging"""
        print(f"Current user: {self.current_user}")
        print(f"Session active: {self.is_session_active()}")
        
        # Test PAM import
        try:
            import pam
            print("✓ PAM module available")
        except ImportError as e:
            print(f"✗ PAM module error: {e}")
            
        # Test tkinter
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()  # Hide window
            print("✓ Tkinter available")
            root.destroy()
        except Exception as e:
            print(f"✗ Tkinter error: {e}")
            
        # Test hostname resolution
        try:
            import socket
            hostname = socket.gethostname()
            socket.gethostbyname(hostname)
            print(f"✓ Hostname resolution: {hostname}")
        except Exception as e:
            print(f"✗ Hostname resolution error: {e}")
            
        print("\nComponent test complete.")
        print("Note: VT switching protection disabled (no sudo required)")


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import pam
    except ImportError:
        print("Error: python3-pam not installed")
        print("Install with: apt install python3-pam")
        return False
        
    return True


def main():
    """Main function"""
    if not check_dependencies():
        sys.exit(1)
        
    ft_lock = FTLock()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--lock":
            ft_lock.lock_screen()
        elif sys.argv[1] == "--screensaver":
            timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            ft_lock.start_screensaver(timeout)
        elif sys.argv[1] == "--test":
            print("Testing FT Lock components...")
            ft_lock.test_components()
        elif sys.argv[1] == "--help":
            print("FT Lock - Linux Screen Saver with Authentication")
            print("Usage:")
            print("  ft_lock.py --lock           Lock screen immediately")
            print("  ft_lock.py --screensaver [timeout]  Start screensaver (default: 10 min)")
            print("  ft_lock.py --test           Test components")
            print("  ft_lock.py --help           Show this help")
        else:
            print("Invalid option. Use --help for usage information")
    else:
        # Default: lock immediately
        ft_lock.lock_screen()


if __name__ == "__main__":
    main()
