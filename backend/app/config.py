import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "../data/facility.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Agent timeout in seconds - hardcoded for easy tweaking
AGENT_TIMEOUT = 60
