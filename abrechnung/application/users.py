from datetime import datetime, timezone

import bcrypt

from abrechnung.domain.users import User
from . import Application, NotFoundError, CommandError


class InvalidPassword(Exception):
    pass


class LoginFailed(Exception):
    pass


class UserService(Application):
    @staticmethod
    def _hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password=password.encode("utf-8"), salt=salt).decode()

    @staticmethod
    def _check_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            password=password.encode("utf-8"),
            hashed_password=hashed_password.encode("utf-8"),
        )

    async def _verify_user_password(self, user_id: int, password: str) -> bool:
        async with self.db_pool.acquire() as conn:
            user = await conn.fetchrow(
                "select hashed_password, pending, deleted from usr where id = $1",
                user_id,
            )
            if user is None:
                raise NotFoundError(f"User with id {user_id} does not exist")

            if user["deleted"] or user["pending"]:
                return False

            return self._check_password(password, user["hashed_password"])

    async def login_user(self, username: str, password: str) -> tuple[int, str]:
        """
        validate whether a given user can login

        If successful return the user id and a session token
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                user = await conn.fetchrow(
                    "select id, hashed_password, pending, deleted from usr where username = $1",
                    username,
                )
                if user is None:
                    raise NotFoundError(f"User with username {username} does not exist")

                if not self._check_password(password, user["hashed_password"]):
                    raise InvalidPassword

                if user["pending"] or user["deleted"]:
                    raise LoginFailed(f"User is not permitted to login")

                session_token = await conn.fetchval(
                    "insert into session (user_id) values ($1) returning token",
                    user["id"],
                )

                return user["id"], session_token

    async def register_user(self, username: str, email: str, password: str) -> int:
        """Register a new user, returning the newly created user id and creating a pending registration entry"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                hashed_password = self._hash_password(password)
                user_id = await conn.fetchval(
                    "insert into usr (username, email, hashed_password) values ($1, $2, $3) returning id",
                    username,
                    email,
                    hashed_password,
                )
                if user_id is None:
                    raise CommandError(f"Registering new user failed")

                await conn.execute(
                    "insert into pending_registration (user_id) values ($1)", user_id
                )

                return user_id

    async def confirm_registration(self, token: str) -> int:
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "select user_id, valid_until from pending_registration where token = $1",
                    token,
                )
                if row is None:
                    raise PermissionError(f"Invalid registration token")

                user_id = row["user_id"]
                valid_until = row["valid_until"]
                if valid_until is None or valid_until < datetime.now(tz=timezone.utc):
                    raise PermissionError(f"Invalid registration token")

                await conn.execute(
                    "delete from pending_registration where user_id = $1", user_id
                )
                await conn.execute(
                    "update usr set pending = false where id = $1", user_id
                )

                return user_id

    async def get_user(self, user_id: int) -> User:
        async with self.db_pool.acquire() as conn:
            user = await conn.fetchrow(
                "select id, email, registered_at, username, pending, deleted from usr where id = $1",
                user_id,
            )

            if user is None:
                raise NotFoundError(f"User with id {user_id} does not exist")

            return User(
                id=user["id"],
                email=user["email"],
                registered_at=user["registered_at"],
                username=user["username"],
                pending=user["pending"],
                deleted=user["deleted"],
            )

    async def change_password(self, user_id: int, old_password: str, new_password: str):
        async with self.db_pool.acquire() as conn:
            valid_pw = await self._verify_user_password(user_id, old_password)
            if not valid_pw:
                raise InvalidPassword

            hashed_password = self._hash_password(new_password)
            await conn.execute(
                "update usr set hashed_password = $1 where id = $2",
                hashed_password,
                user_id,
            )

    async def request_email_change(self, user_id: int, password: str, email: str):
        async with self.db_pool.acquire() as conn:
            valid_pw = await self._verify_user_password(user_id, password)
            if not valid_pw:
                raise InvalidPassword

            await conn.execute(
                "insert into pending_email_change (user_id, new_email) values ($1, $2)",
                user_id,
                email,
            )

    async def confirm_email_change(self, token: str) -> int:
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "select user_id, new_email, valid_until from pending_email_change where token = $1",
                    token,
                )
                user_id = row["user_id"]
                valid_until = row["valid_until"]
                if valid_until is None or valid_until < datetime.now(tz=timezone.utc):
                    raise PermissionError

                await conn.execute(
                    "delete from pending_email_change where user_id = $1", user_id
                )
                await conn.execute(
                    "update usr set email = $2 where id = $1", user_id, row["new_email"]
                )

                return user_id