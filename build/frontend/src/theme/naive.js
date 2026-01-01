/**
 * Naive UI Custom Theme Configuration
 * Dark charcoal → maroon atmospheric glassmorphism theme
 * Features: translucent charcoal glass backgrounds, white text, maroon accents,
 * subtle glass borders, and alternating table columns
 */

export const customTheme = {
  common: {
    // Primary maroon colors (oxblood maroon accents)
    primaryColor: '#500000',
    primaryColorHover: '#6a0000',
    primaryColorPressed: '#3a0000',
    primaryColorSuppl: '#6a0000',

    // Info colors (for links, secondary actions)
    infoColor: '#9faed6',
    infoColorHover: '#b4c2e8',
    infoColorPressed: '#8a9ac4',

    // Success colors
    successColor: '#2d7a3e',
    successColorHover: '#3a9150',
    successColorPressed: '#23612f',

    // Warning colors
    warningColor: '#b87333',
    warningColorHover: '#c98a4d',
    warningColorPressed: '#a66129',

    // Error colors
    errorColor: '#a83232',
    errorColorHover: '#bf4848',
    errorColorPressed: '#8f2727',

    // Base backgrounds - charcoal with atmospheric gradient
    baseColor: '#0a0a0a',              // Matte charcoal (matches gradient start)
    bodyColor: '#0a0a0a',              // Body base charcoal

    // Card/Panel backgrounds - translucent charcoal glass
    cardColor: 'rgba(36, 36, 36, 0.7)',      // Glassmorphic card
    modalColor: 'rgba(26, 26, 26, 0.9)',     // Modal backdrop (more opaque)
    popoverColor: 'rgba(42, 42, 42, 0.8)',   // Popover glass
    tableColor: 'rgba(36, 36, 36, 0.6)',     // Table base glass

    // Text colors - white/near-white for readability against dark gradient
    textColorBase: '#ffffff',          // Pure white base text
    textColor1: '#ffffff',             // Primary text (white)
    textColor2: '#e8e8e8',             // Secondary text (near-white)
    textColor3: '#b8b8b8',             // Tertiary text (light gray)

    // Placeholder text
    placeholderColor: '#b8b8b8',       // Light gray placeholder
    placeholderColorDisabled: '#888888',

    // Icon colors
    iconColor: '#e8e8e8',              // Near-white icons
    iconColorHover: '#ffffff',         // Pure white on hover
    iconColorPressed: '#b8b8b8',       // Light gray when pressed
    iconColorDisabled: '#888888',

    // Border colors - subtle white glass borders
    borderColor: 'rgba(255, 255, 255, 0.08)',    // Subtle glass border
    dividerColor: 'rgba(255, 255, 255, 0.05)',   // Divider line

    // Input backgrounds - translucent glass
    inputColor: 'rgba(42, 42, 42, 0.6)',         // Input field glass
    inputColorDisabled: 'rgba(30, 30, 30, 0.4)', // Disabled input

    // Hover states - maroon tint overlay
    hoverColor: 'rgba(80, 0, 0, 0.1)',           // Subtle maroon hover

    // Pressed/Active states - stronger maroon overlay
    pressedColor: 'rgba(80, 0, 0, 0.15)',        // Maroon press effect

    // Opacity values
    opacityDisabled: '0.4',

    // Border radius - premium rounded corners
    borderRadius: '6px',
    borderRadiusSmall: '4px',

    // Font
    fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
    fontSize: '14px',
    fontSizeMini: '12px',
    fontSizeTiny: '12px',
    fontSizeSmall: '13px',
    fontSizeMedium: '14px',
    fontSizeLarge: '15px',
    fontSizeHuge: '16px',

    // Line height
    lineHeight: '1.6'
  },

  DataTable: {
    // Header styling - glassmorphic with white text
    thColor: 'rgba(36, 36, 36, 0.7)',              // Translucent charcoal header
    thColorHover: 'rgba(80, 0, 0, 0.2)',           // Maroon hover overlay
    thTextColor: '#ffffff',                         // White header text
    thFontWeight: '600',
    thButtonColorHover: 'rgba(80, 0, 0, 0.2)',     // Maroon button hover
    thIconColor: '#e8e8e8',                        // Near-white icons
    thIconColorActive: '#6a0000',                  // Maroon active icon

    // Cell styling - glassmorphic with alternating column colors
    tdColor: 'rgba(255, 255, 255, 0.05)',          // Base cell (very subtle)
    tdColorHover: 'rgba(80, 0, 0, 0.15)',          // Maroon row hover
    tdColorStriped: 'rgba(106, 0, 0, 0.12)',       // Maroon-tinted alternating rows
    tdTextColor: '#ffffff',                         // White cell text

    // Alternating column backgrounds (custom implementation via CSS)
    // Note: NaiveUI doesn't natively support alternating columns, but we can use:
    // - tdColor for base cells
    // - Custom CSS in components for column-specific styling
    tdColorModal: 'rgba(36, 36, 36, 0.5)',         // Modal table cells

    // Borders - subtle white glass borders
    borderColor: 'rgba(255, 255, 255, 0.08)',      // Subtle glass border
    borderRadius: '12px',

    // Filter/Sort indicators
    filterColor: '#6a0000',                         // Maroon filter indicator

    // Loading state
    loadingColor: 'rgba(80, 0, 0, 0.12)',          // Maroon loading overlay

    // Pagination
    paginationBorderColor: 'rgba(255, 255, 255, 0.08)',

    // Action column
    actionDividerColor: 'rgba(255, 255, 255, 0.05)',

    // Font size
    thFontSize: '14px',
    tdFontSize: '14px',

    // Padding
    thPadding: '12px 16px',
    tdPadding: '12px 16px'
  },

  Pagination: {
    // Text colors - white for readability
    itemTextColor: '#ffffff',
    itemTextColorHover: '#ffffff',
    itemTextColorPressed: '#ffffff',
    itemTextColorActive: '#ffffff',
    itemTextColorDisabled: '#888888',

    // Item backgrounds - glassmorphic
    itemColor: 'transparent',
    itemColorHover: 'rgba(80, 0, 0, 0.1)',         // Maroon hover
    itemColorPressed: 'rgba(80, 0, 0, 0.15)',      // Maroon press
    itemColorActive: 'rgba(80, 0, 0, 0.6)',        // Maroon active state
    itemColorActiveHover: 'rgba(106, 0, 0, 0.7)',  // Brighter maroon
    itemColorDisabled: 'transparent',

    // Borders - subtle glass borders with maroon accents
    itemBorder: '1px solid rgba(255, 255, 255, 0.08)',
    itemBorderHover: '1px solid rgba(106, 0, 0, 0.5)',
    itemBorderPressed: '1px solid rgba(80, 0, 0, 0.7)',
    itemBorderActive: '1px solid rgba(106, 0, 0, 0.6)',
    itemBorderDisabled: '1px solid rgba(255, 255, 255, 0.03)',

    itemBorderRadius: '6px',
    itemSize: '32px',
    itemFontSize: '14px',
    itemPadding: '0 12px',

    // Button colors
    buttonColor: 'transparent',
    buttonColorHover: 'rgba(80, 0, 0, 0.1)',
    buttonColorPressed: 'rgba(80, 0, 0, 0.15)',
    buttonBorder: '1px solid rgba(255, 255, 255, 0.08)',
    buttonBorderHover: '1px solid rgba(106, 0, 0, 0.5)',
    buttonBorderPressed: '1px solid rgba(80, 0, 0, 0.7)',
    buttonIconColor: '#e8e8e8',
    buttonIconColorHover: '#ffffff',
    buttonIconColorPressed: '#b8b8b8'
  },

  Select: {
    peers: {
      InternalSelection: {
        // Selection box - translucent glass
        color: 'rgba(42, 42, 42, 0.6)',
        colorActive: 'rgba(42, 42, 42, 0.7)',

        // Borders - glass borders with maroon accents
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderHover: '1px solid rgba(106, 0, 0, 0.5)',
        borderActive: '1px solid rgba(106, 0, 0, 0.6)',
        borderFocus: '1px solid rgba(106, 0, 0, 0.6)',

        // Text - white for readability
        textColor: '#ffffff',
        placeholderColor: '#b8b8b8',

        // Indicators
        caretColor: '#6a0000',                      // Maroon caret
        arrowColor: '#e8e8e8',
        arrowColorActive: '#6a0000'                 // Maroon arrow when active
      },
      InternalSelectMenu: {
        // Dropdown menu - glassmorphic
        color: 'rgba(42, 42, 42, 0.85)',            // More opaque dropdown

        // Option text - white
        optionTextColor: '#ffffff',
        optionTextColorActive: '#ffffff',
        optionTextColorHover: '#ffffff',

        // Option backgrounds - maroon accents
        optionColorHover: 'rgba(80, 0, 0, 0.15)',   // Maroon hover
        optionColorActive: 'rgba(80, 0, 0, 0.6)',   // Maroon selected
        optionCheckColor: '#ffffff',                 // White checkmark

        borderRadius: '6px',

        // Group headers
        groupHeaderTextColor: '#e8e8e8'
      }
    }
  },

  Input: {
    // Input field - translucent glass
    color: 'rgba(42, 42, 42, 0.6)',
    colorFocus: 'rgba(42, 42, 42, 0.7)',
    colorDisabled: 'rgba(30, 30, 30, 0.4)',

    // Text - white for readability
    textColor: '#ffffff',
    textColorDisabled: '#888888',
    placeholderColor: '#b8b8b8',
    placeholderColorDisabled: '#888888',

    // Borders - glass borders with maroon focus
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderHover: '1px solid rgba(106, 0, 0, 0.5)',
    borderFocus: '1px solid rgba(106, 0, 0, 0.6)',
    borderDisabled: '1px solid rgba(255, 255, 255, 0.03)',

    borderRadius: '6px',

    // Caret - maroon accent
    caretColor: '#6a0000',

    // Clear/Icon buttons
    clearColor: '#e8e8e8',
    clearColorHover: '#ffffff',
    clearColorPressed: '#b8b8b8',

    iconColor: '#e8e8e8',
    iconColorHover: '#ffffff',
    iconColorPressed: '#b8b8b8',
    iconColorDisabled: '#888888'
  },

  Button: {
    // Text colors - white for maximum visibility
    textColor: '#ffffff',
    textColorHover: '#ffffff',
    textColorPressed: '#ffffff',
    textColorFocus: '#ffffff',
    textColorDisabled: '#666666',

    // Secondary/Default buttons - visible charcoal glass
    color: 'rgba(60, 60, 60, 0.8)',               // More opaque charcoal
    colorHover: 'rgba(80, 80, 80, 0.9)',          // Lighter on hover
    colorPressed: 'rgba(50, 50, 50, 0.95)',       // Darker on press
    colorFocus: 'rgba(70, 70, 70, 0.85)',
    colorDisabled: 'rgba(40, 40, 40, 0.4)',

    // Borders - visible glass borders
    border: '1px solid rgba(255, 255, 255, 0.15)',
    borderHover: '1px solid rgba(255, 255, 255, 0.25)',
    borderPressed: '1px solid rgba(255, 255, 255, 0.2)',
    borderFocus: '1px solid rgba(180, 60, 60, 0.6)',
    borderDisabled: '1px solid rgba(255, 255, 255, 0.05)',

    rippleColor: 'rgba(255, 255, 255, 0.15)',     // Visible ripple

    // Primary button - BRIGHT VISIBLE MAROON (key fix for "Add to qBittorrent")
    textColorPrimary: '#ffffff',
    textColorHoverPrimary: '#ffffff',
    textColorPressedPrimary: '#ffffff',
    textColorFocusPrimary: '#ffffff',
    textColorDisabledPrimary: '#888888',

    colorPrimary: 'rgba(140, 35, 35, 0.95)',      // Bright, saturated maroon
    colorHoverPrimary: 'rgba(165, 50, 50, 1)',    // Even brighter on hover
    colorPressedPrimary: 'rgba(110, 25, 25, 0.95)', // Darker on press
    colorFocusPrimary: 'rgba(150, 40, 40, 0.95)',
    colorDisabledPrimary: 'rgba(80, 40, 40, 0.4)',

    borderPrimary: '1px solid rgba(200, 80, 80, 0.7)',
    borderHoverPrimary: '1px solid rgba(220, 100, 100, 0.85)',
    borderPressedPrimary: '1px solid rgba(160, 60, 60, 0.9)',
    borderFocusPrimary: '1px solid rgba(220, 100, 100, 0.8)',
    borderDisabledPrimary: '1px solid rgba(100, 50, 50, 0.3)',

    // Info button - visible blue
    textColorInfo: '#ffffff',
    textColorHoverInfo: '#ffffff',
    textColorPressedInfo: '#ffffff',
    textColorFocusInfo: '#ffffff',
    colorInfo: 'rgba(70, 100, 160, 0.9)',
    colorHoverInfo: 'rgba(90, 120, 180, 0.95)',
    colorPressedInfo: 'rgba(60, 85, 140, 0.95)',
    borderInfo: '1px solid rgba(120, 160, 220, 0.7)',

    // Success button - visible green
    textColorSuccess: '#ffffff',
    textColorHoverSuccess: '#ffffff',
    textColorPressedSuccess: '#ffffff',
    textColorFocusSuccess: '#ffffff',
    colorSuccess: 'rgba(45, 120, 65, 0.9)',
    colorHoverSuccess: 'rgba(55, 140, 75, 0.95)',
    colorPressedSuccess: 'rgba(35, 100, 50, 0.95)',
    borderSuccess: '1px solid rgba(80, 180, 100, 0.7)',

    // Warning button - visible amber
    textColorWarning: '#ffffff',
    textColorHoverWarning: '#ffffff',
    textColorPressedWarning: '#ffffff',
    textColorFocusWarning: '#ffffff',
    colorWarning: 'rgba(180, 120, 50, 0.9)',
    colorHoverWarning: 'rgba(200, 140, 60, 0.95)',
    colorPressedWarning: 'rgba(160, 100, 40, 0.95)',
    borderWarning: '1px solid rgba(220, 160, 80, 0.7)',

    // Error button - visible red
    textColorError: '#ffffff',
    textColorHoverError: '#ffffff',
    textColorPressedError: '#ffffff',
    textColorFocusError: '#ffffff',
    colorError: 'rgba(170, 55, 55, 0.9)',
    colorHoverError: 'rgba(190, 70, 70, 0.95)',
    colorPressedError: 'rgba(150, 45, 45, 0.95)',
    borderError: '1px solid rgba(220, 90, 90, 0.7)',

    // Ghost button text colors - BRIGHT for visibility on dark backgrounds
    textColorGhost: '#e8e8e8',
    textColorGhostHover: '#ffffff',
    textColorGhostPressed: '#d0d0d0',
    textColorGhostPrimary: '#ff9090',             // Light maroon
    textColorGhostHoverPrimary: '#ffb0b0',
    textColorGhostInfo: '#a0c4ff',                // Light blue
    textColorGhostHoverInfo: '#c0daff',
    textColorGhostSuccess: '#80e8a0',             // Light green
    textColorGhostHoverSuccess: '#a0ffb8',
    textColorGhostWarning: '#ffc870',             // Light amber
    textColorGhostHoverWarning: '#ffe0a0',
    textColorGhostError: '#ff8080',               // Light red
    textColorGhostHoverError: '#ffa0a0'
  },

  Card: {
    // Glassmorphic card backgrounds with backdrop blur
    color: 'rgba(36, 36, 36, 0.7)',                // Standard card glass
    colorModal: 'rgba(26, 26, 26, 0.9)',           // Modal card (more opaque)
    colorEmbedded: 'rgba(42, 42, 42, 0.5)',        // Embedded card (lighter)
    colorTarget: 'rgba(80, 0, 0, 0.05)',           // Target/hover overlay

    // Text colors - white
    textColor: '#ffffff',
    titleTextColor: '#ffffff',

    // Borders - subtle glass borders
    borderColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',                          // Premium rounded corners

    // Padding
    paddingSmall: '12px 16px',
    paddingMedium: '16px 20px',
    paddingLarge: '20px 24px',
    paddingHuge: '28px 32px',

    // Title font
    titleFontSizeSmall: '16px',
    titleFontSizeMedium: '18px',
    titleFontSizeLarge: '20px',
    titleFontSizeHuge: '22px',

    // Close button - maroon hover
    closeColorHover: 'rgba(80, 0, 0, 0.2)',
    closeColorPressed: 'rgba(80, 0, 0, 0.3)',
    closeIconColor: '#e8e8e8',
    closeIconColorHover: '#ffffff',
    closeIconColorPressed: '#b8b8b8'
  },

  Tag: {
    // Glassmorphic tags
    color: 'rgba(42, 42, 42, 0.5)',                // Translucent tag
    textColor: '#ffffff',                          // White text
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',

    // Primary tag (maroon accent)
    colorPrimary: 'rgba(80, 0, 0, 0.6)',           // Maroon glass tag
    textColorPrimary: '#ffffff',
    borderPrimary: '1px solid rgba(106, 0, 0, 0.5)',

    // Info tag
    colorInfo: 'rgba(159, 174, 214, 0.2)',
    textColorInfo: '#9faed6',
    borderInfo: '1px solid rgba(159, 174, 214, 0.3)',

    // Success tag
    colorSuccess: 'rgba(45, 122, 62, 0.2)',
    textColorSuccess: '#2d7a3e',
    borderSuccess: '1px solid rgba(45, 122, 62, 0.4)',

    // Warning tag
    colorWarning: 'rgba(184, 115, 51, 0.2)',
    textColorWarning: '#b87333',
    borderWarning: '1px solid rgba(184, 115, 51, 0.4)',

    // Error tag
    colorError: 'rgba(168, 50, 50, 0.2)',
    textColorError: '#a83232',
    borderError: '1px solid rgba(168, 50, 50, 0.4)',

    // Close button
    closeIconColor: '#e8e8e8',
    closeIconColorHover: '#ffffff',
    closeIconColorPressed: '#b8b8b8',
    closeColorHover: 'rgba(255, 255, 255, 0.08)',
    closeColorPressed: 'rgba(255, 255, 255, 0.12)'
  }
}
