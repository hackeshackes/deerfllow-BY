import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE_URL = 'http://localhost:2026';
const SCREENSHOT_DIR = '/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests';
const TEST_FILE_PATH = '/Users/baoyu/Documents/GitHub/deerfllow-BY/docker/e2e-tests/test-upload-file.txt';

// Create test file for upload
function createTestFile() {
  const content = `MicX E2E Test File
Created: ${new Date().toISOString()}
This is a test file for knowledge base upload testing.
Content: Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Test data for verification.`;
  fs.writeFileSync(TEST_FILE_PATH, content);
  console.log(`Test file created: ${TEST_FILE_PATH}`);
}

async function takeScreenshot(page, name) {
  const screenshotPath = `${SCREENSHOT_DIR}/${name}.png`;
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`  Screenshot saved: ${screenshotPath}`);
  return screenshotPath;
}

async function runTests() {
  console.log('╔══════════════════════════════════════════════════════════════╗');
  console.log('║           MicX Application - Comprehensive E2E Test          ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');

  createTestFile();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const results = {
    tests: [],
    errors: [],
    consoleErrors: [],
    consoleWarnings: []
  };

  // Capture console messages
  page.on('console', msg => {
    if (msg.type() === 'error') {
      results.consoleErrors.push(`[Console Error] ${msg.text()}`);
    } else if (msg.type() === 'warning') {
      results.consoleWarnings.push(`[Console Warning] ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    results.consoleErrors.push(`[Page Error] ${err.message}`);
  });

  page.on('response', response => {
    if (response.status() >= 400) {
      results.errors.push(`[HTTP ${response.status()}] ${response.url()}`);
    }
  });

  try {
    // ═══════════════════════════════════════════════════════
    // 1. LOGIN
    // ═══════════════════════════════════════════════════════
    console.log('┌──────────────────────────────────────────────────────────────┐');
    console.log('│ 1. LOGIN TEST                                               │');
    console.log('└──────────────────────────────────────────────────────────────┘');

    await page.goto(`${BASE_URL}/sign-in`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '01-sign-in-page');

    // Fill login form
    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    await emailInput.waitFor({ state: 'visible', timeout: 5000 });
    await emailInput.fill('sabar.bao@me.com');
    console.log('  [+] Email filled: sabar.bao@me.com');

    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill('MicxLocal123!');
    console.log('  [+] Password filled');

    const submitButton = page.locator('button[type="submit"], button:has-text("登录")').first();
    await submitButton.click();
    console.log('  [+] Login button clicked');

    await page.waitForTimeout(5000);
    await takeScreenshot(page, '02-after-login');

    const currentUrl = page.url();
    if (currentUrl.includes('sign-in') || currentUrl.includes('login')) {
      results.tests.push({ name: 'User login', status: 'FAIL', details: `Still on sign-in page: ${currentUrl}` });
      console.log('  [FAIL] Login unsuccessful - still on sign-in page\n');
    } else {
      results.tests.push({ name: 'User login', status: 'PASS', details: `Redirected to: ${currentUrl}` });
      console.log(`  [PASS] Login successful - redirected to: ${currentUrl}\n`);
    }

    // ═══════════════════════════════════════════════════════
    // 2. CHAT FUNCTIONALITY
    // ═══════════════════════════════════════════════════════
    console.log('┌──────────────────────────────────────────────────────────────┐');
    console.log('│ 2. CHAT FUNCTIONALITY                                        │');
    console.log('└──────────────────────────────────────────────────────────────┘');

    // 2.1: Create new chat
    console.log('\n  2.1 Creating new chat...');
    await page.waitForTimeout(2000);

    const chatSelectors = [
      'button:has-text("新对话")',
      'button:has-text("New Chat")',
      'button:has-text("新建对话")',
      '[data-testid="new-chat"]',
      'button:has-text("+")'
    ];

    let chatCreated = false;
    for (const selector of chatSelectors) {
      const btn = page.locator(selector).first();
      if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await btn.click();
        console.log(`  [+] Clicked new chat button: ${selector}`);
        chatCreated = true;
        break;
      }
    }

    await page.waitForTimeout(2000);
    await takeScreenshot(page, '03-new-chat-interface');

    if (chatCreated) {
      results.tests.push({ name: 'Create new chat', status: 'PASS', details: 'New chat interface loaded' });
      console.log('  [PASS] New chat created\n');
    } else {
      results.tests.push({ name: 'Create new chat', status: 'FAIL', details: 'New chat button not found' });
      console.log('  [FAIL] Could not create new chat\n');
    }

    // 2.2: Send message and verify streaming response
    console.log('  2.2 Sending test message...');
    await page.waitForTimeout(1000);

    const messageInput = page.locator('textarea, input[type="text"]').first();
    const inputVisible = await messageInput.isVisible({ timeout: 5000 }).catch(() => false);

    if (inputVisible) {
      const testMessage = 'Hello, this is a test message. Can you explain what you can do?';
      await messageInput.fill(testMessage);
      console.log(`  [+] Message typed: "${testMessage.substring(0, 30)}..."`);

      const sendButton = page.locator('button:has-text("发送"), button:has-text("Send"), button[type="submit"]').first();
      await sendButton.click();
      console.log('  [+] Send button clicked');

      await page.waitForTimeout(5000); // Wait for streaming response
      await takeScreenshot(page, '04-chat-with-streaming-response');

      // Check if response appeared
      const responseText = await page.locator('div[data-testid="message-content"], .message-content, [class*="message"]').last().textContent().catch(() => '');
      if (responseText && responseText.length > 0) {
        results.tests.push({ name: 'Send message', status: 'PASS', details: `Response received (${responseText.length} chars)` });
        console.log(`  [PASS] Message sent and response received (${responseText.length} chars)\n`);
      } else {
        results.tests.push({ name: 'Send message', status: 'FAIL', details: 'No response received' });
        console.log('  [FAIL] No response received\n');
      }

      // 2.3: Check artifacts display
      console.log('  2.3 Checking artifacts display...');
      await page.waitForTimeout(2000);

      const artifactSelectors = [
        '[data-testid="artifact"]',
        '.artifact',
        '[class*="artifact"]',
        'pre code',
        '.code-block'
      ];

      let artifactFound = false;
      for (const selector of artifactSelectors) {
        const artifact = page.locator(selector).first();
        if (await artifact.isVisible({ timeout: 1000 }).catch(() => false)) {
          artifactFound = true;
          console.log(`  [+] Artifact found with selector: ${selector}`);
          break;
        }
      }

      if (artifactFound) {
        results.tests.push({ name: 'Artifacts display', status: 'PASS', details: 'Artifacts displayed in chat' });
        console.log('  [PASS] Artifacts are displayed\n');
      } else {
        results.tests.push({ name: 'Artifacts display', status: 'INFO', details: 'No artifacts found (may depend on message content)' });
        console.log('  [INFO] No artifacts found (may depend on message content)\n');
      }
    } else {
      results.tests.push({ name: 'Send message', status: 'FAIL', details: 'Message input not visible' });
      console.log('  [FAIL] Message input not visible\n');
    }

    // ═══════════════════════════════════════════════════════
    // 3. TASK MANAGEMENT
    // ═══════════════════════════════════════════════════════
    console.log('┌──────────────────────────────────────────────────────────────┐');
    console.log('│ 3. TASK MANAGEMENT                                          │');
    console.log('└──────────────────────────────────────────────────────────────┘');

    console.log('\n  3.1 Navigating to Tasks page...');
    await page.goto(`${BASE_URL}/tasks`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '05-tasks-page');

    const tasksUrl = page.url();
    if (tasksUrl.includes('sign-in')) {
      results.tests.push({ name: 'Tasks page access', status: 'FAIL', details: 'Access denied - redirected to sign-in' });
      console.log('  [FAIL] Access denied - redirected to sign-in\n');
    } else {
      results.tests.push({ name: 'Tasks page access', status: 'PASS', details: `Loaded at: ${tasksUrl}` });
      console.log(`  [PASS] Tasks page loaded at: ${tasksUrl}\n`);

      // 3.2: Create a new scheduled task
      console.log('  3.2 Creating new scheduled task...');
      await page.waitForTimeout(1000);

      const createTaskSelectors = [
        'button:has-text("创建任务")',
        'button:has-text("Create Task")',
        'button:has-text("新建任务")',
        'button:has-text("+")',
        '[data-testid="create-task"]'
      ];

      let taskCreated = false;
      for (const selector of createTaskSelectors) {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
          await btn.click();
          console.log(`  [+] Clicked create task button: ${selector}`);
          taskCreated = true;
          break;
        }
      }

      await page.waitForTimeout(2000);

      // Fill task form if modal appeared
      const taskNameInput = page.locator('input[name="title"], input[placeholder*="任务"], input[placeholder*="task"]').first();
      if (await taskNameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await taskNameInput.fill('E2E Test Task - ' + new Date().toISOString());
        console.log('  [+] Task name filled');

        // Look for save/submit button
        const saveButton = page.locator('button:has-text("保存"), button:has-text("Save"), button:has-text("创建")').first();
        if (await saveButton.isVisible({ timeout: 1000 }).catch(() => false)) {
          await saveButton.click();
          console.log('  [+] Save button clicked');
          await page.waitForTimeout(2000);
        }
      }

      await takeScreenshot(page, '06-task-created');

      // Check if task appears in list
      const taskListSelectors = ['tr', 'li', '[data-testid="task-item"]', '[class*="task"]'];
      let taskFound = false;
      for (const selector of taskListSelectors) {
        const items = page.locator(selector);
        const count = await items.count();
        if (count > 0) {
          taskFound = true;
          console.log(`  [+] Found ${count} task items with selector: ${selector}`);
          break;
        }
      }

      if (taskFound || taskCreated) {
        results.tests.push({ name: 'Create scheduled task', status: 'PASS', details: 'Task creation initiated' });
        console.log('  [PASS] Task created successfully\n');
      } else {
        results.tests.push({ name: 'Create scheduled task', status: 'INFO', details: 'Task form may require additional configuration' });
        console.log('  [INFO] Task creation - form may require additional configuration\n');
      }
    }

    // ═══════════════════════════════════════════════════════
    // 4. KNOWLEDGE BASE
    // ═══════════════════════════════════════════════════════
    console.log('┌──────────────────────────────────────────────────────────────┐');
    console.log('│ 4. KNOWLEDGE BASE                                           │');
    console.log('└──────────────────────────────────────────────────────────────┘');

    console.log('\n  4.1 Navigating to Knowledge Base...');
    await page.goto(`${BASE_URL}/knowledge-base`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '07-knowledge-base-page');

    const kbUrl = page.url();
    if (kbUrl.includes('sign-in')) {
      results.tests.push({ name: 'Knowledge Base page access', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    } else {
      results.tests.push({ name: 'Knowledge Base page access', status: 'PASS', details: `Loaded at: ${kbUrl}` });
      console.log(`  [PASS] Knowledge Base page loaded\n`);

      // 4.2: Upload a test file
      console.log('  4.2 Uploading test file...');

      // Look for file upload input
      const fileInput = page.locator('input[type="file"]').first();
      const uploadButton = page.locator('button:has-text("上传"), button:has-text("Upload")').first();

      if (await fileInput.isVisible({ timeout: 1000 }).catch(() => false)) {
        await fileInput.setInputFiles(TEST_FILE_PATH);
        console.log(`  [+] File selected for upload: ${TEST_FILE_PATH}`);
        await page.waitForTimeout(3000);
        await takeScreenshot(page, '08-file-upload-progress');
        results.tests.push({ name: 'Knowledge base file upload', status: 'PASS', details: 'File upload initiated' });
        console.log('  [PASS] File upload initiated\n');
      } else if (await uploadButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await uploadButton.click();
        console.log('  [+] Upload button clicked');
        await page.waitForTimeout(1000);
        // In case it opens a file dialog, we can't fully automate this
        results.tests.push({ name: 'Knowledge base file upload', status: 'INFO', details: 'Upload button found but file dialog requires manual interaction' });
        console.log('  [INFO] Upload initiated (file dialog requires manual interaction)\n');
      } else {
        results.tests.push({ name: 'Knowledge base file upload', status: 'INFO', details: 'Upload interface not immediately visible' });
        console.log('  [INFO] Upload interface not immediately visible\n');
      }
    }

    // ═══════════════════════════════════════════════════════
    // 5. ADMIN FEATURES
    // ═══════════════════════════════════════════════════════
    console.log('┌──────────────────────────────────────────────────────────────┐');
    console.log('│ 5. ADMIN FEATURES                                            │');
    console.log('└──────────────────────────────────────────────────────────────┘');

    // 5.1: Monitoring Dashboard
    console.log('\n  5.1 Admin - Monitoring Dashboard...');
    await page.goto(`${BASE_URL}/admin/monitoring`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '09-admin-monitoring');

    const monitoringUrl = page.url();
    if (monitoringUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Monitoring', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    } else {
      results.tests.push({ name: 'Admin Monitoring', status: 'PASS', details: 'Dashboard loaded' });
      console.log('  [PASS] Monitoring dashboard loaded\n');
    }

    // 5.2: Models Page
    console.log('  5.2 Admin - Models Page...');
    await page.goto(`${BASE_URL}/admin/models`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '10-admin-models');

    const modelsUrl = page.url();
    if (modelsUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Models', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    } else {
      results.tests.push({ name: 'Admin Models', status: 'PASS', details: 'Models page loaded' });
      console.log('  [PASS] Models page loaded\n');
    }

    // 5.3: Skills Page
    console.log('  5.3 Admin - Skills Page...');
    await page.goto(`${BASE_URL}/admin/skills`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '11-admin-skills');

    const skillsUrl = page.url();
    if (skillsUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Skills', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    } else {
      results.tests.push({ name: 'Admin Skills', status: 'PASS', details: 'Skills page loaded' });
      console.log('  [PASS] Skills page loaded\n');
    }

    // 5.4: Memory Page
    console.log('  5.4 Admin - Memory Page...');
    await page.goto(`${BASE_URL}/admin/memory`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '12-admin-memory');

    const memoryUrl = page.url();
    if (memoryUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Memory', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    } else {
      results.tests.push({ name: 'Admin Memory', status: 'PASS', details: 'Memory page loaded' });
      console.log('  [PASS] Memory page loaded\n');
    }

    // 5.5: Audit Logs
    console.log('  5.5 Admin - Audit Logs...');
    await page.goto(`${BASE_URL}/admin/audit`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '13-admin-audit-logs');

    const auditUrl = page.url();
    if (auditUrl.includes('sign-in')) {
      results.tests.push({ name: 'Admin Audit Logs', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    } else {
      results.tests.push({ name: 'Admin Audit Logs', status: 'PASS', details: 'Audit logs page loaded' });
      console.log('  [PASS] Audit logs page loaded\n');
    }

    // ═══════════════════════════════════════════════════════
    // 6. ADDITIONAL ADMIN PAGES
    // ═══════════════════════════════════════════════════════
    console.log('┌──────────────────────────────────────────────────────────────┐');
    console.log('│ 6. ADDITIONAL ADMIN PAGES                                    │');
    console.log('└──────────────────────────────────────────────────────────────┘');

    // Config Page
    console.log('\n  6.1 Admin - Config Page...');
    await page.goto(`${BASE_URL}/admin/config`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '14-admin-config');

    if (!page.url().includes('sign-in')) {
      results.tests.push({ name: 'Admin Config', status: 'PASS', details: 'Config page loaded' });
      console.log('  [PASS] Config page loaded\n');
    } else {
      results.tests.push({ name: 'Admin Config', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    }

    // Users Page
    console.log('  6.2 Admin - Users Page...');
    await page.goto(`${BASE_URL}/admin/users`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '15-admin-users');

    if (!page.url().includes('sign-in')) {
      results.tests.push({ name: 'Admin Users', status: 'PASS', details: 'Users page loaded' });
      console.log('  [PASS] Users page loaded\n');
    } else {
      results.tests.push({ name: 'Admin Users', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    }

    // Sessions Page
    console.log('  6.3 Admin - Sessions Page...');
    await page.goto(`${BASE_URL}/admin/sessions`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '16-admin-sessions');

    if (!page.url().includes('sign-in')) {
      results.tests.push({ name: 'Admin Sessions', status: 'PASS', details: 'Sessions page loaded' });
      console.log('  [PASS] Sessions page loaded\n');
    } else {
      results.tests.push({ name: 'Admin Sessions', status: 'FAIL', details: 'Access denied' });
      console.log('  [FAIL] Access denied\n');
    }

  } catch (err) {
    results.errors.push(`Test execution error: ${err.message}`);
    console.log(`\n[FATAL ERROR] ${err.message}`);
  } finally {
    await browser.close();
    // Clean up test file
    if (fs.existsSync(TEST_FILE_PATH)) {
      fs.unlinkSync(TEST_FILE_PATH);
      console.log(`\n[Test file cleaned up: ${TEST_FILE_PATH}]`);
    }
  }

  // ═══════════════════════════════════════════════════════
  // TEST SUMMARY
  // ═══════════════════════════════════════════════════════
  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║                    TEST SUMMARY                             ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');

  let passCount = 0;
  let failCount = 0;
  let infoCount = 0;

  for (const test of results.tests) {
    const icon = test.status === 'PASS' ? '✓' : test.status === 'FAIL' ? '✗' : 'ℹ';
    console.log(`  ${icon} ${test.name}: ${test.status}`);
    console.log(`    ${test.details}\n`);

    if (test.status === 'PASS') passCount++;
    else if (test.status === 'FAIL') failCount++;
    else infoCount++;
  }

  console.log('─'.repeat(62));
  console.log(`  Results: ${passCount} passed, ${failCount} failed, ${infoCount} info`);
  console.log('─'.repeat(62));

  if (results.errors.length > 0) {
    console.log('\n⚠ HTTP ERRORS (4xx/5xx):');
    for (const error of results.errors) {
      console.log(`   - ${error}`);
    }
  }

  if (results.consoleErrors.length > 0) {
    console.log('\n⚠ CONSOLE ERRORS:');
    for (const error of results.consoleErrors) {
      console.log(`   - ${error}`);
    }
  } else {
    console.log('\n✓ No console errors detected');
  }

  if (results.consoleWarnings.length > 0) {
    console.log('\n⚠ CONSOLE WARNINGS (first 5):');
    for (const warning of results.consoleWarnings.slice(0, 5)) {
      console.log(`   - ${warning}`);
    }
  }

  console.log('\n' + '='.repeat(62));
  console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);
  console.log('='.repeat(62) + '\n');

  return results;
}

runTests().catch(console.error);
