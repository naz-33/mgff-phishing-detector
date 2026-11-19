"""Gmail API client wrapper for querying and retrieving emails with retry logic."""

import logging
import socket
import time
from typing import Any, Dict, List, Optional, Tuple
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GmailClient:
    """Wrapper around Google Gmail API service providing robust email queries."""

    def __init__(self, credentials: Credentials, max_retries: int = 3, retry_delay: float = 2.0):
        self.credentials = credentials
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._service: Optional[Resource] = None
        self._mailbox_email: Optional[str] = None

    @property
    def service(self) -> Resource:
        """Lazily initialize and return the Gmail API Resource service."""
        if self._service is None:
            self._service = build("gmail", "v1", credentials=self.credentials, cache_discovery=False)
        return self._service

    def _execute_with_retry(self, request_callable, description: str = "Gmail API call") -> Any:
        """Execute a Gmail API request with exponential backoff on transient errors."""
        delay = self.retry_delay
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return request_callable().execute()
            except HttpError as error:
                last_exception = error
                status_code = error.resp.status if error.resp else None
                # Retry on 429 (rate limit) or 5xx server errors
                if status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    logger.warning(
                        "Transient HTTP %s error during %s (attempt %d/%d). Retrying in %.1fs...",
                        status_code,
                        description,
                        attempt,
                        self.max_retries,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 2.0
                else:
                    logger.error("HTTP error during %s: %s", description, error)
                    raise
            except (socket.error, ConnectionError, TimeoutError) as net_err:
                last_exception = net_err
                if attempt < self.max_retries:
                    logger.warning(
                        "Network error during %s (%s, attempt %d/%d). Retrying in %.1fs...",
                        description,
                        net_err,
                        attempt,
                        self.max_retries,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 2.0
                else:
                    logger.error("Network error during %s after %d attempts: %s", description, self.max_retries, net_err)
                    raise

        if last_exception:
            raise last_exception

    def get_user_profile(self) -> Dict[str, Any]:
        """Fetch the authenticated user's profile information."""
        return self._execute_with_retry(
            lambda: self.service.users().getProfile(userId="me"),
            description="get user profile",
        )

    def get_mailbox_email(self) -> str:
        """Return the email address of the connected Gmail account."""
        if not self._mailbox_email:
            profile = self.get_user_profile()
            self._mailbox_email = profile.get("emailAddress", "unknown@gmail.com")
        return self._mailbox_email

    def list_messages(
        self,
        query: str = "in:inbox",
        max_results: int = 50,
        page_token: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """List messages matching the query with pagination support.
        
        Returns:
            Tuple of (messages_list, next_page_token)
        """
        req_params: Dict[str, Any] = {
            "userId": "me",
            "q": query,
            "maxResults": max_results,
        }
        if page_token:
            req_params["pageToken"] = page_token

        response = self._execute_with_retry(
            lambda: self.service.users().messages().list(**req_params),
            description="list messages",
        )

        messages = response.get("messages", [])
        next_page_token = response.get("nextPageToken")
        return messages, next_page_token

    def get_message(self, message_id: str, format: str = "full") -> Dict[str, Any]:
        """Retrieve a specific message by its Gmail ID in full format."""
        return self._execute_with_retry(
            lambda: self.service.users().messages().get(userId="me", id=message_id, format=format),
            description=f"get message {message_id}",
        )

