"""Tool definitions for Foyle.

Currently uses gday CLI via Bash tool. May migrate to MCP tools
in the future for finer control and better observability.
"""

from honeysuckle.config import settings

# Path to gday CLI
GDAY_PATH = settings.gday_path


def build_gday_command(subcommand: str, *args: str, json_output: bool = True) -> str:
    """
    Build a gday CLI command.

    Args:
        subcommand: The gday subcommand (mail, cal, etc.)
        *args: Additional arguments
        json_output: Whether to add --json flag

    Returns:
        Complete command string
    """
    parts = [GDAY_PATH, subcommand, *args]
    if json_output:
        parts.append("--json")
    return " ".join(parts)


# Common gday commands
class GdayCommands:
    """Predefined gday command builders."""

    @staticmethod
    def list_unread_mail() -> str:
        """List unread emails."""
        return build_gday_command("mail", "list", "--unread")

    @staticmethod
    def list_mail() -> str:
        """List recent emails."""
        return build_gday_command("mail", "list")

    @staticmethod
    def read_mail(mail_id: str) -> str:
        """Read a specific email."""
        return build_gday_command("mail", "read", mail_id)

    @staticmethod
    def search_mail(query: str) -> str:
        """Search emails."""
        return build_gday_command("mail", "search", f'"{query}"')

    @staticmethod
    def send_mail(to: str, subject: str, body: str) -> str:
        """Send an email."""
        return build_gday_command(
            "mail", "send",
            "--to", to,
            "--subject", f'"{subject}"',
            "--body", f'"{body}"',
            json_output=False,
        )

    @staticmethod
    def reply_mail(mail_id: str, body: str) -> str:
        """Reply to an email."""
        return build_gday_command(
            "mail", "reply", mail_id,
            "--body", f'"{body}"',
            json_output=False,
        )

    @staticmethod
    def today_calendar() -> str:
        """Get today's calendar events."""
        return build_gday_command("cal", "today")

    @staticmethod
    def tomorrow_calendar() -> str:
        """Get tomorrow's calendar events."""
        return build_gday_command("cal", "tomorrow")

    @staticmethod
    def week_calendar() -> str:
        """Get this week's calendar events."""
        return build_gday_command("cal", "week")

    @staticmethod
    def create_event(description: str) -> str:
        """Create an event with natural language."""
        return build_gday_command(
            "cal", "create",
            "--quick", f'"{description}"',
            json_output=False,
        )
