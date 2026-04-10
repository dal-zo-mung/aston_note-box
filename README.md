# Telegram Storage Bot
Try the bot by searching for **@Aston3_bot** on Telegram.

A beginner-friendly Telegram bot for saving personal text notes and media references in MongoDB Atlas.

This project is designed as a private storage assistant inside Telegram. Users can store text, photos, videos, audio, voice messages, animations, and documents, then find them later by ID or keyword.

The bot does not use AI chat. It works with clear command-based actions such as `store*`, `search*`, `update*`, and `delete*`.

## Project Overview 🚀

This bot helps you keep personal information inside Telegram in a simple and structured way.

How it works:

1. A user sends a command like `store* my roadmap keyword* roadmap, backend`.
2. The bot validates the message.
3. The bot saves the note or media metadata into MongoDB Atlas.
4. The bot generates simple keywords if the user does not provide them.
5. Later, the user can search by ID or by keyword.
6. The bot only returns that user's own data.

This project is useful for:

- Students saving study notes and files
- Developers saving ideas, roadmaps, and references
- Anyone who wants a lightweight personal repository in Telegram

## Main Features ✨

- Command-only usage for predictable behavior
- Supports text, photo, video, audio, voice, animation, and document messages
- Stores Telegram `file_id` for media instead of downloading files
- Keyword search and note ID search
- Per-user data isolation with `user_id`
- Optional private allowlist using Telegram user IDs
- Docker-ready deployment for Hugging Face Spaces

## Technologies Used 🛠️

### Core Technologies

