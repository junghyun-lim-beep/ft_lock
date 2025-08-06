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
        """Create the lock screen GUI with full screen background"""
        self.root = tk.Tk()
        self.root.title("FT Lock")
        self.root.configure(bg='black')
        
        # Make window fullscreen and topmost
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Load and set background image
        try:
            bg_path = os.path.join(os.path.dirname(__file__), 'images', 'lock_background.png')
            if os.path.exists(bg_path):
                # Load and resize background image to fit screen
                bg_image = Image.open(bg_path)
                bg_image = bg_image.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(bg_image)
                
                # Create background label that covers entire screen
                bg_label = tk.Label(self.root, image=self.bg_photo)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                # Fallback to gradient background
                self.root.configure(bg='#1a1a2e')
        except Exception as e:
            print(f"Warning: Could not load background image: {e}")
            self.root.configure(bg='#1a1a2e')
        
        # Create top-left container for passcode input
        input_container = tk.Frame(self.root, bg='rgba(0,0,0,0.7)', relief='flat')
        input_container.place(x=40, y=40, width=400, height=300)
        
        # Configure transparent background for container
        try:
            # Create a semi-transparent overlay
            overlay = tk.Frame(input_container, bg='black')
            overlay.place(x=0, y=0, relwidth=1, relheight=1)
            overlay.configure(bg='#000000')
            # Make it semi-transparent by adjusting the alpha (not directly supported in tkinter)
            # So we'll use a dark background with some opacity effect
        except:
            input_container.configure(bg='#000000')
        
        # Lock icon in input container
        lock_label = tk.Label(input_container, text="🔒", font=("Arial", 48), 
                             bg='black', fg='white')
        lock_label.pack(pady=(20, 10))
        
        # System info in top left
        hostname = os.uname().nodename
        current_time = datetime.now().strftime("%H:%M")
        date_str = datetime.now().strftime("%A, %B %d")
        
        time_label = tk.Label(input_container, text=current_time, 
                             font=("Arial", 20, "bold"), bg='black', fg='white')
        time_label.pack(pady=(0, 2))
        
        date_label = tk.Label(input_container, text=date_str,
                             font=("Arial", 12), bg='black', fg='gray')
        date_label.pack(pady=(0, 15))
        
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
        
        # Unlock button with modern styling
        unlock_btn = tk.Button(input_container, text="Unlock", font=("Arial", 12, "bold"),
                              command=self.on_unlock_attempt, 
                              bg='#4a69bd', fg='white', relief='flat',
                              padx=30, pady=8, cursor='hand2')
        unlock_btn.pack(pady=(0, 10))
        
        # Status label
        self.status_label = tk.Label(input_container, text="", font=("Arial", 10),
                                    bg='black', fg='orange', wraplength=350)
        self.status_label.pack(pady=(0, 10))
        
        # Center bottom info (user and hostname)
        bottom_container = tk.Frame(self.root, bg='black')
        bottom_container.place(relx=0.5, rely=0.95, anchor='center')
        
        user_info = tk.Label(bottom_container, 
                            text=f"Locked for {self.current_user}@{hostname}",
                            font=("Arial", 12), bg='black', fg='gray')
        user_info.pack()
        
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
