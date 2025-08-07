#!/usr/bin/env python3
"""
Test script for the FT Lock screen interface
This shows the lock screen GUI with PAM authentication and shortcut blocking
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
import getpass
from datetime import datetime
import threading
import time

# Try to import PAM, but make it optional for testing
try:
    import pam
    PAM_AVAILABLE = True
    print("✓ PAM module loaded - Real authentication available")
except ImportError:
    PAM_AVAILABLE = False
    print("⚠ PAM module not available - Using test mode only")

class TestFTLock:
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
        self.lockout_active = False  # 5분 잠금 상태 추가
        self.lockout_start_time = None  # 잠금 시작 시간
        
    def authenticate_user(self, username, password):
        """Authenticate user using PAM (if available)"""
        if not PAM_AVAILABLE:
            return False
            
        try:
            p = pam.pam()
            return p.authenticate(username, password)
        except Exception as e:
            print(f"PAM Authentication error: {e}")
            return False
        
    def block_all_keys(self, event):
        """Block all key combinations except allowed ones"""
        # Allow basic typing keys and navigation keys
        allowed_keys = {
            'Return', 'BackSpace', 'Delete', 'Left', 'Right', 'Home', 'End',
            'Tab', 'Escape',  # Escape only for test mode
            'space', 'Space'  # Space key
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
        
    def on_unlock_attempt(self, event=None):
        """Handle unlock attempt (test version with PAM support)"""
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
        
        # Check for test password first (always works)
        if password == 'test':
            self.attempts = 0  # 성공 시 시도 횟수 리셋
            self.lockout_active = False  # 잠금 해제
            self.root.after(0, lambda: self.status_label.config(
                text="Test password accepted!", foreground="green"))
            self.root.after(500, self.unlock_screen)
            return
            
        # Try PAM authentication if available
        if PAM_AVAILABLE:
            if self.authenticate_user(self.current_user, password):
                self.attempts = 0  # 성공 시 시도 횟수 리셋
                self.lockout_active = False  # 잠금 해제
                self.root.after(0, lambda: self.status_label.config(
                    text="PAM authentication successful!", foreground="green"))
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
            auth_method = "PAM" if PAM_AVAILABLE else "test"
            self.root.after(0, lambda: self.status_label.config(
                text=f"Invalid password ({auth_method}). {remaining} attempts remaining.", 
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
        if self.root:
            self.root.quit()
            
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
        self.root.title("FT Lock - Test Mode")
        self.root.configure(bg='black')
        
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
                bg_image = bg_image.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
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
        input_container = tk.Frame(self.root, bg='black', relief='flat')
        input_container.place(relx=0.5, rely=0.5, anchor='center', width=400, height=350)
        
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
        
        # Password entry with ABSOLUTE FIXED positioning
        print("🔧 Creating Entry with ABSOLUTE FIXED values for all screens!")
        
        # 완전 고정 설정 (모든 해상도/스케일에서 동일한 절대 위치)
        font_size = 18           # 고정 폰트
        entry_width = 400        # 고정 너비
        entry_height = 60        # 고정 높이
        x_position = 760         # 고정 X 좌표 (1920 기준 중앙)
        y_position = 580         # 고정 Y 좌표 (1080 기준 중앙)
        bg_color = '#8a8abe'     # 밝은 보라색 배경
        
        # Entry를 root에 직접 생성 (절대 위치)
        self.password_entry = tk.Entry(self.root,
                                      show='•',
                                      font=("Arial", font_size, "bold"),
                                      bg=bg_color,
                                      fg='white',
                                      relief='solid',
                                      bd=4,
                                      highlightthickness=2,
                                      highlightcolor='#ffffff',
                                      insertbackground='white',
                                      insertwidth=3)
        
        # 절대 위치로 고정 배치
        self.password_entry.place(x=x_position, y=y_position, width=entry_width, height=entry_height)
        
        print(f"Entry FIXED at absolute position ({x_position}, {y_position}) size {entry_width}x{entry_height}")
        print(f"This position is SAME on ALL screen resolutions and scales!")
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
        
        # Status label with authentication method info
        auth_info = "PAM + test mode" if PAM_AVAILABLE else "Test mode only"
        status_text = f"Auth: {auth_info}\nEnter your password or 'test' to unlock"
        
        self.status_label = tk.Label(input_container, text=status_text, font=("Arial", 10),
                                    bg='black', fg='orange', wraplength=350, justify='center')
        self.status_label.pack(pady=(0, 10))
        
        # Center bottom info (user and hostname)
        bottom_container = tk.Frame(self.root, bg='black')
        bottom_container.place(relx=0.5, rely=0.95, anchor='center')
        
        user_info = tk.Label(bottom_container, 
                            text=f"Test Mode - Locked for {self.current_user}@{hostname}",
                            font=("Arial", 12), bg='black', fg='gray')
        user_info.pack()
        
        # Add escape key to exit test mode (only in test mode)
        def safe_exit(event):
            if event.keysym == 'Escape':
                self.locked = False
                self.root.quit()
            return "break"
            
        self.root.bind('<Escape>', safe_exit)
        
        # Test mode hint
        pam_status = "PAM Available" if PAM_AVAILABLE else "PAM Not Available"
        hint_label = tk.Label(self.root, text=f"Press ESC to exit | {pam_status} | Test password: 'test'",
                             font=("Arial", 10), bg='black', fg='gray')
        hint_label.place(x=10, y=10)
        
        # Ensure window is shown before grabbing input
        self.root.update()
        self.grab_input()
        
        # 실시간 시간 업데이트 시작
        self.update_time()
        
        return self.root
        
    def test_lock_screen(self):
        """Test the lock screen"""
        print(f"Testing lock screen for user: {self.current_user}")
        
        if PAM_AVAILABLE:
            print("✓ PAM authentication enabled - Use your system password")
            print("✓ Test password 'test' also works for quick testing")
        else:
            print("⚠ PAM not available - Only test password 'test' works")
            print("  Install PAM: apt install python3-pam")
        
        print("Press ESC to exit test mode")
        
        self.locked = True
        root = self.create_lock_screen()
        
        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
            
def main():
    """Main function"""
    lock = TestFTLock()
    lock.test_lock_screen()

if __name__ == "__main__":
    main()
