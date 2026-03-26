import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

const errorRate = new Rate('errors');
const productListDuration = new Trend('product_list_duration');
const productDetailDuration = new Trend('product_detail_duration');
const searchDuration = new Trend('search_duration');
const createProductDuration = new Trend('create_product_duration');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 10 },
    { duration: '30s', target: 25 },
    { duration: '1m', target: 25 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
      http_req_duration: ['p(95)<800', 'p(99)<2000'],
      http_req_failed: ['rate<0.05'],
      errors: ['rate<0.05'],
      product_list_duration: ['p(95)<700'],
      product_detail_duration: ['p(95)<500'],
      search_duration: ['p(95)<700'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const EXPERIENCE_ID = __ENV.EXPERIENCE_ID || 'local-dev';

const headers = {
  'Content-Type': 'application/json',
  'X-Experience-ID': EXPERIENCE_ID,
};

export default function () {
  group('Product List', () => {
    const res = http.get(`${BASE_URL}/api/products`, { headers });
    productListDuration.add(res.timings.duration);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response has products': (r) => JSON.parse(r.body).length > 0,
    });
    errorRate.add(!success);
  });

  sleep(1);

  group('Product Detail', () => {
    const id = Math.floor(Math.random() * 10) + 1;
    const res = http.get(`${BASE_URL}/api/products/${id}`, { headers });
    productDetailDuration.add(res.timings.duration);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'has product name': (r) => JSON.parse(r.body).name !== undefined,
    });
    errorRate.add(!success);
  });

  sleep(1);

  group('Search', () => {
    const terms = ['serum', 'lipstick', 'shampoo', 'cream', 'oil'];
    const q = terms[Math.floor(Math.random() * terms.length)];
    const res = http.get(`${BASE_URL}/api/products/search?q=${q}`, { headers });
    searchDuration.add(res.timings.duration);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response is array': (r) => Array.isArray(JSON.parse(r.body)),
    });
    errorRate.add(!success);
  });

  sleep(1);

  group('Create Product', () => {
    const payload = JSON.stringify({
      name: `Perf Test Product ${Date.now()}`,
      brand: 'Perf Test Brand',
      description: 'Created during k6 load test',
      price: (Math.random() * 50 + 5).toFixed(2),
      category: 'skincare',
      inStock: true,
    });
    const res = http.post(`${BASE_URL}/api/products`, payload, { headers });
    createProductDuration.add(res.timings.duration);
    const success = check(res, {
      'status is 201': (r) => r.status === 201,
    });
    errorRate.add(!success);
  });

  sleep(1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    'perf-tests/results/load-test-summary.json': JSON.stringify(data, null, 2),
  };
}
