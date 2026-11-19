#!/usr/bin/env python3
"""ZanderEtAlFishing — Automated Gmail Email Monitoring and Phishing Detection Service.

Phase 2: Continuously polls the connected Gmail inbox, retrieves newly received emails,
classifies them using the Phase 1 hybrid ML engine, prints results to the terminal,
and commits records into a lightweight SQLite database.
"""

import argparse
from datetime import datetime, timezone
import os
import signal
import sys
import time
from typing import Any, Dict

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database.connection import init_db
from database.repository import ScanRepository
from gmail_integration.auth import get_gmail_credentials
from gmail_integration.email_parser import ParsedEmail
from gmail_integration.gmail_client import GmailClient
from gmail_integration.scanner import EmailScanner
from ml_engine.model_loader import ModelLoader
from ml_engine.predictor import PhishingPredictor


def print_banner() -> None:
    banner = """========================================
          ZanderEtAlFishing
       AUTOMATED EMAIL MONITOR
========================================"""
    print(banner)


def handle_email_scanned(parsed: ParsedEmail, result: Dict[str, Any]) -> None:
    """Callback printing newly scanned email details to the terminal."""
    print("\nNew Email Found")
    print(f"\nSubject: {parsed.subject if parsed.subject else '(No Subject)'}")
    print(f"Sender: {parsed.sender}")
    print("\nAnalyzing with Hybrid ML Model...")
    print(f"\nClassification: {result['classification']}")
    print(f"Phishing Probability: {result['phishing_probability']:.4f}")
    print(f"Inference Time: {result['inference_time_ms']:.2f} ms")
    print("\n[OK] Detection result saved")
    print("\n----------------------------------------")
    print("Monitoring for new messages...")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ZanderEtAlFishing Phase 2 — Automated Gmail Phishing Monitor"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("POLLING_INTERVAL_SECONDS", 60)),
        help="Polling interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--backfill",
        type=int,
        default=int(os.environ.get("HISTORICAL_BACKFILL_LIMIT", 0)),
        help="Historical messages to backfill on initial setup (default: 0, scan incoming only)",
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default=os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials/credentials.json"),
        help="Path to Google OAuth client secrets JSON file",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("GMAIL_TOKEN_PATH", "credentials/token.json"),
        help="Path to store authorized OAuth user token JSON",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=os.environ.get("DATABASE_PATH", "zander_email_monitor.db"),
        help="Path to SQLite database file",
    )

    args = parser.parse_args()

    print_banner()

    # Step 1: Initialize ML inference engine
    try:
        artifacts = ModelLoader.load_artifacts()
        predictor = PhishingPredictor(artifacts=artifacts)
        print("[OK] ML Engine Loaded")
    except Exception as e:
        print(f"[FATAL] Failed to load Phase 1 ML model artifacts: {e}")
        sys.exit(1)

    # Step 2: Initialize Database
    try:
        init_db(args.db)
        repo = ScanRepository(db_path=args.db)
        print("[OK] Database Connected")
    except Exception as e:
        print(f"[FATAL] Failed to initialize SQLite database: {e}")
        sys.exit(1)

    # Step 3: Authorize Gmail
    try:
        creds = get_gmail_credentials(
            credentials_path=args.credentials,
            token_path=args.token,
            interactive=True,
        )
        gmail_client = GmailClient(credentials=creds)
        # Verify connection and mailbox profile
        mailbox = gmail_client.get_mailbox_email()
        print(f"[OK] Gmail Authorization Successful ({mailbox})")
    except FileNotFoundError as e:
        print(f"\n[ERROR] Missing OAuth Credentials:\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Gmail Authorization Failed: {e}")
        sys.exit(1)

    # Step 4: Configure and start Email Scanner
    scanner = EmailScanner(
        gmail_client=gmail_client,
        repository=repo,
        predictor=predictor,
        polling_interval=args.interval,
        backfill_limit=args.backfill,
        on_email_scanned=handle_email_scanned,
    )

    # Setup graceful shutdown handlers
    def signal_handler(sig, frame):
        print("\n\n[INFO] Graceful shutdown initiated. Stopping monitor...")
        scanner.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\nMonitoring Status: ACTIVE")
    print(f"Polling Interval: {args.interval} seconds")
    print("\n----------------------------------------")
    print("Checking Gmail for new emails...")

    try:
        scanner.start()
    except Exception as e:
        print(f"[FATAL] Scanner terminated with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

