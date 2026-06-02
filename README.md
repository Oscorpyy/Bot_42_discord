# 🤖 42Bot — Discord Campus Tracker

A Discord bot that monitors **42 campus login/logout activity** in real time using the [42 Intra API](https://api.intra.42.fr). It sends live notifications to a Discord channel whenever tracked users log in or out of a workstation, and provides slash commands to quickly look up who's on campus and where they're sitting.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Live tracking** | Polls the 42 Intra API every 60 seconds and detects login/logout events |
| **Discord notifications** | Sends arrival 📥 and departure 📤 messages to a configured channel |
| **Whitelist system** | Only track specific users (configurable globally and per-user) |
| **Blacklist support** | Permanently exclude logins from tracking |
| **Slash commands** | `/where`, `/whereis`, `/whitelist` for quick lookups |
| **Per-user custom whitelist** | Each Discord user can set their own personal watchlist |
| **Auto token refresh** | Automatically refreshes the 42 API OAuth token on 401 responses |
| **Screen session** | Runs in a detached `screen` session via the Makefile for easy management |

---

## 📋 Prerequisites

- **Python** ≥ 3.12
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **screen** — terminal multiplexer (pre-installed on most Linux systems)
- A **Discord bot token** ([Discord Developer Portal](https://discord.com/developers/applications))
- **42 API credentials** — UID and Secret from [42 Intra API settings](https://profile.intra.42.fr/oauth/applications)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/42bot.git
cd 42bot
```

### 2. Configure environment variables

Create a `.env` file at the project root (this file is git-ignored by default):

```env
DISCORD_TOKEN=your_discord_bot_token
INTRA_UID=your_42_api_uid
INTRA_SECRET=your_42_api_secret
CAMPUS_ID=9
LOG_CHANNEL_ID=1234567890123456789
```

#### Environment Variables Reference

| Variable | Description | Default | Required |
|---|---|---|---|
| `DISCORD_TOKEN` | Your Discord bot token | — | ✅ Yes |
| `INTRA_UID` | 42 Intra API application UID | — | ✅ Yes |
| `INTRA_SECRET` | 42 Intra API application secret | — | ✅ Yes |
| `CAMPUS_ID` | Numeric ID of your 42 campus (see table below) | `9` (Lyon) | No |
| `LOG_CHANNEL_ID` | Discord channel ID where login/logout notifications are sent | `1501554049688932452` | No |

#### How to obtain each credential

<details>
<summary><strong>🔑 DISCORD_TOKEN</strong> — Discord bot token</summary>

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name
3. Navigate to **Bot** in the left sidebar
4. Click **"Reset Token"** and copy the generated token
5. Under **Privileged Gateway Intents**, enable:
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**
6. Navigate to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot permissions: `Send Messages`, `Read Message History`
7. Copy the generated URL and open it to invite the bot to your server

</details>

<details>
<summary><strong>🔑 INTRA_UID & INTRA_SECRET</strong> — 42 API credentials</summary>

1. Log in to [42 Intra](https://profile.intra.42.fr/)
2. Go to **Settings → API** or visit [API Applications](https://profile.intra.42.fr/oauth/applications)
3. Click **"Register a new app"**
4. Fill in the required fields (name, redirect URI — you can use `http://localhost`)
5. After creation, copy the **UID** and **Secret** values

> **Note:** These are OAuth2 client credentials. The bot uses the `client_credentials` grant type, so no user login flow is needed.

</details>

<details>
<summary><strong>🔑 LOG_CHANNEL_ID</strong> — Discord channel ID</summary>

1. Open Discord and go to **User Settings → Advanced**
2. Enable **Developer Mode**
3. Right-click the text channel where you want notifications
4. Click **"Copy Channel ID"**
5. Paste the ID as `LOG_CHANNEL_ID` in your `.env`

</details>

<details>
<summary><strong>🔑 CAMPUS_ID</strong> — Your 42 campus identifier</summary>

Find your campus in the table below and use the corresponding **ID** value.  
The default is `9` (Lyon).

</details>

---

### 🏫 42 Campus IDs Reference

| ID | Campus | | ID | Campus | | ID | Campus |
|---:|--------|---|---:|--------|---|---:|--------|
| 1 | Paris | | 26 | Tokyo | | 50 | Kocaeli |
| 9 | Lyon | | 28 | Rio de Janeiro | | 51 | Berlin |
| 12 | Belgium | | 29 | Seoul | | 52 | Florence |
| 13 | Helsinki | | 30 | Rome | | 53 | Vienna |
| 14 | Amsterdam | | 31 | Angoulême | | 55 | Tétouan |
| 16 | Khouribga | | 32 | Yerevan | | 56 | Prague |
| 20 | São Paulo | | 33 | Bangkok | | 57 | London |
| 21 | Benguerir | | 34 | Kuala Lumpur | | 58 | Porto |
| 22 | Madrid | | 35 | Amman | | 59 | Luxembourg |
| 25 | Quebec | | 36 | Adelaide | | 60 | Perpignan |
| | | | 37 | Málaga | | 61 | Belo Horizonte |
| | | | 38 | Lisboa | | 62 | Le Havre |
| | | | 39 | Heilbronn | | 64 | Singapore |
| | | | 40 | Urduliz | | 65 | Antananarivo |
| | | | 41 | Nice | | 67 | Warsaw |
| | | | 43 | Abu Dhabi | | 68 | Luanda |
| | | | 44 | Wolfsburg | | 69 | Gyeongsan |
| | | | 46 | Barcelona | | 70 | Nablus |
| | | | 47 | Lausanne | | 71 | Beirut |
| | | | 48 | Mulhouse | | 72 | Milano |
| | | | 49 | Istanbul | | 73 | Iskandar Puteri |
| | | | | | | 75 | Rabat |
| | | | | | | 76 | Al-Aïn |

### 3. Install dependencies

```bash
make install
```

This runs `uv sync` to create a virtual environment and install all dependencies.

### 4. Run the bot

```bash
make run
```

The bot will start inside a detached `screen` session named `bot42`.

---

## 🛠️ Makefile Commands

| Command | Description |
|---|---|
| `make install` | Install Python dependencies via `uv sync` |
| `make run` | Start the bot in a detached `screen` session |
| `make stop` | Stop the running bot and kill the screen session |
| `make restart` | Stop and then start the bot |
| `make logs` | Attach to the screen session to view live output |
| `make clean` | Remove `.venv` and all `__pycache__` directories |

> **Tip:** To detach from the screen session without stopping the bot, press `Ctrl+A` then `D`.

---

## 💬 Slash Commands

### `/where`

Displays the current location of all users in your personal whitelist (or the global default whitelist if you haven't set one).

```
✅ opernod : e1r3p5
✅ lgoderne : e1r2p8
🪐 zqian : Knowhere
```

- ✅ = currently logged in, with their workstation host
- 🪐 = not currently on campus

### `/whereis <login>`

Look up the location of a specific 42 login.

```
/whereis opernod
→ ✅ opernod : e1r3p5
```

### `/whitelist <logins>`

Set a custom personal whitelist for your Discord account. Provide a comma or space-separated list of logins.

```
/whitelist opernod, lgoderne, zqian
→ ✅ Whitelist updated: lgoderne, opernod, zqian
```

To reset to the global default whitelist, send an empty or invalid list.

> **Note:** All command responses are **ephemeral** — only you can see the reply.

---

## 🏗️ Architecture

```
42bot/
├── main.py          # Bot logic — API client, event loop, slash commands
├── Makefile         # Process management (run/stop/restart via screen)
├── pyproject.toml   # Project metadata and dependencies
├── uv.lock          # Locked dependency versions
├── .env             # Environment variables (not committed)
├── .gitignore       # Ignores .env, .venv, __pycache__
└── README.md        # This file
```

### Core Class: `IntraBot`

The bot is built on top of `discord.ext.commands.Bot` with the following key methods:

| Method | Description |
|---|---|
| `update_intra_token()` | Requests a new OAuth2 client-credentials token from the 42 API |
| `get_active_logins()` | Fetches all active campus locations, filters by blacklist, paginates through all results |
| `check_logs()` | Background task (runs every 60s) — compares current vs. previous logins, sends arrival/departure messages |
| `setup_hook()` | Syncs slash commands and starts the background loop on bot startup |

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| [discord.py](https://discordpy.readthedocs.io/) | ≥ 2.7.1 | Discord API wrapper and bot framework |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | ≥ 1.2.2 | Load environment variables from `.env` |
| [requests](https://docs.python-requests.org/) | ≥ 2.34.2 | HTTP client for 42 Intra API calls |

---

## ⚙️ How It Works

1. **Startup** — The bot connects to Discord and syncs its slash commands. The background task `check_logs` begins.
2. **Polling** — Every 60 seconds, `check_logs` calls `get_active_logins()` in a thread to avoid blocking the async event loop.
3. **Token management** — If the API returns a `401 Unauthorized`, the bot automatically refreshes the OAuth token and retries.
4. **Diffing** — The bot compares the current set of active logins against the previous snapshot:
   - **New logins** (arrived) → 📥 notification
   - **Missing logins** (left) → 📤 notification
5. **Whitelist filtering** — Only users in the global `WHITELIST` (or a user's personal whitelist) trigger notifications.
6. **Slash commands** — Users can query the cached data at any time via `/where`, `/whereis`, or manage their whitelist via `/whitelist`.

---

## 🔒 Security Notes

- The `.env` file containing your tokens is excluded from version control via `.gitignore`.
- **Never** commit your `.env` file or share your API credentials.
- The bot uses **ephemeral messages** for all slash command responses, so sensitive location data is only visible to the requesting user.

---

## 📝 License

This project is part of the 42 school ecosystem. Feel free to use and modify it for your own campus.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

> Made with ❤️ for the 42 community
