import random
import shutil
import time
import tkinter as tk
from threading import Thread, Event
from tkinter import filedialog, messagebox, ttk
import discord
import asyncio
import requests
import json
import logging
import os
os.chdir(os.path.dirname(__file__))

DISCORD_CHANNEL_ID = 554699306943119360  # Replace with your channel ID
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/818268756215463956/qcjL8trRc70OKHQrJiaJO6HGLl6PBo4fnTG_p6kDkYFCx7EjSSEZLJT3YhPgTJhW1gH_"

LIVE_FOLDER = r"C:\\Users\\provo\\Desktop\\Folder of Folders\\streamstuff\\In-Use Pictures\\RoarTV Reborn (LIVE)"
LOG_FOLDER = r"C:\\Users\\provo\\Desktop\\Folder of Folders\\streamstuff\\Utilities\\Python\\RoarTV"

UPDATE_TXT_PATH = os.path.join(LIVE_FOLDER, "update.txt")
EARLY_FILE = os.path.join(LIVE_FOLDER, "early.txt")
BAD_FILE = os.path.join(LIVE_FOLDER, "bad.txt")
BADNUMBER_FILE = os.path.join(LIVE_FOLDER, "badnumber.txt")
LAST_FOLDER_FILE = os.path.join(LIVE_FOLDER, "last_folder.txt")
PRIORITY_FOLDER_FILE = os.path.join(LIVE_FOLDER, "priority_folder.txt")
PETS_FOLDER = r"E:\RTV1\Pets"  # or load from preset/config later

logging.basicConfig(
    filename=os.path.join(LOG_FOLDER, 'app.log'),
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class DiscordUploader:
    def __init__(self):
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)
        self.ready_event = asyncio.Event()
        self.loop = asyncio.new_event_loop()
        self.client.loop = self.loop

        @self.client.event
        async def on_ready():
            print(f"Logged in as {self.client.user}")
            self.ready_event.set()

        Thread(target=self.loop.run_until_complete, args=(self.start_bot(),), daemon=True).start()

    async def start_bot(self):
        await self.client.start(DISCORD_TOKEN)

    async def _upload_file(self, file_path):
        await self.ready_event.wait()
        channel = self.client.get_channel(DISCORD_CHANNEL_ID)
        if not channel:
            print("Channel not found.")
            return
        await channel.send(file=discord.File(file_path))

    def upload_file(self, file_path):
        asyncio.run_coroutine_threadsafe(self._upload_file(file_path), self.loop)



    def upload_to_discord(self, file_path):
        max_size = 50 * 1024 * 1024  # 8 MB
        size = os.path.getsize(file_path)
        if size > max_size:
            print(f"[DiscordUploader] File too large: {file_path} ({size / 1024 / 1024:.2f} MB).")
            return

        try:
            folder_name = os.path.basename(os.path.dirname(file_path))
            file_name = os.path.basename(file_path)

            with open(file_path, 'rb') as f:
                files = {
                    'file': f,
                    'payload_json': (
                        None,
                        json.dumps({
                            "content": f"Channel: {folder_name}\nFile: {file_name}"
                        }),
                        'application/json'
                    )
                }
                response = requests.post(DISCORD_WEBHOOK_URL, files=files)

            if response.status_code in (200, 204):
                print(f"[DiscordUploader] Uploaded successfully: {file_path}")
            else:
                print(f"[DiscordUploader] Upload failed: Status {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"[DiscordUploader] Upload error: {e}")

        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 0)
            print(f"[DiscordUploader] Rate limited. Retrying after {retry_after} seconds.")
            time.sleep(retry_after / 1000)
            return


