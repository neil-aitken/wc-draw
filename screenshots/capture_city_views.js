const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const cities = [
    'atlanta', 'boston', 'dallas', 'guadalajara', 'houston', 'kansas-city',
    'los-angeles', 'mexico-city', 'miami', 'monterrey', 'new-york',
    'philadelphia', 'san-francisco', 'seattle', 'toronto', 'vancouver'
];

const cityNames = {
    'atlanta': 'Atlanta',
    'boston': 'Boston',
    'dallas': 'Dallas',
    'guadalajara': 'Guadalajara',
    'houston': 'Houston',
    'kansas-city': 'Kansas City',
    'los-angeles': 'Los Angeles',
    'mexico-city': 'Mexico City',
    'miami': 'Miami',
    'monterrey': 'Monterrey',
    'new-york': 'New York/New Jersey',
    'philadelphia': 'Philadelphia',
    'san-francisco': 'San Francisco Bay Area',
    'seattle': 'Seattle',
    'toronto': 'Toronto',
    'vancouver': 'Vancouver'
};

async function captureScreenshots() {
    // Create output directory
    const outputDir = path.join(__dirname, 'city_views');
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 }
    });

    // Start local server (or use your existing one)
    const baseUrl = 'http://localhost:8080/city_team_viewer.html';

    console.log('Capturing city view screenshots...\n');

    for (const city of cities) {
        const displayName = cityNames[city];
        console.log(`Capturing screenshot for ${displayName}...`);
        
        try {
            // Navigate to page
            await page.goto(baseUrl);
            
            // Wait for page to load
            await page.waitForLoadState('networkidle');
            
            // Select the city from dropdown
            await page.selectOption('select#citySelect', city);
            
            // Wait for chart to render
            await page.waitForTimeout(1500);
            
            // Take screenshot
            const filename = `${city}.png`;
            await page.screenshot({
                path: path.join(outputDir, filename),
                fullPage: true
            });
            
            console.log(`✓ Saved ${filename}`);
        } catch (error) {
            console.error(`✗ Failed to capture ${displayName}: ${error.message}`);
        }
    }

    await browser.close();
    console.log('\n✓ All city view screenshots captured!');
    console.log(`  Output directory: ${outputDir}`);
}

captureScreenshots().catch(console.error);
