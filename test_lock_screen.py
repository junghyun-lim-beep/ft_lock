#!/usr/bin/env python3
"""
Test script for the FT Lock screen interface
This shows the lock screen GUI without authentication requirements
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
import getpass
from datetime import datetime
import threading
import time

class TestFTLock:
    def __init__(self):
        self.root = None
        self.password_entry = None
        self.status_label = None
        self.attempts = 0
        self.max_attempts = 3
        self.current_user = getpass.getuser()
        self.locked = False
        
    def on_unlock_attempt(self, event=None):
        """Handle unlock attempt (test version)"""
        password = self.password_entry.get()
        self.password_entry.delete(0, tk.END)
        
        if not password:
            self.status_label.config(text="Please enter password", foreground="orange")
            return
            
        self.status_label.config(text="Authenticating...", foreground="blue")
        self.root.update()
        
        # Simulate authentication delay
        self.root.after(1000, lambda: self.test_authentication(password))
        
    def test_authentication(self, password):
        """Test authentication (accepts 'test' as password)"""
        if password == 'test':
            self.status_label.config(text="Authentication successful!", foreground="green")
            self.root.after(2000, self.unlock_screen)
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            
            if self.attempts >= self.max_attempts:
                self.status_label.config(
                    text=f"Max attempts reached. Try again later.", 
                    foreground="red")
                self.root.after(3000, lambda: setattr(self, 'attempts', 0))
            else:
                self.status_label.config(
                    text=f"Invalid password. {remaining} attempts remaining.", 
                    foreground="red")
                    
    def unlock_screen(self):
        """Unlock the screen and exit"""
        self.locked = False
        if self.root:
            self.root.quit()
            
    def create_lock_screen(self):
        """Create the lock screen GUI with full screen background"""
        self.root = tk.Tk()
        self.root.title("FT Lock - Test Mode")
        self.root.configure(bg='black')
        
        # Make window fullscreen and topmost
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        
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
        input_container = tk.Frame(self.root, bg='black', relief='flat')
        input_container.place(x=40, y=40, width=400, height=320)
        
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
        self.status_label = tk.Label(input_container, text="Enter 'test' to unlock", font=("Arial", 10),
                                    bg='black', fg='orange', wraplength=350)
        self.status_label.pack(pady=(0, 10))
        
        # Center bottom info (user and hostname)
        bottom_container = tk.Frame(self.root, bg='black')
        bottom_container.place(relx=0.5, rely=0.95, anchor='center')
        
        user_info = tk.Label(bottom_container, 
                            text=f"Test Mode - Locked for {self.current_user}@{hostname}",
                            font=("Arial", 12), bg='black', fg='gray')
        user_info.pack()
        
        # Add escape key to exit test mode
        self.root.bind('<Escape>', lambda e: self.root.quit())
        
        # Test mode hint
        hint_label = tk.Label(self.root, text="Press ESC to exit test mode",
                             font=("Arial", 10), bg='black', fg='gray')
        hint_label.place(x=10, y=10)
        
        return self.root
        
    def test_lock_screen(self):
        """Test the lock screen"""
        print(f"Testing lock screen for user: {self.current_user}")
        print("Password: 'test' | Press ESC to exit")
        
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
