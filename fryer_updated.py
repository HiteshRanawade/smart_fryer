import tkinter as tk
from tkinter import messagebox, filedialog
import time
import json
import os
from PIL import Image, ImageTk
import pandas as pd
import shutil
import serial
import threading
import re
import sys
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
from enum import Enum, auto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fryer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FryerState(Enum):
    IDLE = auto()
    HEATING = auto()
    LOWERING_BASKET = auto()
    FRYING = auto()
    RAISING_BASKET = auto()
    EMERGENCY = auto()

@dataclass
class FryerConfig:
    """Configuration settings for the fryer"""
    serial_port: str = '/dev/serial0'
    baudrate: int = 9600
    screen_width: int = 800
    screen_height: int = 480
    default_temp: float = 25.0
    default_target_temp: int = 180
    min_temp: int = 100
    max_temp: int = 250
    min_time: int = 30
    max_time: int = 600

class SmartFryerGUI:
    """Main GUI class for the Smart Induction Fryer"""
    
    def __init__(self, root: tk.Tk):
        """Initialize the Smart Fryer GUI
        
        Args:
            root: The root Tkinter window
        """
        self.root = root
        self.config = FryerConfig()
        self._setup_window()
        self._initialize_state()
        self._setup_serial()
        self._setup_gui()
        
    def _setup_window(self) -> None:
        """Configure the main window settings"""
        self.root.title("Smart Induction Fryer")
        self.root.geometry(f"{self.config.screen_width}x{self.config.screen_height}")
        self.root.attributes('-fullscreen', True)
        self.root.config(cursor="none")
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)
        self._disable_shortcuts()
        
    def _disable_shortcuts(self) -> None:
        """Disable common keyboard shortcuts"""
        shortcuts = ["<Control-c>", "<Control-q>", "<Alt-F4>"]
        for shortcut in shortcuts:
            self.root.bind_all(shortcut, lambda e: "break")
            
    def _initialize_state(self) -> None:
        """Initialize the fryer state variables"""
        self.current_temp = self.config.default_temp
        self.frying_active = False
        self.target_temperature = self.config.default_target_temp
        self.frying_time = 0
        self.basket_state = "raised"
        self.state = FryerState.IDLE
        self.menu_data = self.load_menu_data()
        
        # Create images directory if it doesn't exist
        self.image_dir = "images"
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)
            
    def _setup_serial(self) -> None:
        """Initialize serial connection"""
        self.ser = None
        self.connect_serial()
        
    def connect_serial(self) -> None:
        """Connect to the serial port for communication with the fryer hardware"""
        try:
            self.ser = serial.Serial(
                self.config.serial_port,
                self.config.baudrate,
                timeout=1
            )
            logger.info(f"Connected to serial port {self.config.serial_port}")
            time.sleep(2)  # Allow time for Arduino to initialize
        except serial.SerialException as e:
            logger.error(f"Failed to connect to serial port {self.config.serial_port}: {e}")
            messagebox.showerror(
                "Connection Error",
                f"Failed to connect to fryer hardware: {e}\nPlease check the connection and restart the application."
            )
            
    def send_serial_command(self, command: str, retries: int = 4) -> bool:
        """Send a command to the fryer hardware
        
        Args:
            command: The command to send
            retries: Number of retry attempts
            
        Returns:
            bool: True if command was sent successfully
        """
        if not self.ser or not self.ser.is_open:
            logger.error("Serial port is not open")
            return False
            
        success = True
        for i in range(retries):
            try:
                self.ser.flushInput()
                self.ser.write(f"{command}\n".encode())
                logger.debug(f"Sent command: {command} (Attempt {i+1}/{retries})")
                self.ser.flush()
                time.sleep(0.1)
            except serial.SerialException as e:
                logger.error(f"Serial write failed for '{command}' (Attempt {i+1}/{retries}): {e}")
                success = False
                
        if success:
            if command == "LOWER_BASKET":
                self.basket_state = "lowered"
            elif command == "RAISE_BASKET":
                self.basket_state = "raised"
                
        return success
    
    def create_taskbar(self, back_command=None, show_emergency=False):
        """Create the taskbar with temperature display and optional buttons
        
        Args:
            back_command: Optional callback for back button
            show_emergency: Whether to show emergency stop button
        """
        taskbar = tk.Frame(self.root, bg="#111")
        taskbar.pack(side="top", fill="x")

        self.temp_label = tk.Label(
            taskbar,
            text=f"Current Temp: {self.current_temp:.1f}°C",
            font=("Arial", 14),
            bg="#111",
            fg="white"
        )
        self.temp_label.pack(side="left", padx=10)

        if show_emergency:
            self.emergency_button = tk.Button(
                taskbar,
                text="EMERGENCY STOP",
                font=("Arial", 12, "bold"),
                bg="red",
                fg="white",
                activebackground="#990000",
                command=self.emergency_stop_handler
            )
            self.emergency_button.pack(side="right", padx=10)

        if back_command:
            back_button = tk.Button(
                taskbar,
                text="Back",
                font=("Arial", 12),
                bg="orange",
                fg="black",
                activebackground="#cc8400",
                command=back_command
            )
            back_button.pack(side="right", padx=10)

        self.press_start_time = None
        self.long_press_job = None

        def on_press(event):
            self.press_start_time = time.time()
            self.long_press_job = self.root.after(5000, self.check_long_press)

        def on_release(event):
            if self.long_press_job:
                self.root.after_cancel(self.long_press_job)
                self.long_press_job = None
            self.press_start_time = None

        taskbar.bind("<ButtonPress-1>", on_press)
        taskbar.bind("<ButtonRelease-1>", on_release)
        self.temp_label.bind("<ButtonPress-1>", lambda e: "break")
        self.temp_label.bind("<ButtonRelease-1>", lambda e: "break")

    def check_long_press(self):
        """Check for long press to show admin panel"""
        if self.press_start_time and time.time() - self.press_start_time >= 5:
            self.show_admin_password_prompt()
        self.long_press_job = None
        self.press_start_time = None

    def create_keyboard(self, parent, entry):
        """Create a virtual keyboard
        
        Args:
            parent: Parent frame
            entry: Entry widget to receive input
        """
        keyboard_frame = tk.Frame(parent, bg="black")
        keyboard_frame.pack(pady=10)

        buttons = [
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
            'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p',
            'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '/',
            'z', 'x', 'c', 'v', 'b', 'n', 'm', '.', '_', ' ',
            'Clear', 'Del', 'Enter'
        ]

        def on_key_click(value):
            if value == 'Clear':
                entry.delete(0, tk.END)
            elif value == 'Del':
                current = entry.get()
                entry.delete(0, tk.END)
                entry.insert(0, current[:-1])
            elif value == 'Enter':
                entry.event_generate('<Return>')
            else:
                entry.insert(tk.END, value)

        row = 0
        col = 0
        for button in buttons:
            cmd = lambda val=button: on_key_click(val)
            btn = tk.Button(
                keyboard_frame,
                text=button,
                font=("Arial", 12),
                width=4 if button not in ['Clear', 'Del', 'Enter'] else 8,
                height=2,
                bg="#333",
                fg="white",
                activebackground="#555",
                command=cmd
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            self._add_button_effects(btn, "#333", "#555")
            col += 1
            if col > 9:
                col = 0
                row += 1

        return keyboard_frame

    def show_admin_password_prompt(self):
        """Show admin password prompt window"""
        win = tk.Toplevel(self.root)
        win.geometry(f"{self.config.screen_width}x{self.config.screen_height}")
        win.attributes('-fullscreen', True)
        win.config(cursor="none")
        win.configure(bg="black")

        tk.Label(
            win,
            text="Enter Admin Password",
            font=("Arial", 22, "bold"),
            bg="black",
            fg="white"
        ).pack(pady=20)

        password_entry = tk.Entry(
            win,
            font=("Arial", 18),
            show="*",
            width=20,
            bg="black",
            fg="white"
        )
        password_entry.pack(pady=10)
        password_entry.focus_set()

        keyboard_frame = self.create_keyboard(win, password_entry)

        def verify_password(event=None):
            if password_entry.get() == "admin123":
                win.destroy()
                self.show_admin_panel()
            else:
                messagebox.showerror("Error", "Incorrect password")
                password_entry.delete(0, tk.END)

        password_entry.bind("<Return>", verify_password)

        button_frame = tk.Frame(win, bg="black")
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="Submit",
            font=("Arial", 16),
            bg="#00cc66",
            fg="white",
            activebackground="#009900",
            width=10,
            height=2,
            command=verify_password
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="Cancel",
            font=("Arial", 16),
            bg="red",
            fg="white",
            activebackground="#990000",
            width=10,
            height=2,
            command=win.destroy
        ).pack(side="left", padx=5)

    def show_admin_panel(self) -> None:
        """Display the admin panel"""
        self.clear_root()
        self.create_taskbar(self.show_category)
        self.root.configure(bg="#f0f0f0")

        # Title
        tk.Label(
            self.root,
            text="Admin Panel",
            font=("Arial", 22),
            fg="#222",
            bg="#f0f0f0"
        ).pack(pady=20)

        # File upload section
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(pady=15)

        tk.Label(
            frame,
            text="Upload Excel file with item details",
            font=("Arial", 16),
            bg="#f0f0f0",
            fg="#222"
        ).pack(pady=10)

        file_entry = tk.Entry(frame, font=("Arial", 14), width=30)
        file_entry.pack(pady=5)

        self.create_keyboard(frame, file_entry)

        def select_file() -> None:
            """Handle file selection"""
            file_path = filedialog.askopenfilename(
                filetypes=[("Excel files", "*.xlsx *.xls")]
            )
            if file_path:
                file_entry.delete(0, tk.END)
                file_entry.insert(0, file_path)

        def upload_file(event=None) -> None:
            """Handle file upload"""
            self.upload_excel(file_entry.get())

        file_entry.bind("<Return>", upload_file)

        # Action buttons
        button_frame = tk.Frame(frame, bg="#f0f0f0")
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="Browse",
            font=("Arial", 14),
            bg="#3366cc",
            fg="white",
            activebackground="#224488",
            width=10,
            height=2,
            command=select_file
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="Upload",
            font=("Arial", 14),
            bg="#00cc66",
            fg="white",
            activebackground="#009900",
            width=10,
            height=2,
            command=lambda: upload_file()
        ).pack(side="left", padx=5)