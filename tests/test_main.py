import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException, Request

from app import main
from app.store import Room, StateResponse, User


ROOM_ID = "team-room"


class ApiHandlerTests(unittest.TestCase):
    @staticmethod
    def request(path: str) -> Request:
        return Request(
            {
                "type": "http",
                "method": "GET",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [],
                "server": ("testserver", 80),
            }
        )

    def test_browser_404_uses_the_friendly_error_page(self):
        response = asyncio.run(
            main.http_exception_handler(self.request("/rooms/missing"), HTTPException(status_code=404))
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.body)
        self.assertIn(b"Return home", response.body)

    def test_api_404_remains_a_json_error(self):
        response = asyncio.run(
            main.http_exception_handler(
                self.request("/api/rooms/missing/state"),
                HTTPException(status_code=404, detail="Room not found"),
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.body, b'{"detail":"Room not found"}')

    def test_unhandled_api_error_does_not_expose_internal_details(self):
        response = asyncio.run(main.unhandled_exception_handler(self.request("/api/rooms/id/state"), RuntimeError("secret")))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.body, b'{"detail":"Internal server error"}')

    def test_create_room_strips_name_and_returns_a_share_link(self):
        room = Room(id=ROOM_ID, name="Engineering")
        request = Mock()
        request.url_for.return_value = f"http://testserver/rooms/{ROOM_ID}"
        with patch("app.main.room_store") as rooms:
            rooms.create_room.return_value = room

            response = main.create_room(request, main.CreateRoomRequest(name="  Engineering  "))

        self.assertEqual(response.id, ROOM_ID)
        self.assertEqual(response.name, "Engineering")
        self.assertEqual(response.share_url, f"http://testserver/rooms/{ROOM_ID}")
        rooms.create_room.assert_called_once_with("Engineering")
        request.url_for.assert_called_once_with("read_room", room_id=ROOM_ID)

    def test_create_room_rejects_blank_name(self):
        with self.assertRaises(HTTPException) as error:
            main.create_room(Mock(), main.CreateRoomRequest(name=" \t "))

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.detail, "Team name cannot be empty")

    def test_get_room_state_returns_not_found_for_unknown_room(self):
        with patch("app.main.room_store") as rooms:
            rooms.get_state_store.return_value = None

            with self.assertRaises(HTTPException) as error:
                main.get_room_state_or_404("missing")

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(error.exception.detail, "Room not found")

    def test_get_state_delegates_to_the_requested_room_only(self):
        expected = StateResponse(users=[])
        state_store = Mock()
        state_store.get_state.return_value = expected
        with patch("app.main.room_store") as rooms:
            rooms.get_state_store.return_value = state_store

            response = main.get_state(ROOM_ID)

        self.assertEqual(response, expected)
        rooms.get_state_store.assert_called_once_with(ROOM_ID)
        state_store.get_state.assert_called_once_with()

    def test_create_user_strips_whitespace_before_storing_in_room(self):
        added_user = User(id="user-1", name="Ada")
        state_store = Mock()
        state_store.add_user.return_value = added_user
        with patch("app.main.room_store") as rooms:
            rooms.get_state_store.return_value = state_store

            response = main.create_user(ROOM_ID, main.CreateUserRequest(name="  Ada  "))

        self.assertEqual(response, added_user)
        state_store.add_user.assert_called_once_with("Ada")

    def test_create_user_rejects_a_blank_name(self):
        with self.assertRaises(HTTPException) as error:
            main.create_user(ROOM_ID, main.CreateUserRequest(name=" \t "))

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.detail, "Name cannot be empty")

    def test_toggle_user_returns_not_found_for_unknown_user_in_existing_room(self):
        state_store = Mock()
        state_store.toggle_check.return_value = None
        with patch("app.main.room_store") as rooms:
            rooms.get_state_store.return_value = state_store

            with self.assertRaises(HTTPException) as error:
                main.toggle_user(ROOM_ID, "missing", main.ToggleUserRequest(checked=True))

        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(error.exception.detail, "User not found")

    def test_delete_user_returns_success_after_deletion_from_requested_room(self):
        state_store = Mock()
        state_store.delete_user.return_value = True
        with patch("app.main.room_store") as rooms:
            rooms.get_state_store.return_value = state_store

            response = main.delete_user(ROOM_ID, "user-1")

        self.assertEqual(response, {"status": "success"})
        state_store.delete_user.assert_called_once_with("user-1")

    def test_pick_user_waits_then_uses_requested_room(self):
        user = User(id="user-1", name="Ada")
        state_store = Mock()
        state_store.get_state.return_value = StateResponse(
            users=[user, User(id="user-2", name="Grace")]
        )
        state_store.pick_next.return_value = user
        with patch("app.main.room_store") as rooms, patch(
            "app.main.asyncio.sleep", new_callable=AsyncMock
        ) as sleep:
            rooms.get_state_store.return_value = state_store

            response = asyncio.run(main.pick_user(ROOM_ID))

        self.assertEqual(response, user)
        sleep.assert_awaited_once_with(1.2)
        state_store.pick_next.assert_called_once_with()

    def test_pick_user_skips_delay_when_one_user_is_left(self):
        user = User(id="user-1", name="Ada")
        state_store = Mock()
        state_store.get_state.return_value = StateResponse(users=[user])
        state_store.pick_next.return_value = user
        with patch("app.main.room_store") as rooms, patch(
            "app.main.asyncio.sleep", new_callable=AsyncMock
        ) as sleep:
            rooms.get_state_store.return_value = state_store

            response = asyncio.run(main.pick_user(ROOM_ID))

        self.assertEqual(response, user)
        sleep.assert_not_awaited()
        state_store.pick_next.assert_called_once_with()

    def test_reset_round_delegates_to_requested_room(self):
        state_store = Mock()
        with patch("app.main.room_store") as rooms:
            rooms.get_state_store.return_value = state_store

            response = main.reset_round(ROOM_ID)

        self.assertEqual(response, {"status": "success"})
        state_store.reset_round.assert_called_once_with()
