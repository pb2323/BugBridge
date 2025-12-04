/**
 * Utility functions for Jira integration
 */

/**
 * Get the Jira instance base URL for building ticket links.
 * This should match your Jira instance URL (e.g., https://your-company.atlassian.net)
 */
export const JIRA_BASE_URL = 'https://bugbridge-sjsu.atlassian.net';

/**
 * Build a Jira ticket browse URL from a ticket key.
 * 
 * @param ticketKey - The Jira ticket key (e.g., "ECS-52")
 * @returns The full URL to view the ticket in Jira
 */
export function getJiraTicketUrl(ticketKey: string): string {
  if (!ticketKey) {
    return '#';
  }
  
  // If ticketKey already contains a URL, return it as-is
  if (ticketKey.startsWith('http://') || ticketKey.startsWith('https://')) {
    return ticketKey;
  }
  
  // Build the browse URL: https://bugbridge-sjsu.atlassian.net/browse/ECS-52
  return `${JIRA_BASE_URL}/browse/${ticketKey}`;
}

/**
 * Extract ticket key from a Jira URL.
 * 
 * @param url - The Jira ticket URL
 * @returns The ticket key (e.g., "ECS-52") or null if not found
 */
export function extractTicketKey(url: string): string | null {
  if (!url) {
    return null;
  }
  
  // Match patterns like /browse/ECS-52 or browse/ECS-52
  const match = url.match(/\/browse\/([A-Z]+-\d+)/i);
  return match ? match[1] : null;
}

