import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:2026';
const SCREENSHOT_DIR = '/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests';

const PAGES_TO_TEST = [
  '/workspace/admin/monitoring',
  '/workspace/admin/config',
  '/workspace/admin/users',
  '/workspace/admin/audit',
  '/workspace/tasks',
  '/workspace/knowledge',
  '/workspace/automations',
  '/workspace/admin/models',
  '/workspace/admin/skills',
  '/workspace/admin/memory',
];

async function takeScreenshot(page, name) {
  const path = `${SCREENSHOT_DIR}/${name}.png`;
  await page.screenshot({ path, fullPage: true });
  return path;
}

async function runTests() {
  console.log('MicX E2E Test - Post-Rebuild 404 Verification\n');
  console.log('='.repeat(60));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const results = [];

  // Track HTTP 404 responses
  const http404s = [];
  page.on('response', response => {
    if (response.status() === 404) {
      http404s.push(response.url());
    }
  });

  try {
    // Step 1: Login
    console.log('\n1. Login');
    console.log('   URL: /sign-in');
    await page.goto(`${BASE_URL}/sign-in`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(2000);

    await page.locator('input[type="email"]').first().fill('sabar.bao@me.com');
    await page.locator('input[type="password"]').first().fill('MicxLocal123!');
    await page.locator('button:has-text("登录")').first().click();

    await page.waitForTimeout(5000);
    console.log(`   Current URL: ${page.url()}`);

    if (page.url().includes('sign-in')) {
      console.log('   [FAIL] Login failed - still on sign-in page');
      console.log('\n' + '='.repeat(60));
      console.log('RESULT: Cannot proceed - login failed');
      await browser.close();
      return;
    }
    console.log('   [PASS] Login successful');

    // Step 2: Test each page
    console.log('\n2. Testing Pages');
    console.log('-'.repeat(60));

    for (const path of PAGES_TO_TEST) {
      const url = `${BASE_URL}${path}`;
      console.log(`\n   ${path}`);

      try {
        http404s.length = 0; // Clear previous 404s
        const response = await page.goto(url, { waitUntil: 'load', timeout: 15000 });
        await page.waitForTimeout(2000);

        const finalUrl = page.url();
        const status = response ? response.status() : 'no-response';

        // Check if redirected to sign-in (access denied)
        if (finalUrl.includes('sign-in')) {
          console.log(`       [REDIRECTED] Access denied - redirected to sign-in`);
          results.push({ path, status: 'ACCESS DENIED', httpStatus: status });
          continue;
        }

        // Check page content for 404
        const content = await page.content();
        const has404Text = content.includes('404') && content.includes('Not Found');

        // Check if we got 404s in network requests
        const pageSpecific404s = http404s.filter(u =>
          u.includes(path) || u.includes(path.split('/').pop())
        );

        if (has404Text || pageSpecific404s.length > 0) {
          console.log(`       [FAIL] Page returned 404 (HTTP ${status})`);
          if (pageSpecific404s.length > 0) {
            console.log(`       404 resources: ${pageSpecific404s.length}`);
          }
          results.push({ path, status: '404', httpStatus: status });
        } else {
          console.log(`       [PASS] Page loaded successfully (HTTP ${status})`);
          results.push({ path, status: 'OK', httpStatus: status });
        }
      } catch (err) {
        console.log(`       [ERROR] ${err.message}`);
        results.push({ path, status: 'ERROR', httpStatus: 0 });
      }
    }

  } catch (err) {
    console.error(`Fatal error: ${err.message}`);
  } finally {
    await browser.close();
  }

  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log('TEST SUMMARY');
  console.log('='.repeat(60));

  const successCount = results.filter(r => r.status === 'OK').length;
  const failCount = results.filter(r => r.status === '404').length;
  const deniedCount = results.filter(r => r.status === 'ACCESS DENIED').length;
  const errorCount = results.filter(r => r.status === 'ERROR').length;

  console.log('\nPage Status:');
  console.log('-'.repeat(40));
  for (const r of results) {
    const icon = r.status === 'OK' ? '[PASS]' : r.status === '404' ? '[FAIL]' : r.status === 'ACCESS DENIED' ? '[DENIED]' : '[ERROR]';
    console.log(`  ${icon} ${r.path}`);
    console.log(`         HTTP ${r.httpStatus}`);
  }

  console.log('\n' + '='.repeat(60));
  console.log(`Result: ${successCount}/${results.length} pages working`);
  console.log(`  - OK (working): ${successCount}`);
  console.log(`  - 404 (broken): ${failCount}`);
  console.log(`  - Access Denied: ${deniedCount}`);
  console.log(`  - Errors: ${errorCount}`);
  console.log('='.repeat(60));

  return results;
}

runTests().catch(console.error);