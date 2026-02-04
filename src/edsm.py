"""
EDSM API Integration
Fetches system and star information from EDSM (Elite Dangerous Star Map)
"""
import requests
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class EDSCState(Enum):
    """EDSM system state values"""
    None_value = 0
    Populated = 4
    MajorTreaty = 8
    War = 16
    CivilWar = 32
    Election = 64
    Retirement = 128
    Investment = 256
    Expansion = 512


@dataclass
class SystemInfo:
    """Information about a star system from EDSM"""
    name: str
    allegiance: Optional[str] = None
    government: Optional[str] = None
    population: Optional[int] = None
    security: Optional[str] = None
    economy: Optional[str] = None
    star_type: Optional[str] = None
    is_scoopable: bool = False
    bodies_count: int = 0
    landable_count: int = 0

    def get_description(self) -> str:
        """Generate a human-readable description"""
        parts = []

        # Basic info
        if self.allegiance:
            parts.append(f"{self.allegiance} controlled")

        if self.government:
            parts.append(f"{self.government.lower()} government")

        # Population
        if self.population is not None:
            if self.population == 0:
                pop_desc = "unpopulated"
            elif self.population < 10000:
                pop_desc = "small population"
            elif self.population < 1000000:
                pop_desc = "medium population"
            elif self.population < 10000000:
                pop_desc = "large population"
            else:
                pop_desc = "huge population"
            parts.append(pop_desc)

        # Security
        if self.security and self.security.lower() != "none":
            parts.append(f"{self.security.lower()} security")

        # Economy
        if self.economy:
            parts.append(f"{self.economy.lower()} economy")

        # Star info
        if self.star_type:
            scoop_desc = "excellent for fuel scooping" if self.is_scoopable else "not scoopable"
            parts.append(f"Main star is {self.star_type}-type ({scoop_desc})")

        # Bodies
        if self.bodies_count > 0:
            parts.append(f"{self.bodies_count} bodies")

        if self.landable_count > 0:
            parts.append(f"{self.landable_count} landable")

        return ", ".join(parts) if parts else "No detailed information available"


class EDSMAPI:
    """Interface to EDSM API"""

    BASE_URL = "https://www.edsm.net/api-v1"

    def __init__(self, api_key: Optional[str] = None, commander_name: Optional[str] = None):
        """
        Initialize EDSM API client

        Args:
            api_key: Optional EDSM API key (not needed for system info)
            commander_name: Optional commander name (not needed for system info)
        """
        self.api_key = api_key
        self.commander_name = commander_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EDAI-EliteDangerousAI/1.0'
        })

    def get_system_info(self, system_name: str) -> Optional[SystemInfo]:
        """
        Fetch information about a system from EDSM

        Args:
            system_name: Name of the star system

        Returns:
            SystemInfo object or None if not found
        """
        try:
            # Get system information
            url = f"{self.BASE_URL}/system"
            params = {
                'systemName': system_name,
                'showInformation': 1,
                'showPermits': 0
            }

            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if not data or (isinstance(data, list) and len(data) == 0):
                return None

            # EDSM returns a dict, not a list
            system_data = data if isinstance(data, dict) else data[0]

            # Check if the system was found
            if not system_data or 'name' not in system_data:
                return None

            # Get additional information about bodies/stars
            bodies_data = {}
            try:
                bodies_url = f"{self.BASE_URL}/system-bodies"
                bodies_params = {
                    'systemName': system_name,
                }

                bodies_response = self.session.get(bodies_url, params=bodies_params, timeout=5)
                bodies_response.raise_for_status()
                bodies_response_data = bodies_response.json()

                # Check if bodies is a list (has bodies) or dict (error/no bodies)
                if isinstance(bodies_response_data, dict) and 'bodies' in bodies_response_data:
                    bodies_data = bodies_response_data
                else:
                    bodies_data = {}
            except Exception:
                bodies_data = {}

            return self._parse_system_info(system_name, system_data, bodies_data)

        except requests.RequestException as e:
            print(f"EDSM API error: {e}")
            return None
        except Exception as e:
            print(f"Error parsing EDSM data: {e}")
            return None

    def _parse_system_info(self, name: str, system_data: Dict, bodies_data: Dict) -> SystemInfo:
        """
        Parse EDSM API response into SystemInfo object

        Args:
            name: System name
            system_data: System information from EDSM
            bodies_data: Bodies information from EDSM

        Returns:
            SystemInfo object
        """
        info = system_data.get('information', {})

        # Basic info
        allegiance = info.get('allegiance')
        government = info.get('government')
        population = info.get('population')
        security = info.get('security')
        economy = info.get('economy')

        # Star information
        star_type = None
        is_scoopable = False

        # Get primary star from bodies data
        if bodies_data and 'bodies' in bodies_data:
            for body in bodies_data.get('bodies', []):
                if body.get('type') == 'Star':
                    star_type = body.get('subType')
                    # Check if scoopable (O, B, A, F, G, K, M main sequence)
                    is_scoopable = star_type in [
                        'O (Blue-White)',
                        'B (Blue-White)',
                        'A (Blue-White)',
                        'F (White)',
                        'G (Yellow-White)',
                        'K (Yellow-Orange)',
                        'M (Red)'
                    ] if star_type else False
                    break  # Use primary star

        # Count landable bodies
        bodies_count = 0
        landable_count = 0

        if bodies_data and 'bodies' in bodies_data:
            bodies_count = len(bodies_data.get('bodies', []))
            landable_count = sum(
                1 for body in bodies_data.get('bodies', [])
                if body.get('isLandable')
            )

        return SystemInfo(
            name=name,
            allegiance=allegiance,
            government=government,
            population=population,
            security=security,
            economy=economy,
            star_type=star_type,
            is_scoopable=is_scoopable,
            bodies_count=bodies_count,
            landable_count=landable_count
        )

    def close(self):
        """Close the session"""
        self.session.close()


# Singleton instance
_edsm_instance: Optional[EDSMAPI] = None


def get_edsm_api() -> EDSMAPI:
    """Get or create the EDSM API singleton instance"""
    global _edsm_instance
    if _edsm_instance is None:
        _edsm_instance = EDSMAPI()
    return _edsm_instance


def test_edsm_api():
    """Test the EDSM API"""
    edsm = EDSMAPI()

    # Test with well-known systems
    test_systems = ["Sol", "Shinrarta Dezhra", "Colonia"]

    for system in test_systems:
        print(f"\nFetching info for: {system}")
        info = edsm.get_system_info(system)
        if info:
            print(f"  {info.get_description()}")
        else:
            print(f"  Not found")

    edsm.close()


if __name__ == "__main__":
    test_edsm_api()
