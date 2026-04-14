#!/usr/bin/env python3
"""
ChatGPT + Gemini's Gameboy Emulator 0.1 (STABLE FINAL)

Fixes:
- safe PyBoy frame handling
- thread-safe rendering
- no duplicate windows
- stable stop/start
"""

import sys
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

import logging
logging.getLogger("pyboy").setLevel(logging.CRITICAL)

try:
    from pyboy import PyBoy
    HAS_PYBOY = True
except:
    HAS_PYBOY = False


# =========================================================
# INSTALL WIZARD
# =========================================================

def install_pyboy(callback):
    def run():
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyboy"])
            callback(True)
        except:
            callback(False)

    threading.Thread(target=run, daemon=True).start()


# =========================================================
# EMULATOR CORE
# =========================================================

class Emulator:
    def __init__(self, rom):
        self.rom = rom
        self.pyboy = None
        self.stop_flag = False

    def load(self):
        from pyboy import PyBoy

        self.pyboy = PyBoy(
            self.rom,
            window="null",
            sound_emulated=False
        )

        self.stop_flag = False

    def step(self):
        if self.stop_flag or not self.pyboy:
            return False
        self.pyboy.tick()
        return True

    def frame(self):
        if not self.pyboy:
            return None

        img = self.pyboy.screen.image

        # 🔥 SAFETY: ensure PIL Image
        if hasattr(img, "resize"):
            return img
        return None

    def stop(self):
        self.stop_flag = True
        if self.pyboy:
            try:
                self.pyboy.stop()
            except:
                pass
            self.pyboy = None


# =========================================================
# APP
# =========================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ChatGPT + Gemini's Gameboy Emulator 0.1")
        self.geometry("640x520")
        self.configure(bg="#0b1020")
        self.resizable(False, False)

        self.rom = ""
        self.emu = None
        self.running = False
        self.after_id = None

        self.latest_frame = None
        self.tk_img = None

        self._ui()

    def _ui(self):

        header = tk.Frame(self, bg="#0b1020")
        header.pack(pady=10)

        tk.Label(
            header,
            text="ChatGPT + Gemini",
            fg="#4ea1ff",
            bg="#0b1020",
            font=("Arial", 18, "bold")
        ).pack()

        tk.Label(
            header,
            text="Gameboy Emulator 0.1",
            fg="#7aa7d9",
            bg="#0b1020"
        ).pack()

        self.canvas = tk.Canvas(self, width=320, height=288, bg="black")
        self.canvas.pack(pady=10)

        self.img_id = self.canvas.create_image(160, 144)

        bar = tk.Frame(self, bg="#0b1020")
        bar.pack(pady=10)

        style = {
            "bg": "#0d2a52",
            "fg": "#4ea1ff",
            "activebackground": "#1a4b8c",
            "activeforeground": "white",
            "bd": 0,
            "width": 14
        }

        tk.Button(bar, text="Load ROM", command=self.load_rom, **style).grid(row=0, column=0, padx=5)
        tk.Button(bar, text="Start", command=self.start, **style).grid(row=0, column=1, padx=5)
        tk.Button(bar, text="Stop", command=self.stop, **style).grid(row=0, column=2, padx=5)

        tk.Button(
            self,
            text="Install PyBoy",
            command=self.install,
            bg="#1e6bff",
            fg="white",
            activebackground="#4ea1ff",
            activeforeground="black",
            bd=0,
            font=("Arial", 12, "bold"),
            width=22
        ).pack(pady=8)

        self.status = tk.Label(self, text="Ready", fg="#7aa7d9", bg="#0b1020")
        self.status.pack()

    # -----------------------------------------------------

    def install(self):
        self.status.config(text="Installing PyBoy...")

        def done(ok):
            self.status.config(text="Ready" if ok else "Install failed")
            if ok:
                messagebox.showinfo("Success", "PyBoy installed")

        install_pyboy(done)

    def load_rom(self):
        self.rom = filedialog.askopenfilename()

    def start(self):
        if not self.rom:
            messagebox.showerror("Error", "Load ROM first")
            return

        self.stop()

        self.emu = Emulator(self.rom)
        self.emu.load()

        self.running = True

        threading.Thread(target=self.loop, daemon=True).start()
        self.render()

    def stop(self):
        self.running = False

        if self.after_id:
            try:
                self.after_cancel(self.after_id)
            except:
                pass
            self.after_id = None

        if self.emu:
            self.emu.stop()
            self.emu = None

        self.latest_frame = None

    # -----------------------------------------------------

    def loop(self):
        while self.running and self.emu and not self.emu.stop_flag:
            self.emu.step()
            self.latest_frame = self.emu.frame()
            time.sleep(1/60)

    def render(self):
        if not self.running:
            return

        if self.latest_frame is not None:
            img = self.latest_frame.resize((320, 288))
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.itemconfig(self.img_id, image=self.tk_img)

        self.after_id = self.after(16, self.render)


# =========================================================

if __name__ == "__main__":
    App().mainloop()
