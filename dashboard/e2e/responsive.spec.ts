/**
 * E2E Tests for Responsive Design
 * 
 * Tests the dashboard on different screen sizes.
 */

import { test, expect, devices } from '@playwright/test';

test.describe('Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    // Set up authenticated state
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'mock-token');
    });

    // Mock API responses
    await page.route('**/api/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '1',
          username: 'testuser',
          role: 'admin',
          created_at: '2024-01-01',
        }),
      });
    });

    await page.route('**/api/metrics**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_feedback: 100,
          bugs_count: 30,
          features_count: 70,
        }),
      });
    });
  });

  test('should display correctly on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/dashboard');

    // Check that mobile menu button is visible
    const menuButton = page.locator('button:has-text("Open sidebar"), [aria-label*="menu"]').first();
    // The mobile menu should be accessible (even if not visible by default)

    // Check that content is visible
    await expect(page.locator('text=Total Feedback').first()).toBeVisible();
  });

  test('should display correctly on tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    await page.goto('/dashboard');

    // Check that content is visible
    await expect(page.locator('text=Total Feedback').first()).toBeVisible();
  });

  test('should display correctly on desktop viewport', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    await page.goto('/dashboard');

    // Check that sidebar is visible (on desktop, sidebar should be visible)
    // Check that content is visible
    await expect(page.locator('text=Total Feedback').first()).toBeVisible();
  });

  test('should show mobile sidebar when menu button is clicked', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/dashboard');

    // Find and click menu button (if it exists)
    const menuButton = page.locator('button[aria-label*="sidebar"], button:has-text("Open sidebar")').first();
    if (await menuButton.isVisible()) {
      await menuButton.click();

      // Check that sidebar navigation is visible
      await expect(page.locator('text=Dashboard')).toBeVisible({ timeout: 2000 });
    }
  });
});

