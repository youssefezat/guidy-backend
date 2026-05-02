import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Import your actual code
from main import app
from routing import find_shortest_path, get_route_data, STATIONS

# Set up the fake client to ping your API
client = TestClient(app)

# --- 1. CORE ALGORITHM TESTS ---

def test_find_shortest_path_same_line():
    """Test standard routing on Line 1."""
    path = find_shortest_path("New El-Marg", "Ain Shams")
    assert path == ["New El-Marg", "El-Marg", "Ain Shams"]

def test_find_shortest_path_with_transfer():
    """Test routing that requires transferring lines."""
    path = find_shortest_path("Sadat", "Opera")
    assert path == ["Sadat", "Opera"]

def test_find_shortest_path_invalid_nodes():
    """Ensure the algorithm handles typos gracefully."""
    path = find_shortest_path("Fake Station", "Sadat")
    assert path == []

# --- 2. BUSINESS LOGIC TESTS ---

def test_get_route_data_invalid_stations():
    """Test the error handling in route generation."""
    result = get_route_data("Mars", "Jupiter")
    assert result["success"] is False
    assert result["error"] == "Station not found."

# --- 3. API ENDPOINT TESTS ---

def test_fetch_stations_endpoint():
    """Test the /api/stations endpoint."""
    response = client.get("/api/stations")
    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert len(data["stations"]) > 0

# --- 4. EXTERNAL API MOCKING ---

@patch('routing.requests.get')
def test_calculate_route_tomtom_fallback(mock_get):
    """
    Test the /api/route endpoint while simulating a TomTom API crash.
    """
    # Force the mock to throw an error, triggering your fallback code
    mock_get.side_effect = Exception("TomTom Timeout")

    response = client.get("/api/route?start=Sadat&end=Opera")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert len(data["segments"]) > 0
    assert data["instructions"][0]["title"] == "Board Line 2"