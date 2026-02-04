"""
Game State Tracker
Maintains current state of the game from journal events
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ShipState(Enum):
    """Ship operational states"""
    NORMAL = "normal"
    LOW_FUEL = "low_fuel"
    SHIELDS_DOWN = "shields_down"
    DOCKED = "docked"
    IN_SUPERCURSE = "supercruise"
    IN_NORMAL_SPACE = "normal_space"


@dataclass
class GameState:
    """
    Tracks the current state of the game from journal events
    """
    # Location
    current_system: str = ""
    current_body: str = ""
    current_station: Optional[str] = None
    docked: bool = False

    # Movement state
    in_supercruise: bool = False
    in_normal_space: bool = False

    # Ship info
    ship_name: str = ""
    ship_type: str = ""

    # Ship status
    fuel_level: float = 100.0
    fuel_capacity: float = 32.0
    shields_up: bool = True
    hull_health: float = 100.0

    # Cargo and materials
    cargo_capacity: int = 0
    cargo_used: int = 0
    materials: Dict[str, int] = field(default_factory=dict)

    # Session stats
    jumps_this_session: int = 0
    bounties_claimed: int = 0
    materials_collected: int = 0
    last_docked: Optional[str] = None

    # Recent events for context (last 10 events)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)

    def get_context_description(self) -> str:
        """
        Generate a description of current game state for the LLM

        Returns:
            Formatted string with current context
        """
        parts = []

        # Location
        if self.current_system:
            loc_str = f"Currently in {self.current_system}"
            if self.current_station:
                loc_str += f", docked at {self.current_station}"
            elif self.in_supercruise:
                loc_str += " (in supercruise)"
            parts.append(loc_str)

        # Ship
        if self.ship_name and self.ship_type:
            parts.append(f"Piloting a {self.ship_type} called '{self.ship_name}'")

        # Fuel status
        fuel_percent = (self.fuel_level / self.fuel_capacity * 100) if self.fuel_capacity > 0 else 0
        if fuel_percent < 25:
            parts.append(f"Fuel is LOW: {fuel_percent:.0f}%")
        elif fuel_percent < 50:
            parts.append(f"Fuel is {fuel_percent:.0f}%")
        else:
            parts.append(f"Fuel is good: {fuel_percent:.0f}%")

        # Shields
        if not self.shields_up:
            parts.append("WARNING: Shields are DOWN!")

        # Session stats
        if self.jumps_this_session > 0:
            parts.append(f"Session stats: {self.jumps_this_session} jumps")

        if self.bounties_claimed > 0:
            parts.append(f"{self.bounties_claimed} bounties claimed")

        return ". ".join(parts) + "." if parts else "No game state available yet."

    def update_from_event(self, event_data: Dict[str, Any]) -> None:
        """
        Update game state from a journal event

        Args:
            event_data: Event data from journal
        """
        event_name = event_data.get("event", "")

        # Track recent events
        self.recent_events.append({
            "event": event_name,
            "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
            "data": event_data
        })
        # Keep only last 10 events
        if len(self.recent_events) > 10:
            self.recent_events = self.recent_events[-10:]

        # Update based on event type
        if event_name == "LoadGame":
            self.current_system = event_data.get("StarSystem", "")
            self.ship_name = event_data.get("ShipName", "")
            self.ship_type = event_data.get("Ship", "")
            self.fuel_level = event_data.get("FuelLevel", self.fuel_level)
            self.fuel_capacity = event_data.get("FuelCapacity", self.fuel_capacity)

        elif event_name == "FSDJump":
            self.current_system = event_data.get("StarSystem", "")
            self.current_body = event_data.get("Body", "")
            self.in_supercruise = False
            self.in_normal_space = True
            self.docked = False
            self.jumps_this_session += 1

        elif event_name == "SupercruiseEntry":
            self.in_supercruise = True
            self.in_normal_space = False

        elif event_name == "SupercruiseExit":
            self.in_supercruise = False
            self.in_normal_space = True

        elif event_name == "Docked":
            self.current_station = event_data.get("StationName", "")
            self.docked = True
            self.last_docked = self.current_station
            self.in_supercruise = False
            self.in_normal_space = False

        elif event_name == "Undocked":
            self.docked = False
            self.current_station = None

        elif event_name == "ShipRefuelled":
            fuel_added = event_data.get("Amount", 0)
            self.fuel_level = min(self.fuel_capacity, self.fuel_level + fuel_added)

        elif event_name == "ShieldState":
            self.shields_up = event_data.get("ShieldsUp", True)

        elif event_name == "ShipLowFuel":
            # Trigger low fuel state
            pass

        elif event_name == "Bounty":
            self.bounties_claimed += 1

        elif event_name == "MaterialCollected":
            material = event_data.get("Name", "")
            count = event_data.get("Count", 1)
            self.materials[material] = self.materials.get(material, 0) + count
            self.materials_collected += 1

        elif event_name == "Cargo":
            self.cargo_capacity = event_data.get("Capacity", self.cargo_capacity)
            self.cargo_used = event_data.get("Count", self.cargo_used)


class GameStateTracker:
    """
    Manages game state and provides context for AI responses
    """

    def __init__(self):
        """Initialize the game state tracker"""
        self.state = GameState()
        self.session_start = datetime.now()

    def update(self, event_data: Dict[str, Any]) -> None:
        """
        Update game state from a journal event

        Args:
            event_data: Event data from journal
        """
        self.state.update_from_event(event_data)

    def get_chat_context(self, user_message: str = "") -> str:
        """
        Get formatted context for chat messages

        Args:
            user_message: The user's message (can be used to customize context)

        Returns:
            Formatted context string for LLM
        """
        context_parts = []

        # Add current state description
        state_desc = self.state.get_context_description()
        if state_desc:
            context_parts.append(state_desc)

        # Add recent events if any
        if self.state.recent_events:
            recent = self.state.recent_events[-3:]  # Last 3 events
            event_summaries = []
            for ev in recent:
                ev_name = ev["event"]
                if ev_name == "FSDJump":
                    event_summaries.append(f"Jumped to {ev['data'].get('StarSystem', 'unknown')}")
                elif ev_name == "Docked":
                    event_summaries.append(f"Docked at {ev['data'].get('StationName', 'unknown')}")
                elif ev_name == "Scan":
                    event_summaries.append(f"Scanned {ev['data'].get('BodyName', 'body')}")

            if event_summaries:
                context_parts.append("Recent activity: " + ", ".join(event_summaries))

        return "\n\n".join(context_parts) if context_parts else "Starting new session."

    def get_current_system(self) -> str:
        """Get the current system name"""
        return self.state.current_system

    def is_docked(self) -> bool:
        """Check if currently docked"""
        return self.state.docked

    def get_fuel_status(self) -> tuple[float, float]:
        """Get current fuel level and capacity"""
        return self.state.fuel_level, self.state.fuel_capacity


# Singleton instance
_tracker_instance: Optional[GameStateTracker] = None


def get_game_state_tracker() -> GameStateTracker:
    """Get or create the game state tracker singleton"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = GameStateTracker()
    return _tracker_instance
