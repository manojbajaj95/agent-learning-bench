#!/usr/bin/env python3
import os
import sys

os.execv(
    "/usr/bin/chromium",
    [
        "chromium",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--headless=new",
        *sys.argv[1:],
    ],
)
