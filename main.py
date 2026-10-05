import asyncio
import os
import random
import sys
import threading
import discord
from dotenv import load_dotenv
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import subprocess
from rich.console import Console
from rich.text import Text

load_dotenv()
console = Console()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'red_moon_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

intents = discord.Intents.default()
intents.members = True  # Useful for bot token
client = None

RED = "\033[91m"
DARK_RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

# Global Variables
bot_loop = None
bot_ready = False
selected_guild = None
selected_channels = []
amount = 100
gap = 0.1
running = False
active_task = None
discord_thread = None

# Terminal Inputs
name = input(f"{BOLD}{GREEN}👤 Enters victim name{RESET}: ")
attacker = input(f"{BOLD}{RED}☠ Enters attacker name{RESET}: ")
num = int(input(f"{YELLOW}⏱ Enter Amount of mentions{RESET}: "))

MESSAGES_LIST = [
    f"## ☠️💀🦴💀☠🦴Shut the f**ck up {name}",
    f"## ☠💀🦴💀☠️🦴you get f**ck by {attacker}",
    f"## ☠️️💀🦴💀☠️🦴Good morning! with {attacker} revenge",
    f"## ☠️💀🦴💀☠🦴f*ck you scammer {name}",
    "## ☠️💀🦴💀☠️🦴What's up gooners!",
]

def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return console.width

LARGE_BANNER = r"""
███████╗███████╗██╗     ███████╗    ██████╗ ██████╗ ████████╗
██╔════╝██╔════╝██║     ██╔════╝    ██╔══██╗██╔══██╗╚══██╔══╝
███████╗█████╗  ██║     █████╗      ██████╔╝██║  ██║   ██║   
╚════██║██╔══╝  ██║     ██╔══╝      ██╔══██╗██║  ██║   ██║   
███████║███████╗███████╗██║         ██████╔╝╚██████╔╝   ██║   
╚══════╝╚══════╝╚══════╝╚═╝         ╚═════╝  ╚═════╝    ╚═╝   
""".strip("\n")

SMALL_BANNER = r"""
██████╗ ███████╗██╗   ██╗
██╔══██╗██╔════╝██║   ██║
██║  ██║█████╗  ██║   ██║
██║  ██║██╔══╝  ██║   ██║
██████╔╝███████╗╚██████╔╝
╚═════╝ ╚══════╝ ╚═════╝ 
""".strip("\n")

def print_responsive_banner():
    width = get_terminal_width()
    banner = SMALL_BANNER if width < 60 else LARGE_BANNER
    banner_lines = banner.split("\n")
    max_banner_len = max(len(l) for l in banner_lines)
    separator = "=" * min(width, max_banner_len)

    console.print(separator, style="bold green")
    gradient = Text(banner)
    total_lines = len(banner_lines)
    current_idx = 0

    for i, line_str in enumerate(banner_lines):
        line_len = len(line_str)
        ratio = i / max(total_lines - 1, 1)
        r = 255
        g = int(40 + 140 * ratio)
        b = 0
        gradient.stylize(f"rgb({r},{g},{b})", current_idx, current_idx + line_len)
        current_idx += line_len + 1

    console.print(gradient)
    console.print(separator, style="bold green")

print_responsive_banner()

shit = rf"""## `SHUT THE FUCK UP YOU FUCKED BY {attacker}'s `"""

def log_to_web(msg, status_type="info"):
    socketio.emit("bot_log", {"message": msg, "type": status_type})

def update_status(status_str):
    socketio.emit("status_change", {"status": status_str})

last_tagged = set()

def get_rand3(guild):
    global last_tagged
    try:
        members = [m for m in guild.members if not m.bot]
        if not members:
            return ""
        available = [m for m in members if m.id not in last_tagged]
        if len(available) < num:
            available = members
            last_tagged.clear()
        picked = random.sample(available, min(num, len(available)))
        last_tagged = {m.id for m in picked}
        return " ".join([m.mention for m in picked])
    except Exception:
        return ""

async def run_single_channel(channel, total_amount):
    for i in range(1, total_amount + 1):
        if not running:
            break
        random_msg = random.choice(MESSAGES_LIST)
        rand3person = get_rand3(channel.guild)

        try:
            content = f"{rand3person}\n## [{i}/{total_amount}] {random_msg}\n{shit}" if rand3person else f"## [{i}/{total_amount}] {random_msg}\n{shit}"
            await channel.send(content)
            log_to_web(
                f"[+] Sent [{i}/{total_amount}] in #{channel.name}: \"{random_msg}\"",
                "success"
            )
        except Exception as e:
            log_to_web(
                f"[⚠ SKIPPED] Failed in #{channel.name}: {e}",
                "error"
            )
            break

        if i < total_amount and running:
            await asyncio.sleep(gap)

