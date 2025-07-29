from dotenv import load_dotenv
import os

load_dotenv()  # reads .env in current directory
print("AIRNOW_API_KEY =", os.getenv("AIRNOW_API_KEY"))
