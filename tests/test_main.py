import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app import main
from app.store import StateResponse, User


class ApiHandlerTests(unittest.TestCase):
    def test_create_user_strips_whitespace_before_storing(self):
        added_user = User(id="user-1", name="Ada")
        with patch("app.main.store") as store:
            store.add_user.return_value = added_user

            response = main.create_user(main.CreateUserRequest(name="  Ada  "))

        self.assertEqual(response, added_user)
        store.add_user.assert_called_once_with("Ada")

    def test_create_user_rejects_a_blank_name(self):
        with self.assertRaises(HTTPException) as error:
            main.create_user(main.CreateUserRequest(name=" \t "))

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.detail, "Name cannot be empty")

    def test_get_state_delegates_to_the_store(self):
        expected = StateResponse(users=[])
        with patch("app.main.store") as store:
            store.get_state.return_value = expected

            response = main.get_state()

        self.assertEqual(response, expected)
        store.get_state.assert_called_once_with()

    def test_toggle_user_returns_updated_user(self):
        user = User(id="user-1", name="Ada", checked=False)
        with patch("app.main.store") as store:
            store.toggle_check.return_value = user

            response = main.toggle_user(user.id, main.ToggleUserRequest(checked=False))

        self.assertEqual(response, user)
        store.toggle_check.assert_called_once_with(user.id, False)

    def test_toggle_user_returns_not_found_for_unknown_user(self):
        with patch("app.main.store") as store:
            store.toggle_check.return_value = None

            with self.assertRaises(HTTPException) as error:
                main.toggle_user("missing", main.ToggleUserRequest(checked=True))

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(error.exception.detail, "User not found")

    def test_delete_user_returns_success_after_deletion(self):
        with patch("app.main.store") as store:
            store.delete_user.return_value = True

            response = main.delete_user("user-1")

        self.assertEqual(response, {"status": "success"})
        store.delete_user.assert_called_once_with("user-1")

    def test_delete_user_returns_not_found_for_unknown_user(self):
        with patch("app.main.store") as store:
            store.delete_user.return_value = False

            with self.assertRaises(HTTPException) as error:
                main.delete_user("missing")

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(error.exception.detail, "User not found")

    def test_pick_user_waits_then_returns_store_selection(self):
        user = User(id="user-1", name="Ada")
        with patch("app.main.store") as store, patch(
            "app.main.asyncio.sleep", new_callable=AsyncMock
        ) as sleep:
            store.pick_next.return_value = user

            response = asyncio.run(main.pick_user())

        self.assertEqual(response, user)
        sleep.assert_awaited_once_with(1.2)
        store.pick_next.assert_called_once_with()

    def test_reset_round_delegates_to_store(self):
        with patch("app.main.store") as store:
            response = main.reset_round()

        self.assertEqual(response, {"status": "success"})
        store.reset_round.assert_called_once_with()
