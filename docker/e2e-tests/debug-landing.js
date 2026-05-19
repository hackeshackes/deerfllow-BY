import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:2026';
const SCREENSHOT_DIR = '/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests';

async function takeScreenshot(page, name) {
  const path = `${SCREENSHOT_DIR}/${name}.png`;
  await page.screenshot({ path, fullPage: true });
  console.log(`Screenshot saved: ${path}`);
  return path;
}

async function runDebug() {
  console.log('Debugging landing page...\n');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // Capture console messages
  page.on('console', msg => {
    console.log(`Console [${msg.type()}]: ${msg.text()}`);
  });

  page.on('pageerror', err => {
    console.log(`Page error: ${err.message}`);
  });

  try {
    // Try with domcontentloaded instead of networkidle
    console.log('Navigating to landing page with domcontentloaded...');
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);
    await takeScreenshot(page, 'debug-landing-page');

    const title = await page.title();
    console.log(`Title: ${title}`);

    // Check what URL we are at
    console.log(`Current URL: ${page.url()}`);

    // Check if there's any content
    const bodyText = await page.locator('body').textContent();
    console.log(`Body text (first 200 chars): ${bodyText?.substring(0, 200)}`);

  } catch (err) {
    console.log(`Error: ${err.message}`);
  } finally {
    await browser.close();
  }
}

runDebug().catch(console.error);