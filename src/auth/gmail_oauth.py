"""Google OAuth 2.0 Handler with strictly read-only scope.

Security & Privacy Constraints:
    1. Scope is hardcoded to `https://www.googleapis.com/auth/gmail.readonly`.
    2. Modifying operations (send, trash, modify labels) are strictly forbidden.
    3. Tokens and credentials are held ephemerally in session memory or git-ignored files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build


# NON-NEGOTIABLE: Strictly read-only access
GMAIL_SCOPES: List[str] = ["https://www.googleapis.com/auth/gmail.readonly"]

DEFAULT_CREDENTIALS_PATH = Path("credentials.json")
DEFAULT_TOKEN_PATH = Path("token.json")


class GmailOAuthHandler:
    """Manages secure Google OAuth 2.0 lifecycle with minimal scopes."""

    def __init__(
        self,
        client_secrets_file: Optional[str | Path] = None,
        token_path: Optional[str | Path] = None,
        token_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.client_secrets_file = Path(client_secrets_file or os.getenv("GMAIL_CLIENT_SECRETS_FILE", DEFAULT_CREDENTIALS_PATH))
        self.token_path = Path(token_path or DEFAULT_TOKEN_PATH)
        self.token_info = token_info
        self._credentials: Optional[Credentials] = None

    def _resolve_token_dict(self) -> Optional[Dict[str, Any]]:
        """Resolve token dict from in-memory injection, environment, or Streamlit secrets."""
        if self.token_info:
            return self.token_info

        env_token = os.getenv("GMAIL_TOKEN_JSON")
        if env_token:
            try:
                return json.loads(env_token)
            except Exception:
                pass

        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GMAIL_TOKEN_JSON" in st.secrets:
                secret_val = st.secrets["GMAIL_TOKEN_JSON"]
                if isinstance(secret_val, dict):
                    return secret_val
                elif isinstance(secret_val, str):
                    return json.loads(secret_val)
        except Exception:
            pass

        return None

    def is_configured(self) -> bool:
        """Check whether OAuth credentials/tokens are available."""
        return (
            self.client_secrets_file.exists()
            or self.token_path.exists()
            or bool(self._resolve_token_dict())
            or bool(os.getenv("GMAIL_CLIENT_CONFIG_JSON"))
        )

    def get_credentials(self, allow_browser_flow: bool = True) -> Optional[Credentials]:
        """Load valid credentials from cache, memory, or initiate OAuth flow."""
        creds: Optional[Credentials] = None

        # 1. Check in-memory token_dict or Streamlit Secret / Env Var
        token_dict = self._resolve_token_dict()
        if token_dict:
            try:
                creds = Credentials.from_authorized_user_info(token_dict, GMAIL_SCOPES)
            except Exception:
                creds = None

        # 2. Check existing cached token file
        if not creds and self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), GMAIL_SCOPES)
            except Exception:
                creds = None

        # 3. Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        # 4. If still invalid and browser flow allowed, run Desktop OAuth flow
        if not creds or not creds.valid:
            if not self.is_configured():
                return None

            if not allow_browser_flow or not self.client_secrets_file.exists():
                return None

            # Run Desktop OAuth 2.0 Flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_file),
                scopes=GMAIL_SCOPES,
            )
            creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

            # Persist locally in git-ignored token file
            if creds:
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())

        self._credentials = creds
        return creds

    def get_gmail_service(self) -> Optional[Resource]:
        """Build and return an authorized Gmail API v1 service."""
        creds = self._credentials or self.get_credentials(allow_browser_flow=False)
        if not creds or not creds.valid:
            return None
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def get_user_email(self) -> Optional[str]:
        """Fetch email address of the authenticated user."""
        service = self.get_gmail_service()
        if not service:
            return None
        try:
            profile = service.users().getProfile(userId="me").execute()
            return profile.get("emailAddress")
        except Exception:
            return None

    def revoke_credentials(self) -> bool:
        """Clear cached tokens for session termination."""
        if self.token_path.exists():
            try:
                self.token_path.unlink()
            except OSError:
                pass
        self._credentials = None
        return True
