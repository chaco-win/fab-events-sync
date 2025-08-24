# Majors to always consider (worldwide)
MAJOR_TYPES = ["Pro Quest+", "Calling", "Battle Hardened", "National Championship", "Pro Tour", "World Championship"]

# Local radius caps (applied to events fetched with your ZIP that show "(NNN mi)")
TYPE_RADIUS_MILES = {
  "Pro Quest" = 250,
  "Road to Nationals" = 250,
  "Pre-release" = 50,
  "Skirmish" = 100
}

# Country allowlists per type (only include if address text contains one of these)
# Edit these: examples shown
TYPE_COUNTRY_WHITELIST = {
  "Battle Hardened" = ["USA", "United States", "US"]
  "National Championship" = ["USA", "United States", "US", "Canada", "United Kingdom", "UK"]
  # You can add more, e.g.:
  # "Calling" = ["USA", "Canada"]
}

TIMEZONE = "America/Chicago"
DEFAULT_EVENT_HOURS = 6
