/**
 * E2E Tests for Authentication Flow
 * 
 * Tests the complete authentication flow including login, logout, and protected routes.
 */

import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the login page
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show error message on invalid login', async ({ page }) => {
    // Mock API response for failed login
    await page.route('**/api/auth/login', (route) => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid credentials' }),
      });
    });

    await page.fill('input[name="username"]', 'wronguser');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Wait for error message
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });

  test('should login successfully and redirect to dashboard', async ({ page }) => {
    // Mock API response for successful login
    await page.route('**/api/auth/login', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-token',
          token_type: 'Bearer',
          expires_in: 3600,
          user: {
            id: '1',
            username: 'testuser',
            role: 'admin',
            created_at: '2024-01-01',
          },
        }),
      });
    });

    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard
    await page.waitForURL('/dashboard', { timeout: 5000 });
    await expect(page).toHaveURL('/dashboard');
  });

  test('should logout and redirect to login', async ({ page }) => {
    // Set up authenticated state by storing token
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

    await page.route('**/api/auth/logout', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      });
    });

    // Navigate to dashboard (should be authenticated)
    await page.goto('/dashboard');

    // Click logout button
    await page.click('text=Logout');

    // Wait for redirect to login
    await page.waitForURL('/login', { timeout: 5000 });
    await expect(page).toHaveURL('/login');
  });

  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    // Ensure no token is stored
    await page.addInitScript(() => {
      localStorage.removeItem('auth_token');
    });

    // Try to access dashboard
    await page.goto('/dashboard');

    // Should redirect to login
    await page.waitForURL('/login', { timeout: 5000 });
    await expect(page).toHaveURL('/login');
  });

  test('should show access denied for non-admin accessing settings', async ({ page }) => {
    // Set up authenticated state with viewer role
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
          username: 'viewer',
          role: 'viewer',
          created_at: '2024-01-01',
        }),
      });
    });

    // Try to access settings
    await page.goto('/settings');

    // Should show access denied or redirect
    const url = page.url();
    expect(url).not.toContain('/settings');
  });
});

