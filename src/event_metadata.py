"""
Event Metadata - Display names and information for Elite Dangerous events
"""

# All available events with friendly display names
EVENT_DISPLAY_NAMES = {
    # Navigation
    "FSDJump": "FSD Jump Complete",
    "StartJump": "Starting FSD Jump",
    "SupercruiseEntry": "Entering Supercruise",
    "SupercruiseExit": "Exiting Supercruise",
    "JumpReq": "Jump Required",

    # Docking
    "DockingGranted": "Docking Granted",
    "DockingDenied": "Docking Denied",
    "DockingCancelled": "Docking Cancelled",
    "DockingRequested": "Requesting Docking",
    "Undocked": "Undocked from Station",

    # Combat/Status
    "ShieldState": "Shield Status Changed",
    "ShipLowFuel": "Low Fuel Warning",
    "Died": "Ship Destroyed",
    "Bounty": "Bounty Claimed",
    "Resurrect": "Resurrected",
    "UnderAttack": "Under Attack",
    "PVPKill": "PVP Kill",
    "Interdicted": "Being Interdicted",
    "Interdiction": "Interdiction Attempt",
    "EscapeInterdiction": "Escaped Interdiction",
    "HullDamage": "Hull Damage",
    "FighterDestroyed": "Fighter Destroyed",
    "SRVDestroyed": "SRV Destroyed",
    "HeatWarning": "Heat Warning",
    "HeatDamage": "Heat Damage",
    "CockpitBreached": "Cockpit Breached",
    "SelfDestruct": "Self Destruct",
    "CommitCrime": "Crime Committed",
    "FactionKillBond": "Faction Kill Bond",

    # Exploration
    "Scan": "Body Scanned",
    "SAASignalsFound": "SAA Signals Discovered",
    "MaterialCollected": "Material Collected",
    "MaterialDiscarded": "Material Discarded",

    # Missions
    "MissionAccepted": "Mission Accepted",
    "MissionCompleted": "Mission Completed",
    "MissionFailed": "Mission Failed",
    "MissionRedirected": "Mission Redirected",
    "CommunityGoal": "Community Goal Update",

    # Crew/Multiplayer
    "CrewAssign": "Crew Role Assigned",
    "CrewMemberJoins": "Crew Member Joined",
    "CrewMemberQuits": "Crew Member Quit",
    "CrewLaunchFighter": "Fighter Launched",
    "CrewMemberRoleChange": "Crew Role Changed",

    # Engineering
    "Synthesis": "Synthesis Complete",
    "EngineerCraft": "Engineer Crafting Complete",

    # System
    "LoadGame": "Game Loaded/Commander Login",
    "FuelFull": "Fuel Tank Full",
}

# All available events (for UI generation)
ALL_AVAILABLE_EVENTS = list(EVENT_DISPLAY_NAMES.keys())

# Default recommended events
RECOMMENDED_EVENTS = [
    "FSDJump",
    "DockingGranted",
    "ShieldState",
    "ShipLowFuel",
    "Bounty",
    "Died",
    "Scan",
    "MissionCompleted",
    "UnderAttack",
    "HullDamage",
]
