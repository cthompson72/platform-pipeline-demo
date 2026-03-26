import { test, expect } from './fixtures';

const HEADERS = {
  'Content-Type': 'application/json',
  'X-Experience-ID': process.env.EXPERIENCE_ID || 'local-dev',
};

test.describe('Product API', () => {
  test('GET /api/products returns 200 and a list of products', async ({ request }) => {
    const res = await request.get('/api/products', { headers: HEADERS });
    expect(res.status()).toBe(200);
    expect(res.headers()['content-type']).toContain('application/json');
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body.length).toBeGreaterThanOrEqual(10);
    expect(body[0]).toHaveProperty('name');
    expect(body[0]).toHaveProperty('price');
    expect(body[0]).toHaveProperty('category');
  });

  test('GET /api/products/1 returns a valid product object', async ({ request }) => {
    const res = await request.get('/api/products/1', { headers: HEADERS });
    expect(res.status()).toBe(200);
    const product = await res.json();
    expect(product.id).toBe(1);
    expect(typeof product.name).toBe('string');
    expect(typeof product.price).toBe('number');
    expect(typeof product.category).toBe('string');
    expect(typeof product.inStock).toBe('boolean');
  });

  test('GET /api/products/999 returns 404', async ({ request }) => {
    const res = await request.get('/api/products/999', { headers: HEADERS });
    expect(res.status()).toBe(404);
  });

  test('POST /api/products with valid body returns 201', async ({ request }) => {
    const res = await request.post('/api/products', {
      headers: HEADERS,
      data: {
        name: 'E2E Test Product',
        brand: 'Test Brand',
        description: 'Created by Playwright E2E test',
        price: 19.99,
        category: 'skincare',
        inStock: true,
      },
    });
    expect(res.status()).toBe(201);
    const product = await res.json();
    expect(product.id).toBeTruthy();
    expect(product.name).toBe('E2E Test Product');
  });

  test('POST /api/products with missing name returns 400 with validation errors', async ({ request }) => {
    const res = await request.post('/api/products', {
      headers: HEADERS,
      data: {
        brand: 'Test Brand',
        price: 10.00,
        category: 'skincare',
      },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.error).toBe('Validation Failed');
    expect(body.messages.length).toBeGreaterThanOrEqual(1);
  });

  test('POST /api/products with negative price returns 400', async ({ request }) => {
    const res = await request.post('/api/products', {
      headers: HEADERS,
      data: {
        name: 'Bad Product',
        brand: 'Test Brand',
        price: -5.00,
        category: 'skincare',
      },
    });
    expect(res.status()).toBe(400);
  });

  test('GET /api/products/search?q=serum returns matching products', async ({ request }) => {
    const res = await request.get('/api/products/search?q=serum', { headers: HEADERS });
    expect(res.status()).toBe(200);
    const products = await res.json();
    expect(products.length).toBeGreaterThanOrEqual(1);
    expect(products[0].name.toLowerCase()).toContain('serum');
  });

  test('GET /api/products/search?q=nonexistent returns empty list', async ({ request }) => {
    const res = await request.get('/api/products/search?q=nonexistent', { headers: HEADERS });
    expect(res.status()).toBe(200);
    const products = await res.json();
    expect(products).toEqual([]);
  });

  test('GET /api/products/health/detailed returns status UP with memory and uptime', async ({ request }) => {
    const res = await request.get('/api/products/health/detailed', { headers: HEADERS });
    expect(res.status()).toBe(200);
    const health = await res.json();
    expect(health.status).toBe('UP');
    expect(health.memory).toBeTruthy();
    expect(health.uptime).toBeTruthy();
    expect(health.productCount).toBeGreaterThanOrEqual(10);
  });

  test('API response time is under 500ms', async ({ request }) => {
    const start = Date.now();
    await request.get('/api/products', { headers: HEADERS });
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(500);
  });
});
