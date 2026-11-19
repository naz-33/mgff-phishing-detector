"""Email monitoring service connecting Gmail retrieval with ML phishing detection."""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, List, Optional
import threading

from database.repository import ScanRepository
from gmail_integration.email_parser import ParsedEmail, parse_gmail_message
from gmail_integration.gmail_client import GmailClient
from ml_engine.predictor import PhishingPredictor, get_default_predictor

logger = logging.getLogger(__name__)


class EmailScanner:
    """Continuous email scanner polling Gmail inbox and classifying new emails."""

    def __init__(
        self,
        gmail_client: GmailClient,
        repository: ScanRepository,
        predictor: Optional[PhishingPredictor] = None,
        polling_interval: int = 60,
        backfill_limit: int = 0,
        on_email_scanned: Optional[Callable[[ParsedEmail, Dict[str, Any]], None]] = None,
    ):
        """Initialize the scanner.
        
        Parameters:
            gmail_client: Authenticated Gmail API client.
            repository: SQLite scan storage repository.
            predictor: PhishingPredictor instance (defaults to singleton get_default_predictor).
            polling_interval: Seconds between inbox polls (default 60).
            backfill_limit: Historical emails to backfill on initial run (0 = none, newest only).
            on_email_scanned: Optional callback triggered after each scan result is saved.
        """
        self.gmail_client = gmail_client
        self.repository = repository
        self.predictor = predictor or get_default_predictor()
        self.polling_interval = max(5, polling_interval)
        self.backfill_limit = max(0, backfill_limit)
        self.on_email_scanned = on_email_scanned

        self.mailbox = self.gmail_client.get_mailbox_email()
        self._stop_event = threading.Event()
        self.is_running = False

    def initialize_sync_point(self) -> None:
        """Establish or load the synchronization checkpoint for the connected mailbox.
        
        If no checkpoint exists in the database:
          - If backfill_limit == 0: records the newest message timestamp as the baseline,
            preventing historical inbox messages from being flooded as new.
          - If backfill_limit > 0: scans up to backfill_limit messages to populate history.
        """
        sync_state = self.repository.get_sync_state(self.mailbox)
        if sync_state is not None:
            logger.info(
                "Loaded existing sync checkpoint for %s (last_internal_date=%s)",
                self.mailbox,
                sync_state.get("last_internal_date"),
            )
            return

        logger.info("No prior sync state found for %s. Initializing sync point...", self.mailbox)

        # Query newest message in inbox
        messages, _ = self.gmail_client.list_messages(query="in:inbox", max_results=10)

        if not messages:
            # Inbox is empty; establish baseline as current time
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            self.repository.update_sync_state(self.mailbox, last_internal_date=now_ms)
            logger.info("Inbox is empty. Established sync baseline at current time.")
            return

        if self.backfill_limit == 0:
            # Baseline without scanning historical emails
            first_msg_summary = messages[0]
            try:
                msg_data = self.gmail_client.get_message(first_msg_summary["id"], format="minimal")
                int_date_ms = int(msg_data.get("internalDate", "0"))
            except Exception as e:
                logger.warning("Could not fetch latest message date (%s), using current time.", e)
                int_date_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

            self.repository.update_sync_state(self.mailbox, last_internal_date=int_date_ms)
            logger.info("Established initial synchronization checkpoint at %d (no historical backfill).", int_date_ms)
        else:
            # Limited historical backfill
            logger.info("Historical backfill requested: processing up to %d messages...", self.backfill_limit)
            to_backfill = messages[: self.backfill_limit]
            # Process in chronological order (oldest to newest)
            to_backfill.reverse()
            for msg_meta in to_backfill:
                self._process_message_by_id(msg_meta["id"])

    def _process_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve, parse, classify, and persist a single Gmail message.
        
        Returns the saved classification result dictionary, or None if skipped/failed.
        """
        # Step 1: Duplicate check
        if self.repository.is_message_scanned(self.mailbox, message_id):
            return None

        # Step 2: Retrieve full message
        try:
            raw_message = self.gmail_client.get_message(message_id, format="full")
        except Exception as e:
            logger.error("Failed to retrieve message %s: %s", message_id, e)
            return None

        # Step 3: Parse email content & headers
        try:
            parsed = parse_gmail_message(raw_message)
        except Exception as e:
            logger.error("Failed to parse message %s: %s", message_id, e)
            return None

        # Step 4: ML Inference using existing predict_email logic
        try:
            # Combined text contains subject + body
            ml_input = parsed.combined_text
            prediction_result = self.predictor.predict(ml_input)
        except Exception as e:
            logger.error("ML inference failed for message %s: %s", message_id, e)
            return None

        # Step 5: Save result to SQLite
        record = {
            "mailbox": self.mailbox,
            "gmail_message_id": parsed.message_id,
            "gmail_thread_id": parsed.thread_id,
            "sender": parsed.sender,
            "subject": parsed.subject,
            "body": parsed.body or parsed.combined_text,
            "received_at": parsed.received_at,
            "classification": prediction_result["classification"],
            "risk_tier": prediction_result.get("risk_tier"),
            "phishing_probability": prediction_result["phishing_probability"],
            "logistic_regression_probability": prediction_result["logistic_regression_probability"],
            "lightgbm_probability": prediction_result["lightgbm_probability"],
            "inference_time_ms": prediction_result["inference_time_ms"],
            "model_version": prediction_result["model_version"],
            "spf_pass": parsed.spf_pass,
            "dkim_pass": parsed.dkim_pass,
            "dmarc_pass": parsed.dmarc_pass,
        }

        try:
            self.repository.save_scan_result(record)
            # Update sync state monotonically
            self.repository.update_sync_state(
                mailbox=self.mailbox,
                last_internal_date=parsed.internal_date_ms,
            )
        except Exception as e:
            logger.error("Failed to persist scan record for message %s: %s", message_id, e)
            return None

        # Step 6: Trigger callback (terminal display or notification)
        if self.on_email_scanned:
            try:
                self.on_email_scanned(parsed, prediction_result)
            except Exception as e:
                logger.error("Error in on_email_scanned callback: %s", e)

        return prediction_result

    def scan_once(self) -> int:
        """Perform one poll iteration across inbox messages with pagination.
        
        Returns the number of new emails successfully scanned.
        """
        sync_state = self.repository.get_sync_state(self.mailbox)
        min_internal_date = sync_state.get("last_internal_date", 0) if sync_state else 0

        page_token = None
        new_scans_count = 0
        unprocessed_messages: List[Dict[str, Any]] = []

        # Paginate through inbox messages
        while not self._stop_event.is_set():
            try:
                messages, page_token = self.gmail_client.list_messages(
                    query="in:inbox",
                    max_results=50,
                    page_token=page_token,
                )
            except Exception as e:
                logger.error("Error querying messages from Gmail: %s", e)
                break

            if not messages:
                break

            found_older_than_sync = False
            for msg_meta in messages:
                msg_id = msg_meta["id"]
                if self.repository.is_message_scanned(self.mailbox, msg_id):
                    # Already scanned, continue checking others on page
                    continue
                unprocessed_messages.append(msg_meta)

            if not page_token:
                break

            # If all messages on this page were already scanned, no need to paginate deeply
            if not unprocessed_messages and min_internal_date > 0:
                break

        # Process gathered unprocessed messages chronologically (oldest to newest)
        for msg_meta in reversed(unprocessed_messages):
            if self._stop_event.is_set():
                break
            result = self._process_message_by_id(msg_meta["id"])
            if result is not None:
                new_scans_count += 1

        return new_scans_count

    def start(self) -> None:
        """Start the continuous scanning loop. Blocks until stop() is called."""
        self._stop_event.clear()
        self.is_running = True
        logger.info(
            "Starting automated email monitor for %s (polling every %ds)...",
            self.mailbox,
            self.polling_interval,
        )

        try:
            self.initialize_sync_point()
        except Exception as e:
            logger.error("Failed to initialize sync point: %s", e)

        while not self._stop_event.is_set():
            try:
                self.scan_once()
            except Exception as e:
                logger.error("Unexpected error during scan cycle: %s", e)

            # Interruptible sleep
            self._stop_event.wait(self.polling_interval)

        self.is_running = False
        logger.info("Automated email monitor stopped cleanly.")

    def stop(self) -> None:
        """Signal the scanner to stop gracefully."""
        self._stop_event.set()

