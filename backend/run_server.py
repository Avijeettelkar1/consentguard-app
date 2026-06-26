import os
import sys
from pathlib import Path

import uvicorn

BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    if os.getenv("REDIRECT_LOGS", "false").lower() == "true":
        log_path = BASE_DIR / "uvicorn.log"
        err_path = BASE_DIR / "uvicorn.err.log"
        sys.stdout = open(log_path, "a", encoding="utf-8", buffering=1)
        sys.stderr = open(err_path, "a", encoding="utf-8", buffering=1)

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=port,
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
