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
import uuid
from functools import partial

class SmartFryerGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Smart Induction Fryer")
        self.root.geometry("800x480")
        self.root.attributes('-fullscreen', True)
        self.root.config(cursor="none")
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)
        self.root.bind_all("<Control-c>", lambda e: "break")
        self.root.bind_all("<Control-q>", lambda e: "break")
        self.root.bind_all("<Alt-F4>", lambda e: "break")

        self.current_temp = 25.0
        self.frying_active = False
        self.target_temperature = 180
        self.frying_time = 0
        self.basket_state = "raised"
        self.state_lock = threading.Lock()

        self.menu_data = self.load_menu_data()
        self.image_dir = "images"
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

        # Serial config
        self.ser_port = '/dev/serial0'  # RPi GPIO serial
        self.baudrate = 9600
        self.ser = None
        self.connect_serial()

        # GUI Setup
        self.running = True
        self.images = []
        self.temp_label = None
        self.status_label = None
        self.manual_status_label = None
        self.start_temp_monitoring()
        self.show_category()

    def connect_serial(self):
        """Attempt to connect to the serial port."""
        try:
            self.ser = serial.Serial(self.ser_port, self.baudrate, timeout=1)
            print(f"Connected to serial port {self.ser_port}")
            time.sleep(2)  # Allow time for Arduino to initialize
        except serial.SerialException as e:
            print(f"Failed to connect to serial port {self.ser_port}: {e}")

    def reconnect_serial(self):
        """Attempt to reconnect to the serial port if disconnected."""
        if not self.ser or not self.ser.is_open:
            self.connect_serial()

    def start_temp_monitoring(self):
        def update_temp():
            try:
                if self.ser and self.ser.is_open:
                    self.ser.flush()
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"Raw serial data: '{line}'")
                        with open("serial_log.txt", "a") as f:
                            f.write(f"Raw serial data: '{line}'\n")
                        match = re.search(r"[\d]+\.?\d*\s*°?C", line)
                        if match:
                            temp_str = match.group(0).replace("°C", "").strip()
                            self.current_temp = float(temp_str)
                            print(f"Parsed Temp: {self.current_temp:.1f}°C")
                        else:
                            print(f"Failed to parse temperature from: '{line}'")
                    else:
                        print("No serial data received")
                    # Control heating
                    if self.frying_active:
                        if self.current_temp < self.target_temperature - 2:
                            if not self.heating1_state:
                                self.send_serial_command("H1_ON")
                                self.heating1_state = True
                            if not self.heating2_state:
                                self.send_serial_command("H2_ON")
                                self.heating2_state = True
                        elif self.current_temp > self.target_temperature + 2:
                            if self.heating1_state:
                                self.send_serial_command("H1_OFF")
                                self.heating1_state = False
                            if self.heating2_state:
                                self.send_serial_command("H2_OFF")
                                self.heating2_state = False
                    else:
                        if self.heating1_state:
                            self.send_serial_command("H1_OFF")
                            self.heating1_state = False
                        if self.heating2_state:
                            self.send_serial_command("H2_OFF")
                            self.heating2_state = False
                    self.current_temp = min(max(self.current_temp, 20), 250)
                else:
                    print("Serial port not open, using fallback temperature")
                    self.current_temp += 0.1 if self.frying_active else -0.1
                    self.current_temp = min(max(self.current_temp, 20), 250)
            except Exception as e:
                print(f"Error reading serial: {e}")
            self.update_taskbar()
            if self.running:
                self.root.after(500, update_temp)
        self.root.after(500, update_temp)

    def send_serial_command(self, command):
        if not self.ser or not self.ser.is_open:
            print("Serial port is not open")
            return False
        try:
            self.ser.flush()
            self.ser.write(f"{command}\n".encode('utf-8'))
            print(f"Sent command: {command}")
            self.ser.flush()
            time.sleep(0.1)
            if command == "4":
                self.basket_state = "lowered"
            elif command == "1":
                self.basket_state = "raised"
            return True
        except serial.SerialException as e:
            print(f"Serial write failed for '{command}': {e}")
            return False

    def load_menu_data(self):
        default_menu = {
            "VEG": {
                "Samosa": {"temp": 170, "time": 90},
                "Paneer Pakora": {"temp": 180, "time": 100},
                "Aloo Tikki": {"temp": 175, "time": 90},
                "Kanda Bhaji": {"temp": 185, "time": 90},
                "Batata Vada": {"temp": 170, "time": 90},
                "Palak Pakora": {"temp": 175, "time": 95},
                "Mix Veg Cutlet": {"temp": 180, "time": 120},
                "Corn Cheese Ball": {"temp": 180, "time": 100},
                "Methi Gota": {"temp": 180, "time": 90},
                "Sabudana Vada": {"temp": 180, "time": 100},
                "Chili Paneer": {"temp": 190, "time": 120},
                "Momos": {"temp": 180, "time": 110},
                "Pakora Mix": {"temp": 175, "time": 95},
                "French Fries": {"temp": 180, "time": 120},
                "Onion Rings": {"temp": 175, "time": 100},
            },
            "NON-VEG": {
                "Chicken Pakora": {"temp": 190, "time": 120},
                "Chicken Nuggets": {"temp": 180, "time": 140},
                "Fish Fingers": {"temp": 185, "time": 150},
                "Chicken Wings": {"temp": 190, "time": 180},
                "Tandoori Chicken": {"temp": 200, "time": 210},
                "Mutton Cutlet": {"temp": 190, "time": 160},
                "Egg Pakora": {"temp": 180, "time": 100},
                "Prawns Fry": {"temp": 195, "time": 130},
                "Fish Fry": {"temp": 190, "time": 160},
                "Chicken 65": {"temp": 185, "time": 120},
                "Keema Balls": {"temp": 180, "time": 110},
                "Egg Roll": {"temp": 175, "time": 90},
                "Seekh Kebab": {"temp": 190, "time": 140},
                "Chicken Roll": {"temp": 185, "time": 100},
                "Fried Chicken": {"temp": 195, "time": 180},
                "Egg Devil": {"temp": 180, "time": 90},
                "Chicken Cheese Ball": {"temp": 190, "time": 130},
                "Mutton Samosa": {"temp": 185, "time": 100},
                "Fried Fish Cake": {"temp": 180, "time": 110},
            }
        }
        try:
            if os.path.exists("menu_data.json"):
                with open("menu_data.json", "r") as f:
                    data = json.load(f)
                    for cat in default_menu:
                        if cat not in data:
                            data[cat] = {}
                        for item, params in default_menu[cat].items():
                            if item not in data[cat]:
                                data[cat][item] = params
                    return data
        except Exception as e:
            print(f"Failed to load menu_data.json: {e}")
        return default_menu

    def save_menu_data(self):
        try:
            with open("menu_data.json", "w") as f:
                json.dump(self.menu_data, f, indent=4)
        except Exception as e:
            print(f"Failed to save menu_data.json: {e}")

    def create_taskbar(self, back_command=None, show_emergency=False):
        taskbar = tk.Frame(self.root, bg="#111")
        taskbar.pack(side="top", fill="x")

        self.temp_label = tk.Label(taskbar, text=f"Current Temp: {self.current_temp:.1f}°C",
                                   font=("Arial", 14), bg="#111", fg="white")
        self.temp_label.pack(side="left", padx=10)

        if show_emergency:
            self.emergency_button = tk.Button(taskbar, text="EMERGENCY STOP", font=("Arial", 12, "bold"),
                                             bg="red", fg="white", activebackground="#990000",
                                             command=self.show_emergency_window)
            self.emergency_button.pack(side="right", padx=10)

        if back_command:
            back_button = tk.Button(taskbar, text="Back", font=("Arial", 12),
                                    bg="orange", fg="black", activebackground="#cc8400",
                                    command=back_command)
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
        if self.press_start_time and time.time() - self.press_start_time >= 5:
            self.show_admin_password_prompt()
        self.long_press_job = None
        self.press_start_time = None

    def create_keyboard(self, parent, entry):
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
            btn = tk.Button(keyboard_frame, text=button, font=("Arial", 12),
                            width=4 if button not in ['Clear', 'Del', 'Enter'] else 8,
                            height=2, bg="#333", fg="white", activebackground="#555",
                            command=cmd)
            btn.grid(row=row, column=col, padx=2, pady=2)
            btn.bind("<ButtonPress-1>", lambda e, b=btn: b.config(bg="#555"))
            btn.bind("<ButtonRelease-1>", lambda e, b=btn: b.config(bg="#333"))
            col += 1
            if col > 9:
                col = 0
                row += 1

        return keyboard_frame

    def show_admin_password_prompt(self):
        win = tk.Toplevel(self.root)
        win.geometry("800x480")
        win.attributes('-fullscreen', True)
        win.config(cursor="none")
        win.configure(bg="black")

        tk.Label(win, text="Enter Admin Password", font=("Arial", 22, "bold"),
                 bg="black", fg="white").pack(pady=20)

        password_entry = tk.Entry(win, font=("Arial", 18), show="*", width=20, bg="black", fg="white")
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

        tk.Button(button_frame, text="Submit", font=("Arial", 16),
                  bg="#00cc66", fg="white", activebackground="#009900",
                  width=10, height=2, command=verify_password).pack(side="left", padx=5)

        tk.Button(button_frame, text="Cancel", font=("Arial", 16),
                  bg="red", fg="white", activebackground="#990000",
                  width=10, height=2, command=win.destroy).pack(side="left", padx=5)

    def show_admin_panel(self):
        self.clear_root()
        self.create_taskbar(self.show_category)
        self.root.configure(bg="#f0f0f0")

        tk.Label(self.root, text="Admin Panel", font=("Arial", 22),
                 fg="#222", bg="#f0f0f0").pack(pady=20)

        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(pady=15)

        tk.Label(frame, text="Upload Excel file with item details", font=("Arial", 16),
                 bg="#f0f0f0", fg="#222").pack(pady=10)

        file_entry = tk.Entry(frame, font=("Arial", 14), width=30)
        file_entry.pack(pady=5)

        self.create_keyboard(frame, file_entry)

        button_frame = tk.Frame(frame, bg="#f0f0f0")
        button_frame.pack(pady=10)

        def select_file():
            file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
            if file_path:
                file_entry.delete(0, tk.END)
                file_entry.insert(0, file_path)

        def upload_file(event=None):
            self.upload_excel(file_entry.get())

        file_entry.bind("<Return>", upload_file)

        tk.Button(button_frame, text="Browse", font=("Arial", 14),
                  bg="#3366cc", fg="white", activebackground="#224488",
                  width=10, height=2, command=select_file).pack(side="left", padx=5)

        tk.Button(button_frame, text="Upload", font=("Arial", 14),
                  bg="#00cc66", fg="white", activebackground="#009900",
                  width=10, height=2, command=lambda: upload_file()).pack(side="left", padx=5)

    def upload_excel(self, file_path):
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid Excel file")
            return

        try:
            df = pd.read_excel(file_path)
            required_columns = ["Category", "Item Name", "Temperature (°C)", "Time (seconds)"]
            if not all(col in df.columns for col in required_columns):
                messagebox.showerror("Error", "Excel file must contain columns: Category, Item Name, Temperature (°C), Time (seconds)")
                return

            for index, row in df.iterrows():
                try:
                    category = str(row["Category"]).strip().upper()
                    item_name = str(row["Item Name"]).strip()
                    temp = int(float(row["Temperature (°C)"]))
                    time_secs = int(float(row["Time (seconds)"]))

                    if category not in ["VEG", "NON-VEG"]:
                        messagebox.showerror("Error", f"Invalid category '{category}' for item '{item_name}'. Must be VEG or NON-VEG.")
                        continue
                    if temp < 100 or temp > 250:
                        messagebox.showerror("Error", f"Invalid temperature {temp}°C for item '{item_name}'. Must be between 100 and 250.")
                        continue
                    if time_secs < 30 or time_secs > 600:
                        messagebox.showerror("Error", f"Invalid time {time_secs} seconds for item '{item_name}'. Must be between 30 and 600.")
                        continue

                    image_filename = f"{item_name.replace(' ', '_')}.png"
                    image_path = os.path.join(self.image_dir, image_filename)
                    if "Image Path" in df.columns and pd.notna(row["Image Path"]):
                        src_image = str(row["Image Path"])
                        if os.path.exists(src_image):
                            try:
                                shutil.copy(src_image, image_path)
                                img = Image.open(image_path)
                                img = img.resize((80, 80), Image.LANCZOS)
                                img.save(image_path)
                            except Exception as e:
                                print(f"Failed to process image for {item_name}: {e}")
                        else:
                            print(f"Image path {src_image} does not exist for {item_name}")

                    if category not in self.menu_data:
                        self.menu_data[category] = {}
                    self.menu_data[category][item_name] = {"temp": temp, "time": time_secs}
                except (ValueError, TypeError) as e:
                    messagebox.showerror("Error", f"Invalid data for row {index + 2}: {e}")
                    continue

            self.save_menu_data()
            messagebox.showinfo("Success", "Items uploaded successfully!")
            self.show_category()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process Excel file: {e}")

    def emergency_stop_handler(self):
        self.frying_active = False
        self.send_serial_command("2")
        self.heating1_state = False
        self.heating2_state = False
        
        if not self.send_serial_command("3"):
            print("Failed to send BASKET_UP command")
            self.update_frying_status("Warning: Basket raising command failed")
        
        if hasattr(self, 'emergency_button'):
            self.emergency_button.config(state='disabled')
        
        if hasattr(self, 'frying_window') and self.frying_window():
            self.frying_window.destroy()
            self.show_emergency_window()

    def show_emergency_window(self):
        self.clear_root()
        self.root.configure(bg="black")

        tk.Label(self.root, text=" EMERGENCY STOP ACTIVATED ",
                 font=("Arial", 30, "bold"), fg="red", bg="black").pack(pady=40)

        frame = tk.Frame(self.root, bg="black")
        frame.pack(pady=20)

        tk.Label(frame, text="All operations halted for safety.",
                 font=("Arial", 18), fg="white", bg="black").pack(pady=10)

        tk.Button(frame, text="RESET SYSTEM", font=("Arial", 20, "bold"),
                  bg="yellow", fg="black", activebackground="#cccc00",
                  padx=15, pady=5, command=self.reset_system).pack(pady=20)

    def reset_system(self):
        self.frying_active = False
        if not self.send_serial_command("3"):
            print("Failed to send BASKET_UP")
        self.send_serial_command("2")
        self.heating1_state = False
        self.heating2_state = False
        self.show_category()

    def clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def update_taskbar(self):
        try:
            if hasattr(self, 'temp_label') and self.temp_label.winfo_exists():
                self.temp_label.config(text=f"Current Temp: {self.current_temp:.1f}°C")
        except tk.TclError as e:
            print(f"Tkinter error in update_taskbar: {e}")

    def create_widgets(self):
        self.root.configure(bg="#f0f0f0")
        self.show_category()

    def show_category(self):
        self.clear_root()
        self.create_taskbar()
        self.root.configure(bg="#f0f0f0")

        tk.Label(self.root, text="Select Category", font=("Arial", 24, "bold"),
                 fg="#222", bg="#f0f0f0").pack(pady=20)
        button_frame = tk.Frame(self.root, bg="#f0f0f0")
        button_frame.pack(fill="both", expand=True)

        veg_button = tk.Button(button_frame, text="VEG", font=("Arial", 28, "bold"),
                               bg="green", fg="white", activebackground="#009900",
                               width=15, height=8, command=lambda: self.show_menu("VEG"))
        veg_button.pack(side="left", padx=10, pady=20)

        non_veg_button = tk.Button(button_frame, text="NON-VEG", font=("Arial", 28, "bold"),
                                   bg="red", fg="white", activebackground="#990000",
                                   width=15, height=8, command=lambda: self.show_menu("NON-VEG"))
        non_veg_button.pack(side="left", padx=10, pady=20)

        manual_button = tk.Button(button_frame, text="MANUAL", font=("Arial", 28, "bold"),
                                 bg="blue", fg="white", activebackground="#224488",
                                 width=15, height=8, command=self.show_manual_controls)
        manual_button.pack(side="left", padx=10, pady=20)

    def show_menu(self, category):
        self.clear_root()
        self.create_taskbar(self.show_category)
        self.root.configure(bg="#1e1e2f")

        tk.Label(self.root, text=f"{category} MENU", font=("Arial", 20), fg="white", bg="#1e1e2f").pack(pady=10)

        container = tk.Frame(self.root, bg="#1e1e2f")
        container.pack(fill='both', expand=True)

        canvas = tk.Canvas(container, bg="#1e1e2f", highlightthickness=0, width=800, height=300)
        canvas.pack(side="top", fill="both", expand=True)

        scroll_frame = tk.Frame(canvas, bg="#1e1e2f")
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')

        self.images = []
        x = 0
        for item, data in self.menu_data[category].items():
            card = tk.Frame(scroll_frame, bd=5, relief=tk.RIDGE, bg="#2e2e40", width=200, height=360)
            card.grid(row=0, column=x, padx=10, pady=10)
            card.grid_propagate(False)

            image_filename = item.replace(" ", "_") + ".png"
            image_path = os.path.join(self.image_dir, image_filename)
            try:
                img = Image.open(image_path)
                img = img.resize((150, 150), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                image_label = tk.Label(card, image=photo, bg="#2e2e40")
                image_label.pack(pady=3)
                self.images.append(photo)
            except Exception as e:
                print(f"Failed to load image {image_path}: {e}")
                placeholder_label = tk.Label(card, text="[No Image]", font=("Arial", 10), bg="#2e2e40", fg="white")
                placeholder_label.pack(pady=100)

            tk.Label(card, text=item, font=("Arial", 20, "bold"), fg="white", bg="#2e2e40", wraplength=160).pack(pady=2)
            tk.Label(card, text=f"TEMP: {data['temp']}°C", font=("Arial", 16), fg="white", bg="#2e2e40").pack(pady=1)
            minutes, seconds = divmod(data['time'], 60)
            tk.Label(card, text=f"Time: {minutes}m {seconds}s", font=("Arial", 16), fg="white", bg="#2e2e40").pack(pady=1)

            button_frame = tk.Frame(card, bg="#2e2e40")
            button_frame.pack(pady=2)
            start_cmd = lambda i=item, t=data['temp'], d=data['time']: self.start_frying(i, t, d)
            custom_cmd = lambda i=item, t=data['temp'], d=data['time']: self.custom_settings(i, t, d)

            start_button = tk.Button(button_frame, text="Start", font=("Arial", 16), bg="#00cc66", fg="white",
                                    activebackground="#009900", width=6, height=1, command=start_cmd)
            start_button.pack(side="left", padx=2)
            custom_button = tk.Button(button_frame, text="Customize", font=("Arial", 16), bg="#3366cc", fg="white",
                                     activebackground="#224488", width=7, height=1, command=custom_cmd)
            custom_button.pack(side="left", padx=2)

            def on_button_press(button, original_bg, pressed_bg):
                button.config(bg=pressed_bg)
            def on_button_release(button, original_bg):
                button.config(bg=original_bg)

            start_button.bind("<ButtonPress-1>", lambda e: on_button_press(start_button, "#00cc66", "#009900"))
            start_button.bind("<ButtonRelease-1>", lambda e: on_button_release(start_button, "#00cc66"))
            custom_button.bind("<ButtonPress-1>", lambda e: on_button_press(custom_button, "#3366cc", "#224488"))
            custom_button.bind("<ButtonRelease-1>", lambda e: on_button_release(custom_button, "#3366cc"))

            card.bind("<ButtonPress-1>", lambda e: "break")
            card.bind("<B1-Motion>", lambda e: "break")
            for child in card.winfo_children():
                if child not in (start_button, custom_button):
                    child.bind("<ButtonPress-1>", lambda e: "break")
                    child.bind("<B1-Motion>", lambda e: "break")

            x += 1

        canvas.update_idletasks()
        scroll_region = canvas.bbox("all")
        canvas.config(scrollregion=scroll_region)

        total_items = len(self.menu_data[category])
        items_per_page = 4
        self.current_item_index = 0

        def update_button_states():
            scroll_left_button.config(state=tk.NORMAL if self.current_item_index > 0 else tk.DISABLED)
            scroll_right_button.config(state=tk.NORMAL if self.current_item_index < total_items - items_per_page else tk.DISABLED)

        def scroll_left():
            if self.current_item_index > 0:
                self.current_item_index -= 1
                canvas.xview_moveto((self.current_item_index * 200) / scroll_region[2])
                update_button_states()

        def scroll_right():
            if self.current_item_index < total_items - items_per_page:
                self.current_item_index += 1
                canvas.xview_moveto((self.current_item_index * 200) / scroll_region[2])
                update_button_states()

        scroll_buttons_frame = tk.Frame(self.root, bg="#1e1e2f")
        scroll_buttons_frame.pack(side="bottom", fill="x", pady=10)

        scroll_left_button = tk.Button(scroll_buttons_frame, text="< Scroll Left", font=("Arial", 14, "bold"),
                                      bg="#555", fg="white", activebackground="#777",
                                      width=15, height=2, command=scroll_left)
        scroll_left_button.pack(side="left", padx=20)

        scroll_right_button = tk.Button(scroll_buttons_frame, text="Scroll Right >", font=("Arial", 14, "bold"),
                                       bg="#555", fg="white", activebackground="#777",
                                       width=15, height=2, command=scroll_right)
        scroll_right_button.pack(side="right", padx=20)

        def on_scroll_button_press(button):
            if button['state'] != tk.DISABLED:
                button.config(bg="#777")
        def on_scroll_button_release(button):
            if button['state'] != tk.DISABLED:
                button.config(bg="#555")

        scroll_left_button.bind("<ButtonPress-1>", lambda e: on_scroll_button_press(scroll_left_button))
        scroll_left_button.bind("<ButtonRelease-1>", lambda e: on_scroll_button_release(scroll_left_button))
        scroll_right_button.bind("<ButtonPress-1>", lambda e: on_scroll_button_press(scroll_right_button))
        scroll_right_button.bind("<ButtonRelease-1>", lambda e: on_scroll_button_release(scroll_right_button))

        update_button_states()

    def start_frying(self, item_name, target_temp, fry_time):
        self.target_temperature = target_temp
        self.frying_time = fry_time
        self.frying_active = True
        self.show_frying_screen(item_name)
        threading.Thread(target=self.frying_process, args=(item_name, fry_time), daemon=True).start()

    def frying_process(self, item, total_time):
        self.update_frying_status(f"Heating Oil to {self.target_temperature}°C...")
        self.send_serial_command("1")
        while self.current_temp < self.target_temperature - 5 and self.frying_active:
            time.sleep(1)
            self.update_frying_status(f"Heating... {self.current_temp:.1f}°C")

        if self.frying_active:
            self.update_frying_status("Lowering the basket...")
            if not self.send_serial_command("4"):
                self.update_frying_status("Error: Failed to lower basket")
                self.frying_active = False
                return

            start_time = time.time()
            while time.time() - start_time < 30 and self.frying_active:
                self.send_serial_command("4")
                self.update_frying_status("Lowering the basket...")
                time.sleep(1)

            if self.frying_active:
                self.update_frying_status(f"{item}\nFrying...")
                start_time = time.time()
                while time.time() - start_time < total_time and self.frying_active:
                    remaining = total_time - int(time.time() - start_time)
                    mins, secs = divmod(remaining, 60)
                    self.update_frying_status(f"{item}\n{mins:02}:{secs:02}\nTemp: {self.current_temp:.1f}°C")
                    time.sleep(1)

                self.frying_active = False
                self.update_frying_status("Frying Done! Raising the basket...")
                if not self.send_serial_command("3"):
                    self.update_frying_status("Error: Failed to raise basket")
                    return

                start_time = time.time()
                while time.time() - start_time < 30:
                    self.send_serial_command("3")
                    self.update_frying_status("Raising the basket...")
                    time.sleep(1)
                self.update_frying_status("Process Complete!")
                self.send_serial_command("2")
                self.heating1_state = False
                self.heating2_state = False

    def show_frying_screen(self, item_name):
        self.clear_root()
        self.create_taskbar(self.show_category, show_emergency=True)
        self.root.configure(bg="black")

        self.frying_window = self.root
        main_frame = tk.Frame(self.root, bg="black")
        main_frame.pack(fill="both", expand=True)

        image_filename = item_name.replace(" ", "_") + ".png"
        image_path = os.path.join(self.image_dir, image_filename)
        try:
            img = Image.open(image_path)
            img = img.resize((200, 200), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            image_label = tk.Label(main_frame, image=photo, bg="black")
            image_label.image = photo
            image_label.pack(side="left", padx=20)
            self.images.append(photo)
        except Exception as e:
            print(f"Failed to load image {image_path}: {e}")
            placeholder_label = tk.Label(main_frame, text="[Image Missing]", font=("Arial", 12), bg="black", fg="white")
            placeholder_label.pack(side="left", padx=20)

        info_frame = tk.Frame(main_frame, bg="black")
        info_frame.pack(side="left", fill="both", expand=True)

        self.frying_label = tk.Label(info_frame, text=item_name,
                                     font=("Arial", 24, "bold"), fg="white", bg="black")
        self.frying_label.pack(pady=10)

        minutes, seconds = divmod(self.frying_time, 60)
        tk.Label(info_frame, text=f"Target Temp: {self.target_temperature}°C",
                 font=("Arial", 16), fg="white", bg="black").pack(pady=5)
        tk.Label(info_frame, text=f"Time: {minutes}m {seconds}s",
                 font=("Arial", 16), fg="white", bg="black").pack(pady=5)

        self.status_label = tk.Label(info_frame, text="",
                                     font=("Arial", 18), fg="white", bg="black")
        self.status_label.pack(pady=20)

    def update_frying_status(self, message):
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.config(text=message)
        except tk.TclError:
            pass

    def show_manual_controls(self, item_name="Manual", default_temp=180, default_time=300):
        self.clear_root()
        self.create_taskbar(self.show_category)
        self.root.configure(bg="black")

        main_frame = tk.Frame(self.root, bg="black")
        main_frame.pack(fill="both", expand=True)

        button_frame = tk.Frame(main_frame, bg="black")
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Raise Basket", font=("Arial", 14),
                bg="#3366cc", fg="white", activebackground="#224488",
                width=15, height=2, command=lambda: self.send_serial_command("3")).pack(side="left", padx=5, pady=5)

        tk.Button(button_frame, text="Lower Basket", font=("Arial", 14),
                bg="#3366cc", fg="white", activebackground="#224488",
                width=15, height=2, command=lambda: self.send_serial_command("4")).pack(side="left", padx=5, pady=5)

        tk.Button(button_frame, text="Heating On", font=("Arial", 14),
                bg="#ff6600", fg="white", activebackground="#cc5200",
                width=15, height=2,
                command=lambda: [self.send_serial_command("1"),
                                setattr(self, 'heating1_state', True),
                                setattr(self, 'heating2_state', True)]).pack(side="left", padx=5, pady=5)

        tk.Button(button_frame, text="Heating Off", font=("Arial", 14),
                bg="#ff6600", fg="white", activebackground="#cc5200",
                width=15, height=2,
                command=lambda: [self.send_serial_command("2"),
                                setattr(self, 'heating1_state', False),
                                setattr(self, 'heating2_state', False)]).pack(side="left", padx=5, pady=5)

        right_frame = tk.Frame(main_frame, bg="black")
        right_frame.pack(side="left", fill="both", expand=True)

        tk.Label(right_frame, text=f"Custom Settings: {item_name}",
                font=("Arial", 18, "bold"), bg="black", fg="white").pack(pady=10)

        input_frame = tk.Frame(right_frame, bg="black")
        input_frame.pack(pady=10)

        temp_frame = tk.Frame(input_frame, bg="black")
        temp_frame.pack(side="left", padx=20)

        tk.Label(temp_frame, text="Temp (°C)", font=("Arial", 14), bg="black", fg="white").pack(pady=5)
        self.temp_entry = tk.Entry(temp_frame, font=("Arial", 16), width=5, justify='center')
        self.temp_entry.insert(0, str(default_temp))
        self.temp_entry.pack()

        time_frame = tk.Frame(input_frame, bg="black")
        time_frame.pack(side="left", padx=20)

        tk.Label(time_frame, text="Time (Min:Sec)", font=("Arial", 14), bg="black", fg="white").pack(pady=5)
        time_input_frame = tk.Frame(time_frame, bg="black")
        time_input_frame.pack()

        self.min_entry = tk.Entry(time_input_frame, font=("Arial", 16), width=3, justify='center')
        self.min_entry.insert(0, str(default_time // 60))
        self.min_entry.pack(side="left")

        tk.Label(time_input_frame, text=":", font=("Arial", 16), bg="black", fg="white").pack(side="left")

        self.sec_entry = tk.Entry(time_input_frame, font=("Arial", 16), width=3, justify='center')
        self.sec_entry.insert(0, str(default_time % 60).zfill(2))
        self.sec_entry.pack(side="left")

        self.active_entry = self.temp_entry
        self.temp_entry.bind("<FocusIn>", lambda e: setattr(self, 'active_entry', self.temp_entry))
        self.min_entry.bind("<FocusIn>", lambda e: setattr(self, 'active_entry', self.min_entry))
        self.sec_entry.bind("<FocusIn>", lambda e: setattr(self, 'active_entry', self.sec_entry))

        control_frame = tk.Frame(right_frame, bg="black")
        control_frame.pack(pady=10)

        keypad_frame = tk.Frame(control_frame, bg="black")
        keypad_frame.pack(side="left", padx=10)

        buttons = [
            '1', '2', '3',
            '4', '5', '6',
            '7', '8', '9',
            'Clear', '0', 'Del'
        ]

        def on_keypad_click(value):
            if value == 'Clear':
                self.active_entry.delete(0, tk.END)
            elif value == 'Del':
                current = self.active_entry.get()
                self.active_entry.delete(0, tk.END)
                self.active_entry.insert(0, current[:-1])
            else:
                self.active_entry.insert(tk.END, value)

        row = 0
        col = 0
        for button in buttons:
            btn = tk.Button(keypad_frame, text=button, font=("Arial", 14),
                            width=5, height=2, bg="#333", fg="white",
                            activebackground="#555", command=lambda val=button: on_keypad_click(val))
            btn.grid(row=row, column=col, padx=3, pady=3)
            btn.bind("<ButtonPress-1>", lambda e, b=btn: b.config(bg="#555"))
            btn.bind("<ButtonRelease-1>", lambda e, b=btn: b.config(bg="#333"))
            col += 1
            if col > 2:
                col = 0
                row += 1

        action_frame = tk.Frame(control_frame, bg="black")
        action_frame.pack(side="left", padx=10)

        tk.Button(action_frame, text="Start Manual Fry", font=("Arial", 16),
                bg="#00cc66", fg="white", activebackground="#009900",
                width=15, height=2, command=self.start_manual_frying).pack(pady=10)

    def start_manual_frying(self):
        try:
            temp = int(self.temp_entry.get())
            minutes = int(self.min_entry.get())
            seconds = int(self.sec_entry.get())
            if temp < 100 or temp > 250:
                messagebox.showerror("Invalid Input", "Temperature must be between 100 and 250°C")
                return
            if minutes < 0 or seconds < 0 or seconds > 59:
                messagebox.showerror("Invalid Input", "Time must have valid minutes and seconds (0-59)")
                return
            total_time = minutes * 60 + seconds
            if total_time < 30 or total_time > 600:
                messagebox.showerror("Invalid Input", "Total time must be between 30 and 600 seconds")
                return
            self.start_frying("Manual Frying", temp, total_time)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for temperature and time")

    def custom_settings(self, item_name, default_temp, default_time):
        win = tk.Toplevel(self.root)
        win.geometry("800x480")
        win.attributes('-fullscreen', True)
        win.config(cursor="none")
        win.configure(bg="black")

        taskbar = tk.Frame(win, bg="#111")
        taskbar.pack(side="top", fill="x")

        self.temp_label = tk.Label(taskbar, text=f"Current Temp: {self.current_temp:.1f}°C",
                                   font=("Arial", 14), bg="#111", fg="white")
        self.temp_label.pack(side="left", padx=10)

        tk.Button(taskbar, text="Back", font=("Arial", 12),
                  bg="orange", fg="black", activebackground="#cc8400",
                  command=win.destroy).pack(side="right", padx=10)

        main_frame = tk.Frame(win, bg="black")
        main_frame.pack(fill="both", expand=True)

        image_filename = item_name.replace(" ", "_") + ".png"
        image_path = os.path.join(self.image_dir, image_filename)
        try:
            img = Image.open(image_path)
            img = img.resize((200, 200), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            image_label = tk.Label(main_frame, image=photo, bg="black")
            image_label.image = photo
            image_label.pack(side="left", padx=20)
            self.images.append(photo)
        except Exception as e:
            print(f"Failed to load image {image_path}: {e}")
            placeholder_label = tk.Label(main_frame, text="[Image Missing]", font=("Arial", 12), bg="black", fg="white")
            placeholder_label.pack(side="left", padx=20)

        right_frame = tk.Frame(main_frame, bg="black")
        right_frame.pack(side="left", fill="both", expand=True)

        tk.Label(right_frame, text=f"Custom Settings: {item_name}",
                 font=("Arial", 18, "bold"), bg="black", fg="white").pack(pady=10)

        input_frame = tk.Frame(right_frame, bg="black")
        input_frame.pack(pady=10)

        temp_frame = tk.Frame(input_frame, bg="black")
        temp_frame.pack(side="left", padx=20)

        tk.Label(temp_frame, text="Temp (°C)", font=("Arial", 14), bg="black", fg="white").pack(pady=5)
        self.temp_entry = tk.Entry(temp_frame, font=("Arial", 16), width=5, justify='center')
        self.temp_entry.insert(0, str(default_temp))
        self.temp_entry.pack()

        time_frame = tk.Frame(input_frame, bg="black")
        time_frame.pack(side="left", padx=20)

        tk.Label(time_frame, text="Time (Min:Sec)", font=("Arial", 14), bg="black", fg="white").pack(pady=5)
        time_input_frame = tk.Frame(time_frame, bg="black")
        time_input_frame.pack()

        self.min_entry = tk.Entry(time_input_frame, font=("Arial", 16), width=3, justify='center')
        self.min_entry.insert(0, str(default_time // 60))
        self.min_entry.pack(side="left")
        tk.Label(time_input_frame, text=":", font=("Arial", 16), bg="black", fg="white").pack(side="left")
        self.sec_entry = tk.Entry(time_input_frame, font=("Arial", 16), width=3, justify='center')
        self.sec_entry.insert(0, str(default_time % 60).zfill(2))
        self.sec_entry.pack(side="left")

        self.active_entry = self.temp_entry
        self.temp_entry.bind("<FocusIn>", lambda e: setattr(self, 'active_entry', self.temp_entry))
        self.min_entry.bind("<FocusIn>", lambda e: setattr(self, 'active_entry', self.min_entry))
        self.sec_entry.bind("<FocusIn>", lambda e: setattr(self, 'active_entry', self.sec_entry))

        control_frame = tk.Frame(right_frame, bg="black")
        control_frame.pack(pady=10)

        keypad_frame = tk.Frame(control_frame, bg="black")
        keypad_frame.pack(side="left", padx=10)

        buttons = [
            '1', '2', '3',
            '4', '5', '6',
            '7', '8', '9',
            'Clear', '0', 'Del'
        ]

        def on_keypad_click(value):
            if value == 'Clear':
                self.active_entry.delete(0, tk.END)
            elif value == 'Del':
                current = self.active_entry.get()
                self.active_entry.delete(0, tk.END)
                self.active_entry.insert(0, current[:-1])
            else:
                self.active_entry.insert(tk.END, value)

        row = 0
        col = 0
        for button in buttons:
            btn = tk.Button(keypad_frame, text=button, font=("Arial", 14),
                            width=5, height=2, bg="#333", fg="white",
                            activebackground="#555", command=lambda val=button: on_keypad_click(val))
            btn.grid(row=row, column=col, padx=3, pady=3)
            btn.bind("<ButtonPress-1>", lambda e, b=btn: b.config(bg="#555"))
            btn.bind("<ButtonRelease-1>", lambda e, b=btn: b.config(bg="#333"))
            col += 1
            if col > 2:
                col = 0
                row += 1

        action_frame = tk.Frame(control_frame, bg="black")
        action_frame.pack(side="left", padx=10)

        def start_process():
            try:
                temp = int(self.temp_entry.get())
                minutes = int(self.min_entry.get())
                seconds = int(self.sec_entry.get())
                if temp < 100 or temp > 250 or minutes < 0 or seconds < 0 or seconds > 59:
                    raise ValueError("Invalid input range")
                total_time = minutes * 60 + seconds
                win.destroy()
                self.start_frying(item_name, temp, total_time)
            except ValueError as e:
                messagebox.showerror("Invalid Input", f"Please enter valid numbers: {e}")

        start_process_btn = tk.Button(action_frame, text="Start Process", font=("Arial", 14),
                                      width=12, height=2, bg="#00cc66", fg="white",
                                      activebackground="#009900", command=start_process)
        start_process_btn.pack(pady=5)
        start_process_btn.bind("<ButtonPress-1>", lambda e: start_process_btn.config(bg="#009900"))
        start_process_btn.bind("<ButtonRelease-1>", lambda e: start_process_btn.config(bg="#00cc66"))

        cancel_btn = tk.Button(action_frame, text="Cancel", font=("Arial", 14),
                               width=12, height=2, bg="red", fg="white",
                               activebackground="#990000", command=win.destroy)
        cancel_btn.pack(pady=5)
        cancel_btn.bind("<ButtonPress-1>", lambda e: cancel_btn.config(bg="#990000"))
        cancel_btn.bind("<ButtonRelease-1>", lambda e: cancel_btn.config(bg="red"))

    def cleanup(self):
        self.running = False
        try:
            if self.ser and self.ser.is_open:
                self.send_serial_command("2")
                self.send_serial_command("3")
                self.ser.close()
        except serial.SerialException as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartFryerGUI(root)
    try:
        root.mainloop()
    finally:
        app.cleanup()
