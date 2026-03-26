import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

const errorRate = new Rate('errors');
const productListDuration = new Trend('product_list_duration');
const productDetailDuration = new Trend('product_detail_duration');
const searchDuration = new Trend('search_duration');

export const options = {
  stages: [
    { duration: '30s', target: 25 },
    { duration: '30s', target: 50 },
    { duration: '30s', target: 75 },
    { duration: '30s', target: 100 },
    { duration: '1m', target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<1500'],
    http_req_failed: ['rate<0.15'],
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
    });
    errorRate.add(!success);
  });

  sleep(0.5);

  group('Product Detail', () => {
    const id = Math.floor(Math.random() * 10) + 1;
    const res = http.get(`${BASE_URL}/api/products/${id}`, { headers });
    productDetailDuration.add(res.timings.duration);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
    });
    errorRate.add(!success);
  });

  sleep(0.5);

  group('Search', () => {
    const terms = ['serum', 'lipstick', 'shampoo', 'cream', 'oil'];
    const q = terms[Math.floor(Math.random() * terms.length)];
    const res = http.get(`${BASE_URL}/api/products/search?q=${q}`, { headers });
    searchDuration.add(res.timings.duration);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
    });
    errorRate.add(!success);
  });

  sleep(0.5);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    'perf-tests/results/stress-test-summary.json': JSON.stringify(data, null, 2),
  };
}
