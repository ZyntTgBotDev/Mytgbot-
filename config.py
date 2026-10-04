import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "1784758404"))

# On Render this directory is mounted as a persistent disk.
# Locally it falls back to the project directory.
DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "zynt_films.db")

BOT_NAME = "ZYNT FILMS"
