"""Backwards-compatible entrypoint: python interface.py"""

import os

from trackr import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=os.getenv("TRACKR_HOST", "127.0.0.1"), port=int(os.getenv("TRACKR_PORT", "5000")))
