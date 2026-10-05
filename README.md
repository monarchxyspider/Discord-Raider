 

 

 # Discord Raider

A Discord raiding and automation bot featuring a local Flask web dashboard, live SocketIO logging, and dual authentication support (Bot & Selfbot).

---

## Requirements

- Python 3
- Git
- Termux / Linux / macOS / Windows Terminal

---

## Installation

Run these commands in your terminal:

```bash
pkg update && pkg upgrade -y
pkg install python git -y
git clone https://github.com/monarchxyspider/Discord-Raider
cd Discord-Raider
pip install discord.py Flask Flask-SocketIO python-dotenv rich gevent gevent-websocket
