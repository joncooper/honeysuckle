"""UX context detection and management."""

from enum import Enum


class UXContext(Enum):
    """
    The UX context determines available input/output modalities.

    Low-bandwidth contexts: voice-only, limited visual feedback
    High-bandwidth contexts: full UI, voice + visual + keyboard/touch
    """

    # Low-bandwidth (voice-primary)
    AIRPODS = "airpods"  # Phone in pocket, audio only
    CARPLAY = "carplay"  # In car, minimal glanceable UI
    BLUETOOTH_CAR = "bluetooth_car"  # Car audio, no visual

    # High-bandwidth (full UI)
    DESKTOP = "desktop"  # Full visual + voice + keyboard
    PHONE_IN_HAND = "phone_in_hand"  # Full visual + voice + touch

    def is_low_bandwidth(self) -> bool:
        """Check if this is a low-bandwidth (voice-primary) context."""
        return self in {UXContext.AIRPODS, UXContext.CARPLAY, UXContext.BLUETOOTH_CAR}

    def is_high_bandwidth(self) -> bool:
        """Check if this is a high-bandwidth (full UI) context."""
        return self in {UXContext.DESKTOP, UXContext.PHONE_IN_HAND}

    def supports_visual_approval(self) -> bool:
        """Check if visual approval UI is available."""
        return self.is_high_bandwidth()

    def supports_complex_review(self) -> bool:
        """Check if detailed content review is feasible."""
        return self.is_high_bandwidth()


def detect_context() -> UXContext:
    """
    Detect the current UX context.

    TODO: Implement detection logic:
    - Check for CarPlay connection
    - Check for Bluetooth audio profile
    - Check screen state (on/off)
    - Check app state (foreground/background)
    - Client-reported context

    For now, default to desktop.
    """
    return UXContext.DESKTOP
