import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import os

# Fryer control functions
def raise_basket():
    print("Raising basket...")
    # Add hardware control logic here

def lower_basket():
    print("Lowering basket...")
    # Add hardware control logic here

def heating_on():
    print("Heating turned on...")
    # Add hardware control logic here

def heating_off():
    print("Heating turned off...")
    # Add hardware control logic here

def manual_fry(temp, time):
    print(f"Starting manual fry at {temp}°C for {time} minutes...")
    # Add hardware control logic here

def start_fry(temp, time):
    print(f"Starting fry at {temp}°C for {time} minutes...")
    # Add hardware control logic here

# Menu items based on menu_data from fryer.py
veg_items = [
    {"id": 1, "name": "Samosa", "image": "samosa.png", "temp": 170, "time": 90},
    {"id": 2, "name": "Paneer Pakora", "image": "paneer_pakora.png", "temp": 180, "time": 100}, 
    {"id": 3, "name": "Aloo Tikki", "image": "aloo_tikki.png", "temp": 175, "time": 90},
    {"id": 4, "name": "Kanda Bhaji", "image": "kanda_bhaji.png", "temp": 185, "time": 90},
    {"id": 5, "name": "Batata Vada", "image": "batata_vada.png", "temp": 170, "time": 90},
    {"id": 6, "name": "Palak Pakora", "image": "palak_pakora.png", "temp": 175, "time": 95},
    {"id": 7, "name": "Mix Veg Cutlet", "image": "mix_veg_cutlet.png", "temp": 180, "time": 120},
    {"id": 8, "name": "Corn Cheese Ball", "image": "corn_cheese_ball.png", "temp": 180, "time": 100},
    {"id": 9, "name": "Methi Gota", "image": "methi_gota.png", "temp": 180, "time": 90},
    {"id": 10, "name": "Sabudana Vada", "image": "sabudana_vada.png", "temp": 180, "time": 100},
]

non_veg_items = [
    {"id": 1, "name": "Chicken Pakora", "image": "chicken_pakora.png", "temp": 190, "time": 120},
    {"id": 2, "name": "Chicken Nuggets", "image": "chicken_nuggets.png", "temp": 180, "time": 140},
    {"id": 3, "name": "Fish Fingers", "image": "fish_fingers.png", "temp": 185, "time": 150}, 
    {"id": 4, "name": "Chicken Wings", "image": "chicken_wings.png", "temp": 190, "time": 180},
    {"id": 5, "name": "Tandoori Chicken", "image": "tandoori_chicken.png", "temp": 200, "time": 210},
    {"id": 6, "name": "Mutton Cutlet", "image": "mutton_cutlet.png", "temp": 190, "time": 160},
    {"id": 7, "name": "Egg Pakora", "image": "egg_pakora.png", "temp": 180, "time": 100},
    {"id": 8, "name": "Prawns Fry", "image": "prawns_fry.png", "temp": 195, "time": 130},
    {"id": 9, "name": "Fish Fry", "image": "fish_fry.png", "temp": 190, "time": 160},
]

class FryerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Fryer Interface")
        self.root.geometry("800x600")
        self.current_screen = "home"
        self.current_temp = 180

        # Placeholder image
        self.placeholder_image = ImageTk.PhotoImage(Image.new("RGB", (150, 100), color="gray"))

        self.create_home_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_menu_bar(self, back_callback):
        menu_bar = ttk.Frame(self.root)
        menu_bar.pack(side=tk.TOP, fill=tk.X)

        temp_label = ttk.Label(menu_bar, text=f"Current Temp: {self.current_temp}°C", 
                             font=("Arial", 14))
        temp_label.pack(side=tk.LEFT, padx=10)

        back_button = ttk.Button(menu_bar, text="Back",
                               command=back_callback)
        back_button.pack(side=tk.RIGHT, padx=10)

    def create_home_screen(self):
        self.clear_screen()
        self.create_menu_bar(lambda: None)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill="both", pady=20)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(expand=True)

        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1)
        button_frame.grid_rowconfigure(0, weight=1)

        button_width = 15
        button_height = 8

        veg_button = ttk.Button(button_frame, text="Veg",
                              command=self.show_veg_menu, width=button_width)
        veg_button.grid(row=0, column=0, padx=10, pady=10)

        non_veg_button = ttk.Button(button_frame, text="Non-Veg",
                                  command=self.show_non_veg_menu, width=button_width)
        non_veg_button.grid(row=0, column=1, padx=10, pady=10)

        manual_button = ttk.Button(button_frame, text="Manual Fry",
                                 command=self.show_manual_fry, width=button_width)
        manual_button.grid(row=0, column=2, padx=10, pady=10)

    def create_scrollable_menu(self, items, title):
        self.clear_screen()
        self.create_menu_bar(self.create_home_screen)

        title_label = ttk.Label(self.root, text=title, font=("Arial", 20, "bold"))
        title_label.pack(pady=10)

        # Create main container
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        # Create canvas with scrollbar
        canvas = ttk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
        
        # Configure canvas
        canvas.configure(xscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side="bottom", fill="x")
        canvas.pack(side="top", fill="both", expand=True)

        # Create frame for items
        scroll_frame = ttk.Frame(canvas)
        
        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        # Configure scroll region
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_window_size(event):
            canvas.itemconfig(canvas_window, width=event.width)

        # Bind events
        scroll_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_window_size)

        # Create items in a horizontal layout
        for item in items:
            frame = ttk.Frame(scroll_frame)
            frame.pack(side=tk.LEFT, padx=10, pady=10)

            try:
                img = Image.open(item["image"])
                img = img.resize((150, 100), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
            except:
                photo = self.placeholder_image

            img_label = ttk.Label(frame, image=photo)
            img_label.image = photo
            img_label.pack(pady=5)

            name_label = ttk.Label(frame, text=item["name"], font=("Arial", 12, "bold"))
            name_label.pack()

            temp_label = ttk.Label(frame, text=f"Temp: {item['temp']}°C")
            temp_label.pack()

            time_label = ttk.Label(frame, text=f"Time: {item['time']} min")
            time_label.pack()

            start_button = ttk.Button(frame, text="Start Frying",
                                    command=lambda t=item["temp"], tm=item["time"]: start_fry(t, tm))
            start_button.pack(pady=5)

        # Add navigation buttons
        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(fill="x", pady=5)

        # Store after IDs
        self.after_id = None

        def scroll_left():
            canvas.xview_scroll(-1, "units")
            self.after_id = canvas.after(50, scroll_left)

        def scroll_right():
            canvas.xview_scroll(1, "units")
            self.after_id = canvas.after(50, scroll_right)

        def stop_scroll():
            if self.after_id:
                canvas.after_cancel(self.after_id)
                self.after_id = None

        prev_button = ttk.Button(nav_frame, text="◀ Previous",
                               command=lambda: canvas.xview_scroll(-1, "page"))
        prev_button.pack(side="left", padx=20)
        prev_button.bind("<ButtonPress-1>", lambda e: scroll_left())
        prev_button.bind("<ButtonRelease-1>", lambda e: stop_scroll())

        next_button = ttk.Button(nav_frame, text="Next ▶",
                               command=lambda: canvas.xview_scroll(1, "page"))
        next_button.pack(side="right", padx=20)
        next_button.bind("<ButtonPress-1>", lambda e: scroll_right())
        next_button.bind("<ButtonRelease-1>", lambda e: stop_scroll())

    def show_veg_menu(self):
        self.create_scrollable_menu(veg_items, "Veg Menu")

    def show_non_veg_menu(self):
        self.create_scrollable_menu(non_veg_items, "Non-Veg Menu")

    def show_manual_fry(self):
        self.clear_screen()
        self.create_menu_bar(self.create_home_screen)

        title_label = ttk.Label(self.root, text="Manual Fry", font=("Arial", 20, "bold"))
        title_label.pack(pady=10)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Raise Basket",
                  command=raise_basket).grid(row=0, column=0, padx=10, pady=10)
        ttk.Button(button_frame, text="Lower Basket",
                  command=lower_basket).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(button_frame, text="Heating On",
                  command=heating_on).grid(row=1, column=0, padx=10, pady=10)
        ttk.Button(button_frame, text="Heating Off",
                  command=heating_off).grid(row=1, column=1, padx=10, pady=10)

        input_frame = ttk.Frame(self.root)
        input_frame.pack(pady=10)

        manual_temp = ttk.StringVar(value="180")
        manual_time = ttk.StringVar(value="10")

        ttk.Label(input_frame, text="Temp (°C)").pack()
        ttk.Entry(input_frame, textvariable=manual_temp, width=10).pack(pady=5)
        ttk.Label(input_frame, text="Time (min)").pack()
        ttk.Entry(input_frame, textvariable=manual_time, width=10).pack(pady=5)
        ttk.Button(input_frame, text="Manual Fry",
                  command=lambda: manual_fry(manual_temp.get(), manual_time.get())).pack(pady=10)

if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    app = FryerApp(root)
    root.mainloop()