async def run_all_channels():
    global running, selected_channels, amount

    if not selected_channels:
        log_to_web("⚔ No channels selected! Save configuration first.", "error")
        running = False
        update_status("STOPPED ⏱")
        return

    target_channels = []
    for ch in selected_channels:
        try:
            perms = ch.permissions_for(ch.guild.me)
            if perms.send_messages:
                target_channels.append(ch)
            else:
                log_to_web(f"[⚠ SKIPPED] #{ch.name} (No Send Permission)", "error")
        except Exception:
            continue

    if not target_channels:
        log_to_web("⚔ No accessible channels found with send permissions!", "error")
        running = False
        update_status("-$ STOPPED ")
        return

    log_to_web(
        f" Starting messaging process across {len(target_channels)} channels...",
        "success"
    )
    update_status("-$ RUNNING ⬆")

    tasks = [run_single_channel(ch, amount) for ch in target_channels]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    running = False
    log_to_web(" Process completed or stopped.", "info")
    update_status("-$ STOPPED ⏱")

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>☠DEV MONARCHXY☠</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        :root {
            --bg-color: #080203;
            --card-bg: #120507;
            --primary-red: #ff0033;
            --dark-red: #80001a;
            --neon-glow: #ff1a40;
            --text-color: #e0e0e0;
            --success-color: #00ff66;
            --error-color: #ff3333;
        }
        * { box-sizing: border-box; }
        body {
            background-color: var(--bg-color);
            background-image: url('YOUR_MAIN_BACKGROUND_IMAGE_URL');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: var(--text-color);
            font-family: 'Courier New', Courier, monospace;
            margin: 0;
            padding: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .header { text-align: center; margin-bottom: 15px; width: 100%; }
        .header h1 {
            color: var(--primary-red);
            font-size: 1.8rem;
            text-shadow: 0 0 15px var(--neon-glow);
            margin: 0;
        }
        .dashboard {
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
            width: 100%;
            max-width: 1100px;
        }
        @media (min-width: 768px) {
            .header h1 { font-size: 2.5rem; }
            .dashboard { grid-template-columns: 1fr 1fr; }
        }
        .panel {
            background: rgba(18, 5, 7, 0.85);
            border: 2px solid var(--dark-red);
            box-shadow: 0 0 15px rgba(255, 0, 51, 0.2);
            border-radius: 8px;
            padding: 15px;
            backdrop-filter: blur(5px);
        }
        .panel h2 {
            color: var(--primary-red);
            border-bottom: 1px solid var(--dark-red);
            padding-bottom: 8px;
            margin-top: 0;
            font-size: 1.2rem;
        }
        .input-group { margin-bottom: 12px; }
        label { display: block; margin-bottom: 5px; color: #ff99a8; font-size: 0.9rem; }
        input[type="text"], input[type="password"], input[type="number"], select {
            width: 100%;
            padding: 10px;
            background: #000;
            border: 1px solid var(--dark-red);
            color: #fff;
            border-radius: 4px;
            font-family: inherit;
            font-size: 0.9rem;
        }
        .btn-group { display: flex; gap: 10px; margin-top: 15px; }
        button {
            flex: 1;
            padding: 12px;
            font-weight: bold;
            cursor: pointer;
            border: none;
            border-radius: 4px;
            font-family: inherit;
            transition: 0.2s;
            font-size: 0.95rem;
        }
        .btn-login { background: var(--primary-red); color: white; width: 100%; margin-top: 5px; }
        .btn-login:hover { background: #ff3355; box-shadow: 0 0 10px var(--neon-glow); }
        .btn-setup { background: var(--dark-red); color: white; width: 100%; }
        .btn-setup:hover { background: var(--primary-red); box-shadow: 0 0 10px var(--neon-glow); }
        .btn-start { background: #008033; color: white; }
        .btn-start:hover { background: var(--success-color); color: black; box-shadow: 0 0 10px var(--success-color); }
        .btn-stop { background: #800000; color: white; }
        .btn-stop:hover { background: #ff0000; box-shadow: 0 0 10px #ff0000; }
        .terminal-screen {
            background-color: #030102;
            background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('YOUR_TERMINAL_BACKGROUND_IMAGE_URL');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            border: 1px solid var(--primary-red);
            height: 320px;
            overflow-y: auto;
            padding: 10px;
            font-size: 0.85rem;
            border-radius: 4px;
            box-shadow: inset 0 0 10px rgba(255, 0, 51, 0.3);
        }
        .log-item { margin-bottom: 6px; word-break: break-word; }
        .log-success { color: var(--success-color) !important; font-weight: bold; }
        .log-error { color: var(--error-color) !important; font-weight: bold; }
        .log-info { color: #00ccff; }
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85rem;
            background: #200005;
            border: 1px solid var(--primary-red);
            color: var(--primary-red);
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>☠ DEV MONARCHXY ☠</h1>
        <p style="color: #666; font-size: 0.8rem;">Mobile & Web UI Interface</p>
    </div>
    <div class="dashboard">
        <div class="panel">
            <h2>🔑 ACCOUNT AUTHENTICATION</h2>
            <div class="input-group">
                <label>Token Type:</label>
                <select id="token_type">
                    <option value="user">User Token (Selfbot Account)</option>
                    <option value="bot">Bot Token (Official Bot Account)</option>
                </select>
            </div>
            <div class="input-group">
                <label>Discord Token:</label>
                <input type="password" id="discord_token" placeholder="Enter User or Bot Token">
            </div>
            <button class="btn-login" onclick="startBotLogin()">⚡ LOGIN & RUN BOT</button>
            <hr style="border-color: var(--dark-red); margin: 15px 0;">

            <h2>⚙ CONFIGURATION</h2>
            <div class="input-group">
                <label>Server (Guild) ID:</label>
                <input type="text" id="guild_id" placeholder="Enter Guild ID">
            </div>
            <div class="input-group">
                <label>Channel Target Mode:</label>
                <select id="channel_mode" onchange="toggleChannelInput()">
                    <option value="2">ALL Text Channels (Auto)</option>
                    <option value="1">Specific Channels (Manual IDs)</option>
                </select>
            </div>
            <div class="input-group" id="specific_channels_div" style="display: none;">
                <label>Specific Channel IDs (Space Separated):</label>
                <input type="text" id="channel_ids" placeholder="101 102 103">
            </div>
            <div class="input-group">
                <label>Message Amount (1-50000):</label>
                <input type="number" id="amount" value="5" min="1" max="50000">
            </div>
            <button class="btn-setup" onclick="saveConfig()">☑ SAVE & LOAD CHANNELS</button>
            <hr style="border-color: var(--dark-red); margin: 15px 0;">
            <h2> CONTROLS</h2>
            <p>STATUS: <span id="status-display" class="status-badge">-$ STOPPED ⏱</span></p>
            <div class="btn-group">
                <button class="btn-start" onclick="sendCommand('start')">▶ START</button>
                <button class="btn-stop" onclick="sendCommand('stop')">🛑 STOP</button>
            </div>
        </div>
        <div class="panel">
            <h2>-$ LIVE EXECUTION</h2>
            <div class="terminal-screen" id="terminal-log">
                <div class="log-item log-info">-$ [☠] Dashboard initialized. Select type and enter token to login...</div>
            </div>
        </div>
    </div>
    <script>
        const socket = io();
        function toggleChannelInput() {
            const mode = document.getElementById('channel_mode').value;
            document.getElementById('specific_channels_div').style.display = (mode === '1') ? 'block' : 'none';
        }
        function startBotLogin() {
            const token = document.getElementById('discord_token').value.trim();
            const token_type = document.getElementById('token_type').value;
            if(!token) {
                alert("-$ ☠ Please enter a valid Token!");
                return;
            }
            socket.emit('login_token', { token: token, token_type: token_type });
        }
        function saveConfig() {
            const guild_id = document.getElementById('guild_id').value.trim();
            const mode = document.getElementById('channel_mode').value;
            const channel_ids = document.getElementById('channel_ids').value.trim();
            const amount = document.getElementById('amount').value;
            if(!guild_id) {
                alert("-$ ☠Please enter a valid Guild ID!");
                return;
            }
            socket.emit('save_config', {
                guild_id: guild_id,
                mode: mode,
                channel_ids: channel_ids,
                amount: amount
            });
        }
        function sendCommand(cmd) {
            socket.emit('control_command', { command: cmd });
        }
        socket.on('bot_log', function(data) {
            const term = document.getElementById('terminal-log');
            const item = document.createElement('div');
            item.className = 'log-item log-' + data.type;
            item.innerText = data.message;
            term.appendChild(item);
            term.scrollTop = term.scrollHeight;
        });
        socket.on('status_change', function(data) {
            document.getElementById('status-display').innerText = data.status;
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

# Save original static_login function at global level
ORIGINAL_STATIC_LOGIN = discord.http.HTTPClient.static_login

@socketio.on("login_token")
def handle_token_login(data):
    global client, bot_ready, discord_thread
    token = data.get("token", "").strip()
    token_type = data.get("token_type", "user")

    if not token:
        log_to_web("-$ ⚠ Invalid Token provided!", "error")
        return

    if bot_ready:
        log_to_web("-$ ⚠ Account already logged in!", "error")
        return

    # User Token vs Bot Token setup
    if token_type == "user":
        # User account selfbot monkey patch
        discord.http.HTTPClient.static_login = lambda self, token: setattr(self, 'token', token)
        log_to_web("-$ [⚡] Initializing User Account (Selfbot)...", "info")
    else:
        # Restore original login function for Official Bot
        discord.http.HTTPClient.static_login = ORIGINAL_STATIC_LOGIN
        log_to_web("-$ [⭕] Initializing Official Bot Account...", "info")

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        global bot_ready, bot_loop
        bot_loop = asyncio.get_running_loop()
        bot_ready = True
        account_kind = "User Account" if token_type == "user" else "Bot Account"
        print(f"Logged in as {account_kind}: {client.user}")
        log_to_web(f"-$ [☠] Logged in successfully as {account_kind}: {client.user}", "success")

    def run_discord():
        try:
            client.run(token)
        except Exception as e:
            log_to_web(f"-$ ⚠ Login failed: {e}", "error")
            print(f"Login failed: {e}")

    discord_thread = threading.Thread(target=run_discord, daemon=True)
    discord_thread.start()

@socketio.on("save_config")
def handle_save_config(data):
    global amount
    try:
        guild_id = int(data["guild_id"])
        mode = data["mode"]
        amount = int(data["amount"])

        if bot_ready and bot_loop:
            asyncio.run_coroutine_threadsafe(
                process_config(guild_id, mode, data.get("channel_ids", "")), bot_loop
            )
        else:
            log_to_web("-$ ⚔ Account is not logged in yet. Please enter token and click Login first.", "error")
    except Exception as e:
        log_to_web(f"-$ ⚠ Config processing error: {e}", "error")

async def process_config(guild_id, mode, channel_ids_str):
    global selected_guild, selected_channels
    selected_guild = client.get_guild(guild_id)
    if not selected_guild:
        log_to_web("-$ ⚠ Server not found! Make sure the account is in this server.", "error")
        return

    log_to_web(f"-$ ✔ Server Selected: {selected_guild.name}", "success")
    selected_channels = []

    if mode == "1":
        c_ids = channel_ids_str.split()
        for cid in c_ids:
            try:
                ch = selected_guild.get_channel(int(cid))
                if ch and isinstance(ch, discord.TextChannel):
                    selected_channels.append(ch)
            except Exception:
                continue
    else:
        for ch in selected_guild.text_channels:
            try:
                if ch.permissions_for(selected_guild.me).send_messages:
                    selected_channels.append(ch)
            except Exception:
                continue

    log_to_web(f"-$ ✔ Total {len(selected_channels)} channels successfully configured!", "success")

@socketio.on("control_command")
def handle_control(data):
    global running, active_task
    cmd = data["command"]

    if cmd == "start":
        if running:
            log_to_web("⚠ Process is already running!", "error")
        elif not selected_channels:
            log_to_web("-$⚔ No channels configured! Enter Guild ID and click SAVE & LOAD first.", "error")
        elif bot_ready and bot_loop:
            running = True
            active_task = asyncio.run_coroutine_threadsafe(
                run_all_channels(), bot_loop
            )
        else:
            log_to_web("-$ ⚔ Account is not logged in yet.", "error")
    elif cmd == "stop":
        running = False
        update_status("-$ STOPPED 🔴")
        log_to_web("-$ 🛑 Process stopped successfully!", "error")

if __name__ == "__main__":
    print(f"🚀{YELLOW} Localhost Web Dashboard running on port 5000{RESET}")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