- Python 3.10+
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for Telegram bot handling
- [MongoDB Atlas](https://www.mongodb.com/atlas) for cloud database storage
- [PyMongo](https://pymongo.readthedocs.io/) for MongoDB access
- [python-dotenv](https://pypi.org/project/python-dotenv/) for reading environment variables from `.env`
- Docker for containerized deployment

### How They Work Together 🔗

- Telegram sends updates to the bot.
- `python-telegram-bot` receives and routes those updates.
- The bot handlers parse commands.
- The service layer validates and prepares data.
- The database layer stores and retrieves records from MongoDB Atlas.
- Docker packages the whole project for deployment on Hugging Face Spaces.

## Project Structure 📁

```text
project/
|-- bot/
|   |-- __init__.py
|   |-- commands.py
|   |-- dependencies.py
|   |-- handlers.py
|   `-- ui.py
|-- config/
|   |-- __init__.py
|   `-- settings.py
|-- db/
|   |-- __init__.py
|   `-- database.py
|-- services/
|   |-- __init__.py
|   `-- note_service.py
|-- storage/
|   `-- logs/
|-- utils/
|   |-- __init__.py
|   |-- keywords.py
|   `-- logger.py
|-- .dockerignore
|-- .env.example
|-- .gitignore
|-- Dockerfile
|-- main.py
|-- README.md
`-- requirements.txt
```

## File and Folder Explanation 📘

### `main.py`

This is the entry point of the project.

It is responsible for:

- loading settings
- configuring logging
- creating the database and service objects
- starting the health check server on port `7860`
- building the Telegram application
- starting Telegram polling

### `bot/`

This folder contains all Telegram bot interaction logic.

#### `bot/commands.py`

Handles slash commands such as:

- `/start`
- `/help`
- `/state`
- `/stored_ids`

It also defines the welcome/help text shown to users.

#### `bot/handlers.py`

Handles regular Telegram messages and command-based storage actions such as:

- `store*`
- `search*`
- `update*`
- `delete*`

It also handles media messages like photos, audio, documents, and videos.

#### `bot/dependencies.py`

Defines the shared service container and gives handlers access to app services.

#### `bot/ui.py`

Contains reusable Telegram UI helpers, including:

- the persistent command keyboard
- common reply messages
- helper functions for formatting output

### `config/`

This folder holds project configuration.

#### `config/settings.py`

Reads environment variables from `.env` and converts them into structured settings.

It also validates required values such as:

- `BOT_TOKEN`
- `MONGO_URI`

### `db/`

This folder contains database logic.

#### `db/database.py`

Handles:

- connecting to MongoDB Atlas
- creating indexes
- inserting notes
- updating notes
- deleting notes
- searching notes
- isolating data per `user_id`

### `services/`

This folder contains business logic.

#### `services/note_service.py`

Acts as the middle layer between the handlers and the database.

It is responsible for:

- validating user input
- generating keywords
- controlling limits such as max content length
- calling the database methods safely

### `storage/`

This folder is used for runtime storage.

#### `storage/logs/`

Reserved for bot log output and runtime log files.

### `utils/`

This folder contains helper utilities used by the whole project.

#### `utils/keywords.py`

Generates simple keywords from text and removes common stopwords.

#### `utils/logger.py`

Configures project logging so the bot can print useful runtime information.

### Root Files 🗂️

#### `.env.example`

A safe template showing which environment variables you need.

#### `.gitignore`

Prevents secrets, cache files, virtual environments, and runtime data from being committed.

#### `.dockerignore`

Prevents unnecessary files from being copied into the Docker image.

#### `Dockerfile`

Builds the project as a Docker container using `python:3.10-slim`.

#### `requirements.txt`

Lists the Python packages needed to run the project.

## Requirements ✅

You need the following before running the project:

- Python 3.10 or newer
- A Telegram bot token from BotFather
- A MongoDB Atlas connection string
- Internet access

### Python Dependencies

From `requirements.txt`:

- `python-telegram-bot`
- `python-dotenv`
- `pymongo`
- `dnspython`

## Environment Variables 🧩

Create a `.env` file in the project root. You can copy the example file:

```powershell
Copy-Item .env.example .env
```

### Required Variables

- `BOT_TOKEN`
- `MONGO_URI`

### Optional Variables

- `MONGO_DATABASE`
- `MONGO_COLLECTION`
- `MONGO_COUNTER_COLLECTION`
- `MONGO_USER_COLLECTION`
- `ALLOWED_TELEGRAM_USER_IDS`
- `TELEGRAM_CONNECT_TIMEOUT_SECONDS`
- `TELEGRAM_READ_TIMEOUT_SECONDS`
- `TELEGRAM_WRITE_TIMEOUT_SECONDS`
- `TELEGRAM_POOL_TIMEOUT_SECONDS`
- `TELEGRAM_POLL_TIMEOUT_SECONDS`
- `TELEGRAM_BOOTSTRAP_RETRIES`
- `HEALTHCHECK_PORT`
- `SEARCH_LIMIT`
- `MAX_NOTE_CONTENT_LENGTH`
- `MAX_SEARCH_QUERY_LENGTH`
- `MAX_KEYWORDS`
- `LOG_LEVEL`

### Example `.env`

```env
BOT_TOKEN=your_telegram_bot_token
MONGO_URI=your_mongodb_connection_string
MONGO_DATABASE=telegram_bot
MONGO_COLLECTION=notes
MONGO_COUNTER_COLLECTION=note_counters
MONGO_USER_COLLECTION=user_profiles
ALLOWED_TELEGRAM_USER_IDS=
LOG_LEVEL=INFO
```

## How to Run the Project Locally ▶️

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Activate the virtual environment

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Prepare environment variables

```powershell
Copy-Item .env.example .env
```

Then edit `.env` with your real values.

### 5. Run the bot

```powershell
python main.py
```

If everything is correct:

- the bot starts polling Telegram
- the health server starts on port `7860`
- MongoDB Atlas connects successfully

## How to Use the Bot 🤖

### Slash Commands

- `/start` shows the introduction
- `/help` shows the usage guide
- `/state` shows how many notes the current user has
- `/stored_ids` shows saved note IDs

### Text Commands

#### Store a text note

```text
store* my backend roadmap keyword* backend, roadmap, study
```

#### Search by ID

```text
search* 1
```

#### Search by keyword

```text
search* roadmap
```

#### Update a note

```text
update* 1 | my updated roadmap keyword* backend, updated
```

#### Delete a note

```text
delete* 1
```

### Media Commands

To save media, send the file with a caption that starts with `store*`.

Example:

```text
store* project screenshot keyword* ui, dashboard
```

This works with:

- photos
- videos
- audio
- voice messages
- animations
- documents

## Search Behavior 🔎

The bot supports two search styles:

### 1. Search by exact note ID

If the query is a number, the bot looks for that exact note.

Example:

```text
search* 5
```

### 2. Search by keyword

If the query is text, the bot searches:

- note content
- stored keywords
- file names

MongoDB text search is used first, and fallback matching is used if needed.

## Security Notes 🔐

- Do not put real credentials in `README.md`
- Do not commit `.env`
- Keep `BOT_TOKEN` and `MONGO_URI` in secure secret storage
- Use `ALLOWED_TELEGRAM_USER_IDS` if the bot is private
- MongoDB queries are filtered by `user_id`, so one user cannot see another user's notes

## Docker and Hugging Face Spaces 🐳

This project already includes:

- a Dockerfile
- Hugging Face Spaces-friendly port `7860`
- a simple HTTP health server started from `main.py`

To deploy with Docker:

```powershell
docker build -t telegram-storage-bot .
docker run --env-file .env -p 7860:7860 telegram-storage-bot
```

## Troubleshooting ⚠️

### `Database unavailable. Please try again later.`

This means MongoDB connection failed.

Check:

- `MONGO_URI` is correct
- MongoDB Atlas is running
- your IP is allowed in Atlas Network Access
- your database user and password are valid

### Bot starts but does not respond

Check:

- `BOT_TOKEN` is correct
- your bot is running successfully
- you are sending commands in the expected format

### Media is not stored

Make sure the media message caption starts with `store*`.

## Summary ✅

This project is a structured Telegram storage bot with:

- command-based usage
- MongoDB Atlas persistence
- clean separation of handlers, services, config, and database logic
- Docker support for deployment

At the end, users can try the bot by searching for **@Aston3_bot** on Telegram.
