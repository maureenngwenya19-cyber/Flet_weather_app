# Import Flet to create the graphical user interface.
import flet as ft

# Import requests to communicate with the weather API.
import requests

# Import load_dotenv to load environment variables.
from dotenv import load_dotenv

# Import os to access the API key.
import os

# Import date and time tools for local city time and forecast days.
from datetime import datetime, timedelta, timezone

# Load variables from the .env file.
load_dotenv()

# OpenWeatherMap API endpoints.
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
ICON_URL = "https://openweathermap.org/img/wn/{icon}@4x.png"

# Get the API key from the .env file.
API_KEY = os.getenv("OPENWeatherAPP_API_KEY")

# Background gradients that change with the weather condition.
THEMES = {
    "clear_day": ["#1E90FF", "#56B4F9", "#9AD4FF"],
    "clear_night": ["#0B1D3A", "#1B2F5B", "#34466F"],
    "clouds": ["#4B6584", "#778CA3", "#A5B1C2"],
    "rain": ["#2C3E50", "#3D566E", "#5D7B93"],
    "thunderstorm": ["#1F1C2C", "#363456", "#4B4A74"],
    "snow": ["#7F9BB5", "#A9C1D6", "#DCE8F2"],
    "mist": ["#6C7A89", "#8E9AA6", "#B8C2CC"],
    "default": ["#1687E8", "#4AA8F2", "#8CCBFA"],
}


# Choose a gradient based on the weather condition and time of day.
def pick_theme(main: str, icon: str) -> list:
    main = main.lower()
    is_night = icon.endswith("n")

    if main == "clear":
        return THEMES["clear_night" if is_night else "clear_day"]
    if main == "clouds":
        return THEMES["clouds"]
    if main in ("rain", "drizzle"):
        return THEMES["rain"]
    if main == "thunderstorm":
        return THEMES["thunderstorm"]
    if main == "snow":
        return THEMES["snow"]
    if main in ("mist", "fog", "haze", "smoke", "dust", "sand", "ash"):
        return THEMES["mist"]
    return THEMES["default"]


# Convert a UTC timestamp to the city's local time.
def local_time(timestamp: int, tz_offset: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc) + timedelta(
        seconds=tz_offset
    )


# Convert wind degrees to a compass direction.
def wind_direction(deg: float) -> str:
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return directions[round(deg / 45) % 8]


# Function to fetch the 5-day forecast and reduce it to one entry per day.
def get_forecast(city: str, tz_offset: int) -> list:
    try:
        response = requests.get(
            FORECAST_URL,
            params={"q": city, "appid": API_KEY, "units": "metric"},
            timeout=10,
        )
        if response.status_code != 200:
            return []

        days = {}
        for item in response.json().get("list", []):
            dt = local_time(item["dt"], tz_offset)
            key = dt.date()
            days.setdefault(key, []).append((dt, item))

        forecast = []
        for key in sorted(days)[:5]:
            entries = days[key]

            # Use the entry closest to midday for the icon.
            midday = min(entries, key=lambda e: abs(e[0].hour - 12))[1]

            forecast.append(
                {
                    "day": datetime.combine(key, datetime.min.time()),
                    "icon": midday["weather"][0]["icon"],
                    "min": round(min(e[1]["main"]["temp_min"] for e in entries)),
                    "max": round(max(e[1]["main"]["temp_max"] for e in entries)),
                }
            )
        return forecast

    # The forecast is optional, so ignore any failure.
    except (requests.exceptions.RequestException, ValueError, KeyError):
        return []


# Function to fetch weather data for a given city.
def get_weather_data(city: str) -> dict:
    try:
        # Send a GET request to the weather API.
        response = requests.get(
            BASE_URL,
            params={
                "q": city,
                "appid": API_KEY,
                "units": "metric",
            },
            timeout=10,
        )

        # Convert the API response into a dictionary.
        data = response.json()

        # Check whether the request was successful.
        if response.status_code == 200:
            tz_offset = data.get("timezone", 0)
            weather = data["weather"][0]
            now = local_time(data["dt"], tz_offset)

            return {
                "success": True,
                "city": f"{data['name']}, {data['sys'].get('country', '')}",
                "date": now.strftime("%A, %d %B  •  %H:%M"),
                "temp": f"{round(data['main']['temp'])}°",
                "description": weather["description"].title(),
                "icon": weather["icon"],
                "main": weather["main"],
                "high": f"{round(data['main']['temp_max'])}°",
                "low": f"{round(data['main']['temp_min'])}°",
                "feels_like": f"{round(data['main']['feels_like'])}°C",
                "humidity": f"{data['main']['humidity']}%",
                "wind": (
                    f"{round(data['wind'].get('speed', 0) * 3.6)} km/h "
                    f"{wind_direction(data['wind'].get('deg', 0))}"
                ),
                "pressure": f"{data['main']['pressure']} hPa",
                "visibility": f"{data.get('visibility', 0) / 1000:.1f} km",
                "clouds": f"{data.get('clouds', {}).get('all', 0)}%",
                "sunrise": local_time(data["sys"]["sunrise"], tz_offset).strftime("%H:%M"),
                "sunset": local_time(data["sys"]["sunset"], tz_offset).strftime("%H:%M"),
                "forecast": get_forecast(city, tz_offset),
            }

        # Return the API error message.
        return {
            "success": False,
            "error": data.get("message", "City not found.").capitalize(),
        }

    # Handle network errors and timeouts.
    except requests.exceptions.RequestException:
        return {
            "success": False,
            "error": "Network error. Check your connection.",
        }

    # Handle invalid or unexpected JSON responses.
    except (ValueError, KeyError):
        return {
            "success": False,
            "error": "Unable to read weather data.",
        }


