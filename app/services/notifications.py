from __future__ import annotations

import json
import os
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.schemas.users import User


class NotificationError(RuntimeError):
    """Raised when a notification provider rejects or cannot receive a message."""


class TwilioNotifier:
    """Base sender for SMS and WhatsApp messages through Twilio."""

    def __init__(
        self,
        channel: str,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        timeout_seconds: float = 5.0,
    ):
        self.channel = channel
        prefix = channel.upper()
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv(f"{prefix}_FROM_NUMBER")
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    def send_assignment(self, user: User, room_name: str, pool_name: str, destination: str) -> None:
        if not self.is_configured:
            raise NotificationError(f"{self.channel.title()} notifications are not configured")
        if not destination.strip():
            raise NotificationError(f"{self.channel.title()} destination is not configured")

        body = f"{user.name} has been chosen for {pool_name} in {room_name}."
        self._post_message(destination.strip(), body)

    def _post_message(self, destination: str, body: str) -> None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        sender = self._format_address(self.from_number or "")
        recipient = self._format_address(destination)
        payload = urlencode({"From": sender, "To": recipient, "Body": body}).encode("utf-8")
        request = Request(url, data=payload, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        request.add_header("Authorization", "Basic " + self._basic_auth())
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as error:
            raise NotificationError(f"Unable to reach {self.channel.title()}") from error

        try:
            result = json.loads(response_body)
        except json.JSONDecodeError as error:
            raise NotificationError("Notification provider returned an invalid response") from error
        if not result.get("sid"):
            raise NotificationError(result.get("message", "Notification provider rejected the message"))

    def _basic_auth(self) -> str:
        import base64

        credentials = f"{self.account_sid}:{self.auth_token}".encode("utf-8")
        return base64.b64encode(credentials).decode("ascii")

    def _format_address(self, value: str) -> str:
        if self.channel == "whatsapp" and not value.startswith("whatsapp:"):
            return f"whatsapp:{value}"
        return value


class WhatsAppNotifier(TwilioNotifier):
    def __init__(self, **kwargs):
        super().__init__(channel="whatsapp", **kwargs)


class SmsNotifier(TwilioNotifier):
    def __init__(self, **kwargs):
        super().__init__(channel="sms", **kwargs)