class RandomMP4Mover:
    def __init__(self, root):
        self.root = root
        self.root.title("Random MP4 Selector")

        self.presets_dir = os.path.join(LIVE_FOLDER, "presets")
        os.makedirs(self.presets_dir, exist_ok=True)
        self.preset_names = ["Normal", "Christmas", "Halloween", "Ghibli", "TAS", "DisneyIRL", "DisneyMovies", "Thanksgiving"]
        from tkinter import simpledialog  # add to imports if not already

        preset_frame = tk.Frame(root)
        preset_frame.pack(pady=5)

        tk.Label(preset_frame, text="Presets:").pack(side="left")

        self.selected_preset = tk.StringVar()
        self.preset_dropdown = ttk.Combobox(preset_frame, textvariable=self.selected_preset, values=self.preset_names, state="readonly", width=15)
        self.preset_dropdown.current(0)
        self.preset_dropdown.pack(side="left")

        tk.Button(preset_frame, text="Load", command=self.load_selected_preset).pack(side="left", padx=2)
        tk.Button(preset_frame, text="Save", command=self.save_to_selected_or_prompt).pack(side="left", padx=2)


        self.label = tk.Label(root, text="Select the 5s folder:")
        self.label.pack(pady=5)

        self.last_shantae_roll = 0  # store previous 1-6 roll in memory


        # ---------------------------------------
        # 🎲 Rolls + Cycle count (side by side)
        # ---------------------------------------
        roll_frame = tk.Frame(root)
        roll_frame.pack(pady=4)

        self.roll256_label = tk.Label(roll_frame, text="256 Roll: --", font=("Chronotype", 15), fg="dark grey")
        self.roll256_label.pack(side="left", padx=5)

        self.roll8_label = tk.Label(roll_frame, text="8 Roll: --", font=("Chronotype", 15), fg="dark grey")
        self.roll8_label.pack(side="left", padx=5)

        self.cycle_count_label = tk.Label(roll_frame, text="Cycle Folders: --", font=("Chronotype", 15), fg="dark grey")
        self.cycle_count_label.pack(side="left", padx=5)


        # 📁 Folder selection + Priority options
        browse_frame = tk.Frame(root)
        browse_frame.pack(pady=5)

        # 📂 Browse button
        self.select_button = tk.Button(
            browse_frame,
            text="📂 Pick",
            width=12,
            command=self.select_folder
        )
        self.select_button.pack(side="left", padx=5)

        # ⭐ Priority dropdown (fixed + hover)
        self.priority_menu = tk.Menu(browse_frame, tearoff=0)
        self.priority_menu.add_command(label="⭐ Set Priority Channel", command=self.set_priority_folder)
        self.priority_menu.add_command(label="🎲 Random Priority Folder", command=self.randomize_priority_folder_from_drive)

        self.priority_button = tk.Menubutton(
            browse_frame,
            text="⭐ Priority ▼",
            width=14,
            relief="raised",
            direction="below",
            menu=self.priority_menu
        )
        self.priority_button.pack(side="left", padx=5)

        # Ignore Priority checkbox right next to dropdown
        self.ignore_priority_var = tk.BooleanVar(value=False)
        self.ignore_priority_checkbox = tk.Checkbutton(
            browse_frame,
            text="No Priority",
            variable=self.ignore_priority_var,
            command=self.update_cycle_time_estimate
        )
        self.ignore_priority_checkbox.pack(side="left", padx=(10, 0))

        # Open dropdown on click
        def open_priority_menu(event):
            self.priority_button.event_generate("<ButtonRelease-1>")
            self.priority_menu.tk_popup(event.x_root, event.y_root)
            self.priority_menu.grab_release()

        self.priority_button.bind("<Button-1>", open_priority_menu)

        # 🔹 Hover highlight for Priority
        def on_enter_priority(e): self.priority_button.config(bg="#3a6ea5", fg="white")
        def on_leave_priority(e): self.priority_button.config(bg="SystemButtonFace", fg="black")
        self.priority_button.bind("<Enter>", on_enter_priority)
        self.priority_button.bind("<Leave>", on_leave_priority)


        self.select_none_var = tk.BooleanVar()
        self.discord = DiscordUploader()
        # --- Core state variables (must exist before GUI builds) ---
        self.channel_vars = {}
        self.interval = 100
        self.rotation_interval = tk.IntVar(value=self.interval)


        # -----------------------------
        # Priority Channel (every Nth)
        # -----------------------------
        self.priority_every_n = tk.IntVar(value=4)  # default: every 4th slot

        priority_frame = tk.Frame(root)
        priority_frame.pack(pady=5)
        tk.Label(priority_frame, text="Priority Channel (every Nth):").pack(side="left")
        tk.Entry(priority_frame, textvariable=self.priority_every_n, width=6).pack(side="left", padx=3)
        tk.Button(priority_frame, text="Apply", command=self.update_priority_every_n).pack(side="left", padx=5)

        self.used_subfolders = set()

        # -----------------------------
        # Holiday chance configuration
        # -----------------------------
        self.holiday_chance = tk.IntVar(value=64)  # Default: 1 in 64

        holiday_frame = tk.Frame(root)
        holiday_frame.pack(pady=5)
        tk.Label(holiday_frame, text="Holiday Chance (1 in N):").pack(side="left")
        tk.Entry(holiday_frame, textvariable=self.holiday_chance, width=6).pack(side="left", padx=3)
        tk.Button(holiday_frame, text="Set to 1/3 (Test)", command=lambda: self.holiday_chance.set(3)).pack(side="left", padx=5)

        # Hidden Select All / None controls (logic only, no visible widgets)
        self.select_none_var = tk.BooleanVar(value=False)
        self.select_all_var = tk.BooleanVar(value=True)


        # ▶️ Playback Controls (Start / Stop / History)
        control_frame = tk.Frame(root)
        control_frame.pack(pady=5)

        self.start_button = tk.Button(control_frame, text="▶ Start", width=10, command=self.start_loop)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = tk.Button(control_frame, text="⏹ Stop", width=10, command=self.stop_loop, state=tk.DISABLED)
        self.stop_button.pack(side="left", padx=5)

        # ✅ History dropdown (works + matches Priority behavior)
        self.history_menu = tk.Menu(control_frame, tearoff=0)
        self.history_menu.add_command(label="📜 View History", command=self.show_history)
        self.history_menu.add_command(label="💾 Export History", command=self.export_history)

        self.history_button = tk.Menubutton(
            control_frame,
            text="🕓 History ▼",
            width=12,
            relief="raised",
            direction="below",
            menu=self.history_menu
        )
        self.history_button.pack(side="left", padx=5)

        def open_history_menu(event):
            self.history_button.event_generate("<ButtonRelease-1>")
            self.history_menu.tk_popup(event.x_root, event.y_root)
            self.history_menu.grab_release()

        self.history_button.bind("<Button-1>", open_history_menu)

        # ---------------------------------------
        # 🌀 Cycle Settings (Cycle time + rotation)
        # ---------------------------------------
        cycle_frame = ttk.LabelFrame(root, text="Cycle Settings")
        cycle_frame.pack(fill="x", padx=5, pady=5)

        # Estimated cycle time
        self.cycle_time_label = tk.Label(cycle_frame, text="Estimated Cycle Time: -- seconds")
        self.cycle_time_label.pack(anchor="w", padx=10, pady=(5, 2))

        # Rotation interval
        rotation_frame = tk.Frame(cycle_frame)
        rotation_frame.pack(anchor="w", padx=10, pady=5)
        tk.Label(rotation_frame, text="Rotation Interval (seconds):").pack(side="left")
        tk.Entry(rotation_frame, textvariable=self.rotation_interval, width=6).pack(side="left", padx=3)
        tk.Button(rotation_frame, text="Apply", command=self.update_rotation_interval).pack(side="left", padx=5)

        self.channel_frame = ttk.LabelFrame(root, text="Toggle Channels")
        self.channel_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(self.channel_frame)
        self.scrollbar = ttk.Scrollbar(self.channel_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")


        self.channel_vars = {}
        random.seed(os.urandom(64))
        self.bad_processing = False
        self.running = False

        self.root.bind("<F16>", lambda event: self.send_last_channel_to_discord())
        self.played_history = []
        self.folder_path = None
        self.used_files = set()
        self.all_files = {}
        self.full_subfolder_cycle = []
        self.cycle_index = 0
        self.folder_cycle_index = 0
        self.last_played_file_path = None
        self.change_event = Event()
        self.bad_count = 0
        self.original_active_folders = []
        self.folder_subfolder_index = {}
        self.priority_folder = None
        self.priority_files = []
        self.priority_used = set()
        self.priority_index = 0
        self.insert_priority_next = False
        self.priority_counter = 0

        self.load_last_folder()
        self.load_priority_folder()
        self.select_all_channels()
        if self.select_all_var.get():
            self.select_all_channels()

        self.create_trigger_files()

        with open(BADNUMBER_FILE, 'w') as f:
            f.write("0")

        Thread(target=self.monitor_trigger_files, daemon=True).start()

    def save_to_selected_or_prompt(self):
        name = self.selected_preset.get()
        if not name:
            name = simpledialog.askstring("Save Preset", "Enter new preset name:")
            if not name:
                return
            if name not in self.preset_names:
                self.preset_names.append(name)
                self.preset_dropdown['values'] = self.preset_names
                self.selected_preset.set(name)
        self.save_preset(name)


    def save_preset(self, preset_name):
        preset_path = os.path.join(self.presets_dir, preset_name + ".json")
        preset_data = {
            "channels": {
                os.path.basename(folder): {
                    "enabled": var[0].get(),
                    "double": var[1].get()
                }
                for folder, var in self.channel_vars.items()
            },
            "priority_folder": self.priority_folder,
            "main_folder": self.folder_path,  # ✅ Add this
            "priority_every_n": int(self.priority_every_n.get()),
            "pets_folder": PETS_FOLDER,
            "rotation_interval": int(self.rotation_interval.get()),
            

        }

        try:
            with open(preset_path, "w") as f:
                json.dump(preset_data, f)
            #messagebox.showinfo("Preset Saved", f"Preset '{preset_name}' saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preset: {e}")
        
    def randomize_priority_folder(self):
        """Randomly choose a leaf folder from the main directory and set it as priority."""
        if not self.folder_path or not os.path.isdir(self.folder_path):
            messagebox.showerror("Error", "Please select your main folder first.")
            return

        # Collect all leaf folders under the main folder
        leaf_folders = []
        for root_dir, subdirs, files in os.walk(self.folder_path):
            # A leaf folder is one that has no subdirectories
            if not subdirs:
                leaf_folders.append(root_dir)

        if not leaf_folders:
            messagebox.showwarning("No Leaf Folders", "No leaf folders found in the selected directory.")
            return

        chosen_folder = random.choice(leaf_folders)
        self.priority_folder = chosen_folder
        self.priority_files = [f for f in os.listdir(chosen_folder) if f.lower().endswith(".mp4")]
        self.priority_used.clear()
        self.priority_index = 0

        # Write it to disk
        with open(PRIORITY_FOLDER_FILE, 'w') as f:
            f.write(chosen_folder)

        # Update the interface
        messagebox.showinfo("Priority Folder Set", f"Random Priority Folder chosen:\n{chosen_folder}")
    
    
    
    def update_rotation_interval(self):
        """Update the rotation interval (seconds) for file switching."""
        try:
            new_interval = int(self.rotation_interval.get())
            if new_interval < 5:
                messagebox.showwarning("Too Low", "Interval must be at least 5 seconds.")
                return
            self.interval = new_interval
            self.update_cycle_time_estimate()
            messagebox.showinfo("Updated", f"Rotation interval set to {new_interval} seconds.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number of seconds.")
        
    def update_priority_every_n(self):
        """Validate and apply the priority insertion channel."""
        try:
            n = int(self.priority_every_n.get())
            if n < 2:
                messagebox.showwarning("Too Low", "Priority channel must be at least every 2nd slot.")
                return
            # simply recompute the estimate; play loop reads self.priority_every_n live
            self.update_cycle_time_estimate()
            messagebox.showinfo("Updated", f"Priority channel set to every {n} slot(s).")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid integer (>= 2).")

    def load_preset(self, name):
        preset_path = os.path.join(self.presets_dir, name + ".json")
        if not os.path.exists(preset_path):
            messagebox.showwarning("Preset Missing", f"Preset '{name}' not found.")
            return

        try:
            with open(preset_path, "r") as f:
                preset_data = json.load(f)

            # --- Restore main folder ---
            main_folder = preset_data.get("main_folder")
            if main_folder and os.path.isdir(main_folder):
                self.folder_path = main_folder
                self.label.config(text=f"Selected: {self.folder_path}")
                self.save_last_folder()

            # --- Restore channel & rotation settings ---
            if "priority_every_n" in preset_data:
                try:
                    self.priority_every_n.set(int(preset_data["priority_every_n"]))
                except Exception:
                    pass

            if "rotation_interval" in preset_data:
                try:
                    self.rotation_interval.set(int(preset_data["rotation_interval"]))
                    self.interval = int(self.rotation_interval.get())
                except Exception:
                    pass
            
            if "pets_folder" in preset_data and os.path.isdir(preset_data["pets_folder"]):
                global PETS_FOLDER
                PETS_FOLDER = preset_data["pets_folder"]

            # --- Refresh and apply channel states ---
            self.refresh_file_list(preserve_checkmarks=False)

            for folder, (enabled_var, double_var) in self.channel_vars.items():
                key = os.path.basename(folder)
                if key in preset_data.get("channels", {}):
                    enabled_var.set(preset_data["channels"][key]["enabled"])
                    double_var.set(preset_data["channels"][key]["double"])
                else:
                    enabled_var.set(False)
                    double_var.set(False)

            # --- Load priority folder ---
            priority_path = preset_data.get("priority_folder")
            if priority_path and os.path.isdir(priority_path):
                self.priority_folder = priority_path
                self.priority_files = [f for f in os.listdir(priority_path) if f.endswith(".mp4")]
                self.priority_used.clear()
                self.priority_index = 0
                with open(PRIORITY_FOLDER_FILE, 'w') as f:
                    f.write(priority_path)

            # --- Final housekeeping ---
            self.update_enabled_folders()
            self.update_cycle_time_estimate()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preset: {e}")

        # Update window title and re-select all if needed
        self.root.title(f"Random MP4 Selector — Preset: {name}")
        if self.select_all_var.get():
            self.select_all_channels()

    def load_selected_preset(self):
        name = self.selected_preset.get()
        if name:
            self.load_preset(name)

    def set_priority_folder(self):
        folder = filedialog.askdirectory(title="Select Priority Channel Folder")
        if folder and os.path.isdir(folder):
            self.priority_folder = folder
            self.priority_files = []
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(".mp4"):
                        self.priority_files.append(os.path.join(root, f))

            self.priority_used.clear()
            self.priority_index = 0
            with open(PRIORITY_FOLDER_FILE, 'w') as f:
                f.write(folder)
            #messagebox.showinfo("Priority Channel Set", f"Priority channel set to:\n{folder}")

    def randomize_priority_folder_from_drive(self):
        """Pick a random leaf folder anywhere on the E:\\ drive and set it as the priority folder."""
        root_drive = "E:\\"
        if not os.path.exists(root_drive):
            messagebox.showerror("Drive Missing", f"{root_drive} not found.")
            return

        leaf_folders = []
        for root_dir, subdirs, files in os.walk(root_drive):
            # Skip common system or hidden directories
            if any(part.startswith("$") or part.lower().startswith(("windows", "recycle", "system", "program")) 
                   for part in root_dir.split(os.sep)):
                continue
            if not subdirs:
                leaf_folders.append(root_dir)

        if not leaf_folders:
            messagebox.showwarning("No Leaf Folders", f"No leaf folders found on {root_drive}")
            return

        chosen_folder = random.choice(leaf_folders)
        mp4s = [f for f in os.listdir(chosen_folder) if f.lower().endswith(".mp4")]

        if not mp4s:
            messagebox.showwarning("No MP4s", f"Chosen folder has no MP4 files:\n{chosen_folder}")
            return

        self.priority_folder = chosen_folder
        self.priority_files = mp4s
        self.priority_used.clear()
        self.priority_index = 0

        with open(PRIORITY_FOLDER_FILE, "w", encoding="utf-8") as f:
            f.write(chosen_folder)

        messagebox.showinfo("Priority Folder Set", f"🎲 Random Priority Folder chosen:\n{chosen_folder}")



    def load_last_folder(self):
        if os.path.exists(LAST_FOLDER_FILE):
            with open(LAST_FOLDER_FILE, 'r') as file:
                folder = file.read().strip()
                if os.path.isdir(folder):
                    self.folder_path = folder
                    self.label.config(text=f"Selected: {self.folder_path}")
                    self.refresh_file_list()
                if self.select_all_var.get():
                    self.select_all_channels()


    def load_priority_folder(self):
        if os.path.exists(PRIORITY_FOLDER_FILE):
            with open(PRIORITY_FOLDER_FILE, 'r') as f:
                folder = f.read().strip()
                if os.path.isdir(folder):
                    self.priority_folder = folder
                    self.priority_files = [f for f in os.listdir(folder) if f.endswith(".mp4")]
                    self.priority_used.clear()
                    self.priority_index = 0


    def save_last_folder(self):
        if self.folder_path:
            with open(LAST_FOLDER_FILE, 'w') as file:
                file.write(self.folder_path)

    def create_trigger_files(self):
        os.makedirs(LIVE_FOLDER, exist_ok=True)
        for file in [EARLY_FILE, BAD_FILE]:
            if os.path.exists(BADNUMBER_FILE):
                with open(BADNUMBER_FILE, 'r') as f:
                    try:
                        self.bad_count = int(f.read().strip())
                    except ValueError:
                        self.bad_count = 0
            else:
                self.bad_count = 0
                with open(BADNUMBER_FILE, 'w') as f:
                    f.write("0")


    def select_none_channels(self):
        if self.select_none_var.get():
            for var in self.channel_vars.values():
                var[0].set(False)
            self.update_enabled_folders()
            self.update_cycle_time_estimate()


    def update_cycle_time_estimate(self):
        total = 0
        for folder, (enabled_var, double_var) in self.channel_vars.items():
            if enabled_var.get():
                total += 2 if double_var.get() else 1

        if total == 0:
            self.cycle_time_label.config(text="Estimated Cycle Time: -- seconds")
            return

        use_priority = self.priority_folder and self.priority_files and not self.ignore_priority_var.get()

        # Estimate how many priority insertions will happen in one pass across normal slots.
        # If priority-only mode, skip here (handled elsewhere).
        if use_priority and total > 0:
            try:
                n = int(self.priority_every_n.get())
                n = max(2, n)
            except Exception:
                n = 4
            # Insert roughly one priority slot per N normal slots.
            priority_inserts = total // n
            total_with_priority = total + priority_inserts
        else:
            total_with_priority = total

        est_time = total_with_priority * self.interval
        minutes, seconds = divmod(est_time, 60)
        self.cycle_time_label.config(
            text=f"Estimated Cycle Time: {minutes}m {seconds}s ({est_time} seconds)"
        )


    def update_shantae_number(self):
        try:
            shantae_file = os.path.join(LIVE_FOLDER, "shantaeNumber.txt")

            # Roll 1-256 first
            roll_256 = random.randint(1, 256)
            if roll_256 == 256:
                with open(shantae_file, "w") as f:
                    f.write("nu")
                self.last_shantae_roll = 0
                self.roll256_label.config(text="256 Roll: nu")
                self.roll8_label.config(text="8 Roll: --")  # clear since nu skips it
                return
            else:
                self.roll256_label.config(text=f"256 Roll: {roll_256}")

            # Roll 1-8 ensuring it's not the same as previous
            roll = random.randint(1, 8)
            while roll == self.last_shantae_roll:
                roll = random.randint(1, 8)
            self.last_shantae_roll = roll

            with open(shantae_file, "w") as f:
                f.write(str(roll))

            # Update the GUI label with the 1–8 roll
            self.roll8_label.config(text=f"8 Roll: {roll}")

        except Exception as e:
            logging.error(f"Failed to update shantaeNumber.txt: {e}")


    def select_all_channels(self):
        if self.select_all_var.get():
            for var in self.channel_vars.values():
                var[0].set(True)
            self.update_enabled_folders()
            self.update_cycle_time_estimate()


    def find_leaf_subfolder(self, folder):
        current = folder
        while True:
            subfolders = [os.path.join(current, d) for d in os.listdir(current) if os.path.isdir(os.path.join(current, d))]
            if not subfolders:
                return current
            current = random.choice(subfolders)

    def get_random_pet_folder(self):
        """Pick a random directory under PETS_FOLDER that contains at least one .mp4.
        Prefer leaf folders (no subdirs). If none, fall back to any folder that has mp4s.
        """
        if not os.path.isdir(PETS_FOLDER):
            logging.warning(f"[PetCameo] Pets folder missing: {PETS_FOLDER}")
            return None

        leaf_dirs_with_mp4s = []
        any_dirs_with_mp4s = []

        for root, subdirs, files in os.walk(PETS_FOLDER):
            mp4s = [f for f in files if f.lower().endswith(".mp4")]
            if mp4s:
                any_dirs_with_mp4s.append(root)
                if not subdirs:
                    leaf_dirs_with_mp4s.append(root)

        chosen_pool = leaf_dirs_with_mp4s if leaf_dirs_with_mp4s else any_dirs_with_mp4s
        if not chosen_pool:
            logging.warning(f"[PetCameo] No pet folders with mp4s found in {PETS_FOLDER}")
            return None

        chosen = random.choice(chosen_pool)
        logging.info(f"[PetCameo] Candidates: leaf={len(leaf_dirs_with_mp4s)} any={len(any_dirs_with_mp4s)} | chose: {chosen}")
        return chosen


    def monitor_trigger_files(self):
        try:
            bad_mtime = os.path.getmtime(BAD_FILE)
        except:
            bad_mtime = 0

        try:
            early_mtime = os.path.getmtime(EARLY_FILE)
        except:
            early_mtime = 0

        while True:
            time.sleep(1)
            if not self.running:
                continue

            try:
                new_bad_mtime = os.path.getmtime(BAD_FILE)
                if new_bad_mtime != bad_mtime and not self.bad_processing:
                    with open(BAD_FILE, 'r') as f:
                        if f.read().strip() == "1":
                            self.bad_processing = True
                            Thread(target=self.bad_channel, daemon=True).start()
                    bad_mtime = new_bad_mtime
            except Exception as e:
                print(f"Error monitoring bad.txt: {e}")

            try:
                new_early_mtime = os.path.getmtime(EARLY_FILE)
                if new_early_mtime != early_mtime:
                    self.early_change()
                    early_mtime = new_early_mtime
            except Exception as e:
                print(f"Error monitoring early.txt: {e}")

    def select_folder(self):
        self.folder_path = filedialog.askdirectory()
        if self.folder_path:
            self.label.config(text=f"Selected: {self.folder_path}")
            self.refresh_file_list()
            self.save_last_folder()

    def refresh_file_list(self, preserve_checkmarks=False):
        if not self.folder_path:
            return

        logging.info(f"Refreshing file list for: {self.folder_path}")

        previous_states = {}
        if preserve_checkmarks:
            for folder, (enabled_var, double_var) in self.channel_vars.items():
                folder_key = os.path.basename(folder)
                previous_states[folder_key] = (enabled_var.get(), double_var.get())

        self.all_files.clear()
        self.channel_vars.clear()
        self.original_active_folders.clear()

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        try:
            all_subfolders = [
                os.path.join(self.folder_path, d)
                for d in sorted(os.listdir(self.folder_path))
                if os.path.isdir(os.path.join(self.folder_path, d)) and 'bad' not in d.lower()
            ]

            # ✅ If no subfolders exist, treat the chosen folder as the leaf
            if not all_subfolders:
                logging.info(f"No subfolders found in {self.folder_path}, using folder itself.")
                all_subfolders = [self.folder_path]

            logging.debug(f"Found subfolders: {all_subfolders}")


            if not all_subfolders:
                logging.warning("No valid subfolders found in selected path.")

            for folder in all_subfolders:
                try:
                    leaf_folder = self.find_leaf_subfolder(folder)
                    if not leaf_folder or not os.path.isdir(leaf_folder):
                        logging.warning(f"Invalid or missing leaf: {leaf_folder} from {folder}")
                        continue

                    if leaf_folder in self.used_subfolders:
                        continue

                    logging.debug(f"Processing: {folder} → Leaf: {leaf_folder}")

                    self.original_active_folders.append((folder, []))
                    folder = leaf_folder
                    folder_key = os.path.basename(folder)

                    prev_enabled, prev_double = previous_states.get(folder_key, (True, False))

                    var = tk.BooleanVar(value=prev_enabled if preserve_checkmarks else True)
                    double_var = tk.BooleanVar(value=prev_double if preserve_checkmarks else False)


                    if PETS_FOLDER in folder:
                        var.set(True)
                        var.trace_add("write", lambda *_, v=var: v.set(True))  # prevent user unchecking

                    frame = tk.Frame(self.scrollable_frame)
                    frame.pack(anchor="w", fill="x")

                    cb = ttk.Checkbutton(frame, text=folder_key, variable=var, command=self.update_cycle_time_estimate)
                    cb.pack(side="left")

                    cb2 = ttk.Checkbutton(frame, text="x2", variable=double_var, command=self.update_cycle_time_estimate)
                    cb2.pack(side="left", padx=10)

                    self.channel_vars[folder] = (var, double_var)

                    self.scrollable_frame.update_idletasks()
                    time.sleep(0.05)

                except Exception as e:
                    logging.exception(f"Failed to process folder {folder}: {e}")

            logging.info(f"Channel list updated with {len(self.channel_vars)} folders.")

        except Exception as e:
            logging.exception("Error listing folder contents")

        self.update_enabled_folders()
        self.update_cycle_time_estimate()
        if self.select_all_var.get():
            self.select_all_channels()
            


    def update_enabled_folders(self):
        enabled_folders = [
            folder for folder, (enabled_var, _) in self.channel_vars.items() if enabled_var.get()
        ]
        if not enabled_folders:
            self.full_subfolder_cycle = []
            # If there's no normal cycle, make sure the per-cycle holiday flag is cleared.
            self.holiday_sent_this_cycle = False
            return

        #random.shuffle(enabled_folders)  # Optional: shuffle cycle
        self.full_subfolder_cycle = enabled_folders
        # 🔮 Wild fuckery zone: make priority channel auto-match number of folders
        folder_count = len(self.full_subfolder_cycle)
        if folder_count > 0:
            self.priority_every_n.set(folder_count)
            self.cycle_count_label.config(text=f"Cycle Folders: {folder_count}")
            logging.info(f"[AutoChannel] Priority channel auto-set to {folder_count}")
        else:
            self.cycle_count_label.config(text="Cycle Folders: --")

        self.cycle_index = 0

        for subfolder in self.full_subfolder_cycle:
            self.all_files[subfolder] = [f for f in os.listdir(subfolder) if f.endswith(".mp4")]

        self.folder_cycle_index = 0

        # Rebuilding the cycle = start of a new cycle → allow one holiday again.
        self.holiday_sent_this_cycle = False
        self.cycle_count_label.config(text=f"Cycle Folders: {len(self.full_subfolder_cycle)}")


    def update_txt(self, message):
        with open(UPDATE_TXT_PATH, 'a') as file:
            file.write(f"{message}\n")

    def update_channel_txt(self, folder, filename):
        name_without_ext = os.path.splitext(filename)[0]
        folder_name = os.path.basename(folder)

        # Check if the folder name starts with 'z' or 'Z' and remove it
        if folder_name.lower().startswith('z'):
            folder_name = folder_name[1:]

        channel_message = f"{folder_name} - {name_without_ext}"

        channel_txt_path = os.path.join(LIVE_FOLDER, "channel.txt")
        last_channel_txt_path = os.path.join(LIVE_FOLDER, "lastchannel.txt")

        # Save current channel.txt to lastchannel.txt before updating it
        if os.path.exists(channel_txt_path):
            try:
                with open(channel_txt_path, 'r') as current_file:
                    previous_content = current_file.read()
                with open(last_channel_txt_path, 'w') as last_file:
                    last_file.write(previous_content)
            except Exception as e:
                print(f"Error updating lastchannel.txt: {e}")

        # Now update channel.txt with the new video info
        with open(channel_txt_path, 'w') as file:
            file.write(channel_message)

        # Immediately update the history file
        full_path = os.path.join(folder, filename)
        try:
            history_file = os.path.join(LIVE_FOLDER, "history_paths.txt")
            with open(history_file, "a", encoding="utf-8") as histfile:
                histfile.write(f"{full_path}\n")

            with open(history_file, 'r+', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) > 100:
                    f.seek(0)
                    f.writelines(lines[-100:])
                    f.truncate()
        except Exception:
            pass


    def get_next_folder(self):
        if not self.full_subfolder_cycle:
            return None

        # Loop until we find a folder with available files
        attempts = 0
        while attempts < len(self.full_subfolder_cycle):
            if self.cycle_index >= len(self.full_subfolder_cycle):
                self.cycle_index = 0  # wrap around, but don’t rebuild


            folder = self.full_subfolder_cycle[self.cycle_index]
            self.cycle_index += 1

            # If this folder has no files left, refresh it immediately
            available_files = list(set(self.all_files.get(folder, [])) - self.used_files)
            if not available_files:
                # Reset only this folder’s used list
                all_folder_files = [f for f in os.listdir(folder) if f.endswith(".mp4")]
                self.all_files[folder] = all_folder_files
                available_files = all_folder_files
                if not available_files:
                    attempts += 1
                    continue  # Folder truly empty, skip it

            return folder

        # if we somehow exhausted all folders, start a fresh cycle safely
        if not self.full_subfolder_cycle:
            logging.warning("Cycle exhausted — restarting cleanly.")
            self.refresh_file_list(preserve_checkmarks=True)
            self.cycle_index = 0
            if self.full_subfolder_cycle:
                return self.full_subfolder_cycle[0]
        return None

    def get_next_active_subfolder(self, folder):
        for root, subs in self.original_active_folders:
            if root == folder:
                if not subs:
                    return folder
                if root not in self.folder_subfolder_index:
                    self.folder_subfolder_index[root] = 0
                index = self.folder_subfolder_index[root]
                next_sub = subs[index % len(subs)]
                self.folder_subfolder_index[root] = (index + 1) % len(subs)
                return next_sub
        return folder

    def play_next_video(self):
        use_priority = (
            self.priority_folder
            and self.priority_files
            and not self.ignore_priority_var.get()
        )

        # Priority-only mode (no normal folders)
        if use_priority and not self.full_subfolder_cycle:
            folder_to_use = self.priority_folder
            files = list(set(self.priority_files) - self.priority_used)
            if not files:
                self.priority_used.clear()
                files = self.priority_files[:]
            selected_file = random.choice(files)
            self.priority_used.add(selected_file)
            self.priority_counter = 0  # reset for next cycle

        else:
            should_use_priority = False
            n = max(2, int(self.priority_every_n.get() or 4)) if use_priority else 0

            # ✅ Check BEFORE increment to fix off-by-one behavior
            if use_priority and self.priority_counter + 1 >= n:
                should_use_priority = True
                self.priority_counter = 0
            else:
                should_use_priority = False
                self.priority_counter += 1

            if should_use_priority:
                folder_to_use = self.priority_folder
                files = list(set(self.priority_files) - self.priority_used)
                if not files:
                    self.priority_used.clear()
                    files = self.priority_files[:]
                selected_file = random.choice(files)
                self.priority_used.add(selected_file)
            else:
                subfolder = self.get_next_folder()
                if not subfolder:
                    return
                folder_to_use = subfolder
                self.folder_cycle_index += 1

                available_files = self.all_files.get(subfolder, [])
                if not available_files:
                    return
                selected_file = random.choice(available_files)

        # ---- Common part ----
        self.current_file = selected_file
        if os.path.isabs(selected_file):
            self.current_file_path = selected_file
        else:
            self.current_file_path = os.path.join(folder_to_use, selected_file)

        display_name = f"{os.path.basename(folder_to_use)} - {selected_file}"
        self.played_history.append((self.current_file_path, display_name))
        if len(self.played_history) > 10:
            self.played_history.pop(0)

        shutil.copy2(self.current_file_path, os.path.join(LIVE_FOLDER, "roarTV2.mp4"))
        self.last_played_file_path = self.current_file_path

        self.update_txt(selected_file)
        self.update_channel_txt(folder_to_use, selected_file)
        self.update_shantae_number()

        _, double_var = self.channel_vars.get(folder_to_use, (None, tk.BooleanVar(value=False)))
        delay = self.interval * 2 if double_var.get() else self.interval

        self.change_event.clear()
        for _ in range(delay):
            if not self.running or self.change_event.is_set():
                break
            time.sleep(1)

        return folder_to_use

       
    def play_special_video(self, root_folder, is_holiday=False):
        """Play a special channel (holiday) using the same logic as normal ones."""
        try:
            leaf = self.find_leaf_subfolder(root_folder)
            mp4s = [
                os.path.join(leaf, f)
                for f in os.listdir(leaf)
                if f.lower().endswith(".mp4")
            ]
            if not mp4s:
                logging.warning(f"No MP4s found in {leaf}")
                return None

            chosen_file = random.choice(mp4s)
            dest = os.path.join(LIVE_FOLDER, "roarTV2.mp4")
            shutil.copy2(chosen_file, dest)

            # --- identical state updates ---
            self.last_played_file_path = chosen_file
            self.last_folder = leaf
            self.update_channel_txt(leaf, os.path.basename(chosen_file))
            self.update_txt(os.path.basename(chosen_file))
            self.update_shantae_number()
            self.holiday_sent_this_cycle = False
            #self.discord.upload_to_discord(dest)

            label = "🎄 Holiday Channel" if is_holiday else "Special Channel"
            logging.info(f"{label}: {chosen_file}")

            # allow early/bad.txt to interrupt the normal delay
            self.change_event.clear()
            for _ in range(self.interval):
                if not self.running or self.change_event.is_set():
                    break
                time.sleep(1)
            return leaf

        except Exception as e:
            logging.error(f"Failed to play special video: {e}")
            return None


    def move_random_mp4(self):
        """Main loop that plays videos and occasionally injects a holiday channel and pet cameo."""
        cycle_counter = 0

        while self.running:
            # Only allow ONE holiday per cycle, regardless of chance setting.
            try_holiday = (
                not self.holiday_sent_this_cycle
                and len(self.full_subfolder_cycle) > 0  # define "cycle" only when we have normal folders
            )

            # 🔹 1/N chance before each normal slot — but only if we haven't sent a holiday yet this cycle
            if try_holiday and random.randint(1, self.holiday_chance.get()) == 1:
                try:
                    holiday_root = r"E:\Holiday"
                    if not os.path.isdir(holiday_root):
                        logging.warning("Holiday root missing.")
                    else:
                        holiday_folders = [
                            os.path.join(holiday_root, d)
                            for d in os.listdir(holiday_root)
                            if os.path.isdir(os.path.join(holiday_root, d))
                        ]
                        if holiday_folders:
                            chosen_holiday = random.choice(holiday_folders)
                            # ✅ Play like a normal channel so it reacts to early/bad.txt
                            self.play_special_video(chosen_holiday, is_holiday=True)
                            # Mark that we've done our one holiday for this cycle
                            self.holiday_sent_this_cycle = True
                            continue  # Skip to next loop iteration after holiday
                except Exception as e:
                    logging.error(f"Holiday channel injection failed: {e}")

            # 🔹 Normal playback
            folder_used = self.play_next_video()
            if folder_used:
                self.used_subfolders.add(folder_used)
                cycle_counter += 1

            # 🔹 One "cycle" == one pass through all enabled normal folders
            if len(self.full_subfolder_cycle) > 0 and cycle_counter >= len(self.full_subfolder_cycle):
                cycle_counter = 0
                self.used_subfolders.clear()
                self.holiday_sent_this_cycle = False

                # 🐾 Play one random pet folder per cycle
                pet_folder = self.get_random_pet_folder()
                if pet_folder:
                    logging.info(f"🐾 Pet cameo folder: {pet_folder}")
                    try:
                        self.play_special_video(pet_folder, is_holiday=False)
                    except Exception as e:
                        logging.error(f"Failed to play pet cameo: {e}")

    def start_loop(self):
        if not self.folder_path:
            messagebox.showerror("Error", "Please select the 5s folder.")
            return

        self.stop_loop()  # Ensure any previous thread is stopped
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        Thread(target=self.move_random_mp4, daemon=True).start()

    def stop_loop(self):
        self.running = False
        self.used_files.clear()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def early_change(self):
        if self.running:
            self.change_event.set()

    def reset_timer(self):
        self.change_event.set()


    def show_history(self):
        history_path_file = os.path.join(LIVE_FOLDER, "history_paths.txt")
        if not os.path.exists(history_path_file):
            messagebox.showinfo("History", "No history available.")
            return

        try:
            with open(history_path_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()[-100:]  # Last 50 entries

            if not lines:
                messagebox.showinfo("History", "No history available.")
                return

            history_window = tk.Toplevel(self.root)
            history_window.title("Last 10 Videos")

            for line in reversed(lines[-10:]):
                path = line.strip()
                if os.path.exists(path):
                    link = tk.Label(history_window, text=path, fg="blue", cursor="hand2")
                    link.pack(anchor="w", padx=10, pady=2)

                    # Left-click: open file
                    link.bind("<Button-1>", lambda e, p=path: os.startfile(p))

                    # Right-click: upload to Discord
                    link.bind("<Button-3>", lambda e, p=path: self.discord.upload_to_discord(p))
                    

                else:
                    missing_label = tk.Label(history_window, text=f"(Missing) {path}", fg="gray")
                    missing_label.pack(anchor="w", padx=10, pady=2)

        except Exception as e:
            messagebox.showerror("Error", f"Could not load history: {e}")
            
        # After writing to it:
        with open(history_path_file, 'r+', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > 100:
                f.seek(0)
                f.writelines(lines[-100:])
                f.truncate()

    def export_history(self):
        history_path_file = os.path.join(LIVE_FOLDER, "history_paths.txt")
        if not os.path.exists(history_path_file):
            messagebox.showinfo("Export", "No history to export.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")],
            title="Save History As"
        )
        if save_path:
            try:
                shutil.copy2(history_path_file, save_path)
                messagebox.showinfo("Export", f"History exported to:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export history: {e}")

    def send_last_channel_to_discord(self):
        history_path_file = os.path.join(LIVE_FOLDER, "history_paths.txt")
        if not os.path.exists(history_path_file):
            return  # No history to send

        try:
            with open(history_path_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            if len(lines) < 2:
                return  # Not enough history to go back one

            last_video_path = lines[-2].strip()  # <-- second-to-last entry
            if os.path.exists(last_video_path):
                self.discord.upload_to_discord(last_video_path)

        except Exception:
            pass

    def upload_with_retry(file_path, retries=3):
        for attempt in range(retries):
            response = ... # your upload code here
            if response.status_code in (200, 204):
                print("Uploaded successfully")
                return True
            elif response.status_code == 429:
                retry_after = response.json().get("retry_after", 0)
                print(f"Rate limited, retrying after {retry_after} seconds")
                time.sleep(retry_after)
            else:
                print(f"Upload failed: {response.status_code}")
                break
        return False



    def bad_channel(self):
        if not self.running or not self.last_played_file_path:
            return
        try:
            self.bad_count += 1
            with open(BADNUMBER_FILE, 'w') as f:
                f.write(str(self.bad_count))

            source_path = self.last_played_file_path
            original_filename = os.path.basename(source_path)
            subfolder_name = os.path.basename(os.path.dirname(source_path))
            bad_folder = os.path.join(self.folder_path, "bad", subfolder_name)
            os.makedirs(bad_folder, exist_ok=True)
            dest_path = os.path.join(bad_folder, original_filename)

            if not os.path.exists(dest_path):
                shutil.move(source_path, dest_path)

            for subfolder, files in self.all_files.items():
                if original_filename in files:
                    files.remove(original_filename)
                    break

            self.used_files.discard(original_filename)
            self.current_file = None
            self.current_file_path = None
            self.last_played_file_path = None

            self.change_event.set()
            time.sleep(5)

            with open(BAD_FILE, 'w') as f:
                f.write("0")
            self.bad_processing = False

        except Exception as e:
            print(f"Error moving bad file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("500x500")  # <-- width x height in pixels
    app = RandomMP4Mover(root)
    root.mainloop()