# Reusable frosted-glass style card.
def glass_card(content, padding=16, expand=False) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        border_radius=20,
        bgcolor="#26FFFFFF",
        expand=expand,
    )


# Small tile showing one weather detail (icon, label, value).
def detail_tile(icon, label: str, value: str) -> ft.Container:
    return glass_card(
        ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icon, size=16, color="#E6F2FF"),
                        ft.Text(label.upper(), size=11, color="#E6F2FF",
                                weight=ft.FontWeight.W_600),
                    ],
                    spacing=6,
                ),
                ft.Text(value, size=20, weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ],
            spacing=8,
        ),
        padding=14,
        expand=True,
    )


# One row of the 5-day forecast.
def forecast_row(item: dict, today) -> ft.Row:
    day_name = "Today" if item["day"].date() == today else item["day"].strftime("%a")
    return ft.Row(
        controls=[
            ft.Text(day_name, size=15, color="#FFFFFF",
                    weight=ft.FontWeight.W_500, width=60),
            ft.Image(src=ICON_URL.format(icon=item["icon"]), width=40, height=40),
            ft.Text(f"{item['min']}°", size=15, color="#D6E9FA", width=40,
                    text_align=ft.TextAlign.RIGHT),
            ft.Container(
                height=4,
                expand=True,
                border_radius=2,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(-1, 0),
                    end=ft.Alignment(1, 0),
                    colors=["#7FD1FF", "#FFD166"],
                ),
            ),
            ft.Text(f"{item['max']}°", size=15, color="#FFFFFF",
                    weight=ft.FontWeight.W_600, width=40),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )


