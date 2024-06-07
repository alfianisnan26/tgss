from tgss.internal.config import Config
import os
import logging

Config.init()

class ColorFormatter(logging.Formatter):
    # Define color codes
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m',# Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[95m'# Magenta
    }
    RESET = '\033[0m'  # Reset color

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        log_message = super().format(record)
        return f"{log_color}{log_message}{self.RESET}"

# Custom format
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
date_format = "%H:%M:%S"

# Create a custom formatter
formatter = ColorFormatter(log_format, datefmt=date_format)

# Create a console handler and set its formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Configure the root logger
logging.basicConfig(level=logging.INFO, handlers=[console_handler])

logging.info("Initialize Configuration")

