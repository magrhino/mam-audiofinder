/**
 * useMAMErrorDialog Composable
 * Handles MAM API error notifications, particularly for 502 errors
 * indicating an expired API token.
 */

import { h } from 'vue'
import { useDialog } from 'naive-ui'
import { NText } from 'naive-ui'

const MAM_SECURITY_URL = 'https://www.myanonamouse.net/preferences/index.php?view=security'

/**
 * Check if an error message indicates a MAM 502 error
 * @param {string} message - Error message to check
 * @returns {boolean}
 */
export function isMAM502Error(message) {
  return typeof message === 'string' && message.startsWith('HTTP 502')
}

export function useMAMErrorDialog() {
  const dialog = useDialog()

  /**
   * Show a warning dialog for MAM 502 errors
   * Provides a clickable link to the MAM security settings page
   */
  const showMAM502Dialog = () => {
    console.log('[MAMErrorDialog] showMAM502Dialog called')
    dialog.warning({
      title: 'MAM API Token Expired',
      content: () => h('div', { style: { lineHeight: '1.6' } }, [
        h(NText, { depth: 2 }, () => 'Your MAM API token may have expired. Please refresh it at:'),
        h('br'),
        h('br'),
        h('a', {
          href: MAM_SECURITY_URL,
          target: '_blank',
          rel: 'noopener noreferrer',
          style: {
            color: '#63e2b7',
            textDecoration: 'underline',
            wordBreak: 'break-all'
          }
        }, 'MAM Security Settings'),
        h('br'),
        h('br'),
        h(NText, { depth: 3, style: { fontSize: '0.9em', fontStyle: 'italic' } },
          () => 'After updating the token in your .env file, restart the container for changes to take effect.'
        )
      ]),
      positiveText: 'OK',
      style: { maxWidth: '450px' }
    })
  }

  return {
    isMAM502Error,
    showMAM502Dialog
  }
}
