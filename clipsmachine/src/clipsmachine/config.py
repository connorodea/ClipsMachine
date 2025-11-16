import os

# Root for all generated assets
OUTPUT_ROOT = os.getenv("CLIPSMACHINE_OUTPUT_ROOT", "clips_output")

# Clip length settings (in seconds)
MIN_CLIP_SEC = int(os.getenv("CLIPSMACHINE_MIN_CLIP_SEC", "40"))
TARGET_CLIP_SEC = int(os.getenv("CLIPSMACHINE_TARGET_CLIP_SEC", "90"))
MAX_CLIP_SEC = int(os.getenv("CLIPSMACHINE_MAX_CLIP_SEC", "180"))
MAX_CLIPS_PER_VIDEO = int(os.getenv("CLIPSMACHINE_MAX_CLIPS_PER_VIDEO", "20"))

# YouTube upload defaults
DEFAULT_PRIVACY = os.getenv("CLIPSMACHINE_DEFAULT_PRIVACY", "unlisted")  # public/unlisted/private
CATEGORY_ID = os.getenv("CLIPSMACHINE_CATEGORY_ID", "27")  # 27 = Education, 24 = Entertainment

# OAuth files
CLIENT_SECRET_FILE = os.getenv("CLIPSMACHINE_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = os.getenv("CLIPSMACHINE_TOKEN_FILE", "token.json")

# LLM
OPENAI_MODEL = os.getenv("CLIPSMACHINE_OPENAI_MODEL", "gpt-4o-mini")
MAX_LLM_RETRIES = int(os.getenv("CLIPSMACHINE_MAX_LLM_RETRIES", "3"))
LLM_SLEEP_BETWEEN_CALLS = float(os.getenv("CLIPSMACHINE_LLM_SLEEP_BETWEEN", "1"))

# Subtitles
ENABLE_SUBTITLES = os.getenv("CLIPSMACHINE_ENABLE_SUBTITLES", "true").lower() == "true"
MAX_SUBTITLE_WORDS = int(os.getenv("CLIPSMACHINE_MAX_SUBTITLE_WORDS", "8"))  # Max key words per clip

# Subtitle types: "keywords", "transcription", or "both"
SUBTITLE_TYPE = os.getenv("CLIPSMACHINE_SUBTITLE_TYPE", "transcription")
WORDS_PER_SUBTITLE_LINE = int(os.getenv("CLIPSMACHINE_WORDS_PER_LINE", "3"))  # For transcription subtitles
