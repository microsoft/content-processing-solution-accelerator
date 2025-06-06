import os

from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("url")
if URL.endswith("/"):
    URL = URL[:-1]
