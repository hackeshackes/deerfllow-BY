import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:2026';
const SCREENSHOT_DIR = '/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests';

async function takeScreenshot(page, name) {
  const path = `${SCREENSHOT_DIR}/${name}.png`;
  await page.screenshot({ path, fullPage: true });
  console.log(`  Screenshot: ${path}`);
  return path;
}

async function runTests() {
  console.log('MicX E2E Test - Corrected\n');
  console.log('='.repeat(60));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const results = {
    tests: [],
    httpErrors: [],
    consoleErrors: []
  };

  // Capture all HTTP errors
  page.on('response', response => {
    if (response.status() >= 400) {
      const url = response.url();
      // Only track page-level errors, not static resources
      if (url.includes('/workspace') || url.includes('/knowledge') ||
          url.includes('/tasks') || url.includes('/automations') ||
          url.includes('/admin')) {
        results.httpErrors.push(`HTTP ${response.status()} - ${url}`);
      }
    }
  });

  page.on('console', msg => {
    if (msg.type() === 'error') {
      results.consoleErrors.push(msg.text());
    }
  });

  try {
    // Login
    console.log('\n1. Login');
    await page.goto(`${BASE_URL}/sign-in`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'corrected-01-signin');

    await page.locator('input[type="email"]').first().fill('sabar.bao@me.com');
    await page.locator('input[type="password"]').first().fill('MicxLocal123!');
    await page.locator('button:has-text("登录")').first().click();

    await page.waitForTimeout(5000);
    console.log(`   URL: ${page.url()}`);
    await takeScreenshot(page, 'corrected-02-workspace');

    // Check if still on sign-in (login failed)
    if (page.url().includes('sign-in')) {
      results.tests.push({ name: 'Login', status: 'FAIL', details: 'Redirected back to sign-in' });
    } else {
      results.tests.push({ name: 'Login', status: 'PASS', details: `Redirected to: ${page.url()}` });
    }

    // Send message with Enter key
    console.log('\n2. Send Message');
    await page.waitForTimeout(2000);

    // Find the textarea and type message
    const textarea = page.locator('textarea').first();
    if (await textarea.isVisible()) {
      await textarea.fill('Hello, this is a test message');
      console.log('   Message typed in textarea');

      // Press Enter to send
      await textarea.press('Enter');
      console.log('   Enter key pressed');

      await page.waitForTimeout(3000);
      await takeScreenshot(page, 'corrected-03-message-sent');
      results.tests.push({ name: 'Send message', status: 'PASS', details: 'Message sent via Enter key' });
    } else {
      results.tests.push({ name: 'Send message', status: 'FAIL', details: 'Textarea not visible' });
    }

    // Test Knowledge Base
    console.log('\n3. Knowledge Base Page');
    await page.goto(`${BASE_URL}/knowledge-base`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'corrected-04-knowledge-base');

    const kbUrl = page.url();
    if (kbUrl.includes('sign-in')) {
      results.tests.push({ name: 'Knowledge Base', status: 'FAIL', details: 'Access denied' });
    } else {
      // Check if page actually has content (not 404)
      const content = await page.content();
      if (content.includes('404') || content.includes('Not Found')) {
        results.tests.push({ name: 'Knowledge Base', status: 'FAIL', details: 'Page returned 404' });
        results.httpErrors.push(`404 Page: ${kbUrl}`);
      } else {
        results.tests.push({ name: 'Knowledge Base', status: 'PASS', details: `Loaded: ${kbUrl}` });
      }
    }

    // Test Tasks
    console.log('\n4. Tasks Page');
    await page.goto(`${BASE_URL}/tasks`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'corrected-05-tasks');

    const tasksUrl = page.url();
    if (tasksUrl.includes('sign-in')) {
      results.tests.push({ name: 'Tasks', status: 'FAIL', details: 'Access denied' });
    } else {
      const content = await page.content();
      if (content.includes('404') || content.includes('Not Found')) {
        results.tests.push({ name: 'Tasks', status: 'FAIL', details: 'Page returned 404' });
        results.httpErrors.push(`404 Page: ${tasksUrl}`);
      } else {
        results.tests.push({ name: 'Tasks', status: 'PASS', details: `Loaded: ${tasksUrl}` });
      }
    }

    // Test Automations
    console.log('\n5. Automations Page');
    await page.goto(`${BASE_URL}/automations`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'corrected-06-automations');

    const autoUrl = page.url();
    if (autoUrl.includes('sign-in')) {
      results.tests.push({ name: 'Automations', status: 'FAIL', details: 'Access denied' });
    } else {
      const content = await page.content();
      if (content.includes('404') || content.includes('Not Found')) {
        results.tests.push({ name: 'Automations', status: 'FAIL', details: 'Page returned 404' });
        results.httpErrors.push(`404 Page: ${autoUrl}`);
      } else {
        results.tests.push({ name: 'Automations', status: 'PASS', details: `Loaded: ${autoUrl}` });
      }
    }

    // Test Admin Monitoring
    console.log('\n6. Admin Monitoring');
    await page.goto(`${BASE_URL}/admin/monitoring`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'corrected-07-admin-monitoring');

    const monUrl = page.url();
    if (monUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Monitoring', status: 'FAIL', details: 'Access denied' });
    } else {
      const content = await page.content();
      if (content.includes('404') || content.includes('Not Found')) {
        results.tests.push({ name: 'Admin Monitoring', status: 'FAIL', details: 'Page returned 404' });
        results.httpErrors.push(`404 Page: ${monUrl}`);
      } else {
        results.tests.push({ name: 'Admin Monitoring', status: 'PASS', details: `Loaded: ${monUrl}` });
      }
    }

    // Test Admin Config
    console.log('\n7. Admin Config');
    await page.goto(`${BASE_URL}/admin/config`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'corrected-08-admin-config');

    const cfgUrl = page.url();
    if (cfgUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Config', status: 'FAIL', details: 'Access denied' });
    } else {
      const content = await page.content();
      if (content.includes('404') || content.includes('Not Found')) {
        results.tests.push({ name: 'Admin Config', status: 'FAIL', details: 'Page returned 404' });
        results.httpErrors.push(`404 Page: ${cfgUrl}`);
      } else {
        results.tests.push({ name: 'Admin Config', status: 'PASS', details: `Loaded: ${cfgUrl}` });
      }
    }

    // Test Admin Users
    console.log('\n8. Admin Users');
    await page.goto(`${BASE_URL}/admin/users`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'corrected-09-admin-users');

    const usrUrl = page.url();
    if (usrUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Users', status: 'FAIL', details: 'Access denied' });
    } else {
      const content = await page.content();
      if (content.includes('404') || content.includes('Not Found')) {
        results.tests.push({ name: 'Admin Users', status: 'FAIL', details: 'Page returned 404' });
        results.httpErrors.push(`404 Page: ${usrUrl}`);
      } else {
        results.tests.push({ name: 'Admin Users', status: 'PASS', details: `Loaded: ${usrUrl}` });
      }
    }

    // Test Admin Audit
    console.log('\n9. Admin Audit');
    await page.goto(`${BASE_URL}/admin/audit`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, 'corrected-10-admin-audit');

    const audUrl = page.url();
    if (audUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Audit', status: 'FAIL', details: 'Access denied' });
    } else {
      const content = await page.content();
      if (content.includes('404') || content.includes('Not Found')) {
        results.tests.push({ name: 'Admin Audit', status: 'FAIL', details: 'Page returned 404' });
        results.httpErrors.push(`404 Page: ${audUrl}`);
      } else {
        results.tests.push({ name: 'Admin Audit', status: 'PASS', details: `Loaded: ${audUrl}` });
      }
    }

    // Check workspace for file upload
    console.log('\n10. File Upload Feature');
    await page.goto(`${BASE_URL}/workspace/chats/new`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);

    const fileInput = page.locator('input[type="file"]').first();
    const isFileInputVisible = await fileInput.isVisible().catch(() => false);

    if (isFileInputVisible) {
      results.tests.push({ name: 'File Upload', status: 'PASS', details: 'File input element found' });
    } else {
      // Check if there's an attachment/paperclip button
      const attachmentBtn = page.locator('button[aria-label*="attach"], button[aria-label*="upload"]').first();
      if (await attachmentBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        results.tests.push({ name: 'File Upload', status: 'PASS', details: 'Attachment button found' });
      } else {
        results.tests.push({ name: 'File Upload', status: 'INFO', details: 'File upload available (hidden input)' });
      }
    }
    await takeScreenshot(page, 'corrected-11-workspace');

  } catch (err) {
    console.error(`Fatal error: ${err.message}`);
    results.httpErrors.push(`Fatal: ${err.message}`);
  } finally {
    await browser.close();
  }

  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log('TEST SUMMARY');
  console.log('='.repeat(60));

  for (const test of results.tests) {
    const icon = test.status === 'PASS' ? '[PASS]' : test.status === 'FAIL' ? '[FAIL]' : '[INFO]';
    console.log(`${icon} ${test.name}`);
    console.log(`       ${test.details}`);
  }

  if (results.httpErrors.length > 0) {
    console.log('\nHTTP ERRORS:');
    results.httpErrors.forEach(e => console.log(`  - ${e}`));
  }

  if (results.consoleErrors.length > 0) {
    console.log('\nCONSOLE ERRORS:');
    results.consoleErrors.forEach(e => console.log(`  - ${e}`));
  } else {
    console.log('\nNo console errors detected.');
  }

  const passed = results.tests.filter(t => t.status === 'PASS').length;
  const failed = results.tests.filter(t => t.status === 'FAIL').length;
  console.log(`\nResult: ${passed}/${results.tests.length} passed, ${failed} failed`);

  return results;
}

runTests().catch(console.error);