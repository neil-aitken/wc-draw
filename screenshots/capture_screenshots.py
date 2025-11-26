"""
Automated screenshot capture for World Cup draw visualizations.
Captures screenshots for all cities and teams.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# City configurations
CITIES = [
    "atlanta",
    "boston",
    "dallas",
    "guadalajara",
    "houston",
    "kansas-city",
    "los-angeles",
    "mexico-city",
    "miami",
    "monterrey",
    "new-york",
    "philadelphia",
    "san-francisco",
    "seattle",
    "toronto",
    "vancouver",
]

CITY_NAMES = {
    "atlanta": "Atlanta",
    "boston": "Boston",
    "dallas": "Dallas",
    "guadalajara": "Guadalajara",
    "houston": "Houston",
    "kansas-city": "Kansas City",
    "los-angeles": "Los Angeles",
    "mexico-city": "Mexico City",
    "miami": "Miami",
    "monterrey": "Monterrey",
    "new-york": "New York/New Jersey",
    "philadelphia": "Philadelphia",
    "san-francisco": "San Francisco Bay Area",
    "seattle": "Seattle",
    "toronto": "Toronto",
    "vancouver": "Vancouver",
}


async def capture_city_views(base_url: str = "http://localhost:8080"):
    """Capture screenshots for all city views."""
    output_dir = Path(__file__).parent / "city_views"
    output_dir.mkdir(exist_ok=True)

    print("Capturing team view screenshots...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 2560, "height": 1440})

        for city in CITIES:
            display_name = CITY_NAMES[city]
            print(f"Capturing screenshot for {display_name}...")

            try:
                # Navigate to page
                await page.goto(f"{base_url}/city_team_viewer.html")

                # Wait for page to load
                await page.wait_for_load_state("networkidle")

                # Select the city from dropdown
                await page.select_option("select#citySelect", city)

                # Wait for chart to render
                await page.wait_for_timeout(1500)

                # Take screenshot
                filename = f"{city}.png"
                await page.screenshot(path=output_dir / filename, full_page=True)

                print(f"✓ Saved {filename}")
            except Exception as e:
                print(f"✗ Failed to capture {display_name}: {e}")

        await browser.close()

    print("\n✓ All city view screenshots captured!")
    print(f"  Output directory: {output_dir}")


async def capture_team_views(base_url: str = "http://localhost:8080"):
    """Capture screenshots for all team views."""
    # Read teams from CSV
    csv_path = Path(__file__).parent.parent / "teams.csv"
    teams = []

    with open(csv_path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split(",")
            if parts:
                team_name = parts[0].strip()
                if team_name:
                    teams.append(team_name)

    output_dir = Path(__file__).parent / "team_views"
    output_dir.mkdir(exist_ok=True)

    print("Capturing team view screenshots...\n")
    print(f"Found {len(teams)} teams\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})

        for team in teams:
            print(f"Capturing screenshot for {team}...")

            try:
                # Navigate to page
                await page.goto(f"{base_url}/city_probability_viewer.html")

                # Wait for page to load
                await page.wait_for_load_state("networkidle")

                # Select the team from dropdown
                await page.select_option("select#teamSelect", team)

                # Wait for charts to render
                await page.wait_for_timeout(2000)

                # Take screenshot
                filename = f"{team.lower().replace(' ', '_').replace('/', '-')}.png"
                await page.screenshot(path=output_dir / filename, full_page=True)

                print(f"✓ Saved {filename}")
            except Exception as e:
                print(f"✗ Failed to capture {team}: {e}")

        await browser.close()

    print("\n✓ All team view screenshots captured!")
    print(f"  Output directory: {output_dir}")


async def main():
    """Main function to capture all screenshots."""
    base_url = "http://localhost:8080"

    print("=" * 60)
    print("World Cup Draw Screenshot Capture")
    print("=" * 60)
    print()

    # Capture city views
    await capture_city_views(base_url)
    print()

    # Capture team views
    await capture_team_views(base_url)
    print()

    print("=" * 60)
    print("✓ All screenshots captured successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
