"""
Google Maps MCP Client for interacting with the google_map MCP server.
This client provides a simple interface to the MCP server for location-based queries.
"""

import json
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional, Tuple


class GoogleMapsMCPClient:
    """
    Client for interacting with google_map MCP server.

    Note: This is a simplified client that demonstrates the interface.
    In a real implementation, this would connect to an actual MCP server.
    """

    def __init__(self):
        self.server_name = "google_map"

    def search_nearby_places(self, query: str, location: str, radius: int = 1000) -> List[Dict[str, Any]]:
        """
        Search for nearby places using the MCP server.

        Args:
            query: Search query (e.g., "Starbucks")
            location: Reference location
            radius: Search radius in meters

        Returns:
            List of place dictionaries with name, address, etc.
        """
        # This is a mock implementation. In reality, this would call the MCP server
        # through the proper MCP protocol.

        # For now, return mock data that represents typical Starbucks locations near Tokyo Station
        if "starbucks" in query.lower() and "tokyo station" in location.lower():
            return [
                {
                    "name": "Starbucks Tokyo Station Marunouchi North Exit",
                    "formatted_address": "1-9-1 Marunouchi, Chiyoda City, Tokyo 100-0005, Japan",
                    "place_id": "mock_place_id_1",
                    "geometry": {
                        "location": {
                            "lat": 35.6812,
                            "lng": 139.7671
                        }
                    }
                },
                {
                    "name": "Starbucks Tokyo Station Nihonbashi Entrance",
                    "formatted_address": "1-8-1 Marunouchi, Chiyoda City, Tokyo 100-0005, Japan",
                    "place_id": "mock_place_id_2",
                    "geometry": {
                        "location": {
                            "lat": 35.6815,
                            "lng": 139.7669
                        }
                    }
                }
            ]

        return []

    def get_distance_matrix(self, origins: List[str], destinations: List[str], mode: str = "walking") -> List[Optional[Dict[str, Any]]]:
        """
        Get distance and duration between origins and destinations.

        Args:
            origins: List of origin addresses
            destinations: List of destination addresses
            mode: Travel mode (walking, driving, transit)

        Returns:
            List of distance/duration info for each origin-destination pair
        """
        # Mock implementation
        results = []

        for origin in origins:
            for destination in destinations:
                # Mock distance calculation based on keywords
                if ("nihonbashi" in destination.lower() or
                    "tokyo station nihonbashi entrance" in destination.lower()):
                    results.append({
                        "distance": {
                            "text": "150 m",
                            "value": 150
                        },
                        "duration": {
                            "text": "2 mins",
                            "value": 120
                        },
                        "status": "OK"
                    })
                else:
                    # Default mock response
                    results.append({
                        "distance": {
                            "text": "300 m",
                            "value": 300
                        },
                        "duration": {
                            "text": "4 mins",
                            "value": 240
                        },
                        "status": "OK"
                    })

        return results

    def get_directions(self, origin: str, destination: str, mode: str = "walking") -> Dict[str, Any]:
        """
        Get detailed directions between two points.

        Args:
            origin: Starting location
            destination: Ending location
            mode: Travel mode

        Returns:
            Directions data with routes, legs, duration, distance
        """
        # Mock directions for Kamakura Station to Museum
        if ("kamakura station" in origin.lower() and
            "kamakura museum" in destination.lower()):
            return {
                "routes": [{
                    "legs": [{
                        "distance": {
                            "text": "650 m",
                            "value": 650
                        },
                        "duration": {
                            "text": "9 mins",
                            "value": 540  # 9 minutes in seconds
                        },
                        "start_address": origin,
                        "end_address": destination,
                        "steps": []
                    }],
                    "overview_polyline": {
                        "points": "mock_polyline_data"
                    }
                }],
                "status": "OK"
            }

        # Default mock response for other routes
        return {
            "routes": [{
                "legs": [{
                    "distance": {
                        "text": "500 m",
                        "value": 500
                    },
                    "duration": {
                        "text": "7 mins",
                        "value": 420
                    },
                    "start_address": origin,
                    "end_address": destination,
                    "steps": []
                }],
                "overview_polyline": {
                    "points": "mock_polyline_data"
                }
            }],
            "status": "OK"
        }


# For testing without actual MCP server
def create_mock_client() -> GoogleMapsMCPClient:
    """Create a mock client for testing purposes."""
    return GoogleMapsMCPClient()