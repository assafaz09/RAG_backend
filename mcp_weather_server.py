#!/usr/bin/env python3
"""
Weather MCP Server - מביא מידע אמיתי על מזג אוויר מהאינטרנט
Uses Open-Meteo API (חינמי, לא צריך API Key)
"""

from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("Weather MCP")

# מילון של ערים עם קואורדינטות
CITIES = {
    "london": {"lat": 51.5074, "lon": -0.1278},
    "new york": {"lat": 40.7128, "lon": -74.0060},
    "tel aviv": {"lat": 32.0853, "lon": 34.7818},
    "jerusalem": {"lat": 31.7683, "lon": 35.2137},
    "paris": {"lat": 48.8566, "lon": 2.3522},
    "tokyo": {"lat": 35.6762, "lon": 139.6503},
    "sydney": {"lat": -33.8688, "lon": 151.2093},
    "berlin": {"lat": 52.5200, "lon": 13.4050},
    "moscow": {"lat": 55.7558, "lon": 37.6173},
    "dubai": {"lat": 25.2048, "lon": 55.2708},
    "miami": {"lat": 25.7617, "lon": -80.1918},
    "los angeles": {"lat": 34.0522, "lon": -118.2437},
    "chicago": {"lat": 41.8781, "lon": -87.6298},
    "toronto": {"lat": 43.6532, "lon": -79.3832},
    "mumbai": {"lat": 19.0760, "lon": 72.8777},
    "singapore": {"lat": 1.3521, "lon": 103.8198},
    "hong kong": {"lat": 22.3193, "lon": 114.1694},
    "bangkok": {"lat": 13.7563, "lon": 100.5018},
    "istanbul": {"lat": 41.0082, "lon": 28.9784},
    "rome": {"lat": 41.9028, "lon": 12.4964},
}


@mcp.tool()
def get_weather(city: str) -> str:
    """
    Get current weather for a city.
    
    Args:
        city: Name of the city (e.g., "London", "New York", "Tel Aviv")
    """
    city_lower = city.lower().strip()
    
    # חיפוש העיר ברשימה
    if city_lower not in CITIES:
        available = ", ".join(sorted(CITIES.keys())[:10]) + "..."
        return f"Sorry, I don't have coordinates for '{city}'. Available cities include: {available}"
    
    coords = CITIES[city_lower]
    
    try:
        # קריאה ל-API חינמי
        url = f"https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        current = data.get("current", {})
        temp = current.get("temperature_2m", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        wind = current.get("wind_speed_10m", "N/A")
        code = current.get("weather_code", 0)
        
        # תרגום קוד מזג אוויר לתיאור
        weather_desc = get_weather_description(code)
        
        return (
            f"🌍 Weather in {city.title()}:\n"
            f"🌡️ Temperature: {temp}°C\n"
            f"💧 Humidity: {humidity}%\n"
            f"💨 Wind Speed: {wind} km/h\n"
            f"☁️ Conditions: {weather_desc}"
        )
        
    except Exception as e:
        return f"Error fetching weather: {str(e)}"


@mcp.tool()
def get_forecast(city: str, days: int = 3) -> str:
    """
    Get weather forecast for a city.
    
    Args:
        city: Name of the city
        days: Number of days for forecast (1-7)
    """
    city_lower = city.lower().strip()
    days = min(max(days, 1), 7)  # הגבלה בין 1-7
    
    if city_lower not in CITIES:
        return f"Sorry, I don't have coordinates for '{city}'"
    
    coords = CITIES[city_lower]
    
    try:
        url = f"https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "timezone": "auto",
            "forecast_days": days
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        codes = daily.get("weather_code", [])
        
        result = f"📅 {days}-Day Forecast for {city.title()}:\n\n"
        
        for i in range(len(dates)):
            date = dates[i]
            max_t = max_temps[i] if i < len(max_temps) else "N/A"
            min_t = min_temps[i] if i < len(min_temps) else "N/A"
            code = codes[i] if i < len(codes) else 0
            desc = get_weather_description(code)
            
            result += f"📆 {date}:\n"
            result += f"   High: {max_t}°C | Low: {min_t}°C\n"
            result += f"   {desc}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error fetching forecast: {str(e)}"


@mcp.tool()
def list_supported_cities() -> str:
    """List all cities supported by the weather service."""
    cities = sorted(CITIES.keys())
    return f"🌍 Supported Cities ({len(cities)}):\n" + "\n".join([f"• {c.title()}" for c in cities])


def get_weather_description(code: int) -> str:
    """Convert weather code to description."""
    codes = {
        0: "☀️ Clear sky",
        1: "🌤️ Mainly clear",
        2: "⛅ Partly cloudy",
        3: "☁️ Overcast",
        45: "🌫️ Fog",
        48: "🌫️ Depositing rime fog",
        51: "🌦️ Light drizzle",
        53: "🌧️ Moderate drizzle",
        55: "🌧️ Dense drizzle",
        61: "🌧️ Slight rain",
        63: "🌧️ Moderate rain",
        65: "🌧️ Heavy rain",
        71: "🌨️ Slight snow",
        73: "🌨️ Moderate snow",
        75: "🌨️ Heavy snow",
        77: "❄️ Snow grains",
        80: "🌦️ Slight rain showers",
        81: "🌧️ Moderate rain showers",
        82: "⛈️ Violent rain showers",
        85: "🌨️ Slight snow showers",
        86: "🌨️ Heavy snow showers",
        95: "⛈️ Thunderstorm",
        96: "⛈️ Thunderstorm with hail",
        99: "⛈️ Thunderstorm with heavy hail",
    }
    return codes.get(code, "🌡️ Unknown")


if __name__ == "__main__":
    mcp.run()
