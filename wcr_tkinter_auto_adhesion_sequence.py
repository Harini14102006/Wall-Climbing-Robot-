"""
WALL-CLIMBING ROBOT (WCR) — Tkinter visual simulator
---------------------------------------------------
Includes:
- Side profile: horizontal floor, smooth curved transition, vertical wall
- Top view: square chassis, 4 corner wheels, central rotating suction fan,
  and two side-mounted electromagnetic adhesion modules
- Console: drive direction, speed, wheel steering, fan ON/OFF,
  magnetic modules deploy/retract, simulated battery voltage/level,
  emergency stop, reset, and event log

This is a VISUAL SIMULATOR ONLY. It does not operate physical motors,
fans, electromagnets, or read real battery voltage.
Run: python wcr_tkinter_simulator.py
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import math


class WCRSimulator:
    BG = "#0b1117"
    PANEL = "#141f29"
    PANEL_2 = "#1c2b37"
    GRID = "#233642"
    TEXT = "#eaf3f7"
    MUTED = "#8da4b2"
    CYAN = "#35d8ff"
    GREEN = "#57e3a0"
    ORANGE = "#ffb454"
    RED = "#ff5c70"
    METAL = "#b6c7d1"
    DARK = "#304652"

    def __init__(self, root):
        self.root = root
        root.title("WCR | Wall-Climbing Robot Control Simulator")
        root.geometry("1280x820")
        root.minsize(1000, 700)
        root.configure(bg=self.BG)

        # Simulation state
        self.position = 0.0          # 0 = floor, 1 = upper wall
        self.drive_command = "STOP"
        self.moving = False
        self.steering_angle = tk.IntVar(value=0)  # -45 to +45 degrees
        self.speed = tk.IntVar(value=35)
        self.fan_on = tk.BooleanVar(value=False)
        # Fan output is a simulated percentage (0..100), allowing gradual ramp-down.
        self.fan_power = 0.0
        # Magnet extension: 0.0 = fully retracted, 1.0 = fully deployed.
        self.magnet_extension = 0.0
        self.magnets_deployed = tk.BooleanVar(value=False)
        self.adhesion_transition = "IDLE"  # IDLE, CLIMB, STOPPING_ON_WALL
        self.emergency = False
        self.battery_voltage = 12.4    # simulated voltage
        self.fan_phase = 0.0
        self.log_lines = []

        self._build_ui()
        self._refresh_all()
        self._tick()

    # --------------------------- UI ---------------------------------
    def _build_ui(self):
        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill="x", padx=16, pady=(12, 8))
        tk.Label(header, text="WCR  /  WALL-CLIMBING ROBOT",
                 bg=self.BG, fg=self.CYAN,
                 font=("Segoe UI", 19, "bold")).pack(side="left")
        tk.Label(header, text="DIGITAL CONSOLE  •  SIMULATION ONLY",
                 bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(side="right")

        main = tk.Frame(self.root, bg=self.BG)
        main.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        left = tk.Frame(main, bg=self.PANEL, highlightbackground=self.GRID, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        right = tk.Frame(main, bg=self.PANEL, width=340,
                         highlightbackground=self.GRID, highlightthickness=1)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(left, text="01  SIDE PROFILE  /  FLOOR → CURVE → VERTICAL WALL",
                 bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.side_canvas = tk.Canvas(left, bg="#080e13", height=340, highlightthickness=0)
        self.side_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Label(left, text="02  TOP VIEW  /  FAN + ELECTROMAGNETIC ADHESION",
                 bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(2, 4))
        self.top_canvas = tk.Canvas(left, bg="#080e13", height=310, highlightthickness=0)
        self.top_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Console header and status
        tk.Label(right, text="CONTROL CONSOLE", bg=self.PANEL, fg=self.CYAN,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=15, pady=(13, 2))
        tk.Label(right, text="Auto adhesion • drive • battery monitor",
                 bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=15, pady=(0, 10))

        self.status_label = tk.Label(right, text="READY", bg="#213a43", fg=self.GREEN,
                                     font=("Consolas", 11, "bold"), padx=8, pady=8)
        self.status_label.pack(fill="x", padx=13, pady=(0, 10))

        # Movement controls
        tk.Label(right, text="MOVEMENT", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(2, 4))
        pad = tk.Frame(right, bg=self.PANEL)
        pad.pack(fill="x", padx=13)
        self._button(pad, "▲  FORWARD / CLIMB", lambda: self.drive("FORWARD"),
                     bg="#17657a").grid(row=0, column=0, columnspan=3, sticky="ew", pady=2)
        self._button(pad, "◀ LEFT", lambda: self.drive("LEFT")).grid(row=1, column=0, sticky="ew", padx=(0, 3), pady=2)
        self._button(pad, "■ STOP", lambda: self.drive("STOP"), bg="#703642").grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        self._button(pad, "RIGHT ▶", lambda: self.drive("RIGHT")).grid(row=1, column=2, sticky="ew", padx=(3, 0), pady=2)
        self._button(pad, "▼ REVERSE", lambda: self.drive("REVERSE")).grid(row=2, column=0, columnspan=3, sticky="ew", pady=2)
        for col in range(3):
            pad.grid_columnconfigure(col, weight=1)

        # Speed slider
        self._section_label(right, "DRIVE SPEED")
        speed_line = tk.Frame(right, bg=self.PANEL)
        speed_line.pack(fill="x", padx=14)
        self.speed_text = tk.Label(speed_line, text="35%", bg=self.PANEL, fg=self.CYAN,
                                   font=("Consolas", 10, "bold"))
        self.speed_text.pack(side="right")
        tk.Scale(right, from_=0, to=100, orient="horizontal", variable=self.speed,
                 command=self._speed_changed, bg=self.PANEL, fg=self.TEXT,
                 troughcolor="#29434f", highlightthickness=0, showvalue=False,
                 activebackground=self.CYAN, bd=0).pack(fill="x", padx=12)

        # Steering controls
        self._section_label(right, "WHEEL DIRECTION / STEERING")
        self.steer_text = tk.Label(right, text="0°  •  STRAIGHT", bg=self.PANEL, fg=self.CYAN,
                                   font=("Consolas", 10, "bold"))
        self.steer_text.pack(anchor="w", padx=15)
        steer_row = tk.Frame(right, bg=self.PANEL)
        steer_row.pack(fill="x", padx=13, pady=(3, 2))
        self._button(steer_row, "↶ −15°", lambda: self.set_steering(self.steering_angle.get() - 15)).pack(side="left", expand=True, fill="x", padx=(0, 3))
        self._button(steer_row, "CENTER", lambda: self.set_steering(0), bg="#17657a").pack(side="left", expand=True, fill="x", padx=3)
        self._button(steer_row, "+15° ↷", lambda: self.set_steering(self.steering_angle.get() + 15)).pack(side="left", expand=True, fill="x", padx=(3, 0))
        tk.Scale(right, from_=-45, to=45, orient="horizontal", variable=self.steering_angle,
                 command=self._steering_changed, bg=self.PANEL, fg=self.TEXT,
                 troughcolor="#29434f", highlightthickness=0, showvalue=False,
                 activebackground=self.CYAN, bd=0).pack(fill="x", padx=12)

        # Fan and electromagnet
        self._section_label(right, "ADHESION SYSTEMS")
        self.fan_button = self._button(right, "SUCTION FAN: OFF", self.toggle_fan, bg="#703642")
        self.fan_button.pack(fill="x", padx=13, pady=3)
        self.magnet_button = self._button(right, "MAGNETS: RETRACTED", self.toggle_magnets, bg="#304652")
        self.magnet_button.pack(fill="x", padx=13, pady=3)

        # Battery panel
        self._section_label(right, "BATTERY VOLTAGE  •  SIMULATED")
        battery_row = tk.Frame(right, bg=self.PANEL)
        battery_row.pack(fill="x", padx=15, pady=(2, 1))
        self.voltage_label = tk.Label(battery_row, text="12.4 V", bg=self.PANEL, fg=self.GREEN,
                                      font=("Consolas", 15, "bold"))
        self.voltage_label.pack(side="left")
        self.battery_pct = tk.Label(battery_row, text="100%", bg=self.PANEL, fg=self.MUTED,
                                    font=("Consolas", 10, "bold"))
        self.battery_pct.pack(side="right")
        self.battery_canvas = tk.Canvas(right, height=19, bg=self.PANEL, highlightthickness=0)
        self.battery_canvas.pack(fill="x", padx=15, pady=(2, 2))
        tk.Label(right, text="12.6 V full  •  10.5 V low (example 3S pack)",
                 bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=15)

        # Safety controls
        self._button(right, "EMERGENCY STOP", self.emergency_stop, bg="#a52f42",
                     font=("Segoe UI", 10, "bold")).pack(fill="x", padx=13, pady=(10, 3))
        self._button(right, "RESET E-STOP", self.reset, bg=self.DARK).pack(fill="x", padx=13, pady=3)

        self._section_label(right, "EVENT LOG")
        self.log_box = tk.Text(right, height=4, bg="#080e13", fg="#9fe7c4",
                               insertbackground=self.TEXT, relief="flat",
                               font=("Consolas", 8), wrap="word", state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=13, pady=(2, 10))

        tk.Label(self.root,
                 text="Keys: W/↑ forward  •  S/↓ reverse  •  A/← left  •  D/→ right  •  Space stop  •  adhesion is automatic",
                 bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)).pack(fill="x", padx=18, pady=(0, 7))

        self.root.bind("<KeyPress>", self._key_press)
        self._log("Simulator started. Hardware is not connected.")

    def _button(self, parent, text, command, bg=None, font=("Segoe UI", 9, "bold")):
        return tk.Button(parent, text=text, command=command, bg=bg or self.DARK,
                         fg="white", activebackground=self.CYAN, activeforeground="#061018",
                         relief="flat", bd=0, font=font, padx=5, pady=7, cursor="hand2")

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(9, 1))

    # ------------------------- Controls ------------------------------
    def _log(self, message):
        self.log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.log_lines = self.log_lines[-30:]
        if hasattr(self, "log_box"):
            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.insert("end", "\n".join(self.log_lines[-6:]))
            self.log_box.configure(state="disabled")

    def drive(self, command):
        if self.emergency:
            self.status_label.configure(text="E-STOP ACTIVE — RESET FIRST", fg=self.RED)
            return

        if command == "LEFT":
            self.set_steering(max(-45, self.steering_angle.get() - 15))
            self.status_label.configure(text="STEERING LEFT", fg=self.CYAN)
            self._log("Steering left")
            return
        if command == "RIGHT":
            self.set_steering(min(45, self.steering_angle.get() + 15))
            self.status_label.configure(text="STEERING RIGHT", fg=self.CYAN)
            self._log("Steering right")
            return

        if command == "STOP":
            was_moving = self.moving
            self.moving = False
            self.drive_command = "STOP"
            if self.position >= 0.70:
                # Stop on the wall: transfer support from suction to magnets.
                self.adhesion_transition = "STOPPING_ON_WALL"
                self.status_label.configure(text="SECURING WALL HOLD", fg=self.ORANGE)
                self._log("Wall stop: ramping fan down while magnets deploy")
            elif self.position >= 0.34:
                # Inclined transition: keep fan available and deploy magnets for a safe hold.
                self.adhesion_transition = "STOPPING_ON_WALL"
                self.status_label.configure(text="SECURING INCLINE", fg=self.ORANGE)
                self._log("Incline stop: engaging magnetic backup")
            else:
                # On horizontal floor, no adhesion system is needed.
                self.adhesion_transition = "IDLE"
                self.fan_power = 0.0
                self.fan_on.set(False)
                self.magnet_extension = 0.0
                self.magnets_deployed.set(False)
                self.status_label.configure(text="STOPPED ON FLOOR", fg=self.GREEN)
                self._log("Stopped on horizontal floor; fan and magnets OFF")
            self._update_adhesion_buttons()
            self._refresh_all()
            return

        # Starting horizontal travel requires no adhesion.
        if self.position < 0.34:
            self.adhesion_transition = "IDLE"
            self.fan_power = 0.0
            self.fan_on.set(False)
            self.magnet_extension = 0.0
            self.magnets_deployed.set(False)
        # Starting or moving onto the incline/wall automatically starts the fan.
        if command == "FORWARD" and self.position >= 0.28:
            self.adhesion_transition = "CLIMB"
            self.fan_on.set(True)
            self._log("Incline/climb detected: suction fan starting automatically")
        elif command == "REVERSE" and self.position >= 0.34:
            self.adhesion_transition = "CLIMB"
            self.fan_on.set(True)
            self._log("Incline/wall reverse: suction fan enabled")

        self.drive_command = command
        self.moving = command in ("FORWARD", "REVERSE")
        self.status_label.configure(text=command, fg=self.GREEN)
        self._update_adhesion_buttons()
        self._log(f"Drive command: {command}")
        self._refresh_all()

    def set_steering(self, angle):
        self.steering_angle.set(max(-45, min(45, int(angle))))
        self._update_steering_label()
        self._refresh_all()

    def _steering_changed(self, _value):
        self._update_steering_label()
        self._refresh_all()

    def _update_steering_label(self):
        angle = self.steering_angle.get()
        text = "STRAIGHT" if angle == 0 else ("LEFT" if angle < 0 else "RIGHT")
        self.steer_text.configure(text=f"{angle:+d}°  •  {text}")

    def _speed_changed(self, _value):
        self.speed_text.configure(text=f"{self.speed.get()}%")

    def toggle_fan(self):
        # Manual fan override is allowed only while the robot is on the horizontal floor.
        # During climbing/holding, the automatic adhesion state machine has priority.
        if self.position >= 0.34:
            self._log("Fan control is automatic on incline/wall; use STOP to secure the robot")
            return
        self.fan_on.set(not self.fan_on.get())
        self.fan_power = 100.0 if self.fan_on.get() else 0.0
        self._update_adhesion_buttons()
        self._log(f"Floor fan manually set {'ON' if self.fan_on.get() else 'OFF'}")
        self._refresh_all()

    def toggle_magnets(self):
        # Magnets are automatically controlled for the transition sequence.
        self._log("Magnetic deployment is automatic and linked to robot position")
        self._update_adhesion_buttons()
        self._refresh_all()

    def _update_adhesion_buttons(self):
        if self.fan_power > 1:
            fan_text = f"SUCTION FAN: ON ({int(self.fan_power)}%)"
            fan_bg = "#1e684f"
        elif self.fan_on.get():
            fan_text = "SUCTION FAN: STARTING"
            fan_bg = "#8a6728"
        else:
            fan_text = "SUCTION FAN: OFF"
            fan_bg = "#703642"
        self.fan_button.configure(text=fan_text, bg=fan_bg)

        if self.magnet_extension >= 0.99:
            magnet_text = "MAGNETS: FULLY DEPLOYED"
        elif self.magnet_extension > 0.01:
            magnet_text = f"MAGNETS: DEPLOYING ({int(self.magnet_extension * 100)}%)"
        else:
            magnet_text = "MAGNETS: RETRACTED"
        self.magnet_button.configure(
            text=magnet_text,
            bg="#1e684f" if self.magnet_extension >= 0.99 else "#304652"
        )

    def emergency_stop(self):
        self.emergency = True
        self.moving = False
        self.drive_command = "STOP"
        if self.position >= 0.34:
            self.adhesion_transition = "STOPPING_ON_WALL"
            self.status_label.configure(text="E-STOP: SECURING ROBOT", fg=self.RED)
            self._log("E-stop on incline/wall: transfer to magnetic hold")
        else:
            self.adhesion_transition = "IDLE"
            self.fan_power = 0.0
            self.fan_on.set(False)
            self.magnet_extension = 0.0
            self.magnets_deployed.set(False)
            self.status_label.configure(text="EMERGENCY STOP", fg=self.RED)
            self._log("E-stop on floor: drive and adhesion OFF")
        self._refresh_all()

    def reset(self):
        self.emergency = False
        self.moving = False
        self.drive_command = "STOP"
        if self.position >= 0.34:
            self.adhesion_transition = "STOPPING_ON_WALL"
            self.status_label.configure(text="WALL HOLD ACTIVE", fg=self.GREEN)
        else:
            self.adhesion_transition = "IDLE"
            self.status_label.configure(text="READY", fg=self.GREEN)
        self._log("Emergency stop reset; safety hold preserved")
        self._refresh_all()

    def _key_press(self, event):
        key = event.keysym.lower()
        mapping = {"w": "FORWARD", "up": "FORWARD",
                   "s": "REVERSE", "down": "REVERSE",
                   "a": "LEFT", "left": "LEFT",
                   "d": "RIGHT", "right": "RIGHT",
                   "space": "STOP"}
        if key in mapping:
            self.drive(mapping[key])
        elif key == "f":
            self.toggle_fan()
        elif key == "m":
            self.toggle_magnets()

    # ------------------------- Drawing -------------------------------
    def _grid(self, canvas, width, height):
        for x in range(0, width, 25):
            canvas.create_line(x, 0, x, height, fill="#14232b")
        for y in range(0, height, 25):
            canvas.create_line(0, y, width, y, fill="#14232b")

    def _refresh_all(self):
        self._draw_side_view()
        self._draw_top_view()
        self._draw_battery()

    def _draw_side_view(self):
        c = self.side_canvas
        c.delete("all")
        w = max(c.winfo_width(), 550)
        h = max(c.winfo_height(), 300)
        self._grid(c, w, h)

        # Floor at the bottom and wall at the right, with a broad smooth transition.
        floor_y = h - 36
        wall_x = w - 64
        c.create_line(20, floor_y, wall_x - 145, floor_y, fill="#8296a2", width=3)
        c.create_line(wall_x, 20, wall_x, floor_y, fill="#8296a2", width=4)
        c.create_text(25, floor_y + 15, text="FLOOR", fill=self.MUTED, anchor="w",
                      font=("Consolas", 8))
        c.create_text(wall_x + 8, 24, text="WALL", fill=self.MUTED, anchor="nw",
                      font=("Consolas", 8))

        # Curved floor-to-wall profile
        curve_pts = []
        curve_start_x = wall_x - 145
        curve_end_y = floor_y - min(180, h * 0.58)
        for i in range(41):
            t = i / 40
            # smoothstep bend
            x = curve_start_x + 145 * t
            y = floor_y - (floor_y - curve_end_y) * (t * t * (3 - 2 * t))
            curve_pts.extend((x, y))
        c.create_line(*curve_pts, fill=self.CYAN, width=3, smooth=True)

        # Robot travels along the drawn floor/curve/wall path.
        p = self.position
        if p < 0.34:
            t = p / 0.34
            x = 55 + t * (curve_start_x - 55)
            y = floor_y - 15
            angle = 0
            self._set_mode("FLOOR")
        elif p < 0.70:
            t = (p - 0.34) / 0.36
            x = curve_start_x + 145 * t
            y = floor_y - (floor_y - curve_end_y) * (t * t * (3 - 2 * t)) - 15
            angle = -math.radians(90 * (t * t * (3 - 2 * t)))
            self._set_mode("TRANSITION")
        else:
            t = (p - 0.70) / 0.30
            x = wall_x - 17
            y = curve_end_y - t * max(0, curve_end_y - 45)
            angle = -math.pi / 2
            self._set_mode("WALL")

        # Draw robot chassis transformed by orientation.
        ca, sa = math.cos(angle), math.sin(angle)
        def tr(lx, ly):
            return x + lx * ca - ly * sa, y + lx * sa + ly * ca

        chassis = [tr(-32, -10), tr(32, -10), tr(32, 10), tr(-32, 10)]
        c.create_polygon(chassis, fill="#284d5b", outline=self.CYAN, width=2)

        # Side wheels
        for wx in (-23, 23):
            xx, yy = tr(wx, 12)
            c.create_oval(xx - 7, yy - 7, xx + 7, yy + 7,
                          fill="#05090c", outline=self.ORANGE, width=2)
            a = math.radians(self.steering_angle.get()) + angle
            c.create_line(xx - 4 * math.cos(a), yy - 4 * math.sin(a),
                          xx + 4 * math.cos(a), yy + 4 * math.sin(a),
                          fill=self.TEXT, width=2)

        # Suction fan and magnet modules represented on the side silhouette.
        fx, fy = tr(0, 0)
        c.create_oval(fx - 9, fy - 6, fx + 9, fy + 6,
                      fill="#1d654d" if self.fan_power > 1 else "#6e3540",
                      outline=self.GREEN if self.fan_power > 1 else self.RED, width=2)
        c.create_text(fx, fy, text="F" if self.fan_power > 1 else "X",
                      fill="white", font=("Consolas", 8, "bold"))
        # Magnetic contact pads along the wall-facing side
        pad_color = self.GREEN if self.magnets_deployed.get() else self.MUTED
        for local_y in (-7, 7):
            px, py = tr(30, local_y)
            c.create_rectangle(px - 3, py - 5, px + 3, py + 5,
                               fill=pad_color, outline=pad_color)

        c.create_text(12, 12,
                      text=f"MODE: {self._mode_name()}   |   PATH: {int(self.position * 100)}%",
                      fill=self.TEXT, anchor="nw", font=("Consolas", 9, "bold"))
        if self.emergency:
            c.create_text(w / 2, 40, text="EMERGENCY STOP", fill=self.RED,
                          font=("Segoe UI", 15, "bold"))

    def _set_mode(self, mode):
        self.mode = mode

    def _mode_name(self):
        return getattr(self, "mode", "FLOOR")

    def _draw_top_view(self):
        c = self.top_canvas
        c.delete("all")
        w = max(c.winfo_width(), 550)
        h = max(c.winfo_height(), 250)
        self._grid(c, w, h)

        cx, cy = w * 0.50, h * 0.53
        side = min(150, h * 0.56, w * 0.32)
        half = side / 2

        # chassis square
        c.create_rectangle(cx - half, cy - half, cx + half, cy + half,
                           fill="#284d5b", outline=self.CYAN, width=3)
        c.create_text(cx, cy - half + 17, text="WCR TOP VIEW", fill=self.TEXT,
                      font=("Consolas", 8, "bold"))

        # Four wheels at chassis corners. Top pair are steerable.
        wheel_specs = [
            (cx - half - 9, cy - half + 5, True),
            (cx + half + 9, cy - half + 5, True),
            (cx - half - 9, cy + half - 5, False),
            (cx + half + 9, cy + half - 5, False),
        ]
        a = math.radians(self.steering_angle.get())
        for wx, wy, steerable in wheel_specs:
            angle = a if steerable else 0
            rw, rh = 13, 22
            corners = []
            for px, py in [(-rw/2, -rh/2), (rw/2, -rh/2),
                           (rw/2, rh/2), (-rw/2, rh/2)]:
                corners.append((wx + px * math.cos(angle) - py * math.sin(angle),
                                wy + px * math.sin(angle) + py * math.cos(angle)))
            c.create_polygon(corners, fill="#05090c",
                             outline=self.ORANGE if steerable else self.METAL, width=2)
            if steerable:
                c.create_line(wx, wy, wx + 16 * math.sin(angle),
                              wy - 16 * math.cos(angle), fill=self.CYAN,
                              width=2, arrow="last")

        # Two electromagnetic modules left and right of central fan.
        deployed = self.magnet_extension > 0.01
        mag_color = self.GREEN if deployed else "#6d7d86"
        for sign in (-1, 1):
            base_x = cx + sign * half * 0.66
            # Move the magnetic pads outward as they deploy.
            mx = base_x + sign * (self.magnet_extension * 12)
            pad_width = 10
            c.create_rectangle(mx - pad_width, cy - 30, mx + pad_width, cy + 30,
                               fill=mag_color if deployed else "#26343d",
                               outline=mag_color, width=2)
            c.create_text(mx, cy, text="M", fill="#061018" if deployed else self.TEXT,
                          font=("Consolas", 10, "bold"))
            if deployed:
                c.create_line(mx, cy + 34, mx, cy + 43, fill=self.GREEN, width=2, arrow="last")
            elif self.fan_on.get():
                c.create_line(mx, cy + 43, mx, cy + 34, fill=self.MUTED, width=2, arrow="last")

        # Central fan housing and rotating blades
        fan_r = min(33, side * 0.22)
        fan_active = self.fan_power > 1
        c.create_oval(cx - fan_r, cy - fan_r, cx + fan_r, cy + fan_r,
                      fill="#132630", outline=self.GREEN if fan_active else self.RED, width=3)
        c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=self.METAL, outline=self.TEXT)
        for blade in range(3):
            theta = self.fan_phase + blade * 2 * math.pi / 3
            x1 = cx + 5 * math.cos(theta)
            y1 = cy + 5 * math.sin(theta)
            x2 = cx + fan_r * 0.83 * math.cos(theta + 0.32)
            y2 = cy + fan_r * 0.83 * math.sin(theta + 0.32)
            c.create_line(x1, y1, x2, y2,
                          fill=self.CYAN if fan_active else self.RED, width=max(1, int(5 * max(0.25, self.fan_power / 100.0))),
                          capstyle=tk.ROUND)
        if self.magnet_extension >= 0.99:
            magnet_state = "DEPLOYED"
        elif self.magnet_extension > 0.01:
            magnet_state = f"DEPLOYING {int(self.magnet_extension * 100)}%"
        else:
            magnet_state = "RETRACTED"
        c.create_text(cx, cy + half + 30,
                      text=f"FAN {int(self.fan_power)}%     MAGNETS {magnet_state}",
                      fill=self.GREEN if self.fan_power > 1 else self.ORANGE,
                      font=("Consolas", 8, "bold"))
        c.create_text(12, 12, text=f"STEERING ANGLE: {self.steering_angle.get():+d}°",
                      fill=self.TEXT, anchor="nw", font=("Consolas", 9, "bold"))

    def _draw_battery(self):
        # Example mapping for a 3-cell lithium-ion pack: 10.5 V low to 12.6 V full.
        pct = max(0, min(100, (self.battery_voltage - 10.5) / (12.6 - 10.5) * 100))
        color = self.GREEN if pct > 35 else self.ORANGE if pct > 15 else self.RED
        self.voltage_label.configure(text=f"{self.battery_voltage:.1f} V", fg=color)
        self.battery_pct.configure(text=f"{pct:.0f}%")
        self.battery_canvas.delete("all")
        width = max(self.battery_canvas.winfo_width(), 100)
        self.battery_canvas.create_rectangle(2, 3, width - 7, 16, outline=self.MUTED, width=1)
        self.battery_canvas.create_rectangle(width - 6, 7, width - 2, 12, fill=self.MUTED, outline=self.MUTED)
        fill_width = max(0, (width - 11) * pct / 100)
        self.battery_canvas.create_rectangle(4, 5, 4 + fill_width, 14, fill=color, outline=color)

    # ------------------------- Animation -----------------------------
    def _tick(self):
        # Movement along the floor -> incline -> wall profile.
        if self.moving and not self.emergency:
            step = (self.speed.get() / 100.0) * 0.0025
            if self.drive_command == "FORWARD":
                previous_position = self.position
                self.position = min(1.0, self.position + step)
                # Fan starts automatically as the robot approaches the incline.
                if previous_position < 0.34 <= self.position or self.position >= 0.28:
                    if self.position >= 0.28:
                        self.adhesion_transition = "CLIMB"
                        self.fan_on.set(True)
                if self.position >= 1.0:
                    self.moving = False
                    self.drive_command = "STOP"
                    self.adhesion_transition = "STOPPING_ON_WALL"
                    self.status_label.configure(text="WALL POSITION — SECURING", fg=self.GREEN)
                    self._log("Reached wall position; securing with magnets")
            elif self.drive_command == "REVERSE":
                self.position = max(0.0, self.position - step)
                if self.position < 0.34:
                    # Back on horizontal floor: fan and magnets are not needed.
                    self.adhesion_transition = "IDLE"
                    self.fan_on.set(False)
                    self.fan_power = 0.0
                    self.magnet_extension = 0.0
                    self.magnets_deployed.set(False)
                else:
                    self.adhesion_transition = "CLIMB"
                    self.fan_on.set(True)
                if self.position <= 0.0:
                    self.moving = False
                    self.drive_command = "STOP"
                    self.status_label.configure(text="FLOOR POSITION", fg=self.GREEN)
                    self._log("Returned to horizontal floor; adhesion systems OFF")

        # Automatic adhesion sequence:
        # Horizontal: fan OFF, magnets retracted.
        # Incline/wall moving: fan ramps up, magnets retract gradually.
        # Stopped on incline/wall: magnets deploy while fan ramps down;
        # fan reaches OFF only after magnets are fully deployed.
        if self.position < 0.28 and not self.moving:
            self.adhesion_transition = "IDLE"
            self.fan_power = max(0.0, self.fan_power - 8.0)
            self.fan_on.set(self.fan_power > 1.0)
            self.magnet_extension = max(0.0, self.magnet_extension - 0.08)
        elif self.adhesion_transition == "CLIMB" and self.moving:
            self.fan_power = min(100.0, self.fan_power + 4.0)
            self.fan_on.set(self.fan_power > 1.0)
            self.magnet_extension = max(0.0, self.magnet_extension - 0.025)
        elif self.adhesion_transition == "STOPPING_ON_WALL":
            # Deploy backup magnets immediately into the transition sequence,
            # while suction gradually slows down.
            self.magnet_extension = min(1.0, self.magnet_extension + 0.025)
            if self.magnet_extension >= 0.99:
                self.magnet_extension = 1.0
                self.fan_power = max(0.0, self.fan_power - 8.0)
            else:
                self.fan_power = max(0.0, self.fan_power - 1.8)
            self.fan_on.set(self.fan_power > 1.0)
            if self.magnet_extension >= 1.0 and self.fan_power <= 0.0:
                self.fan_on.set(False)
                self.fan_power = 0.0
                self.magnets_deployed.set(True)
                self.status_label.configure(text="WALL HOLD: MAGNETS LOCKED", fg=self.GREEN)
                self.adhesion_transition = "IDLE"
        else:
            # When stationary on the floor, keep both adhesion systems inactive.
            if self.position < 0.28:
                self.fan_power = 0.0
                self.fan_on.set(False)
                self.magnet_extension = 0.0

        self.magnets_deployed.set(self.magnet_extension >= 0.99)
        if self.fan_power > 1:
            self.fan_phase += 0.08 + (self.fan_power / 100.0) * 0.20

        self._update_adhesion_buttons()
        self._refresh_all()
        self.root.after(50, self._tick)


if __name__ == "__main__":
    root = tk.Tk()
    app = WCRSimulator(root)
    root.mainloop()
