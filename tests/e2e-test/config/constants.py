"""
Configuration constants module for test environment settings.
"""

import os

from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("url")
if URL and URL.endswith("/"):
    URL = URL[:-1]
