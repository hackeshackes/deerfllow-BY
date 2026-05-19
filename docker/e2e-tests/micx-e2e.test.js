import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:2026';
const SCREENSHOT_DIR = '/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests';

async function takeScreenshot(page, name) {
  const path = `${SCREENSHOT_DIR}/${name}.png`;
  await page.screenshot({ path, fullPage: true });
  console.log(`Screenshot saved: ${path}`);
  return path;
}

async function runTests() {
  console.log('Starting MicX E2E Tests...\n');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const results = {
    tests: [],
    errors: [],
  };

  // Capture console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      results.errors.push(`Console Error: ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    results.errors.push(`Page Error: ${err.message}`);
  });

  try {
    // Test 1: Landing page loads
    console.log('Test 1: Landing page loads at http://localhost:2026');
    try {
      // Use 'load' instead of 'networkidle' to avoid WebGL/canvas hanging
      await page.goto(BASE_URL, { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(2000);
      await takeScreenshot(page, '01-landing-page');
      const title = await page.title();
      results.tests.push({ name: 'Landing page loads', status: 'PASS', details: `Title: ${title}` });
      console.log('  PASS - Landing page loaded\n');
    } catch (err) {
      results.tests.push({ name: 'Landing page loads', status: 'FAIL', details: err.message });
      console.log(`  FAIL - ${err.message}\n`);
    }

    // Test 2: Sign-in page loads
    console.log('Test 2: Sign-in page loads at http://localhost:2026/sign-in');
    try {
      await page.goto(`${BASE_URL}/sign-in`, { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(2000);
      await takeScreenshot(page, '02-sign-in-page');
      const signInTitle = await page.title();
      results.tests.push({ name: 'Sign-in page loads', status: 'PASS', details: `Title: ${signInTitle}` });
      console.log('  PASS - Sign-in page loaded\n');
    } catch (err) {
      results.tests.push({ name: 'Sign-in page loads', status: 'FAIL', details: err.message });
      console.log(`  FAIL - ${err.message}\n`);
    }

    // Test 3: Login with credentials
    console.log('Test 3: Login with email: sabar.bao@me.com and password: MicxLocal123!');
    try {
      // Wait for the page to be fully loaded
      await page.waitForTimeout(1000);

      // Fill email
      const emailInput = page.locator('input[type="email"]').first();
      await emailInput.waitFor({ timeout: 5000 });
      await emailInput.fill('sabar.bao@me.com');
      console.log('  - Email filled');

      // Fill password
      const passwordInput = page.locator('input[type="password"]').first();
      await passwordInput.fill('MicxLocal123!');
      console.log('  - Password filled');

      // Find and click the login button using Chinese text
      const submitButton = page.locator('button:has-text("登录")').first();
      await submitButton.click();
      console.log('  - Login button clicked');

      // Wait for navigation after login
      await page.waitForTimeout(5000);
      await takeScreenshot(page, '03-after-login');

      // Check current URL
      const currentUrl = page.url();
      console.log(`  - Current URL after login: ${currentUrl}`);

      if (currentUrl.includes('sign-in') || currentUrl.includes('login')) {
        results.tests.push({ name: 'User login', status: 'FAIL', details: `Still on sign-in page: ${currentUrl}` });
      } else {
        results.tests.push({ name: 'User login', status: 'PASS', details: `Redirected to: ${currentUrl}` });
      }
    } catch (err) {
      results.tests.push({ name: 'User login', status: 'FAIL', details: err.message });
      console.log(`  FAIL - ${err.message}\n`);
    }

    // Test 4: Workspace page loads after login
    console.log('Test 4: Workspace page loads after login');
    try {
      const workspaceContent = await page.content();
      const hasWorkspace = workspaceContent.length > 0;
      await takeScreenshot(page, '04-workspace-page');

      if (hasWorkspace) {
        results.tests.push({ name: 'Workspace page loads', status: 'PASS', details: `Content length: ${workspaceContent.length}` });
        console.log('  PASS - Workspace page loaded\n');
      } else {
        results.tests.push({ name: 'Workspace page loads', status: 'FAIL', details: 'Empty content' });
        console.log('  FAIL - Empty content\n');
      }
    } catch (err) {
      results.tests.push({ name: 'Workspace page loads', status: 'FAIL', details: err.message });
      console.log(`  FAIL - ${err.message}\n`);
    }

    // Test 5: Admin pages accessible
    const adminPages = [
      { name: 'Models', path: '/admin/models' },
      { name: 'Skills', path: '/admin/skills' },
      { name: 'Memory', path: '/admin/memory' },
    ];

    for (const adminPage of adminPages) {
      console.log(`Test 5${adminPages.indexOf(adminPage) + 1}: ${adminPage.name} admin page`);
      try {
        await page.goto(`${BASE_URL}${adminPage.path}`, { waitUntil: 'load', timeout: 30000 });
        await page.waitForTimeout(2000);
        await takeScreenshot(page, `05-admin-${adminPage.name.toLowerCase()}-page`);

        const currentUrl = page.url();
        const isAccessible = !currentUrl.includes('sign-in') && !currentUrl.includes('login');

        if (isAccessible) {
          results.tests.push({ name: `${adminPage.name} admin page accessible`, status: 'PASS', details: `URL: ${currentUrl}` });
          console.log(`  PASS - ${adminPage.name} page accessible at ${currentUrl}\n`);
        } else {
          results.tests.push({ name: `${adminPage.name} admin page accessible`, status: 'FAIL', details: `Redirected to: ${currentUrl}` });
          console.log(`  FAIL - Redirected to: ${currentUrl}\n`);
        }
      } catch (err) {
        results.tests.push({ name: `${adminPage.name} admin page accessible`, status: 'FAIL', details: err.message });
        console.log(`  FAIL - ${err.message}\n`);
      }
    }

  } catch (err) {
    results.errors.push(`Test execution error: ${err.message}`);
    console.log(`Fatal error: ${err.message}`);
  } finally {
    await browser.close();
  }

  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log('TEST SUMMARY');
  console.log('='.repeat(60));

  for (const test of results.tests) {
    const statusIcon = test.status === 'PASS' ? '[PASS]' : '[FAIL]';
    console.log(`${statusIcon} ${test.name}`);
    console.log(`       ${test.details}\n`);
  }

  if (results.errors.length > 0) {
    console.log('\nERRORS ENCOUNTERED:');
    for (const error of results.errors) {
      console.log(`  - ${error}`);
    }
  }

  const passedCount = results.tests.filter(t => t.status === 'PASS').length;
  const totalCount = results.tests.length;
  console.log(`\nTotal: ${passedCount}/${totalCount} tests passed`);

  return results;
}

runTests().catch(console.error);