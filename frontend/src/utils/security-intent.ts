/**
 * Format a security_intent machine value to a human-readable label.
 * Examples:
 *   prompt_injection → Prompt Injection
 *   credential_access → Credential Access
 *   safe_educational → Safe Educational
 */
export function formatSecurityIntent(intent: string): string {
  if (!intent) return 'Unknown';
  
  return intent
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Check if a security intent represents a dangerous classification.
 */
export function isDangerousIntent(intent: string): boolean {
  const safeIntents = ['safe_educational', 'general_conversation'];
  return !safeIntents.includes(intent.toLowerCase());
}
