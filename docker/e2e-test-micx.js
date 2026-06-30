import { chromium } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:2026';
const EMAIL = process.env.E2E_EMAIL;
const PASSWORD = process.env.E2E_PASSWORD;

if (!EMAIL || !PASSWORD) {
  throw new Error(
    'E2E_EMAIL and E2E_PASSWORD environment variables are required. ' +
    'Set them in your shell or a local .env (not committed).',
  );
}


async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', err => {
    consoleErrors.push(`PAGE ERROR: ${err.message}`);
  });

  async function screenshot(name, pageRef = page) {
    const path = `/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/test-results/${name}.png`;
    await pageRef.screenshot({ path, fullPage: true });
    results.screenshots.push(path);
    console.log(`  Screenshot: ${path}`);
    return path;
  }

  async function testPage(name, url, checkFn) {
    try {
      console.log(`\n[TEST] ${name} (${url})`);
      await page.goto(`${BASE_URL}${url}`, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(2000);

      const content = await page.content();
      const hasRebuilding = content.includes('channel is being rebuilt') || content.includes('rebuilding');

      if (hasRebuilding) {
        console.log(`  WARN: Found "rebuilding" message`);
      }

      if (checkFn) await checkFn(page);

      await screenshot(name.replace(/\s+/g, '_').toLowerCase());
      results.passed.push(name);
      console.log(`  PASS`);
    } catch (err) {
      results.failed.push({ name, url, error: err.message });
      console.log(`  FAIL: ${err.message}`);
      await screenshot(`${name.replace(/\s+/g, '_').toLowerCase()}_error`);
    }
  }

  // 1. Login
  console.log('\n=== LOGIN ===');
  try {
    await page.goto(`${BASE_URL}/sign-in`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await screenshot('login_page');

    // Fill using input types
    await page.locator('input[type="email"]').fill(EMAIL);
    await page.locator('input[type="password"]').fill(PASSWORD);
    await screenshot('login_filled');

    // Submit - try any button or pressing Enter
    await page.locator('button').first().click();
    await page.waitForTimeout(5000);
    await screenshot('after_login');
    console.log('  Login submitted');
  } catch (err) {
    console.log(`  LOGIN FAIL: ${err.message}`);
    await screenshot('login_error');
    results.failed.push({ name: 'Login', error: err.message });
    await browser.close();
    return;
  }

  // 2. Admin pages
  console.log('\n=== ADMIN PAGES ===');
  await testPage('Admin Monitoring', '/workspace/admin/monitoring');
  await testPage('Admin Config', '/workspace/admin/config');
  await testPage('Admin Models', '/workspace/admin/models');
  await testPage('Admin Skills', '/workspace/admin/skills');
  await testPage('Admin Memory', '/workspace/admin/memory');
  await testPage('Admin Users', '/workspace/admin/users');
  await testPage('Admin Audit', '/workspace/admin/audit');

  // 3. Workspace pages
  console.log('\n=== WORKSPACE PAGES ===');
  await testPage('Tasks', '/workspace/tasks');
  await testPage('Knowledge Base', '/workspace/knowledge');

  // 4. Workspace chat
  console.log('\n=== WORKSPACE CHAT ===');
  try {
    console.log('[TEST] Workspace Chat - New Thread');
    await page.goto(`${BASE_URL}/workspace/chats/new`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await screenshot('chat_new_page');

    const textarea = page.locator('textarea').first();
    await textarea.fill('Hello, this is a test message');
    await screenshot('chat_message_typed');

    const sendBtn = page.locator('button:has-text("Send"), button[type="submit"]').first();
    await sendBtn.click();
    await page.waitForTimeout(3000);
    await screenshot('chat_response');

    const content = await page.content();
    const hasRebuilding = content.includes('channel is being rebuilt');
    if (hasRebuilding) {
      results.failed.push({ name: 'Chat - No Rebuilding', error: 'Found "channel is being rebuilt" message' });
      console.log('  FAIL: Found "channel is being rebuilt" message');
    } else {
      results.passed.push('Chat - No Rebuilding');
      console.log('  PASS: No rebuilding error');
    }
  } catch (err) {
    results.failed.push({ name: 'Workspace Chat', error: err.message });
    console.log(`  FAIL: ${err.message}`);
  }

  // 5. Report console errors
  console.log('\n=== CONSOLE ERRORS ===');
  if (consoleErrors.length > 0) {
    console.log(`Found ${consoleErrors.length} console errors:`);
    consoleErrors.forEach((e, i) => console.log(`  ${i + 1}. ${e}`));
  } else {
    console.log('No console errors found');
  }

  // Summary
  console.log('\n=== SUMMARY ===');
  console.log(`Passed: ${results.passed.length}`);
  results.passed.forEach(n => console.log(`  - ${n}`));
  console.log(`\nFailed: ${results.failed.length}`);
  results.failed.forEach(f => console.log(`  - ${f.name}: ${f.error}`));
  console.log(`\nScreenshots: ${results.screenshots.length}`);
  results.screenshots.forEach(s => console.log(`  - ${s}`));

  await browser.close();
  process.exit(results.failed.length > 0 ? 1 : 0);
}

run().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});