#!/usr/bin/env python3
"""
Gemini's GB Emulator
A Tkinter frontend natively integrating the 'mewgb' Cython Gameboy emulator backend.
Includes a thread-safe rendering pipeline using PIL to display the framebuffer.
"""

import os
import time
import threading
import queue
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Import Pillow for fast RGB array rendering
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ==========================================
# MewGB Cython Backend Integration
# ==========================================
try:
    import mewgb
    BACKEND_STATUS = "Active (Hardware Accelerated)"
except ImportError:
    BACKEND_STATUS = "Mock Mode (mewgb not installed)"
    
    # Fallback dummy implementation of the mewgb Cython backend
    class MockMewGBEmulator:
        def __init__(self, rom_path):
            self.rom_path = rom_path
            self.is_running = False
            
            # Gameboy Resolution
            self.width = 160
            self.height = 144
            
            # 3 bytes per pixel (RGB)
            self.framebuffer = bytearray([15, 56, 15] * (self.width * self.height))
            
            # Classic Gameboy color palette
            self.palette = [
                [15, 56, 15],     # Darkest green
                [48, 98, 48],     # Dark green
                [139, 172, 15],   # Light green
                [155, 188, 15]    # Lightest green
            ]
            
        def load(self):
            if not os.path.exists(self.rom_path):
                raise FileNotFoundError(f"ROM file not found: {self.rom_path}")
            self.is_running = True
            
        def tick(self):
            """Simulates processing a single frame (~60 FPS) and generating pixels"""
            if not self.is_running:
                return False
            time.sleep(0.016) # Simulate work for 1 frame
            
            # Mock rendering: Generate a retro chunky screen effect
            for _ in range(40):
                rx = random.randint(0, self.width - 8)
                ry = random.randint(0, self.height - 8)
                rc = random.choice(self.palette)
                for y in range(8):
                    for x in range(8):
                        idx = ((ry + y) * self.width + (rx + x)) * 3
                        self.framebuffer[idx:idx+3] = rc
                        
            return True
            
        def get_framebuffer(self):
            """Returns the current raw RGB frame bytes."""
            return self.framebuffer
            
        def stop(self):
            self.is_running = False

    # Create a mock module structure
    class MockMewGBModule:
        Emulator = MockMewGBEmulator
        
    mewgb = MockMewGBModule()


