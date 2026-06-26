"""
Person 1 runs this FIRST before anything else.
Builds a Daytona sandbox snapshot with Playwright pre-installed.
Share the printed snapshot ID in the group chat immediately.
"""
import os
from dotenv import load_dotenv
load_dotenv("backend/.env")

from daytona import Daytona, CreateSandboxFromImageParams, Image

daytona = Daytona()

image = (
    Image.debian_slim("3.12")
    .pip_install(["playwright", "requests"])
    .run_commands([
        "playwright install chromium",
        "playwright install-deps chromium",
    ])
)

print("Building snapshot... (takes 2-3 minutes)")
sandbox = daytona.create(CreateSandboxFromImageParams(image=image))

print(f"\n✅ SNAPSHOT READY")
print(f"Sandbox ID: {sandbox.id}")
print(f"\nAdd this to backend/.env:")
print(f"DAYTONA_SNAPSHOT={sandbox.id}")
print(f"\nPost the DAYTONA_SNAPSHOT value in the group chat NOW.")
# Do not delete — this IS the snapshot
