import unittest
from datetime import datetime
from unittest.mock import patch

from app.store import MemoryStore


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        # Tests define their own participants rather than relying on seed data.
        self.store._users.clear()

    def add_users(self, *names):
        return [self.store.add_user(name) for name in names]

    def test_new_store_seeds_the_default_checked_users(self):
        store = MemoryStore()

        self.assertEqual([user.name for user in store.get_state().users], ["Mario", "Luigi", "Yoshi"])
        self.assertTrue(all(user.checked for user in store.get_state().users))

    def test_add_user_creates_a_checked_user_with_a_unique_id(self):
        first, second = self.add_users("Ada", "Grace")

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.name, "Ada")
        self.assertTrue(first.checked)
        self.assertFalse(first.pickedThisRound)
        self.assertIsNone(first.picked_at)

    def test_toggle_check_updates_existing_user_and_unknown_user_returns_none(self):
        user = self.add_users("Ada")[0]

        updated = self.store.toggle_check(user.id, False)

        self.assertIsNotNone(updated)
        self.assertFalse(updated.checked)
        self.assertIsNone(self.store.toggle_check("missing", True))

    def test_delete_removes_user_and_clears_last_pick_when_needed(self):
        user = self.add_users("Ada")[0]
        with patch("app.store.random.choice", return_value=user):
            self.store.pick_next()

        self.assertTrue(self.store.delete_user(user.id))
        state = self.store.get_state()
        self.assertEqual(state.users, [])
        self.assertIsNone(state.last_picked_user)
        self.assertFalse(self.store.delete_user(user.id))

    def test_pick_returns_none_when_no_checked_users_exist(self):
        user = self.add_users("Ada")[0]
        self.store.toggle_check(user.id, False)

        self.assertIsNone(self.store.pick_next())
        self.assertIsNone(self.store.get_state().last_picked_user)

    def test_pick_marks_user_records_utc_timestamp_and_updates_last_pick(self):
        user = self.add_users("Ada")[0]
        with patch("app.store.random.choice", return_value=user):
            picked = self.store.pick_next()

        self.assertEqual(picked.id, user.id)
        self.assertTrue(picked.pickedThisRound)
        self.assertEqual(self.store.get_state().last_picked_user.id, user.id)
        self.assertEqual(datetime.fromisoformat(picked.picked_at).utcoffset().total_seconds(), 0)

    def test_each_checked_user_is_picked_once_before_the_round_restarts(self):
        ada, grace = self.add_users("Ada", "Grace")

        with patch("app.store.random.choice", side_effect=lambda choices: choices[0]):
            picks = [self.store.pick_next(), self.store.pick_next(), self.store.pick_next()]

        self.assertEqual([user.id for user in picks], [ada.id, grace.id, ada.id])
        self.assertTrue(ada.pickedThisRound)
        self.assertFalse(grace.pickedThisRound)

    def test_picker_does_not_repeat_the_previous_user_when_another_is_checked(self):
        ada, grace = self.add_users("Ada", "Grace")
        ada.pickedThisRound = True
        grace.pickedThisRound = True
        self.store._last_picked_id = ada.id
        self.store._last_picked_user = ada

        with patch("app.store.random.choice", side_effect=lambda choices: choices[0]) as choose:
            picked = self.store.pick_next()

        self.assertEqual(picked.id, grace.id)
        self.assertEqual([user.id for user in choose.call_args.args[0]], [grace.id])

    def test_reset_round_makes_every_user_eligible_without_discarding_last_pick(self):
        ada, grace = self.add_users("Ada", "Grace")
        ada.pickedThisRound = True
        grace.pickedThisRound = True
        self.store._last_picked_id = ada.id
        self.store._last_picked_user = ada

        self.store.reset_round()

        state = self.store.get_state()
        self.assertFalse(any(user.pickedThisRound for user in state.users))
        self.assertEqual(state.last_picked_user.id, ada.id)
