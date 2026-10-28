import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN", "").strip()
VK_GROUP_ID = int(os.getenv("VK_GROUP_ID", "0") or 0)
VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199").strip()
MAX_FILE_MB = max(10, int(os.getenv("MAX_FILE_MB", "100")))
MAX_DURATION_SECONDS = max(30, int(os.getenv("MAX_DURATION_SECONDS", "900")))
MAX_CONCURRENT_DOWNLOADS = max(1, min(4, int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2"))))
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()
