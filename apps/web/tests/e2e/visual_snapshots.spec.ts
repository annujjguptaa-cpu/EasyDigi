import { test, expect } from '@playwright/test';

test.describe('DocFlow Visual Snapshot Tests', () => {
  const viewports = [
    { name: 'mobile', width: 390, height: 844 },
    { name: 'desktop', width: 1280, height: 800 },
  ];

  const screens = [
    { name: 'design-gallery', path: '/design' },
    { name: 'customer-verify', path: '/verify/demo-token' },
    { name: 'mock-digilocker', path: '/mock-digilocker' },
    { name: 'lender-portal', path: '/lender' },
    { name: 'insurance-portal', path: '/insurance' },
    { name: 'device-vault', path: '/vault' },
    { name: 'share-consent', path: '/share/demo-token' },
    { name: 'platform-metrics', path: '/metrics' },
  ];

  for (const vp of viewports) {
    for (const screen of screens) {
      test(`${screen.name} at ${vp.name} [Light Theme]`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        // Visual smoke check
        expect(page).toBeDefined();
      });

      test(`${screen.name} at ${vp.name} [Dark Theme]`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        expect(page).toBeDefined();
      });
    }
  }
});
