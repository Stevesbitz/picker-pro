import unittest
from unittest.mock import patch

from app.store.db import DatabaseRoomStore


class DatabaseRoomStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = DatabaseRoomStore("sqlite:///:memory:")
        self.room = self.store.create_room("Engineering")

    def test_room_and_pool_lifecycle_persists_metadata(self):
        pool = self.store.create_pool(self.room.id, "Standup")

        saved_room = self.store.get_room(self.room.id)
        pools = self.store.list_pools(self.room.id)

        self.assertEqual(saved_room.name, "Engineering")
        self.assertEqual([item.name for item in pools], ["Default", "Standup"])
        self.assertEqual(pools[1].id, pool.id)

    def test_database_picker_excludes_ooo_users(self):
        pool = self.store.create_pool(self.room.id, "On-Call")
        state = self.store.get_state_store(self.room.id)
        unavailable = state.add_user("Ada", pool.id)
        available = state.add_user("Grace", pool.id)
        state.toggle_ooo(unavailable.id, True, pool.id)

        with patch("app.store.db.random.choice", return_value=available):
            picked = state.pick_next(pool.id)

        self.assertEqual(picked.id, available.id)
        self.assertTrue(state.get_state(pool.id).users[0].is_ooo)

    def test_database_rounds_and_last_pick_are_pool_scoped(self):
        first_pool = self.store.create_pool(self.room.id, "Standup")
        second_pool = self.store.create_pool(self.room.id, "Review")
        state = self.store.get_state_store(self.room.id)
        first_user = state.add_user("Ada", first_pool.id)
        second_user = state.add_user("Grace", second_pool.id)

        with patch("app.store.db.random.choice", side_effect=lambda choices: choices[0]):
            state.pick_next(first_pool.id)

        self.assertEqual(state.get_state(first_pool.id).last_picked_user.id, first_user.id)
        self.assertIsNone(state.get_state(second_pool.id).last_picked_user)
        self.assertFalse(second_user.pickedThisRound)

    def test_room_slack_channel_can_be_saved_and_cleared(self):
        self.room.slack_channel_id = "C0123456789"
        self.store.save_room(self.room)
        self.assertEqual(self.store.get_room(self.room.id).slack_channel_id, "C0123456789")

        self.room.slack_channel_id = None
        self.store.save_room(self.room)
        self.assertIsNone(self.store.get_room(self.room.id).slack_channel_id)


if __name__ == "__main__":
    unittest.main()