# ==========================================
# Tkinter GUI Application
# ==========================================
class GeminiGBApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.rom_path = ""
        self.emulator = None
        self.emu_thread = None
        self.is_playing = False
        self.frame_queue = queue.Queue(maxsize=3)
        self.current_tk_image = None
        
        # Window Configuration
        self.title("Gemini's GB Emulator (mewgb backend)")
        self.geometry("600x530")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)
        
        self._setup_styles()
        self._build_ui()
        
        if not HAS_PIL:
            messagebox.showwarning("Missing Dependency", 
                                   "Pillow (PIL) is required for hardware rendering.\n"
                                   "Please install it using: pip install pillow\n"
                                   "The game won't render frames without it.")
        
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground="#89b4fa")
        style.configure("Status.TLabel", font=("Segoe UI", 8, "italic"), foreground="#a6adc8")
        
        style.configure("TButton", 
                        background="#313244", 
                        foreground="#cdd6f4", 
                        font=("Segoe UI", 10, "bold"),
                        padding=6)
        style.map("TButton", background=[("active", "#89b4fa"), ("disabled", "#45475a")])
        
        style.configure("TFrame", background="#1e1e2e")

    def _build_ui(self):
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", pady=15)
        
        ttk.Label(header_frame, text="✨ GEMINI'S GB EMULATOR ✨", style="Header.TLabel").pack()
        ttk.Label(header_frame, text=f"Backend: mewgb | Status: {BACKEND_STATUS}", style="Status.TLabel").pack()
        
        # Display Screen (320x288 is exactly double Gameboy's 160x144 resolution)
        self.screen_canvas = tk.Canvas(self, width=320, height=288, bg="#11111b", highlightthickness=2, highlightbackground="#89b4fa")
        self.screen_canvas.pack(pady=10)
        
        self.screen_text = self.screen_canvas.create_text(160, 144, text="NO ROM LOADED", fill="#f38ba8", font=("Courier", 14, "bold"))
        self.screen_image_item = self.screen_canvas.create_image(160, 144, image=None, state="hidden")
        
        # Main Control Area
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="both", expand=True, padx=30, pady=10)
        
        # ROM Selection
        rom_frame = ttk.Frame(control_frame)
        rom_frame.pack(fill="x", pady=(0, 15))
        
        self.rom_var = tk.StringVar(value="Select a Gameboy ROM...")
        rom_entry = ttk.Entry(rom_frame, textvariable=self.rom_var, state="readonly")
        rom_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Button(rom_frame, text="Browse", command=self.load_rom).pack(side="right")
        
        # Launch/Stop Button
        self.action_btn = ttk.Button(self, text="▶ BOOT CONSOLE", command=self.toggle_emulation, state="disabled")
        self.action_btn.pack(fill="x", padx=100, pady=(0, 20), ipady=5)

    def load_rom(self):
        if self.is_playing:
            messagebox.showwarning("Warning", "Please stop the current game before loading a new one.")
            return

        filetypes = [
            ("Gameboy ROMs", "*.gb *.gbc"),
            ("All Files", "*.*")
        ]
        path = filedialog.askopenfilename(title="Select Game ROM", filetypes=filetypes)
        if path:
            self.rom_path = path
            self.rom_var.set(os.path.basename(path))
            self.action_btn.configure(state="normal")
            
            self.screen_canvas.itemconfig(self.screen_image_item, state="hidden")
            self.screen_canvas.itemconfig(self.screen_text, text="READY TO BOOT", fill="#a6e3a1", state="normal")

    def toggle_emulation(self):
        if not self.is_playing:
            self._start_emulation()
        else:
            self._stop_emulation()

    def _start_emulation(self):
        if not self.rom_path:
            return
            
        try:
            # Empty out old frames from the queue
            while not self.frame_queue.empty():
                self.frame_queue.get()
                
            self.emulator = mewgb.Emulator(self.rom_path)
            self.emulator.load()
            
            self.is_playing = True
            self.action_btn.configure(text="■ POWER OFF CONSOLE")
            
            self.screen_canvas.itemconfig(self.screen_text, state="hidden")
            self.screen_canvas.itemconfig(self.screen_image_item, state="normal")
            
            # Start Backend Thread
            self.emu_thread = threading.Thread(target=self._emulation_loop, daemon=True)
            self.emu_thread.start()
            
            # Start Frontend Rendering Poll
            if HAS_PIL:
                self._render_loop()
            
        except Exception as e:
            messagebox.showerror("Backend Error", f"mewgb failed to load ROM:\n{str(e)}")
            self._stop_emulation()

    def _emulation_loop(self):
        """Background thread running the Cython mewgb tick loop and fetching frames."""
        while self.is_playing and self.emulator:
            try:
                running = self.emulator.tick()
                if not running:
                    break
                    
                # Fetch RGB frame bytes and add to queue for rendering
                frame_bytes = self.emulator.get_framebuffer()
                if not self.frame_queue.full():
                    self.frame_queue.put(bytes(frame_bytes))
                    
            except Exception as e:
                print(f"Emulation error: {e}")
                break
                
        # Safely trigger a stop in the main thread once done
        self.after(0, self._stop_emulation)

    def _render_loop(self):
        """Main Tkinter thread loop that pulls frames and draws them."""
        if not self.is_playing:
            return
            
        try:
            # Attempt to grab the latest frame from the emulation thread
            frame_data = self.frame_queue.get_nowait()
            
            # Convert raw RGB bytes into a PIL image
            img = Image.frombytes("RGB", (160, 144), frame_data)
            
            # Scale it up x2 using nearest-neighbor scaling for that crisp pixel art look
            img_scaled = img.resize((320, 288), Image.Resampling.NEAREST)
            
            # Keep a reference to prevent Tkinter from garbage collecting the image
            self.current_tk_image = ImageTk.PhotoImage(image=img_scaled)
            
            # Update canvas image item
            self.screen_canvas.itemconfig(self.screen_image_item, image=self.current_tk_image)
            
        except queue.Empty:
            # No frame was ready yet, we'll try again next tick
            pass
            
        # Schedule the next render check in ~16ms (~60 FPS)
        self.after(16, self._render_loop)

    def _stop_emulation(self):
        self.is_playing = False
        if self.emulator:
            self.emulator.stop()
            self.emulator = None
            
        self.action_btn.configure(text="▶ BOOT CONSOLE")
        self.screen_canvas.itemconfig(self.screen_image_item, state="hidden")
        self.screen_canvas.itemconfig(self.screen_text, text="READY TO BOOT", fill="#a6e3a1", state="normal")

if __name__ == "__main__":
    app = GeminiGBApp()
    app.mainloop()
