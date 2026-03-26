import { test as base } from '@playwright/test';

export const test = base.extend<{ experienceId: string }>({
  experienceId: [process.env.EXPERIENCE_ID || 'local-dev', { option: true }],
});

export { expect } from '@playwright/test';
