import os
import sys
from unittest.mock import patch, MagicMock
import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api import fetch_city_forecast, parse_forecast_data, suggest_cities, WeatherAPIError

SAMPLE_API_RESPONSE = {
    "city": {
        "id": 710791,
        "name": "Cherkasy",
        "country": "UA",
        "population": 272651,
        "timezone": 7200
    },
    "list": [
        {
            "dt_txt": "2026-11-15 18:00:00",
            "main": {"temp": 5.5, "feels_like": 2.1, "humidity": 80},
            "weather": [{"description": "хмарно"}],
            "wind": {"speed": 4.2}
        }
    ]
}


def test_parse_forecast_data():
    parsed = parse_forecast_data(SAMPLE_API_RESPONSE, state="Cherkasy Oblast")
    assert parsed["city"]["city_id"] == 710791
    assert parsed["city"]["name"] == "Cherkasy (Cherkasy Oblast)"
    assert len(parsed["forecasts"]) == 1
    assert parsed["forecasts"][0]["temp"] == 5.5
    assert parsed["forecasts"][0]["description"] == "хмарно"


@patch("app.api.Config.validate")
@patch("app.api.requests.get")
def test_suggest_cities(mock_get, mock_validate):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "name": "Trostianets",
            "local_names": {"uk": "Тростянець"},
            "state": "Sumy Oblast",
            "country": "UA",
            "lat": 50.48,
            "lon": 34.96
        },
        {
            "name": "Trostianets",
            "local_names": {"uk": "Тростянець"},
            "state": "Vinnytsia Oblast",
            "country": "UA",
            "lat": 48.51,
            "lon": 29.22
        }
    ]
    mock_get.return_value = mock_resp

    suggestions = suggest_cities("Тростянець")
    assert len(suggestions) == 2
    assert suggestions[0]["label"] == "Тростянець, Sumy Oblast, UA"
    assert suggestions[1]["label"] == "Тростянець, Vinnytsia Oblast, UA"


@patch("app.api.Config.validate")
@patch("app.api.requests.get")
def test_api_status_not_200(mock_get, mock_validate):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    with pytest.raises(WeatherAPIError, match="404"):
        fetch_city_forecast("NonExistentCity123")


@patch("app.api.Config.validate")
@patch("app.api.requests.get")
def test_api_network_error(mock_get, mock_validate):
    mock_get.side_effect = requests.exceptions.ConnectionError()

    with pytest.raises(WeatherAPIError, match="Помилка мережі"):
        fetch_city_forecast("Cherkasy")


@patch("app.api.Config.validate")
@patch("app.api.requests.get")
def test_api_empty_response(mock_get, mock_validate):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "   "
    mock_get.return_value = mock_resp

    with pytest.raises(WeatherAPIError, match="порожню відповідь"):
        fetch_city_forecast("Cherkasy")
