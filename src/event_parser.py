"""
Event Parser - Filters and formats Elite Dangerous events
This module filters relevant events and formats them for the LLM
"""
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading


# Import EDSM API for system information
try:
    from edsm import get_edsm_api
    EDSM_AVAILABLE = True
except ImportError:
    EDSM_AVAILABLE = False


class EventPriority(Enum):
    """Priority levels for events"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ParsedEvent:
    """
    Represents a parsed and formatted event
    """
    event_type: str
    priority: EventPriority
    formatted_text: str
    raw_data: Dict
    is_urgent: bool = False


class EventParser:
    """
    Parses and formats Elite Dangerous journal events
    """

    # Default event whitelist - events we want to comment on
    DEFAULT_WHITELIST = {
        "FSDJump",
        "DockingGranted",
        "DockingDenied",
        "ShieldState",
        "ShipLowFuel",
        "Bounty",
        "Died",
        "MaterialCollected",
        "JumpReq",
        "FuelFull",
        "Scan",
        "SAASignalsFound",
        "CommunityGoal",
        "CrewAssign",
        "CrewMemberJoins",
        "CrewMemberQuits",
        "CrewLaunchFighter",
        "CrewMemberRoleChange",
        "DockingCancelled",
        "DockingRequested",
        "Undocked",
        "SupercruiseExit",
        "SupercruiseEntry",
        "MaterialDiscarded",
        "Synthesis",
        "EngineerCraft",
        "MissionAccepted",
        "MissionCompleted",
        "MissionFailed",
        "MissionRedirected",
        "Resurrect",
        "StartJump",
        "LoadGame",
        "Music"
    }

    # Events that should trigger immediate, pre-canned responses
    URGENT_EVENTS = {
        "ShipLowFuel",
        "Died",
        "ShieldState"
    }

    def __init__(self, whitelist: Optional[set] = None, urgent_events: Optional[set] = None, use_edsm: bool = True):
        """
        Initialize the event parser

        Args:
            whitelist: Set of event names to process (None for default)
            urgent_events: Set of event names considered urgent (None for default)
            use_edsm: Whether to fetch system information from EDSM API
        """
        self.whitelist = whitelist if whitelist is not None else self.DEFAULT_WHITELIST
        self.urgent_events = urgent_events if urgent_events is not None else self.URGENT_EVENTS
        self.use_edsm = use_edsm and EDSM_AVAILABLE
        self.edsm_api = get_edsm_api() if self.use_edsm else None

        # Cache for system information to avoid repeated API calls
        self.system_cache: Dict[str, any] = {}
        self.cache_lock = threading.Lock()

    def is_relevant(self, event_data: Dict) -> bool:
        """
        Check if an event should be processed

        Args:
            event_data: Raw event data from journal

        Returns:
            True if event is in whitelist
        """
        event_name = event_data.get("event", "")
        return event_name in self.whitelist

    def is_urgent(self, event_data: Dict) -> bool:
        """
        Check if an event is urgent (requires immediate response)

        Args:
            event_data: Raw event data from journal

        Returns:
            True if event is urgent
        """
        event_name = event_data.get("event", "")
        return event_name in self.urgent_events

    def parse(self, event_data: Dict) -> Optional[ParsedEvent]:
        """
        Parse and format an event

        Args:
            event_data: Raw event data from journal

        Returns:
            ParsedEvent object or None if event is not relevant
        """
        if not self.is_relevant(event_data):
            return None

        event_name = event_data.get("event", "")
        is_urgent = self.is_urgent(event_data)

        # Determine priority
        if is_urgent:
            priority = EventPriority.URGENT
        elif event_name in {"FSDJump", "DockingGranted", "Scan"}:
            priority = EventPriority.HIGH
        elif event_name in {"MaterialCollected", "Bounty", "MissionCompleted"}:
            priority = EventPriority.NORMAL
        else:
            priority = EventPriority.LOW

        # Format the event for the LLM
        formatted_text = self._format_event(event_name, event_data)

        return ParsedEvent(
            event_type=event_name,
            priority=priority,
            formatted_text=formatted_text,
            raw_data=event_data,
            is_urgent=is_urgent
        )

    def _format_event(self, event_name: str, event_data: Dict) -> str:
        """
        Format an event into a descriptive string for the LLM

        Args:
            event_name: Name of the event
            event_data: Raw event data

        Returns:
            Formatted description string
        """
        formatters = {
            "FSDJump": self._format_fsd_jump,
            "DockingGranted": self._format_docking_granted,
            "DockingDenied": self._format_docking_denied,
            "ShieldState": self._format_shield_state,
            "ShipLowFuel": self._format_low_fuel,
            "Bounty": self._format_bounty,
            "Died": self._format_died,
            "MaterialCollected": self._format_material_collected,
            "Scan": self._format_scan,
            "Undocked": self._format_undocked,
            "SupercruiseEntry": self._format_supercruise_entry,
            "SupercruiseExit": self._format_supercruise_exit,
            "FuelFull": self._format_fuel_full,
            "StartJump": self._format_start_jump,
            "LoadGame": self._format_load_game,
        }

        formatter = formatters.get(event_name)
        if formatter:
            return formatter(event_data)
        else:
            # Generic formatter for unhandled events
            return self._format_generic(event_name, event_data)

    # Event formatters

    def _format_fsd_jump(self, data: Dict) -> str:
        """Format FSDJump event with optional EDSM information"""
        system = data.get("StarSystem", "Unknown System")
        body = data.get("Body", "Unknown Body")

        # Build base message
        parts = [f"Arrived in {system}"]

        # Add EDSM information if available
        if self.use_edsm and self.edsm_api:
            system_info = self._get_system_info(system)
            if system_info:
                parts.append(system_info.get_description())

        # Add body info
        if body and body != "Unknown Body":
            parts.append(f"Near {body}")

        return ". ".join(parts) + "."

    def _get_system_info(self, system_name: str) -> Optional[any]:
        """
        Get system information from EDSM with caching

        Args:
            system_name: Name of the star system

        Returns:
            SystemInfo object or None
        """
        # Check cache first
        with self.cache_lock:
            if system_name in self.system_cache:
                return self.system_cache[system_name]

        # Fetch from EDSM
        if self.edsm_api:
            info = self.edsm_api.get_system_info(system_name)

            # Cache the result
            with self.cache_lock:
                self.system_cache[system_name] = info

            return info

        return None

    def _format_docking_granted(self, data: Dict) -> str:
        """Format DockingGranted event"""
        station = data.get("StationName", "Unknown Station")
        return f"Docking granted at {station}."

    def _format_docking_denied(self, data: Dict) -> str:
        """Format DockingDenied event"""
        station = data.get("StationName", "Unknown Station")
        reason = data.get("Reason", "No reason given")
        return f"Docking denied at {station}. Reason: {reason}."

    def _format_shield_state(self, data: Dict) -> str:
        """Format ShieldState event"""
        shields_up = data.get("ShieldsUp", True)
        if not shields_up:
            return "WARNING: Shields have gone down!"
        return "Shields are back online."

    def _format_low_fuel(self, data: Dict) -> str:
        """Format ShipLowFuel event"""
        return "CRITICAL: Ship fuel is critically low!"

    def _format_bounty(self, data: Dict) -> str:
        """Format Bounty event"""
        target = data.get("Target", "Unknown")
        reward = data.get("TotalReward", 0)
        return f"Bounty claimed: {reward} credits for {target}."

    def _format_died(self, data: Dict) -> str:
        """Format Died event"""
        return "ALERT: Ship has been destroyed. Commander, you have died."

    def _format_material_collected(self, data: Dict) -> str:
        """Format MaterialCollected event"""
        material = data.get("Name", "Unknown Material")
        return f"Material collected: {material}."

    def _format_scan(self, data: Dict) -> str:
        """Format Scan event"""
        body_type = data.get("BodyType", "Unknown")
        name = data.get("BodyName", "Unknown")
        return f"Scan complete: {name} ({body_type})."

    def _format_undocked(self, data: Dict) -> str:
        """Format Undocked event"""
        station = data.get("StationName", "Unknown Station")
        return f"Undocked from {station}."

    def _format_supercruise_entry(self, data: Dict) -> str:
        """Format SupercruiseEntry event"""
        system = data.get("StarSystem", "Unknown System")
        return f"Entering supercruise in {system}."

    def _format_supercruise_exit(self, data: Dict) -> str:
        """Format SupercruiseExit event"""
        body_type = data.get("BodyType", "Unknown")
        return f"Dropping from supercruise near {body_type}."

    def _format_fuel_full(self, data: Dict) -> str:
        """Format FuelFull event"""
        return "Fuel tanks are now full."

    def _format_start_jump(self, data: Dict) -> str:
        """Format StartJump event"""
        system = data.get("StarSystem", "Unknown System")
        jump_type = data.get("JumpType", "Hyperspace")
        return f"Initiating {jump_type} jump to {system}."

    def _format_load_game(self, data: Dict) -> str:
        """Format LoadGame event"""
        commander = data.get("Commander", "Commander")
        ship = data.get("Ship", "Unknown Ship")
        return f"Welcome back, Commander {commander}. Systems online. Aboard the {ship}."

    def _format_generic(self, event_name: str, data: Dict) -> str:
        """Generic formatter for unhandled events"""
        return f"Event detected: {event_name}."


# Pre-canned urgent responses for instant playback
CANNED_RESPONSES = {
    "ShipLowFuel": [
        "Fuel critical! Find a refuel immediately!",
        "Warning! Fuel reserves depleted!"
    ],
    "Died": [
        "Ship destroyed. Reinitiating systems...",
        "Critical failure. Ship destroyed."
    ],
    "ShieldState": [
        "Shields down! Evasive action recommended!",
        "Shield failure detected!"
    ]
}


def get_canned_response(event_name: str) -> Optional[str]:
    """
    Get a pre-canned response for an urgent event

    Args:
        event_name: Name of the event

    Returns:
        Canned response string or None
    """
    import random

    responses = CANNED_RESPONSES.get(event_name)
    if responses:
        return random.choice(responses)
    return None
