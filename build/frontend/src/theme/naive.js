/**
 * Naive UI Custom Theme Configuration
 * Matches existing dark theme with maroon accents from main.css
 */

export const customTheme = {
  common: {
    // Primary maroon colors
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

    // Base backgrounds
    baseColor: '#000000',
    bodyColor: '#000000',

    // Card/Panel backgrounds
    cardColor: '#242424',
    modalColor: '#242424',
    popoverColor: '#2a2a2a',
    tableColor: '#242424',

    // Text colors
    textColorBase: '#e8e8e8',
    textColor1: '#e8e8e8',
    textColor2: '#b8b8b8',
    textColor3: '#888888',

    // Placeholder text
    placeholderColor: '#888888',
    placeholderColorDisabled: '#5a5a5a',

    // Icon colors
    iconColor: '#b8b8b8',
    iconColorHover: '#e8e8e8',
    iconColorPressed: '#888888',
    iconColorDisabled: '#5a5a5a',

    // Border colors
    borderColor: '#3a3a3a',
    dividerColor: '#2a2a2a',

    // Input backgrounds
    inputColor: '#2a2a2a',
    inputColorDisabled: '#1f1f1f',

    // Hover states
    hoverColor: 'rgba(80, 0, 0, 0.1)',

    // Pressed/Active states
    pressedColor: 'rgba(80, 0, 0, 0.15)',

    // Opacity values
    opacityDisabled: '0.4',

    // Border radius
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
    // Header styling - Glassmorphic
    thColor: 'rgba(42, 42, 42, 0.7)',
    thColorHover: 'rgba(50, 50, 50, 0.8)',
    thTextColor: '#e8e8e8',
    thFontWeight: '600',
    thButtonColorHover: 'rgba(80, 0, 0, 0.2)',
    thIconColor: '#b8b8b8',
    thIconColorActive: '#6a0000',

    // Cell styling - Glassmorphic
    tdColor: 'rgba(36, 36, 36, 0.3)',
    tdColorHover: 'rgba(80, 0, 0, 0.15)',
    tdColorStriped: 'rgba(80, 0, 0, 0.08)',
    tdTextColor: '#e8e8e8',

    // Borders - Subtle glass borders
    borderColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',

    // Filter/Sort indicators
    filterColor: '#6a0000',

    // Loading state
    loadingColor: 'rgba(80, 0, 0, 0.12)',

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
    itemTextColor: '#e8e8e8',
    itemTextColorHover: '#e8e8e8',
    itemTextColorPressed: '#e8e8e8',
    itemTextColorActive: '#e8e8e8',
    itemTextColorDisabled: '#5a5a5a',

    itemColor: 'transparent',
    itemColorHover: 'rgba(80, 0, 0, 0.1)',
    itemColorPressed: 'rgba(80, 0, 0, 0.15)',
    itemColorActive: '#500000',
    itemColorActiveHover: '#6a0000',
    itemColorDisabled: 'transparent',

    itemBorder: '1px solid #3a3a3a',
    itemBorderHover: '1px solid #500000',
    itemBorderPressed: '1px solid #3a0000',
    itemBorderActive: '1px solid #500000',
    itemBorderDisabled: '1px solid #2a2a2a',

    itemBorderRadius: '6px',
    itemSize: '32px',
    itemFontSize: '14px',
    itemPadding: '0 12px',

    buttonColor: 'transparent',
    buttonColorHover: 'rgba(80, 0, 0, 0.1)',
    buttonColorPressed: 'rgba(80, 0, 0, 0.15)',
    buttonBorder: '1px solid #3a3a3a',
    buttonBorderHover: '1px solid #500000',
    buttonBorderPressed: '1px solid #3a0000',
    buttonIconColor: '#b8b8b8',
    buttonIconColorHover: '#e8e8e8',
    buttonIconColorPressed: '#888888'
  },

  Select: {
    peers: {
      InternalSelection: {
        color: '#2a2a2a',
        colorActive: '#2a2a2a',
        border: '1px solid #3a3a3a',
        borderHover: '1px solid #500000',
        borderActive: '1px solid #500000',
        borderFocus: '1px solid #500000',
        textColor: '#e8e8e8',
        placeholderColor: '#888888',

        caretColor: '#500000',
        arrowColor: '#b8b8b8',
        arrowColorActive: '#500000'
      },
      InternalSelectMenu: {
        color: '#2a2a2a',
        optionTextColor: '#e8e8e8',
        optionTextColorActive: '#e8e8e8',
        optionTextColorHover: '#e8e8e8',
        optionColorHover: 'rgba(80, 0, 0, 0.1)',
        optionColorActive: '#500000',
        optionCheckColor: '#e8e8e8',
        borderRadius: '6px',

        groupHeaderTextColor: '#b8b8b8'
      }
    }
  },

  Input: {
    color: '#2a2a2a',
    colorFocus: '#2a2a2a',
    colorDisabled: '#1f1f1f',

    textColor: '#e8e8e8',
    textColorDisabled: '#5a5a5a',
    placeholderColor: '#888888',
    placeholderColorDisabled: '#5a5a5a',

    border: '1px solid #3a3a3a',
    borderHover: '1px solid #500000',
    borderFocus: '1px solid #500000',
    borderDisabled: '1px solid #2a2a2a',

    borderRadius: '6px',

    caretColor: '#500000',

    clearColor: '#b8b8b8',
    clearColorHover: '#e8e8e8',
    clearColorPressed: '#888888',

    iconColor: '#b8b8b8',
    iconColorHover: '#e8e8e8',
    iconColorPressed: '#888888',
    iconColorDisabled: '#5a5a5a'
  },

  Button: {
    textColor: '#e8e8e8',
    textColorHover: '#e8e8e8',
    textColorPressed: '#e8e8e8',
    textColorFocus: '#e8e8e8',
    textColorDisabled: '#5a5a5a',

    // Secondary/Default buttons - Glassmorphic
    color: 'rgba(42, 42, 42, 0.4)',
    colorHover: 'rgba(80, 0, 0, 0.2)',
    colorPressed: 'rgba(80, 0, 0, 0.3)',
    colorFocus: 'rgba(80, 0, 0, 0.2)',
    colorDisabled: 'rgba(36, 36, 36, 0.2)',

    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderHover: '1px solid rgba(80, 0, 0, 0.5)',
    borderPressed: '1px solid rgba(80, 0, 0, 0.7)',
    borderFocus: '1px solid rgba(80, 0, 0, 0.5)',
    borderDisabled: '1px solid rgba(255, 255, 255, 0.03)',

    rippleColor: 'rgba(80, 0, 0, 0.3)',

    // Primary button - Glassmorphic maroon
    textColorPrimary: '#ffffff',
    textColorHoverPrimary: '#ffffff',
    textColorPressedPrimary: '#ffffff',
    textColorFocusPrimary: '#ffffff',
    textColorDisabledPrimary: '#5a5a5a',

    colorPrimary: 'rgba(80, 0, 0, 0.7)',
    colorHoverPrimary: 'rgba(106, 0, 0, 0.8)',
    colorPressedPrimary: 'rgba(58, 0, 0, 0.9)',
    colorFocusPrimary: 'rgba(80, 0, 0, 0.7)',
    colorDisabledPrimary: 'rgba(42, 42, 42, 0.3)',

    borderPrimary: '1px solid rgba(106, 0, 0, 0.6)',
    borderHoverPrimary: '1px solid rgba(106, 0, 0, 0.8)',
    borderPressedPrimary: '1px solid rgba(58, 0, 0, 0.9)',
    borderFocusPrimary: '1px solid rgba(106, 0, 0, 0.6)',
    borderDisabledPrimary: '1px solid rgba(255, 255, 255, 0.03)'
  },

  Card: {
    // Glassmorphic card backgrounds
    color: 'rgba(36, 36, 36, 0.7)',
    colorModal: 'rgba(26, 26, 26, 0.9)',
    colorEmbedded: 'rgba(42, 42, 42, 0.5)',
    colorTarget: 'rgba(80, 0, 0, 0.05)',

    // Text colors
    textColor: '#e8e8e8',
    titleTextColor: '#e8e8e8',

    // Borders
    borderColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',

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

    // Close button
    closeColorHover: 'rgba(80, 0, 0, 0.2)',
    closeColorPressed: 'rgba(80, 0, 0, 0.3)',
    closeIconColor: '#b8b8b8',
    closeIconColorHover: '#e8e8e8',
    closeIconColorPressed: '#888888'
  },

  Tag: {
    // Glassmorphic tags
    color: 'rgba(42, 42, 42, 0.5)',
    textColor: '#e8e8e8',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',

    // Primary tag (maroon)
    colorPrimary: 'rgba(80, 0, 0, 0.6)',
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
    closeIconColor: '#b8b8b8',
    closeIconColorHover: '#e8e8e8',
    closeIconColorPressed: '#888888',
    closeColorHover: 'rgba(255, 255, 255, 0.08)',
    closeColorPressed: 'rgba(255, 255, 255, 0.12)'
  }
}
