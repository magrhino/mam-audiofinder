/**
 * HTML Sanitization Utilities
 *
 * Provides safe HTML sanitization for user-generated content and external API responses.
 * Uses DOMPurify to prevent XSS attacks while preserving basic formatting.
 */

import DOMPurify from 'dompurify'

/**
 * Sanitize HTML description content
 *
 * Strips block-level tags (like <p>) and replaces them with inline breaks
 * to prevent layout width issues. Only allows safe inline formatting tags.
 *
 * @param {string} html - Raw HTML string to sanitize
 * @returns {string} Sanitized HTML safe for v-html rendering
 */
export function sanitizeDescription(html) {
  if (!html || typeof html !== 'string') {
    return ''
  }

  // Configure DOMPurify to allow only safe inline tags
  const config = {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'span', 'br'],
    ALLOWED_ATTR: [], // No attributes needed for basic formatting
    KEEP_CONTENT: true // Preserve text content even if tags are stripped
  }

  // First pass: sanitize with DOMPurify
  let clean = DOMPurify.sanitize(html, config)

  // Second pass: unwrap <p> tags and replace with double line breaks
  // This prevents block-level elements from breaking responsive layout
  clean = clean
    .replace(/<p[^>]*>/gi, '') // Remove opening <p> tags
    .replace(/<\/p>/gi, '<br><br>') // Replace closing </p> with double breaks
    .replace(/<br\s*\/?>(\s*<br\s*\/?>)+/gi, '<br><br>') // Normalize multiple breaks to max 2
    .trim()

  return clean
}
