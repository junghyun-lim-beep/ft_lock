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
import xml.etree.ElementTree as ET

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
        
    def get_display_scale(self):
        """monitors.xml에서 현재 사용 중인 정확한 스케일 찾기"""
        actual_scale = 1.0
        
        print("=" * 50)
        print("스케일 감지 중...")
        print("=" * 50)
        
        try:
            monitors_file = os.path.expanduser("~/.config/monitors.xml")
            if os.path.exists(monitors_file):
                tree = ET.parse(monitors_file)
                root = tree.getroot()
                
                print("monitors.xml 분석:")
                
                # 모든 configuration을 확인하되, 첫 번째가 현재 활성
                configs = root.findall('configuration')
                print(f"총 {len(configs)}개 configuration 발견")
                
                if configs:
                    # 첫 번째 configuration 사용
                    active_config = configs[0]
                    print("첫 번째 configuration 사용:")
                    
                    logicalmonitors = active_config.findall('logicalmonitor')
                    print(f"  {len(logicalmonitors)}개 logicalmonitor 발견")
                    
                    # 모든 모니터 정보 수집 및 상세 출력
                    monitors_info = []
                    for i, lm in enumerate(logicalmonitors):
                        print(f"\n  === Monitor {i+1} 상세 정보 ===")
                        
                        # 스케일
                        scale_elem = lm.find('scale')
                        scale_val = float(scale_elem.text) if scale_elem is not None else 1.0
                        print(f"    scale: {scale_val}")
                        
                        # primary
                        primary_elem = lm.find('primary')
                        is_primary = primary_elem is not None and primary_elem.text == 'yes'
                        print(f"    primary: {is_primary}")
                        
                        # x, y 좌표
                        x_elem = lm.find('x')
                        y_elem = lm.find('y')
                        x_val = x_elem.text if x_elem is not None else 'N/A'
                        y_val = y_elem.text if y_elem is not None else 'N/A'
                        print(f"    좌표: ({x_val}, {y_val})")
                        
                        # 모니터 상세 정보
                        for monitor in lm.findall('monitor'):
                            monitorspec = monitor.find('monitorspec')
                            if monitorspec is not None:
                                connector = monitorspec.find('connector')
                                vendor = monitorspec.find('vendor')
                                product = monitorspec.find('product')
                                serial = monitorspec.find('serial')
                                
                                print(f"    connector: {connector.text if connector is not None else 'N/A'}")
                                print(f"    vendor: {vendor.text if vendor is not None else 'N/A'}")
                                print(f"    product: {product.text if product is not None else 'N/A'}")
                                print(f"    serial: {serial.text if serial is not None else 'N/A'}")
                            
                            # 해상도 정보
                            mode = monitor.find('mode')
                            if mode is not None:
                                width = mode.find('width')
                                height = mode.find('height')
                                rate = mode.find('rate')
                                
                                width_val = width.text if width is not None else 'N/A'
                                height_val = height.text if height is not None else 'N/A'
                                rate_val = rate.text if rate is not None else 'N/A'
                                
                                print(f"    해상도: {width_val}x{height_val}")
                                print(f"    주사율: {rate_val}")
                        
                        monitors_info.append((i+1, scale_val, is_primary))
                    
                    # 스케일 선택 로직: xrandr primary 모니터와 정확히 매칭
                    print("\n  xrandr primary 모니터와 monitors.xml 매칭...")
                    try:
                        import subprocess
                        
                        # 현재 primary 모니터 이름 찾기
                        xrandr_result = subprocess.run(['xrandr'], capture_output=True, text=True, timeout=5)
                        primary_monitor_name = None
                        
                        if xrandr_result.returncode == 0:
                            print("  xrandr 출력 분석:")
                            for line in xrandr_result.stdout.split('\n'):
                                if 'connected' in line:
                                    print(f"    연결된 모니터: {line}")
                                    if 'connected primary' in line:
                                        primary_monitor_name = line.split()[0]
                                        print(f"    ✓ Primary 모니터: {primary_monitor_name}")
                        
                        if primary_monitor_name:
                            print(f"\n  monitors.xml에서 {primary_monitor_name} 모니터 찾기...")
                            
                            # monitors.xml에서 해당 모니터의 스케일 찾기
                            for i, lm in enumerate(active_config.findall('logicalmonitor')):
                                print(f"\n    LogicalMonitor {i+1} 분석:")
                                
                                # 모니터 connector 이름 찾기
                                monitor_connector = None
                                for monitor in lm.findall('monitor'):
                                    monitorspec = monitor.find('monitorspec')
                                    if monitorspec is not None:
                                        connector = monitorspec.find('connector')
                                        if connector is not None:
                                            monitor_connector = connector.text
                                            print(f"      connector: {monitor_connector}")
                                            break
                                
                                # 스케일과 primary 상태 확인
                                scale_elem = lm.find('scale')
                                primary_elem = lm.find('primary')
                                if scale_elem is not None:
                                    scale_val = float(scale_elem.text)
                                    is_primary = primary_elem is not None and primary_elem.text == 'yes'
                                    print(f"      scale: {scale_val}")
                                    print(f"      primary: {is_primary}")
                                    
                                    # connector 이름이 일치하는지 확인
                                    if monitor_connector == primary_monitor_name:
                                        actual_scale = scale_val
                                        print(f"      🎯 매칭 성공! {primary_monitor_name}의 스케일: {actual_scale}")
                                        break
                                    else:
                                        print(f"      ❌ 매칭 실패: {monitor_connector} ≠ {primary_monitor_name}")
                        
                        # 매칭 실패시에만 fallback
                        if actual_scale == 1.0:
                            print("\n  ⚠️ 매칭 실패! 아무거나 사용하지 말고 오류 리포트:")
                            print(f"    찾던 모니터: {primary_monitor_name}")
                            print("    monitors.xml의 모든 connector들:")
                            for i, lm in enumerate(active_config.findall('logicalmonitor')):
                                for monitor in lm.findall('monitor'):
                                    monitorspec = monitor.find('monitorspec')
                                    if monitorspec is not None:
                                        connector = monitorspec.find('connector')
                                        if connector is not None:
                                            print(f"      Monitor {i+1}: {connector.text}")
                        
                    except Exception as e:
                        print(f"  매칭 과정 오류: {e}")
                        actual_scale = 1.0
                
            else:
                print("monitors.xml 없음")
                        
        except Exception as e:
            print(f"오류: {e}")
        
        print(f"최종 스케일: {actual_scale}")
        print("=" * 50)
        
        return actual_scale
        
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
                # Load and resize background image to logical screen size (not scaled)
                bg_image = Image.open(bg_path)
                # 논리적 해상도에 맞춰 리사이징 (스케일 무시)
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
