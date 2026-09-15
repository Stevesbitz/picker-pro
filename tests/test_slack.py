import json
import unittest
from unittest.mock import patch

from app.schemas.users import User
from app.services.slack import SlackNotifier, SlackNotifierError


class SlackNotifierTests(unittest.TestCase):
    def setUp(self):
        self.user = User(id="user-1", name="Ada")

    @patch("app.services.slack.urlopen")
    def test_sends_assignment_to_configured_channel(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"ok": true}'
        notifier = SlackNotifier(bot_token="token", channel_id="channel")

        notifier.send_assignment(self.user, "Engineering", "Standup")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://slack.com/api/chat.postMessage")
        self.assertEqual(request.get_header("Authorization"), "Bearer token")
        self.assertEqual(
            json.loads(request.data),
            {"channel": "channel", "text": "🎯 *Ada* has been chosen for *Standup* in *Engineering*."},
        )

    def test_webhook_configuration_is_supported(self):
        notifier = SlackNotifier(webhook_url="https://hooks.slack.test/example")
        self.assertTrue(notifier.is_configured)

    def test_unconfigured_notifier_fails_clearly(self):
        notifier = SlackNotifier()
        self.assertFalse(notifier.is_configured)
        with self.assertRaises(SlackNotifierError):
            notifier.send_assignment(self.user, "Engineering", "Standup")


if __name__ == "__main__":
    unittest.main()
