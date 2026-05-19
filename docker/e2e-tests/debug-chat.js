import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:2026';

async function debugChatInterface() {
  console.log('Debugging Chat Interface...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    // Login
    await page.goto(`${BASE_URL}/sign-in`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);

    await page.locator('input[type="email"]').first().fill('sabar.bao@me.com');
    await page.locator('input[type="password"]').first().fill('MicxLocal123!');
    await page.locator('button:has-text("登录")').first().click();

    await page.waitForTimeout(5000);
    console.log('Logged in, URL:', page.url());

    // Take screenshot of chat page
    await page.screenshot({ path: '/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests/debug-chat-page.png', fullPage: true });
    console.log('Screenshot saved');

    // Get all buttons on page
    const buttons = await page.locator('button').all();
    console.log(`\nFound ${buttons.length} buttons on page:`);
    for (let i = 0; i < Math.min(buttons.length, 20); i++) {
      const text = await buttons[i].textContent();
      const isVisible = await buttons[i].isVisible().catch(() => false);
      console.log(`  Button ${i + 1}: "${text}" (visible: ${isVisible})`);
    }

    // Get all textareas
    const textareas = await page.locator('textarea').all();
    console.log(`\nFound ${textareas.length} textareas on page:`);
    for (let i = 0; i < textareas.length; i++) {
      const isVisible = await textareas[i].isVisible().catch(() => false);
      console.log(`  Textarea ${i + 1}: (visible: ${isVisible})`);
    }

    // Get all inputs
    const inputs = await page.locator('input').all();
    console.log(`\nFound ${inputs.length} inputs on page:`);
    for (let i = 0; i < Math.min(inputs.length, 20); i++) {
      const type = await inputs[i].getAttribute('type');
      const isVisible = await inputs[i].isVisible().catch(() => false);
      console.log(`  Input ${i + 1}: type="${type}" (visible: ${isVisible})`);
    }

    // Check page HTML structure
    const html = await page.content();
    console.log(`\nPage HTML length: ${html.length}`);
    console.log('First 2000 chars of body:');
    const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    if (bodyMatch) {
      console.log(bodyMatch[1].substring(0, 2000));
    }

  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    await browser.close();
  }
}

debugChatInterface().catch(console.error);