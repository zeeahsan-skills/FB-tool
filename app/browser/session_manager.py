import logging
from pathlib import Path

logger = logging.getLogger("facebook_agent.session")


class SessionManager:
    """Manages browser session profile directory state and persistence."""

    def __init__(self, profile_dir: Path):
        self.profile_dir = Path(profile_dir)

    def ensure_profile_dir(self) -> Path:
        """Ensures that the profile directory exists."""
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        return self.profile_dir

    def has_existing_session_data(self) -> bool:
        """Checks if the user profile directory has previous cookies/session data."""
        if not self.profile_dir.exists():
            return False
        # If there are any files or subdirectories inside, session files exist
        return any(self.profile_dir.iterdir())
