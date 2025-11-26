const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function captureScreenshots() {
    // Read teams from CSV
    const csvPath = path.join(__dirname, '..', 'teams.csv');
    const csvContent = fs.readFileSync(csvPath, 'utf-8');
    
    // Parse CSV manually to extract team names
    const teams = [];
    const lines = csvContent.split('\n');
    for (const line of lines) {
        if (line.startsWith('#') || !line.trim()) continue;
        const parts = line.split(',');
        if (parts.length > 0) {
            const teamName = parts[0].trim();
            if (teamName) {
                teams.push(teamName);
            }
        }
    }

    // Create output directory
    const outputDir = path.join(__dirname, 'team_views');
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 }
    });

    const baseUrl = 'http://localhost:8080/city_probability_viewer.html';

    console.log('Capturing team view screenshots...\n');
    console.log(`Found ${teams.length} teams\n`);

    for (const team of teams) {
        console.log(`Capturing screenshot for ${team}...`);
        
        try {
            // Navigate to page
            await page.goto(baseUrl);
            
            // Wait for page to load
            await page.waitForLoadState('networkidle');
            
            // Select the team from dropdown
            await page.selectOption('select#teamSelect', team);
            
            // Wait for charts to render
            await page.waitForTimeout(2000);
            
            // Take screenshot
            const filename = `${team.toLowerCase().replace(/ /g, '_').replace(/\//g, '-')}.png`;
            await page.screenshot({
                path: path.join(outputDir, filename),
                fullPage: true
            });
            
            console.log(`✓ Saved ${filename}`);
        } catch (error) {
            console.error(`✗ Failed to capture ${team}: ${error.message}`);
        }
    }

    await browser.close();
    console.log('\n✓ All team view screenshots captured!');
    console.log(`  Output directory: ${outputDir}`);
}

captureScreenshots().catch(console.error);
