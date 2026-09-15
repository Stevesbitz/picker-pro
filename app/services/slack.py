from __future__ import annotations

import json
import os
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas.users import User


class SlackNotifierError(RuntimeError):
    """Raised when Slack rejects or cannot receive a notification."""


class SlackNotifier:
    """Sends picker assignments to Slack through the configured transport."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
        timeout_seconds: float = 5.0,
    ):
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = channel_id or os.getenv("SLACK_CHANNEL_ID")
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool((self.bot_token and self.channel_id) or self.webhook_url)

    def send_assignment(self, user: User, room_name: str, pool_name: str) -> None:
        text = f"🎯 *{user.name}* has been chosen for *{pool_name}* in *{room_name}*."
        if self.bot_token and self.channel_id:
            self._send_web_api(text)
            return
        if self.webhook_url:
            self._send_webhook(text)
            return
        raise SlackNotifierError("Slack notifications are not configured")

    def _send_web_api(self, text: str) -> None:
        self._post_json(
            "https://slack.com/api/chat.postMessage",
            {"channel": self.channel_id, "text": text},
            headers={"Authorization": f"Bearer {self.bot_token}"},
            slack_api=True,
        )

    def _send_webhook(self, text: str) -> None:
        self._post_json(self.webhook_url, {"text": text})

    def _post_json(self, url: str, payload: dict, headers: Optional[dict] = None, slack_api: bool = False) -> None:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as error:
            raise SlackNotifierError("Unable to reach Slack") from error

        if slack_api:
            try:
                result = json.loads(body)
            except json.JSONDecodeError as error:
                raise SlackNotifierError("Slack returned an invalid response") from error
            if not result.get("ok"):
                raise SlackNotifierError(result.get("error", "Slack rejected the message"))
        elif body and body != "ok":
            raise SlackNotifierError("Slack rejected the webhook message")
