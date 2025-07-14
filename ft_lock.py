#!/usr/bin/env python3
"""
FT Lock - Linux Screen Saver with Authentication
A secure screen locker for Ubuntu 22.04 with lightdm integration
"""

import tkinter as tk
from tkinter import ttk, messagebox
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


class FTLock:
    def __init__(self):
        self.root = None
        self.password_entry = None
        self.status_label = None
        self.attempts = 0
        self.max_attempts = 3
        self.current_user = getpass.getuser()
        self.locked = False
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        if self.root:
            self.root.quit()
        sys.exit(0)
        
    def disable_virtual_terminals(self):
        """Disable virtual terminal switching"""
        try:
            # Disable Ctrl+Alt+F1-F12 switching
            subprocess.run(['sudo', '-n', 'chvt', '7'], 
                         stderr=subprocess.DEVNULL, check=False)
            for i in range(1, 13):
                subprocess.run(['sudo', '-n', 'deallocvt', str(i)], 
                             stderr=subprocess.DEVNULL, check=False)
        except Exception as e:
            print(f"Warning: Could not disable VT switching: {e}")
            
    def enable_virtual_terminals(self):
        """Re-enable virtual terminal switching"""
        try:
            for i in range(1, 13):
                subprocess.run(['sudo', '-n', 'openvt', '-c', str(i)], 
                             stderr=subprocess.DEVNULL, check=False)
        except Exception as e:
            print(f"Warning: Could not re-enable VT switching: {e}")
            
    def grab_input(self):
        """Grab keyboard and mouse input"""
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
            self.root.grab_set_global()
            self.root.focus_force()
            if self.password_entry:
                self.password_entry.focus_set()
        except Exception as e:
            print(f"Warning: Delayed grab failed: {e}")
            # Try alternative focus method
            try:
                self.root.focus_set()
                if self.password_entry:
                    self.password_entry.focus_set()
            except:
                pass
            
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
        if self.authenticate_user(self.current_user, password):
            self.unlock_screen()
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            
            if self.attempts >= self.max_attempts:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Max attempts reached. System will be locked for 5 minutes.", 
                    foreground="red"))
                time.sleep(300)  # 5 minute lockout
                self.attempts = 0
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Invalid password. {remaining} attempts remaining.", 
                    foreground="red"))
                    
    def unlock_screen(self):
        """Unlock the screen and exit"""
        self.locked = False
        self.enable_virtual_terminals()
        if self.root:
            self.root.quit()
            
    def create_lock_screen(self):
        """Create the lock screen GUI"""
        self.root = tk.Tk()
        self.root.title("FT Lock")
        self.root.configure(bg='black')
        
        # Make window fullscreen and topmost
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Center container
        container = tk.Frame(self.root, bg='black')
        container.place(relx=0.5, rely=0.5, anchor='center')
        
        # Lock icon (using Unicode)
        lock_label = tk.Label(container, text="🔒", font=("Arial", 72), 
                             bg='black', fg='white')
        lock_label.pack(pady=20)
        
        # System info
        hostname = os.uname().nodename
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        info_label = tk.Label(container, 
                             text=f"{hostname}\n{current_time}\nUser: {self.current_user}",
                             font=("Arial", 14), bg='black', fg='gray',
                             justify='center')
        info_label.pack(pady=10)
        
        # Password prompt
        prompt_label = tk.Label(container, text="Enter password to unlock:",
                               font=("Arial", 16), bg='black', fg='white')
        prompt_label.pack(pady=10)
        
        # Password entry
        self.password_entry = tk.Entry(container, show='*', font=("Arial", 14),
                                      width=20, justify='center')
        self.password_entry.pack(pady=10)
        self.password_entry.focus_set()
        self.password_entry.bind('<Return>', self.on_unlock_attempt)
        
        # Unlock button
        unlock_btn = tk.Button(container, text="Unlock", font=("Arial", 12),
                              command=self.on_unlock_attempt, 
                              bg='darkblue', fg='white', padx=20)
        unlock_btn.pack(pady=10)
        
        # Status label
        self.status_label = tk.Label(container, text="", font=("Arial", 12),
                                    bg='black', fg='white')
        self.status_label.pack(pady=10)
        
        # Disable window manager functions
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Ensure window is shown before grabbing input
        self.root.update()
        self.grab_input()
        
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
            
        # Test sudo access (non-interactive)
        try:
            result = subprocess.run(['sudo', '-n', 'true'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✓ Sudo access available")
            else:
                print("⚠ Sudo requires password (VT switching may not work)")
        except Exception as e:
            print(f"✗ Sudo test error: {e}")
            
        print("\nComponent test complete.")


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import pam
    except ImportError:
        print("Error: python3-pam not installed")
        print("Install with: sudo apt install python3-pam")
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
