#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AC's NX2 Emulator 0.1.1.2 - Horizon OS Edition
"""

import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

BG = "#0a0a0a"
PANEL = "#1f1f1f"
ACCENT = "#00d0ff"
TEXT = "#e0e0e0"
FPS = 60
FRAME_MS = 1000 // FPS
SCALE = 3
SCREEN_W = 320 * SCALE
SCREEN_H = 180 * SCALE


class ACNX2Assembler:
    def assemble(self, source: str) -> bytes:
        program = bytearray()
        for line in source.splitlines():
            line = line.strip().split(";")[0].strip()
            if not line: continue
            parts = line.replace(",", " ").split()
            mnem = parts[0].upper()

            if mnem == "NOP": program += bytes([0x00, 0, 0, 0])
            elif mnem == "MOV": program += bytes([0x01, int(parts[1][1:])&0xF, 0, int(parts[2])&0xFF])
            elif mnem == "ADD": program += bytes([0x02, int(parts[1][1:])&0xF, 0, int(parts[2])&0xFF])
            elif mnem == "SUB": program += bytes([0x03, int(parts[1][1:])&0xF, 0, int(parts[2])&0xFF])
            elif mnem == "RECT": program += bytes([0x07, int(parts[1][1:])&0xF, int(parts[2][1:])&0xF, int(parts[3])&0xFF])
            elif mnem == "JOYCON": program += bytes([0x10, 0, 0, 0])
            elif mnem == "DOCK": program += bytes([0x20, 0, 0, 0])
            elif mnem == "HORIZON": program += bytes([0x30, 0, 0, 0])  # Horizon OS boot
            elif mnem == "HALT": program += bytes([0xFF, 0, 0, 0])
        return bytes(program)


class ACNX2VM:
    def __init__(self):
        self.x = 120
        self.y = 60
        self.halted = False
        self.program = b""
        self.pc = 0
        self.mode = "HANDHELD"
        self.dirty = True
        self.horizon_booted = False

    def load(self, bytecode: bytes):
        self.program = bytecode
        self.pc = 0
        self.halted = False
        self.dirty = True
        self.horizon_booted = False

    def step(self):
        if self.halted or not self.program or self.pc >= len(self.program):
            self.halted = True
            return False

        opcode = self.program[self.pc]
        self.pc += 4

        if opcode == 0x01:   # MOV
            self.x = self.program[self.pc-1] * 2
        elif opcode == 0x02: # ADD
            self.x = (self.x + self.program[self.pc-1]) % 280
        elif opcode == 0x03: # SUB
            self.x = max(0, self.x - self.program[self.pc-1])
        elif opcode == 0x07: # RECT
            self.x = self.program[self.pc-3] * 18
            self.y = self.program[self.pc-2] * 18
        elif opcode == 0x10: # JOYCON
            self.x = (self.x + 12) % 280
        elif opcode == 0x20: # DOCK
            self.mode = "DOCK"
        elif opcode == 0x30: # HORIZON OS
            self.horizon_booted = True
        elif opcode == 0xFF:
            self.halted = True

        self.dirty = True
        return True


class ScreenCanvas:
    def __init__(self, canvas: tk.Canvas, scale=SCALE):
        self.canvas = canvas
        self.scale = scale
        self._dock = None
        self._horizon = None
        s = scale
        # Background
        canvas.create_rectangle(0, 0, SCREEN_W, SCREEN_H, fill="#000000", tags="bg")
        self.sprite = canvas.create_rectangle(0, 0, 60*s, 50*s, fill=ACCENT, outline="#ffffff", width=6, tags="sprite")
        self.dock_frame = canvas.create_rectangle(20, 10, SCREEN_W-20, SCREEN_H-10, outline=ACCENT, width=22, state="hidden")
        self.dock_text = canvas.create_text(SCREEN_W//2, 40, text="HORIZON OS - DOCKED", fill="#00ffcc", font=("Consolas", 14, "bold"), state="hidden")

    def sync(self, vm: ACNX2VM):
        s = self.scale
        # Update sprite
        x1 = vm.x * s
        y1 = vm.y * s
        self.canvas.coords(self.sprite, x1, y1, x1 + 60*s, y1 + 50*s)

        # Dock + Horizon
        if vm.mode == "DOCK":
            self.canvas.itemconfig(self.dock_frame, state="normal")
            self.canvas.itemconfig(self.dock_text, state="normal")
        else:
            self.canvas.itemconfig(self.dock_frame, state="hidden")
            self.canvas.itemconfig(self.dock_text, state="hidden")


class ACNXEMU:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ac's nx2 emu 0.1.1.2")
        self.root.configure(bg=BG)
        self.root.geometry("1380x820")

        self.vm = ACNX2VM()
        self.assembler = ACNX2Assembler()
        self.running = False
        self._frame_loop()

        self._build_ui()
        self.screen = ScreenCanvas(self.canvas)
        self.render(force=True)

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg="#003366", height=60)
        top.pack(fill="x")
        tk.Label(top, text="AC's NX2 Emulator 0.1.1.2 - Horizon OS", bg="#003366", fg="white", font=("Consolas", 18, "bold")).pack(pady=12)

        tb = tk.Frame(self.root, bg=PANEL, height=50)
        tb.pack(fill="x", padx=12, pady=8)

        ttk.Button(tb, text="▶ Run", command=self.toggle_run).pack(side="left", padx=6)
        ttk.Button(tb, text="⏹ Stop", command=self.stop).pack(side="left", padx=6)
        ttk.Button(tb, text="Step", command=self.step).pack(side="left", padx=6)
        ttk.Button(tb, text="Load .nx2", command=self.load).pack(side="left", padx=6)
        ttk.Button(tb, text="Assemble", command=self.assemble).pack(side="left", padx=6)
        ttk.Button(tb, text="Toggle Dock", command=self.toggle_mode).pack(side="left", padx=6)

        main = tk.PanedWindow(self.root, orient="horizontal", bg=BG)
        main.pack(fill="both", expand=True, padx=12, pady=8)

        # Editor
        left = tk.Frame(main, bg=PANEL)
        main.add(left, width=520)
        tk.Label(left, text="Horizon OS Assembly", bg=PANEL, fg=ACCENT, font=("Consolas", 12, "bold")).pack(anchor="w", padx=15, pady=8)
        self.editor = scrolledtext.ScrolledText(left, bg="#111111", fg=TEXT, font=("Consolas", 11))
        self.editor.pack(fill="both", expand=True, padx=15, pady=5)
        self.editor.insert("1.0", """; Horizon OS Example
