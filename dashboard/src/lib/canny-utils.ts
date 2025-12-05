/**
 * Utility functions for Canny.io integration
 */

/**
 * Get the Canny.io subdomain for building feedback post links.
 * This should match your Canny.io instance subdomain (e.g., "bugbridge")
 */
export const CANNY_SUBDOMAIN = 'bugbridge';

/**
 * Get the Canny.io board slug for building feedback post links.
 * This is the URL-friendly version of your board name (e.g., "feedback-and-feature-requests")
 */
export const CANNY_BOARD_SLUG = 'feedback-and-feature-requests';

/**
 * Get the Canny.io base URL for building feedback post links.
 */
export const CANNY_BASE_URL = `https://${CANNY_SUBDOMAIN}.canny.io`;

/**
 * Convert a Canny.io post title to a URL-friendly slug.
 * 
 * @param title - The post title
 * @returns URL-friendly slug
 */
function slugifyTitle(title: string): string {
  return title
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '') // Remove special characters
    .replace(/[\s_-]+/g, '-') // Replace spaces and underscores with hyphens
    .replace(/^-+|-+$/g, ''); // Remove leading/trailing hyphens
}

/**
 * Convert a Canny.io admin URL to a public-facing URL.
 * 
 * @param adminUrl - Admin URL (e.g., https://bugbridge.canny.io/admin/board/feedback-and-feature-requests/p/...)
 * @returns Public URL (e.g., https://bugbridge.canny.io/feedback-and-feature-requests/p/...)
 */
function convertAdminUrlToPublic(adminUrl: string): string {
  // Remove /admin/board/ from the path
  return adminUrl.replace('/admin/board/', '/');
}

/**
 * Build a Canny.io feedback post public URL from available data.
 * 
 * @param postId - The Canny.io post ID (optional, used as fallback)
 * @param title - The post title (used to create slug)
 * @param storedUrl - Optional stored URL from Canny API (admin or public)
 * @returns The full public URL to view the post in Canny.io
 */
export function getCannyPostUrl(
  postId: string,
  title: string,
  storedUrl?: string | null
): string {
  if (!postId && !title) {
    return '#';
  }
  
  // If we have a stored URL, try to convert it to public format
  if (storedUrl) {
    // If it's already a public URL, return as-is
    if (storedUrl.includes('/p/') && !storedUrl.includes('/admin/')) {
      return storedUrl;
    }
    
    // If it's an admin URL, convert to public
    if (storedUrl.includes('/admin/board/')) {
      return convertAdminUrlToPublic(storedUrl);
    }
    
    // If URL contains the post path, try to extract and use it
    const postPathMatch = storedUrl.match(/\/p\/([^/?]+)/);
    if (postPathMatch) {
      return `${CANNY_BASE_URL}/${CANNY_BOARD_SLUG}/p/${postPathMatch[1]}`;
    }
  }
  
  // Build URL from title slug
  const postSlug = slugifyTitle(title);
  return `${CANNY_BASE_URL}/${CANNY_BOARD_SLUG}/p/${postSlug}`;
}

/**
 * Extract post slug from a Canny.io URL.
 * 
 * @param url - The Canny.io post URL
 * @returns The post slug or null if not found
 */
export function extractPostSlug(url: string): string | null {
  if (!url) {
    return null;
  }
  
  // Match pattern like /p/post-slug or /admin/board/.../p/post-slug
  const match = url.match(/\/p\/([^/?]+)/);
  return match ? match[1] : null;
}

