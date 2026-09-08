"""Test data loader utility."""
import json
import os
from pathlib import Path
from typing import Any, Dict

def load_test_data(filename: str = "test_data.json") -> Dict[str, Any]:
    """Load JSON test data from shared/test_data directory with runtime env secret resolution."""
    data_path = Path(__file__).resolve().parent / filename
    data = {}
    if data_path.is_file():
        data = json.loads(data_path.read_text(encoding="utf-8"))
    if "credentials" in data and "default" in data["credentials"]:
        env_pwd = os.getenv("TEST_PASSWORD")
        if env_pwd:
            data["credentials"]["default"]["password"] = env_pwd
    return data