MOV R0, 80
MOV R1, 50
RECT R0, R1, 60
JOYCON
DOCK
HORIZON
HALT
""")

        # Screen
        right = tk.Frame(main, bg=BG)
        main.add(right)
        tk.Label(right, text="NX2 Screen (Horizon OS)", bg=BG, fg=ACCENT, font=("Consolas", 13, "bold")).pack(anchor="w", padx=15, pady=8)
        self.canvas = tk.Canvas(right, width=SCREEN_W, height=SCREEN_H, bg="#000000", highlightthickness=14, highlightbackground=ACCENT)
        self.canvas.pack(pady=20)

        self.status = tk.Label(self.root, text="Horizon OS Ready", bg=PANEL, fg=TEXT, anchor="w", padx=15)
        self.status.pack(fill="x", side="bottom")

    def load(self):
        path = filedialog.askopenfilename(filetypes=[("NX2", "*.nx2 *.txt")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", code)
            self.assemble()

    def assemble(self):
        code = self.editor.get("1.0", "end").strip()
        try:
            bytecode = self.assembler.assemble(code)
            self.vm.load(bytecode)
            self.status.config(text=f"Horizon OS booted • {len(bytecode)} bytes")
            self.render(force=True)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def toggle_run(self):
        self.running = not self.running
        self.status.config(text="RUNNING - Horizon OS" if self.running else "PAUSED")

    def stop(self):
        self.running = False
        self.status.config(text="Stopped")

    def step(self):
        self.vm.step()
        self.render(force=True)

    def toggle_mode(self):
        self.vm.mode = "DOCK" if self.vm.mode == "HANDHELD" else "HANDHELD"
        self.render(force=True)

    def render(self, force=False):
        if force or self.vm.dirty:
            self.screen.sync(self.vm)
            self.vm.dirty = False

    def _frame_loop(self):
        if self.running:
            for _ in range(8):
                self.vm.step()
            self.render()
        self.root.after(FRAME_MS, self._frame_loop)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ACNXEMU().run()