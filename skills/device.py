import platform
import os
import sqlite3
import json
import subprocess
import shlex
import time
from typing import Optional

DB_DEFAULT = os.getenv("DB_PATH", "data/assistant.db")
ALLOWLIST_PATH = os.getenv("DEVICE_ALLOWLIST_PATH", "config/device_allowlist.json")
ENABLE_DEVICE_CONTROL = os.getenv("ENABLE_DEVICE_CONTROL", "true").lower() == "true"

class DeviceSkill:
    def __init__(self, db_path=DB_DEFAULT):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()
        self.platform = platform.system().lower()
        self.allowlist = self._load_allowlist()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS device_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_input TEXT, action_json TEXT, confirmed INTEGER DEFAULT 0, executed INTEGER DEFAULT 0, result_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )

    def _load_allowlist(self):
        if not os.path.exists(ALLOWLIST_PATH):
            return {"allowed_scripts": [], "allowed_apps": []}
        try:
            with open(ALLOWLIST_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {"allowed_scripts": [], "allowed_apps": []}

    def plan_action(self, action: dict, user_text: str) -> dict:
        """
        Validate and store a planned device action. Returns a dict with keys:
          - requires_confirmation (bool)
          - pending_id (int) if stored
          - message (str) human message
        """
        if not ENABLE_DEVICE_CONTROL:
            return {"requires_confirmation": False, "message": "Device control is disabled."}

        # Basic validation: action must contain device_action
        device_action = action.get("device_action")
        if not device_action:
            return {"requires_confirmation": False, "message": "No device_action in request."}

        # Determine if action is risky
        risky_actions = {"reboot", "shutdown", "format", "factory_reset", "delete_file"}
        is_risky = device_action in risky_actions

        # Persist planned action
        with self._conn() as c:
            cur = c.execute("INSERT INTO device_actions (user_input, action_json, confirmed, executed) VALUES (?, ?, 0, 0)", (user_text, json.dumps(action)))
            pending_id = cur.lastrowid

        message = f"Planned device action '{device_action}'."
        if is_risky:
            message += " This is a risky action and requires confirmation. Say 'confirm' to proceed."
        else:
            message += " Say 'confirm' to execute or 'cancel' to abort."

        return {"requires_confirmation": is_risky or True, "pending_id": pending_id, "message": message}

    def list_pending(self) -> list:
        with self._conn() as c:
            cur = c.execute("SELECT id, user_input, action_json, confirmed, executed, result_text, created_at FROM device_actions WHERE executed=0")
            rows = cur.fetchall()
            return [{"id": r[0], "user_input": r[1], "action_json": json.loads(r[2]), "confirmed": bool(r[3]), "executed": bool(r[4]), "result_text": r[5], "created_at": r[6]} for r in rows]

    def confirm_and_execute(self, pending_id: int) -> dict:
        with self._conn() as c:
            cur = c.execute("SELECT id, action_json, confirmed, executed FROM device_actions WHERE id=?", (pending_id,))
            row = cur.fetchone()
            if not row:
                return {"ok": False, "message": "Pending action not found."}
            if row[3]:
                return {"ok": False, "message": "Already executed."}
            action = json.loads(row[1])
            # mark confirmed
            c.execute("UPDATE device_actions SET confirmed=1 WHERE id=?", (pending_id,))

        # Execute action (may be platform-specific)
        try:
            result_text = self._execute(action)
            with self._conn() as c:
                c.execute("UPDATE device_actions SET executed=1, result_text=? WHERE id=?", (result_text, pending_id))
            return {"ok": True, "message": result_text}
        except Exception as e:
            with self._conn() as c:
                c.execute("UPDATE device_actions SET executed=1, result_text=? WHERE id=?", (f"error: {e}", pending_id))
            return {"ok": False, "message": f"Execution failed: {e}"}

    def _execute(self, action: dict) -> str:
        da = action.get("device_action")
        args = action.get("args", {}) or {}

        # Map actions
        if da in ("volume_up", "volume_down", "mute_toggle"):
            return self._change_volume(da, args)
        if da in ("media_play_pause", "media_next", "media_prev"):
            return self._media_control(da)
        if da == "open_app":
            return self._open_app(args)
        if da == "run_script":
            return self._run_script(args)
        if da == "take_screenshot":
            return self._take_screenshot(args)
        if da == "reboot":
            return self._reboot(args)
        if da == "shutdown":
            return self._shutdown(args)

        return f"Unknown device action: {da}"

    # Platform-specific implementations
    def _change_volume(self, action: str, args: dict) -> str:
        # delta or absolute level
        try:
            if self.platform == "windows":
                # Try pycaw first
                try:
                    from ctypes import POINTER, cast
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    step = float(args.get("step", 0.05))
                    current = volume.GetMasterVolumeLevelScalar()
                    if action == "volume_up":
                        new = min(1.0, current + step)
                    elif action == "volume_down":
                        new = max(0.0, current - step)
                    else:
                        new = 1.0 - current
                    volume.SetMasterVolumeLevelScalar(new, None)
                    return f"Volume set to {new:.2f}"
                except Exception:
                    # fallback to PowerShell (requires nircmd or other tool)
                    return "Volume control not available on this Windows installation."
            elif self.platform == "linux":
                # Use amixer if present
                step = args.get("step", "5%")
                if action == "volume_up":
                    subprocess.run(shlex.split(f"amixer -D pulse sset Master {step}+"))
                    return "Increased volume."
                elif action == "volume_down":
                    subprocess.run(shlex.split(f"amixer -D pulse sset Master {step}-"))
                    return "Decreased volume."
                else:
                    subprocess.run(shlex.split("amixer -D pulse sset Master toggle"))
                    return "Toggled mute."
            elif self.platform == "darwin":
                return "Mac volume control not implemented in this skill yet."
            else:
                return "Volume control not supported on this platform."
        except Exception as e:
            return f"Error changing volume: {e}"

    def _media_control(self, action: str) -> str:
        try:
            if self.platform == "windows":
                try:
                    import pyautogui
                    if action == "media_play_pause":
                        pyautogui.press('playpause')
                    elif action == "media_next":
                        pyautogui.press('nexttrack')
                    elif action == "media_prev":
                        pyautogui.press('prevtrack')
                    return "Media key sent."
                except Exception:
                    return "Media control not available (pyautogui error)."
            else:
                # Use playerctl for linux
                if action == "media_play_pause":
                    subprocess.run(shlex.split("playerctl play-pause"))
                elif action == "media_next":
                    subprocess.run(shlex.split("playerctl next"))
                elif action == "media_prev":
                    subprocess.run(shlex.split("playerctl previous"))
                return "Media control executed."
        except Exception as e:
            return f"Error controlling media: {e}"

    def _open_app(self, args: dict) -> str:
        name = args.get("name") or args.get("path")
        if not name:
            return "No app name/path provided."
        # Validate against allowlist
        allowed = self.allowlist.get("allowed_apps", [])
        if allowed and name not in allowed:
            return "App not in allowlist. Add it to config/device_allowlist.json to allow."

        try:
            if self.platform == "windows":
                # Use start
                subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
                return f"Opening app {name}"
            elif self.platform == "linux":
                subprocess.Popen([name])
                return f"Opening app {name}"
            else:
                return "Open app not implemented for this platform."
        except Exception as e:
            return f"Failed to open app: {e}"

    def _run_script(self, args: dict) -> str:
        script = args.get("script")
        if not script:
            return "No script provided."
        # Ensure script is inside ./scripts/safe or in allowlist
        safe_dir = os.path.abspath("scripts/safe")
        script_path = os.path.abspath(script)
        if not script_path.startswith(safe_dir):
            return "Script not allowed. Place safe scripts in ./scripts/safe/ and add to allowlist if needed."
        # Run with timeout
        try:
            proc = subprocess.run([script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            return proc.stdout.decode('utf-8', errors='ignore')
        except subprocess.TimeoutExpired:
            return "Script timed out."
        except Exception as e:
            return f"Script error: {e}"

    def _take_screenshot(self, args: dict) -> str:
        if self.platform in ("linux", "darwin"):
            path = args.get("path", "./data/screenshot.png")
            subprocess.run(shlex.split(f"import -window root {shlex.quote(path)}"))
            return f"Screenshot saved to {path}"
        elif self.platform == "windows":
            try:
                from PIL import ImageGrab
                path = args.get("path", "./data/screenshot.png")
                img = ImageGrab.grab()
                os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
                img.save(path)
                return f"Screenshot saved to {path}"
            except Exception as e:
                return f"Screenshot failed: {e}"
        else:
            # Android via ADB
            path = args.get("path", "/sdcard/screen.png")
            try:
                subprocess.run(shlex.split(f"adb shell screencap -p {path}"), timeout=10)
                local_path = args.get("local_path", "./data/screen_device.png")
                os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
                subprocess.run(shlex.split(f"adb pull {path} {local_path}"), timeout=10)
                return f"Screenshot pulled to {local_path}"
            except Exception as e:
                return f"ADB screenshot failed: {e}"

    def _reboot(self, args: dict) -> str:
        # Risky: require confirmation already handled before calling execute
        if self.platform == "windows":
            subprocess.run(shlex.split("shutdown /r /t 0"))
            return "Rebooting Windows now."
        elif self.platform == "linux":
            subprocess.run(shlex.split("sudo reboot"))
            return "Rebooting Linux now."
        else:
            # Android via adb
            try:
                subprocess.run(shlex.split("adb reboot"), timeout=10)
                return "Sent reboot to Android device."
            except Exception as e:
                return f"ADB reboot failed: {e}"

    def _shutdown(self, args: dict) -> str:
        if self.platform == "windows":
            subprocess.run(shlex.split("shutdown /s /t 0"))
            return "Shutting down Windows now."
        elif self.platform == "linux":
            subprocess.run(shlex.split("sudo shutdown now"))
            return "Shutting down Linux now."
        else:
            try:
                subprocess.run(shlex.split("adb shell reboot -p"), timeout=10)
                return "Sent poweroff to Android device."
            except Exception as e:
                return f"ADB poweroff failed: {e}"
