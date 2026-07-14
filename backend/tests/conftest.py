"""Test setup: isolate env + DB before any app module imports."""
import os
import sys
import tempfile

os.environ.setdefault("MOCK", "true")               # no real browser scans
os.environ.setdefault("DISABLE_SCHEDULER", "1")     # no background monitor loop
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["CG_DB_PATH"] = os.path.join(tempfile.gettempdir(), "consentguard_ci_test.db")

# fresh DB each run
if os.path.exists(os.environ["CG_DB_PATH"]):
    try:
        os.remove(os.environ["CG_DB_PATH"])
    except OSError:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
