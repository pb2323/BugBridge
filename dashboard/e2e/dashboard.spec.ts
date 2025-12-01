/**
 * E2E Tests for Dashboard Features
 * 
 * Tests the main dashboard functionality including metrics display and navigation.
 */

import { test, expect } from '@playwright/test';

test.describe('Dashboard Features', () => {
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
          jira_tickets_created: 25,
          resolution_rate: 0.85,
          average_response_time_hours: 2.5,
          average_resolution_time_hours: 24.0,
          sentiment_distribution: {
            positive: 40,
            neutral: 50,
            negative: 10,
          },
          priority_distribution: {
            high: 20,
            medium: 50,
            low: 30,
          },
          recent_posts: [],
          recent_tickets: [],
          recent_resolutions: [],
        }),
      });
    });

    await page.goto('/dashboard');
  });

  test('should display dashboard with metrics', async ({ page }) => {
    // Wait for metrics to load
    await page.waitForSelector('text=Total Feedback', { timeout: 5000 });

    // Check that key metrics are displayed
    await expect(page.locator('text=Total Feedback')).toBeVisible();
    await expect(page.locator('text=Bugs')).toBeVisible();
    await expect(page.locator('text=Features')).toBeVisible();
    await expect(page.locator('text=Jira Tickets')).toBeVisible();
  });

  test('should display charts', async ({ page }) => {
    // Wait for charts to render
    await page.waitForTimeout(2000);

    // Check that charts are present (they should have SVG elements)
    const charts = await page.locator('svg').count();
    expect(charts).toBeGreaterThan(0);
  });

  test('should navigate to feedback page', async ({ page }) => {
    await page.click('text=Feedback');

    await page.waitForURL('/feedback', { timeout: 5000 });
    await expect(page).toHaveURL('/feedback');
  });

  test('should navigate to reports page', async ({ page }) => {
    await page.click('text=Reports');

    await page.waitForURL('/reports', { timeout: 5000 });
    await expect(page).toHaveURL('/reports');
  });

  test('should toggle auto-refresh', async ({ page }) => {
    // Find auto-refresh toggle (if present)
    const autoRefreshToggle = page.locator('input[type="checkbox"]').first();
    if (await autoRefreshToggle.isVisible()) {
      await autoRefreshToggle.click();
      // Verify toggle state changed
      await expect(autoRefreshToggle).not.toBeChecked();
    }
  });
});