# Main function that builds the Flet application.
def main(page: ft.Page):

    # Configure the application window.
    page.title = "Flet Weather App"
    page.window.height = 820
    page.window.width = 440
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0

    # Text field where the user enters a city name.
    city_input = ft.TextField(
        hint_text="Search city, e.g. Johannesburg",
        hint_style=ft.TextStyle(color="#D6E9FA"),
        text_style=ft.TextStyle(color="#FFFFFF"),
        prefix_icon=ft.Icons.LOCATION_ON_OUTLINED,
        border_radius=16,
        border_color="transparent",
        focused_border_color="#FFFFFF",
        bgcolor="#33FFFFFF",
        cursor_color="#FFFFFF",
        content_padding=ft.Padding(left=12, top=12, right=12, bottom=12),
        expand=True,
    )

    # Search button.
    search_btn = ft.IconButton(
        icon=ft.Icons.SEARCH,
        icon_color="#FFFFFF",
        bgcolor="#33FFFFFF",
        icon_size=24,
        tooltip="Search weather",
    )

    # Loading spinner shown while fetching data.
    loader = ft.ProgressRing(width=36, height=36, color="#FFFFFF", visible=False)

    # Error message shown in a red pill.
    error_text = ft.Text(value="", color="#FFFFFF", text_align=ft.TextAlign.CENTER)
    error_box = ft.Container(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.ERROR_OUTLINE, color="#FFFFFF", size=18), error_text],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        bgcolor="#CCD32F2F",
        border_radius=14,
        padding=12,
        visible=False,
    )

    # Empty-state message shown before the first search.
    welcome = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.WB_SUNNY_OUTLINED, size=80, color="#FFFFFF"),
                ft.Text("Check the weather", size=26, weight=ft.FontWeight.BOLD,
                        color="#FFFFFF"),
                ft.Text("Search for any city to see the current conditions "
                        "and the 5-day forecast.",
                        size=14, color="#E6F2FF", text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        padding=ft.Padding(left=20, top=80, right=20, bottom=0),
    )

    # Column that holds the weather results.
    results = ft.Column(spacing=16, visible=False)

    # Background container with a gradient that changes with the weather.
    background = ft.Container(
        expand=True,
        padding=24,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(0, -1),
            end=ft.Alignment(0, 1),
            colors=THEMES["default"],
        ),
        animate=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
    )

    # Build the results UI from the weather data.
    def build_results(w: dict):
        today = datetime.now(timezone.utc).date()

        # Main card: city, date, icon, temperature and description.
        main_card = glass_card(
            ft.Column(
                controls=[
                    ft.Text(w["city"], size=28, weight=ft.FontWeight.BOLD,
                            color="#FFFFFF", text_align=ft.TextAlign.CENTER),
                    ft.Text(w["date"], size=13, color="#E6F2FF"),
                    ft.Image(src=ICON_URL.format(icon=w["icon"]),
                             width=130, height=130),
                    ft.Text(w["temp"], size=76, weight=ft.FontWeight.W_300,
                            color="#FFFFFF"),
                    ft.Text(w["description"], size=20, weight=ft.FontWeight.W_500,
                            color="#FFFFFF"),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ARROW_UPWARD, size=16, color="#FFD166"),
                            ft.Text(w["high"], color="#FFFFFF", size=16),
                            ft.Container(width=12),
                            ft.Icon(ft.Icons.ARROW_DOWNWARD, size=16, color="#7FD1FF"),
                            ft.Text(w["low"], color="#FFFFFF", size=16),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=4,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=20,
        )

        # Grid of weather details.
        details = ft.Column(
            controls=[
                ft.Row([
                    detail_tile(ft.Icons.THERMOSTAT, "Feels like", w["feels_like"]),
                    detail_tile(ft.Icons.WATER_DROP_OUTLINED, "Humidity", w["humidity"]),
                ], spacing=12),
                ft.Row([
                    detail_tile(ft.Icons.AIR, "Wind", w["wind"]),
                    detail_tile(ft.Icons.COMPRESS, "Pressure", w["pressure"]),
                ], spacing=12),
                ft.Row([
                    detail_tile(ft.Icons.VISIBILITY_OUTLINED, "Visibility", w["visibility"]),
                    detail_tile(ft.Icons.CLOUD_OUTLINED, "Cloudiness", w["clouds"]),
                ], spacing=12),
                ft.Row([
                    detail_tile(ft.Icons.WB_TWILIGHT, "Sunrise", w["sunrise"]),
                    detail_tile(ft.Icons.NIGHTLIGHT_ROUND, "Sunset", w["sunset"]),
                ], spacing=12),
            ],
            spacing=12,
        )

        results.controls = [main_card, details]

        # 5-day forecast card, shown only if the forecast was loaded.
        if w["forecast"]:
            results.controls.append(
                glass_card(
                    ft.Column(
                        controls=[
                            ft.Row([
                                ft.Icon(ft.Icons.CALENDAR_MONTH, size=16, color="#E6F2FF"),
                                ft.Text("5-DAY FORECAST", size=12, color="#E6F2FF",
                                        weight=ft.FontWeight.W_600),
                            ], spacing=6),
                            *[forecast_row(item, today) for item in w["forecast"]],
                        ],
                        spacing=6,
                    )
                )
            )

    # Function called when the user searches for a city.
    def handle_search(e=None):
        city = (city_input.value or "").strip()

        # Hide any previous error message.
        error_box.visible = False

        # Validate the entered city.
        if not city:
            error_text.value = "Please enter a valid city."
            error_box.visible = True
            page.update()
            return

        # Show the loading spinner and hide old content.
        welcome.visible = False
        results.visible = False
        loader.visible = True
        page.update()

        # Fetch the weather data.
        result = get_weather_data(city)
        loader.visible = False

        if result["success"]:
            # Update the background gradient and show the results.
            background.gradient = ft.LinearGradient(
                begin=ft.Alignment(0, -1),
                end=ft.Alignment(0, 1),
                colors=pick_theme(result["main"], result["icon"]),
            )
            build_results(result)
            results.visible = True
        else:
            # Display the error returned by the API.
            error_text.value = result["error"]
            error_box.visible = True
            welcome.visible = True

        page.update()

    # Connect the search button and Enter key to the search function.
    search_btn.on_click = handle_search
    city_input.on_submit = handle_search

    # Put all content inside a scrollable column on the gradient background.
    background.content = ft.Column(
        controls=[
            ft.Row(controls=[city_input, search_btn], spacing=8),
            error_box,
            ft.Row([loader], alignment=ft.MainAxisAlignment.CENTER),
            welcome,
            results,
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    # Add the background to the page.
    page.add(background)


# Start the application.
if __name__ == "__main__":
    ft.run(main)