"""Settings from the environment: the account login and an optional time zone override."""
import os


def email() -> str:
    """Account e-mail."""
    return os.environ.get("EIGHTSLEEP_EMAIL", "").strip()


def password() -> str:
    """Account password."""
    return os.environ.get("EIGHTSLEEP_PASSWORD", "")


def timezone() -> str:
    """Empty = use the time zone of the user's device."""
    return os.environ.get("EIGHTSLEEP_TIMEZONE", "").strip()
