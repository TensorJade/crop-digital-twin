"""Argon2id password adapter; credentials never reach a network service."""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type


class Argon2Passwords:
    """Use mature hashing and equivalent work for unknown usernames."""

    def __init__(self) -> None:
        self.hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, type=Type.ID)
        self._dummy = self.hasher.hash(secrets.token_urlsafe(32))

    def hash(self, password: str) -> str:
        """Hash with a fresh random salt provided by argon2-cffi."""
        return self.hasher.hash(password)

    def verify(self, password_hash: str | None, password: str) -> bool:
        """Mask account absence and corrupted hashes without exposing library messages."""
        try:
            matches = self.hasher.verify(password_hash or self._dummy, password)
            return password_hash is not None and matches
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """Allow the next successful login to upgrade a stored work factor."""
        return self.hasher.check_needs_rehash(password_hash)
