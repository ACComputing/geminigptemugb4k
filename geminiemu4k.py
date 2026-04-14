#!/usr/bin/env python3
"""
Gemini's GB Emulator
A Tkinter frontend natively integrating the 'mewgb' Cython Gameboy emulator backend.
"""

import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ==========================================
# MewGB Cython Backend Integration
# ==========================================
# Attempt to load the real Cython-compiled mewgb backend.
# If it's not installed, we provide a mock implementation for testing the GUI.
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
            
        def load(self):
            if not os.path.exists(self.rom_path):
                raise FileNotFoundError(f"ROM file not found: {self.rom_path}")
            self.is_running = True
            
        def tick(self):
            """Simulates processing a single frame (~60 FPS)"""
            if not self.is_running:
                return False
            time.sleep(0.016) 
            return True
            
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
        
        # Window Configuration
        self.title("Gemini's GB Emulator (mewgb backend)")
        self.geometry("600x500")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)
        
        self._setup_styles()
        self._build_ui()
        
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
        
        # Display Screen (Placeholder for game rendering)
        self.screen_canvas = tk.Canvas(self, width=320, height=288, bg="#11111b", highlightthickness=2, highlightbackground="#89b4fa")
        self.screen_canvas.pack(pady=10)
        self.screen_text = self.screen_canvas.create_text(160, 144, text="NO ROM LOADED", fill="#f38ba8", font=("Courier", 14, "bold"))
        
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
            self.screen_canvas.itemconfig(self.screen_text, text="READY TO BOOT", fill="#a6e3a1")

    def toggle_emulation(self):
        if not self.is_playing:
            self._start_emulation()
        else:
            self._stop_emulation()

    def _start_emulation(self):
        if not self.rom_path:
            return
            
        try:
            # Initialize the Cython mewgb backend
            self.emulator = mewgb.Emulator(self.rom_path)
            self.emulator.load()
            
            self.is_playing = True
            self.action_btn.configure(text="■ POWER OFF CONSOLE")
            self.screen_canvas.itemconfig(self.screen_text, text="[ MEWGB RUNNING ]", fill="#89b4fa")
            
            # Run the emulator in a separate thread so it doesn't freeze the Tkinter GUI
            self.emu_thread = threading.Thread(target=self._emulation_loop, daemon=True)
            self.emu_thread.start()
            
        except Exception as e:
            messagebox.showerror("Backend Error", f"mewgb failed to load ROM:\n{str(e)}")
            self._stop_emulation()

    def _emulation_loop(self):
        """Background thread running the Cython mewgb tick loop."""
        while self.is_playing and self.emulator:
            try:
                # Tell the Cython backend to process the next frame
                running = self.emulator.tick()
                if not running:
                    break
            except Exception as e:
                print(f"Emulation error: {e}")
                break
                
        # Safely update the GUI once the loop ends
        self.after(0, self._stop_emulation)

    def _stop_emulation(self):
        self.is_playing = False
        if self.emulator:
            self.emulator.stop()
            self.emulator = None
            
        self.action_btn.configure(text="▶ BOOT CONSOLE")
        self.screen_canvas.itemconfig(self.screen_text, text="READY TO BOOT", fill="#a6e3a1")

if __name__ == "__main__":
    app = GeminiGBApp()
    app.mainloop()
