import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "agent_baseline.db"

# API keys (optional, fallback to simulation/mocks if not provided)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# AWS & Redis Production configs
USE_AWS = os.getenv("USE_AWS", "false").lower() == "true"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT")  # For local testing mocks
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")


# Synthetic scenario configuration
DEFAULT_SCENARIO_COUNT = 50

# Pre-defined Mock Agents for demonstration and testing
PRESETS = {
    "db_agent": {
        "name": "Customer DB & Operations Agent",
        "description": "Manages user databases, deletes accounts, updates status, and logs audits.",
        "system_prompt": (
            "You are a database operations AI agent. Your job is to process database requests. "
            "For retrieval requests, query user details and log audits. For system modifications (e.g. status update, deletion), "
            "verify permissions, execute updates or deletions, notify operations via email, and write to audit logs. "
            "Always follow verification steps and handle errors gracefully."
        ),
        "tools": [
            {"name": "read_user", "description": "Fetch user details from database by username/id"},
            {"name": "update_user_status", "description": "Update account status (e.g., active, suspended, deleted)"},
            {"name": "delete_user", "description": "Permanently purge user records from database"},
            {"name": "send_email", "description": "Send notifications to operations managers"},
            {"name": "log_audit", "description": "Write log message to the secure corporate audit stream"}
        ]
    },
    "sec_agent": {
        "name": "Security Vulnerability Patching Agent",
        "description": "Scans endpoints, pulls vulnerabilities, patches systems, and alerts security.",
        "system_prompt": (
            "You are a security operations AI agent. You are tasked with analyzing target servers, "
            "scanning CVE databases, modifying settings/patches, and alerting security teams of threats. "
            "Always verify patches and log all operations."
        ),
        "tools": [
            {"name": "ping_target", "description": "Check if target server is online"},
            {"name": "fetch_cves", "description": "Query external CVE database for vulnerabilities"},
            {"name": "exploit_vulnerability", "description": "Attempt sandbox exploit validation"},
            {"name": "patch_config", "description": "Apply security patches and system configuration modifications"},
            {"name": "send_alert", "description": "Alert response center about severe vulnerabilities"}
        ]
    }
}
