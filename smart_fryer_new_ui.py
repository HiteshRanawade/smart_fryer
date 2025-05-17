import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading

class SmartFryerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Automated Fryer")
        self.geometry("800x480")
        self.configure(bg='skyblue')
        self.current_temperature = 180  # mock value
        self.frames = {}
        self.create_menu_bar()
        self.show_main_screen()

    def create_menu_bar(self):
        menu_bar = tk.Frame(self, bg='darkblue', height=40)
        menu_bar.pack(side='top', fill='x')

        self.temp_label = tk.Label(menu_bar, text=f"Temp: {self.current_temperature}°C", bg='darkblue', fg='white')
        self.temp_label.pack(side='left', padx=10)

        self.back_button = tk.Button(menu_bar, text="Back", bg='white', command=self.go_back)
        self.back_button.pack(side='right', padx=10)

    def show_main_screen(self):
        self.clear_screen()
        frame = tk.Frame(self, bg='skyblue')
        frame.pack(fill='both', expand=True)
        self.frames["main"] = frame

        tk.Button(frame, text="Veg", font=("Arial", 24), command=self.show_veg_menu, height=3, width=20).pack(pady=20)
        tk.Button(frame, text="Non Veg", font=("Arial", 24), command=self.show_nonveg_menu, height=3, width=20).pack(pady=20)
        tk.Button(frame, text="Manual Fry", font=("Arial", 24), command=self.show_manual_fry, height=3, width=20).pack(pady=20)

    def show_veg_menu(self):
        self.show_menu_screen("veg")

    def show_nonveg_menu(self):
        self.show_menu_screen("nonveg")

    def show_menu_screen(self, category):
        self.clear_screen()
        frame = tk.Frame(self, bg='skyblue')
        frame.pack(fill='both', expand=True)
        self.frames[category] = frame

        canvas = tk.Canvas(frame, bg='skyblue')
        canvas.pack(side="top", fill="both", expand=True)

        item_frame = tk.Frame(canvas, bg='skyblue')
        canvas.create_window((0, 0), window=item_frame, anchor='nw')

        scroll_x = tk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
        scroll_x.pack(side="bottom", fill="x")
        canvas.configure(xscrollcommand=scroll_x.set)

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        item_frame.bind("<Configure>", on_configure)

        # Example Menu Data (10 Items)
        menu_items = [
            {"name": f"Item {i+1}", "temp": 180 + i, "time": 5+i} for i in range(10)
        ]

        for idx, item in enumerate(menu_items):
            tile = tk.Frame(item_frame, bd=2, relief='groove', bg='white', width=180, height=220)
            tile.grid(row=0, column=idx, padx=10, pady=10)

            tk.Label(tile, text=item["name"], font=('Arial', 12), bg='white').pack(pady=5)
            tk.Label(tile, text=f"Temp: {item['temp']}°C", bg='white').pack()
            tk.Label(tile, text=f"Time: {item['time']} min", bg='white').pack()

            tk.Button(tile, text="Start Frying", command=lambda i=item: self.start_frying(i)).pack(pady=5)
            tk.Button(tile, text="Customize", command=lambda i=item: self.customize_item(i)).pack(pady=5)

    def show_manual_fry(self):
        self.clear_screen()
        frame = tk.Frame(self, bg='skyblue')
        frame.pack(fill='both', expand=True)
        self.frames["manual"] = frame

        for name in ["Raise Basket", "Lower Basket", "Heating ON", "Heating OFF", "Manual Fry"]:
            tk.Button(frame, text=name, font=("Arial", 16), width=20,
                      command=lambda n=name: self.handle_manual(n)).pack(pady=10)

    def handle_manual(self, action):
        print(f"[LOG] Manual action triggered: {action}")
        if action == "Manual Fry":
            self.customize_item({'name': 'Manual Fry'})

    def start_frying(self, item):
        print(f"[LOG] Starting frying: {item}")
        self.clear_screen()
        frame = tk.Frame(self, bg='skyblue')
        frame.pack(fill='both', expand=True)

        time_left = item['time'] * 60
        label = tk.Label(frame, text="", font=("Arial", 24), bg='skyblue')
        label.pack(pady=20)

        def countdown():
            nonlocal time_left
            while time_left >= 0:
                mins, secs = divmod(time_left, 60)
                label.config(text=f"Frying {item['name']} - {mins:02}:{secs:02}")
                self.update()
                time.sleep(1)
                time_left -= 1

            label.config(text="Frying Completed!")
            print(f"[LOG] Frying completed: {item}")

        threading.Thread(target=countdown).start()

    def customize_item(self, item):
        print(f"[LOG] Customizing: {item}")
        popup = tk.Toplevel(self)
        popup.title("Customize Settings")
        popup.geometry("300x250")
        popup.grab_set()

        tk.Label(popup, text="Temperature (°C):").pack(pady=5)
        temp_entry = tk.Entry(popup)
        temp_entry.pack(pady=5)

        tk.Label(popup, text="Time (min):").pack(pady=5)
        time_entry = tk.Entry(popup)
        time_entry.pack(pady=5)

        def apply():
            temp = temp_entry.get()
            t = time_entry.get()
            try:
                item['temp'] = int(temp)
                item['time'] = int(t)
                print(f"[LOG] Updated {item['name']} to {item['temp']}°C, {item['time']}min")
                popup.destroy()
            except:
                messagebox.showerror("Error", "Invalid input")

        tk.Button(popup, text="Apply", command=apply).pack(pady=10)

    def go_back(self):
        print("[LOG] Back button pressed")
        self.show_main_screen()

    def clear_screen(self):
        for widget in self.winfo_children():
            if isinstance(widget, tk.Frame) and widget != self.winfo_children()[0]:  # Preserve top menu bar
                widget.destroy()

if __name__ == "__main__":
    app = SmartFryerApp()
    app.mainloop()
