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
        # Entry 위젯인지 Text 위젯인지 확인
        if isinstance(self.password_entry, tk.Text):
            password = self.password_entry.get("1.0", tk.END).strip()
            self.password_entry.delete("1.0", tk.END)
        else:
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
            
    def _print_entry_info(self):
        """Entry 위젯 상태 정보 출력"""
        try:
            if hasattr(self, 'password_entry'):
                entry = self.password_entry
                print("=== ENTRY WIDGET STATUS ===")
                print(f"Widget exists: {entry.winfo_exists()}")
                print(f"Widget mapped: {entry.winfo_ismapped()}")
                print(f"Widget viewable: {entry.winfo_viewable()}")
                print(f"Widget position: {entry.winfo_x()}, {entry.winfo_y()}")
                print(f"Widget size: {entry.winfo_width()}x{entry.winfo_height()}")
                print(f"Widget requested size: {entry.winfo_reqwidth()}x{entry.winfo_reqheight()}")
                print(f"Widget manager: {entry.winfo_manager()}")
                print(f"Widget class: {entry.winfo_class()}")
                print(f"Widget parent: {entry.winfo_parent()}")
                
                # 부모 컨테이너 정보도 출력
                parent = entry.master
                if parent:
                    print(f"Parent mapped: {parent.winfo_ismapped()}")
                    print(f"Parent viewable: {parent.winfo_viewable()}")
                    print(f"Parent size: {parent.winfo_width()}x{parent.winfo_height()}")
                
                # 스케일링 정보
                current_scale = self.root.tk.call('tk', 'scaling')
                print(f"Current tkinter scaling: {current_scale}")
                
                print("=== END ENTRY STATUS ===")
                
                # 매핑되지 않은 경우 강제 매핑 시도
                if not entry.winfo_ismapped():
                    print("*** WIDGET NOT MAPPED - ATTEMPTING FORCED MAPPING ***")
                    try:
                        # 다양한 매핑 시도
                        entry.update()
                        entry.update_idletasks()
                        entry.tkraise()
                        entry.lift()
                        
                        # place 매니저 정보 확인 및 재설정
                        place_info = entry.place_info()
                        print(f"Place info: {place_info}")
                        
                        if place_info:
                            # place 설정 재적용
                            entry.place_forget()
                            entry.place(relx=0.5, rely=0.6, anchor='center', 
                                       width=280, height=40)
                            print("Place settings reapplied")
                            
                        # 최종 상태 확인
                        self.root.after(100, lambda: print(f"After forced mapping - mapped: {entry.winfo_ismapped()}, viewable: {entry.winfo_viewable()}"))
                        
                    except Exception as map_e:
                        print(f"Forced mapping failed: {map_e}")
                        
        except Exception as e:
            print(f"Entry info failed: {e}")
            
    def _try_alternative_entry_placement(self):
        """Entry가 보이지 않을 때 대안 배치 방법 시도"""
        if not hasattr(self, 'password_entry') or not self.password_entry:
            return
            
        try:
            entry = self.password_entry
            print("=== TRYING ALTERNATIVE ENTRY PLACEMENT ===")
            
            # 현재 상태 확인
            is_mapped = entry.winfo_ismapped()
            is_viewable = entry.winfo_viewable()
            print(f"Current state - mapped: {is_mapped}, viewable: {is_viewable}")
            
            if not is_mapped or not is_viewable:
                print("Entry not visible - trying alternative methods...")
                
                # 방법 1: 새로운 Entry를 root에 직접 생성
                print("Method 1: Creating new Entry directly on root")
                try:
                    # 기존 Entry 제거
                    entry.destroy()
                    
                    # 새 Entry를 root에 직접 생성
                    self.password_entry = tk.Entry(self.root, 
                                                  show='•', 
                                                  font=("Arial", 24),
                                                  width=15,
                                                  bg='red',
                                                  fg='yellow',
                                                  relief='solid',
                                                  bd=5,
                                                  insertbackground='white')
                    
                    # 화면 중앙에 절대 위치 배치
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    x = screen_width // 2 - 150  # 대략적인 중앙
                    y = screen_height // 2 + 50   # 중앙보다 약간 아래
                    
                    self.password_entry.place(x=x, y=y, width=300, height=50)
                    
                    # 이벤트 바인딩 재설정
                    self.password_entry.bind('<Return>', self.on_unlock_attempt)
                    self.password_entry.bind('<Key>', lambda e: None if self.block_all_keys(e) != "break" else "break")
                    
                    # 강제 업데이트
                    self.root.update_idletasks()
                    self.root.update()
                    
                    # 포커스 설정
                    self.password_entry.focus_set()
                    self.password_entry.tkraise()
                    
                    print(f"New Entry created on root at position ({x}, {y})")
                    
                    # 상태 재확인
                    self.root.after(200, lambda: print(f"Alternative method result - mapped: {self.password_entry.winfo_ismapped()}, viewable: {self.password_entry.winfo_viewable()}"))
                    
                except Exception as alt_e:
                    print(f"Alternative method 1 failed: {alt_e}")
                    
                    # 방법 2: 간단한 Text 위젯으로 대체
                    print("Method 2: Trying Text widget as fallback")
                    try:
                        self.password_entry = tk.Text(self.root, 
                                                     font=("Arial", 24),
                                                     height=1,
                                                     width=15,
                                                     bg='red',
                                                     fg='yellow',
                                                     relief='solid',
                                                     bd=5,
                                                     insertbackground='white')
                        
                        self.password_entry.place(x=x, y=y, width=300, height=50)
                        self.password_entry.focus_set()
                        
                        print("Text widget fallback created")
                        
                    except Exception as text_e:
                        print(f"Text widget fallback failed: {text_e}")
            else:
                print("Entry is visible - no alternative needed")
                
        except Exception as e:
            print(f"Alternative placement failed: {e}")
            
    def create_lock_screen(self):
        """Create the lock screen GUI with full screen background"""
        self.root = tk.Tk()
        self.root.title("FT Lock - Test Mode")
        self.root.configure(bg='black')
        
        # 스케일 조회 및 강제 적용 테스트
        try:
            print("=== SCALE DETECTION TEST ===")
            
            # 1. 현재 tkinter 스케일링 값 조회
            current_scale = self.root.tk.call('tk', 'scaling')
            print(f"Current tkinter scaling: {current_scale}")
            
            # 2. 화면 정보 조회
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            screen_width_mm = self.root.winfo_screenmmwidth()
            screen_height_mm = self.root.winfo_screenmmheight()
            print(f"Screen: {screen_width}x{screen_height}px, {screen_width_mm}x{screen_height_mm}mm")
            
            # 3. DPI 계산
            dpi_x = screen_width / (screen_width_mm / 25.4)
            dpi_y = screen_height / (screen_height_mm / 25.4)
            print(f"Calculated DPI: {dpi_x:.1f}x{dpi_y:.1f}")
            
            # 4. tkinter DPI 조회
            tk_dpi = self.root.winfo_fpixels('1i')
            print(f"Tkinter DPI: {tk_dpi:.1f}")
            
            print("=== SCALE FORCE TEST ===")
            
            # 5. 강제로 다양한 스케일 값 적용해보기
            test_scales = [0.5, 1.0, 1.5, 2.0]
            for scale in test_scales:
                try:
                    self.root.tk.call('tk', 'scaling', scale)
                    new_scale = self.root.tk.call('tk', 'scaling')
                    print(f"Set scale {scale} -> Got scale {new_scale}")
                except Exception as e:
                    print(f"Failed to set scale {scale}: {e}")
            
            # 6. 1.33 스케일링 문제 해결 - 강제로 1.0 고정
            if current_scale > 1.2:  # 1.33이나 다른 이상한 값들
                print(f"Problematic scaling detected: {current_scale}")
                print("Forcing scaling to 1.0 to fix UI rendering...")
                
                # 여러 번 시도해서 확실히 1.0으로 설정
                for attempt in range(3):
                    self.root.tk.call('tk', 'scaling', 1.0)
                    new_scale = self.root.tk.call('tk', 'scaling')
                    print(f"Attempt {attempt+1}: Set 1.0 -> Got {new_scale}")
                    if abs(new_scale - 1.0) < 0.01:  # 거의 1.0이면 성공
                        break
                
                final_scale = self.root.tk.call('tk', 'scaling')
                print(f"Final scaling locked to: {final_scale}")
                
                if abs(final_scale - 1.0) < 0.01:
                    print("✅ Scaling fix successful - UI should render properly now")
                else:
                    print("❌ Scaling fix failed - UI may still have issues")
            else:
                print("Normal scaling detected - no fix needed")
            
            print("=== SCALE TEST COMPLETE ===")
            
        except Exception as e:
            print(f"Scale test failed: {e}")
        
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
        
        # Entry 위젯 매핑 문제 해결 시도 - 스케일링 200% 대응
        print("Trying different Entry placement methods for high DPI...")
        
        # 스케일링 정보 다시 확인
        current_scale = self.root.tk.call('tk', 'scaling')
        print(f"Current scaling when creating Entry: {current_scale}")
        
        # 방법 1: 절대 위치 지정으로 Entry 생성 (place 사용)
        print("Method 1: Using place() with absolute positioning")
        
        # 컨테이너 크기 확인
        input_container.update_idletasks()
        container_width = input_container.winfo_reqwidth()
        container_height = input_container.winfo_reqheight()
        print(f"Container size: {container_width}x{container_height}")
        
        self.password_entry = tk.Entry(input_container, 
                                      show='•', 
                                      font=("Arial", 16),        # 폰트 크기 조정
                                      width=20,                  # 너비 증가
                                      bg='red',                  # 빨간 배경 (테스트용)
                                      fg='yellow',               # 노란 글자
                                      relief='solid',            # 실선 테두리
                                      bd=3,                      # 테두리 두께
                                      insertbackground='white')  # 흰색 커서
        
        # pack 대신 place 사용으로 절대 위치 지정
        self.password_entry.place(relx=0.5, rely=0.6, anchor='center', 
                                 width=280, height=40)
        
        # 강제로 업데이트 및 매핑 시도
        print("Forcing widget updates and mapping...")
        self.root.update_idletasks()
        self.root.update()
        input_container.update_idletasks()
        input_container.update()
        
        # 위젯 강제 매핑 시도
        try:
            self.password_entry.tkraise()  # 위젯을 맨 앞으로
            self.password_entry.lift()     # 다른 방법으로도 앞으로
            print("Widget raised to front")
        except Exception as e:
            print(f"Widget raise failed: {e}")
            
        # 위젯 가시성 강제 설정
        try:
            # 위젯이 실제로 보이도록 강제 설정
            self.password_entry.configure(state='normal')
            print("Widget state set to normal")
        except Exception as e:
            print(f"Widget state setting failed: {e}")
            
        # 추가 매핑 시도
        try:
            # 부모 컨테이너도 강제 업데이트
            input_container.tkraise()
            input_container.lift()
            print("Container raised to front")
        except Exception as e:
            print(f"Container raise failed: {e}")
        
        print("Entry widget configured with HIGH VISIBILITY settings:")
        print(f"- Font: Arial 20")
        print(f"- Background: red")
        print(f"- Foreground: yellow") 
        print(f"- Border: solid 5px")
        print(f"- Size: width=15, padding=15x20")
        
        # Entry 위젯 정보 여러 번 체크 및 대안 방법 시도
        self.root.after(50, self._print_entry_info)    # 50ms 후
        self.root.after(200, self._print_entry_info)   # 200ms 후  
        self.root.after(500, self._print_entry_info)   # 500ms 후
        self.root.after(1000, self._try_alternative_entry_placement)  # 1초 후 대안 시도
        
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
