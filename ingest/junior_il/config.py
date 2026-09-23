"""Configuration, all of it from the environment."""
import os

DSN = os.environ.get(
    "JUNIOR_IL_DSN",
    "postgresql://junior:junior@localhost:55432/junior_il",
)

# Boards are polled politely: these are public career pages, but there is no
# reason to hammer them.
REQUEST_TIMEOUT = float(os.environ.get("JUNIOR_IL_TIMEOUT", "30"))
DELAY_BETWEEN_BOARDS = float(os.environ.get("JUNIOR_IL_DELAY", "1.0"))
USER_AGENT = os.environ.get(
    "JUNIOR_IL_USER_AGENT",
    "junior-il/0.1 (+https://github.com/adam4ever0100/junior-il) contact: adamabusaad@gmail.com",
)
