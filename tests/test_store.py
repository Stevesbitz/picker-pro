import unittest
from datetime import datetime
from unittest.mock import patch

from app.store import DEFAULT_POOL_ID, MemoryStore, RoomStore


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

    def test_ooo_users_are_kept_in_state_but_excluded_from_picks(self):
        ada, grace = self.add_users("Ada", "Grace")
        self.store.toggle_ooo(ada.id, True)

        with patch("app.store.random.choice", return_value=grace):
            picked = self.store.pick_next()

        self.assertEqual(picked.id, grace.id)
        self.assertTrue(next(user for user in self.store.get_state().users if user.id == ada.id).is_ooo)

    def test_pools_keep_users_and_rounds_isolated(self):
        standup_user = self.store.add_user("Ada", pool_id="standup")
        review_user = self.store.add_user("Grace", pool_id="review")

        with patch("app.store.random.choice", side_effect=lambda choices: choices[0]):
            self.assertEqual(self.store.pick_next("standup").id, standup_user.id)

        self.assertEqual([user.id for user in self.store.get_state("review").users], [review_user.id])
        self.assertTrue(review_user.pickedThisRound is False)
        self.assertEqual(self.store.get_state("standup").pool_id, "standup")


class RoomStoreTests(unittest.TestCase):
    def test_each_room_has_an_empty_and_isolated_picker_state(self):
        rooms = RoomStore()
        engineering = rooms.create_room("Engineering")
        design = rooms.create_room("Design")

        engineering_state = rooms.get_state_store(engineering.id)
        design_state = rooms.get_state_store(design.id)
        engineering_state.add_user("Ada")

        self.assertEqual(engineering.name, "Engineering")
        self.assertEqual(design.name, "Design")
        self.assertNotEqual(engineering.id, design.id)
        self.assertEqual([user.name for user in engineering_state.get_state().users], ["Ada"])
        self.assertEqual(design_state.get_state().users, [])

    def test_unknown_room_has_no_metadata_or_picker_state(self):
        rooms = RoomStore()

        self.assertIsNone(rooms.get_room("missing"))
        self.assertIsNone(rooms.get_state_store("missing"))

    def test_new_room_has_a_default_pool_and_custom_pools(self):
        rooms = RoomStore()
        room = rooms.create_room("Engineering")
        standup = rooms.create_pool(room.id, "Standup")

        self.assertEqual([pool.id for pool in rooms.list_pools(room.id)], [DEFAULT_POOL_ID, standup.id])
        self.assertEqual(rooms.list_pools("missing"), [])
