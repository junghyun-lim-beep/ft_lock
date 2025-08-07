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
            
    def _check_entry_status(self):
        """Entry 위젯 상태 확인 및 문제 시 강제 수정"""
        try:
            if hasattr(self, 'password_entry') and self.password_entry:
                is_mapped = self.password_entry.winfo_ismapped()
                is_viewable = self.password_entry.winfo_viewable()
                width = self.password_entry.winfo_width()
                height = self.password_entry.winfo_height()
                
                print(f"Entry status: mapped={is_mapped}, viewable={is_viewable}, size={width}x{height}")
                
                if not is_mapped or not is_viewable or width < 10 or height < 10:
                    print("⚠️  Entry widget has visibility issues!")
                    print("🔧 Attempting emergency fix...")
                    
                    # 긴급 수정: 새로운 Entry를 root에 직접 생성
                    try:
                        # 기존 Entry 제거
                        if hasattr(self, 'password_entry') and self.password_entry:
                            self.password_entry.destroy()
                        
                        # 화면 중앙에 직접 Entry 생성
                        screen_width = self.root.winfo_screenwidth()
                        screen_height = self.root.winfo_screenheight()
                        
                        self.password_entry = tk.Entry(self.root,
                                                      show='•',
                                                      font=("Arial", 16),
                                                      width=20,
                                                      bg='#6a6a8e',  # 더욱 밝은 배경
                                                      fg='white',
                                                      relief='solid',
                                                      bd=3,
                                                      insertbackground='white')
                        
                        # 화면 정중앙에 배치
                        x = screen_width // 2 - 150
                        y = screen_height // 2 + 50
                        self.password_entry.place(x=x, y=y, width=300, height=50)
                        
                        # 이벤트 재바인딩
                        self.password_entry.bind('<Return>', self.on_unlock_attempt)
                        self.password_entry.bind('<Key>', lambda e: None if self.block_all_keys(e) != "break" else "break")
                        
                        # 강제 업데이트 및 포커스
                        self.root.update()
                        self.password_entry.focus_set()
                        
                        print("✅ Emergency Entry created directly on root!")
                        
                        # 상태 재확인
                        self.root.after(100, lambda: print(f"Emergency Entry status: mapped={self.password_entry.winfo_ismapped()}, viewable={self.password_entry.winfo_viewable()}"))
                        
                    except Exception as fix_e:
                        print(f"❌ Emergency fix failed: {fix_e}")
                else:
                    print("✅ Entry widget appears to be visible")
        except Exception as e:
            print(f"Entry status check failed: {e}")
            
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
        
        # Password entry with scaling-aware styling
        print("Creating password entry with scaling detection...")
        
        # 다양한 방법으로 스케일링 감지 (우분투 대응)
        print("=== SCALING DETECTION ===")
        
        # 방법 1: tkinter 스케일링
        try:
            tk_scale = self.root.tk.call('tk', 'scaling')
            print(f"Tkinter scaling: {tk_scale}")
        except:
            tk_scale = 1.0
            print("Tkinter scaling: failed, using 1.0")
        
        # 방법 2: DPI 기반 계산
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight() 
            screen_width_mm = self.root.winfo_screenmmwidth()
            screen_height_mm = self.root.winfo_screenmmheight()
            
            dpi_x = screen_width / (screen_width_mm / 25.4) if screen_width_mm > 0 else 96
            dpi_y = screen_height / (screen_height_mm / 25.4) if screen_height_mm > 0 else 96
            dpi_scale = max(dpi_x, dpi_y) / 96.0
            
            print(f"Screen: {screen_width}x{screen_height}px, {screen_width_mm}x{screen_height_mm}mm")
            print(f"DPI: {dpi_x:.1f}x{dpi_y:.1f}, DPI scale: {dpi_scale:.2f}")
        except:
            dpi_scale = 1.0
            print("DPI detection failed, using 1.0")
        
        # 방법 3: 환경 변수 확인 (우분투/GNOME)
        env_scale = 1.0
        try:
            # GDK_SCALE 환경 변수
            if 'GDK_SCALE' in os.environ:
                env_scale = float(os.environ['GDK_SCALE'])
                print(f"GDK_SCALE: {env_scale}")
            
            # QT_SCALE_FACTOR 환경 변수
            elif 'QT_SCALE_FACTOR' in os.environ:
                env_scale = float(os.environ['QT_SCALE_FACTOR'])
                print(f"QT_SCALE_FACTOR: {env_scale}")
            else:
                print("No scaling environment variables found")
        except:
            print("Environment variable detection failed")
            
        # 방법 4: GNOME/우분투 시스템 스케일링 직접 확인
        system_scale = 1.0
        try:
            import subprocess
            
            # gsettings로 GNOME 스케일링 확인
            try:
                result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'scaling-factor'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    scale_str = result.stdout.strip()
                    if scale_str.startswith('uint32'):
                        # uint32 2 형태에서 숫자 추출
                        system_scale = float(scale_str.split()[-1])
                        print(f"GNOME scaling-factor: {system_scale}")
                    else:
                        system_scale = float(scale_str)
                        print(f"GNOME scaling-factor: {system_scale}")
            except:
                print("gsettings scaling-factor check failed")
            
            # Fractional Scaling 확인 (우분투 20.04+)
            try:
                # mutter의 experimental features 확인
                result = subprocess.run(['gsettings', 'get', 'org.gnome.mutter', 'experimental-features'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and 'scale-monitor-framebuffer' in result.stdout:
                    print("Fractional scaling detected")
                    
                    # monitors.xml 파일에서 실제 스케일 확인
                    import xml.etree.ElementTree as ET
                    monitors_path = os.path.expanduser("~/.config/monitors.xml")
                    if os.path.exists(monitors_path):
                        try:
                            tree = ET.parse(monitors_path)
                            root = tree.getroot()
                            for monitor in root.findall('.//monitor'):
                                scale_elem = monitor.find('.//scale')
                                if scale_elem is not None:
                                    fractional_scale = float(scale_elem.text)
                                    if fractional_scale > system_scale:
                                        system_scale = fractional_scale
                                        print(f"Fractional scale from monitors.xml: {fractional_scale}")
                        except:
                            print("Failed to parse monitors.xml")
                    
                    # xrandr로도 확인 시도
                    try:
                        result = subprocess.run(['xrandr', '--listmonitors'], 
                                              capture_output=True, text=True, timeout=2)
                        if result.returncode == 0:
                            # xrandr 출력에서 스케일링 정보 찾기
                            lines = result.stdout.split('\n')
                            for line in lines:
                                if 'x' in line and '/' in line:
                                    # 예: 3840/1920x2160/1080 형태에서 스케일 계산
                                    parts = line.split()
                                    for part in parts:
                                        if '/' in part and 'x' in part:
                                            try:
                                                # 3840/1920x2160/1080 -> 3840/1920 = 2.0
                                                width_part = part.split('x')[0]
                                                if '/' in width_part:
                                                    actual, logical = width_part.split('/')
                                                    xrandr_scale = float(actual) / float(logical)
                                                    if xrandr_scale > 1.5:
                                                        system_scale = max(system_scale, xrandr_scale)
                                                        print(f"Xrandr detected scale: {xrandr_scale}")
                                            except:
                                                pass
                    except:
                        print("xrandr check failed")
            except:
                print("Fractional scaling check failed")
            
            # text-scaling-factor도 확인
            try:
                result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'text-scaling-factor'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    text_scale = float(result.stdout.strip())
                    print(f"GNOME text-scaling-factor: {text_scale}")
                    if text_scale > system_scale:
                        system_scale = text_scale
            except:
                print("gsettings text-scaling-factor check failed")
                
        except:
            print("System scaling detection failed")
            
        print(f"System scale: {system_scale}")
        
        # 최종 스케일 결정 (시스템 스케일 우선, 그 다음 최대값)
        detected_scales = [tk_scale, dpi_scale, env_scale, system_scale]
        
        # 시스템 스케일이 2.0이면 확실히 200%
        if system_scale >= 2.0:
            current_scale = system_scale
            print(f"Using system scale (200% detected): {current_scale}")
        else:
            current_scale = max(detected_scales)
            print(f"Using max detected scale: {current_scale}")
        
        print(f"All detected scales: tkinter={tk_scale}, dpi={dpi_scale:.2f}, env={env_scale}, system={system_scale}")
        print(f"Final scale decision: {current_scale}")
        print("=== SCALING DETECTION END ===")
        
        # 방법 5: 화면 해상도 기반 스케일링 추정 (더 정확한 방법)
        resolution_scale = 1.0
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 일반적인 해상도별 스케일링 추정
            if screen_width >= 3840 or screen_height >= 2160:  # 4K
                resolution_scale = 2.0
                print(f"4K resolution detected ({screen_width}x{screen_height}) - likely 200% scaling")
            elif screen_width >= 2560 or screen_height >= 1440:  # QHD
                resolution_scale = 1.5
                print(f"QHD resolution detected ({screen_width}x{screen_height}) - likely 150% scaling")
            elif screen_width >= 1920 and screen_height >= 1080:  # FHD
                # FHD에서도 200% 스케일링 가능 (작은 화면)
                if screen_width_mm > 0 and screen_height_mm > 0:
                    diagonal_inch = ((screen_width_mm**2 + screen_height_mm**2)**0.5) / 25.4
                    if diagonal_inch < 15:  # 15인치 미만이면 고해상도
                        resolution_scale = 2.0
                        print(f"Small high-res screen detected ({diagonal_inch:.1f}\" {screen_width}x{screen_height}) - likely 200% scaling")
                    else:
                        resolution_scale = 1.0
                        print(f"Standard FHD screen ({diagonal_inch:.1f}\" {screen_width}x{screen_height}) - likely 100% scaling")
                else:
                    resolution_scale = 1.0
                    print(f"FHD resolution ({screen_width}x{screen_height}) - assuming 100% scaling")
            
            print(f"Resolution-based scale: {resolution_scale}")
        except:
            print("Resolution-based scaling detection failed")
        
        # 최종 스케일 결정 (해상도 기반 추정 포함)
        all_scales = [tk_scale, dpi_scale, env_scale, system_scale, resolution_scale]
        
        # 시스템 스케일이나 해상도 기반이 2.0이면 우선
        if system_scale >= 2.0 or resolution_scale >= 2.0:
            current_scale = max(system_scale, resolution_scale)
            print(f"Using high-confidence scale: {current_scale}")
        else:
            current_scale = max(all_scales)
            print(f"Using max detected scale: {current_scale}")
        
        # 고해상도 판단 (1.33333 제외하고 판단)
        is_high_dpi = (current_scale >= 1.5 or 
                      system_scale >= 2.0 or 
                      resolution_scale >= 1.5)
        
        print(f"High DPI mode: {is_high_dpi} (final_scale={current_scale})")
        print(f"All scales: tk={tk_scale}, dpi={dpi_scale:.2f}, env={env_scale}, system={system_scale}, resolution={resolution_scale}")
        
        # 방법 6: 사용자 확인 (환경변수로 강제 설정 가능)
        if 'FT_LOCK_SCALE' in os.environ:
            try:
                user_scale = float(os.environ['FT_LOCK_SCALE'])
                current_scale = user_scale
                is_high_dpi = user_scale >= 1.5
                print(f"🎯 User override: FT_LOCK_SCALE={user_scale} (set 'export FT_LOCK_SCALE=2.0' for 200%)")
            except:
                print("Invalid FT_LOCK_SCALE value")
        
        print(f"💡 Tip: If scaling detection is wrong, run: export FT_LOCK_SCALE=2.0")
        
        entry_frame = tk.Frame(input_container, bg='black')
        entry_frame.pack(pady=(0, 15))
        
        # 스케일링에 따른 설정 조정 (우분투 1.33333 대응)
        if is_high_dpi:  # 1.25 이상 (고해상도/스케일링)
            print("Using HIGH DPI settings (for 150%+ scaling)")
            font_size = 12
            entry_width = 18
            padding_y = 5
            padding_x = 6
            # 더 강한 가시성을 위한 설정
            bg_color = '#4a4a6e'  # 더 밝은 배경
            relief_style = 'solid'
            border_width = 2
        else:  # 일반 해상도
            print("Using NORMAL DPI settings (100% scaling)")
            font_size = 14
            entry_width = 25
            padding_y = 8
            padding_x = 10
            bg_color = '#2a2a3e'  # 기본 배경
            relief_style = 'flat'
            border_width = 0
        
        self.password_entry = tk.Entry(entry_frame, 
                                      show='•', 
                                      font=("Arial", font_size),
                                      width=entry_width, 
                                      bg=bg_color, 
                                      fg='white',
                                      relief=relief_style, 
                                      bd=border_width, 
                                      insertbackground='white')
        self.password_entry.pack(ipady=padding_y, ipadx=padding_x)
        
        print(f"Entry created: font={font_size}, width={entry_width}, bg={bg_color}")
        print(f"Entry styling: relief={relief_style}, bd={border_width}, padding=({padding_x},{padding_y})")
        
        # 강제 업데이트로 확실한 렌더링
        self.root.update_idletasks()
        entry_frame.update_idletasks()
        self.password_entry.update_idletasks()
        
        # 고해상도에서 추가 보장 조치
        if is_high_dpi:
            print("Applying additional HIGH DPI measures...")
            
            # 강제 업데이트
            self.root.update()
            entry_frame.update()
            self.password_entry.update()
            
            # 추가 가시성 향상 시도
            try:
                self.password_entry.configure(highlightthickness=1, highlightcolor='white')
                print("Added highlight for better visibility")
            except:
                pass
            
            print("HIGH DPI adjustments applied")
        
        self.password_entry.focus_set()
        self.password_entry.bind('<Return>', self.on_unlock_attempt)
        
        # Entry 위젯 상태 확인 (디버깅용)
        self.root.after(200, self._check_entry_status)
        
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
