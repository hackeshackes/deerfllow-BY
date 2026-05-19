import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:2026';
const SCREENSHOT_DIR = '/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests';

async function runDebug() {
  console.log('Debugging MicX Sign-in Page...\n');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/sign-in`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'debug-sign-in-page');

    // Get all buttons
    console.log('\nAll buttons on sign-in page:');
    const buttons = await page.locator('button').all();
    for (let i = 0; i < buttons.length; i++) {
      const btn = buttons[i];
      const text = await btn.textContent();
      const type = await btn.getAttribute('type');
      const classes = await btn.getAttribute('class');
      console.log(`  [${i}] text="${text}" type="${type}" class="${classes}"`);
    }

    // Get all inputs
    console.log('\nAll inputs on sign-in page:');
    const inputs = await page.locator('input').all();
    for (let i = 0; i < inputs.length; i++) {
      const input = inputs[i];
      const type = await input.getAttribute('type');
      const name = await input.getAttribute('name');
      const placeholder = await input.getAttribute('placeholder');
      const id = await input.getAttribute('id');
      console.log(`  [${i}] type="${type}" name="${name}" placeholder="${placeholder}" id="${id}"`);
    }

    // Get form element
    console.log('\nForm element:');
    const form = await page.locator('form').first();
    if (form) {
      const formHTML = await form.innerHTML();
      console.log('Form HTML:', formHTML.substring(0, 500));
    }

  } finally {
    await browser.close();
  }
}

async function takeScreenshot(page, name) {
  const path = `${SCREENSHOT_DIR}/${name}.png`;
  await page.screenshot({ path, fullPage: true });
  console.log(`Screenshot saved: ${path}`);
  return path;
}

runDebug().catch(console.error);