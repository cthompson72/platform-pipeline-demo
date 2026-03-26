import { test, expect } from './fixtures';

test.describe('Product UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('Home page loads and displays product table', async ({ page }) => {
    await expect(page.locator('#product-table')).toBeVisible();
    const rows = page.locator('#product-tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(10);
  });

  test('Product table contains seeded products', async ({ page }) => {
    const tableText = await page.locator('#product-tbody').textContent();
    expect(tableText).toContain('Revitalift Serum');
    expect(tableText).toContain('Voluminous Mascara');
  });

  test('Search filters products by name', async ({ page }) => {
    await page.fill('#search-input', 'Serum');
    await page.click('#search-btn');
    await page.waitForTimeout(500);
    const rows = page.locator('#product-tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(1);
    const text = await rows.first().textContent();
    expect(text?.toLowerCase()).toContain('serum');
  });

  test('Search with no results shows empty state message', async ({ page }) => {
    await page.fill('#search-input', 'zzz_nonexistent_zzz');
    await page.click('#search-btn');
    await page.waitForTimeout(500);
    await expect(page.locator('#empty-state')).toBeVisible();
  });

  test('Add Product form submits successfully and product appears in table', async ({ page }) => {
    await page.fill('#prod-name', 'Playwright Test Product');
    await page.fill('#prod-brand', 'Test Brand');
    await page.fill('#prod-price', '25.99');
    await page.selectOption('#prod-category', 'skincare');
    await page.click('#add-product-form button[type="submit"]');
    await page.waitForTimeout(1000);

    const msgEl = page.locator('#form-msg');
    await expect(msgEl).toContainText('Product created successfully');

    const tableText = await page.locator('#product-tbody').textContent();
    expect(tableText).toContain('Playwright Test Product');
  });

  test('Add Product form shows validation errors for empty fields', async ({ page }) => {
    await page.fill('#prod-name', '');
    await page.fill('#prod-brand', '');
    // Submit via JS to bypass HTML5 validation
    await page.evaluate(() => {
      const form = document.getElementById('add-product-form') as HTMLFormElement;
      form.querySelectorAll('input, select').forEach(el => el.removeAttribute('required'));
      form.dispatchEvent(new Event('submit', { bubbles: true }));
    });
    await page.waitForTimeout(1000);
    const msgEl = page.locator('#form-msg');
    await expect(msgEl).toBeVisible();
    await expect(msgEl).toHaveClass(/msg-error/);
  });

  test('Page title and header are correct', async ({ page }) => {
    await expect(page).toHaveTitle('Product Catalog - Platform Pipeline Demo');
    await expect(page.locator('header h1')).toHaveText('Product Catalog');
  });
});
