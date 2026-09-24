import json
import unittest
from unittest.mock import patch

from app.schemas.users import User
from app.services.notifications import NotificationError, SmsNotifier, WhatsAppNotifier


class TwilioNotifierTests(unittest.TestCase):
    def setUp(self):
        self.user = User(id="user-1", name="Ada")

    @patch("app.services.notifications.urlopen")
    def test_sends_sms_assignment(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"sid": "SM123"}'
        notifier = SmsNotifier(account_sid="sid", auth_token="token", from_number="+15550000000")

        notifier.send_assignment(self.user, "Engineering", "Standup", "+15551111111")

        request = urlopen.call_args.args[0]
        self.assertIn("Messages.json", request.full_url)
        self.assertEqual(request.get_header("Authorization"), "Basic c2lkOnRva2Vu")
        self.assertIn("To=%2B15551111111", request.data.decode())
        self.assertIn("From=%2B15550000000", request.data.decode())

    @patch("app.services.notifications.urlopen")
    def test_formats_whatsapp_addresses(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"sid": "SM123"}'
        notifier = WhatsAppNotifier(account_sid="sid", auth_token="token", from_number="whatsapp:+14155238886")

        notifier.send_assignment(self.user, "Engineering", "Standup", "+15551111111")

        request = urlopen.call_args.args[0]
        body = request.data.decode()
        self.assertIn("From=whatsapp%3A%2B14155238886", body)
        self.assertIn("To=whatsapp%3A%2B15551111111", body)

    def test_unconfigured_provider_fails_clearly(self):
        notifier = SmsNotifier()
        self.assertFalse(notifier.is_configured)
        with self.assertRaises(NotificationError):
            notifier.send_assignment(self.user, "Engineering", "Standup", "+15551111111")


if __name__ == "__main__":
    unittest.main()
