from tgss.quart import app
from tgss.internal.config import Config

import os

if __name__ == "__main__":
    app.run(port=Config.SERVER_PORT())
