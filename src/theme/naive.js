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
    baseColor: '#1a1a1a',
    bodyColor: '#1a1a1a',

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
    // Header styling
    thColor: '#2a2a2a',
    thColorHover: '#323232',
    thTextColor: '#e8e8e8',
    thFontWeight: '600',
    thButtonColorHover: 'rgba(80, 0, 0, 0.1)',
    thIconColor: '#b8b8b8',
    thIconColorActive: '#500000',

    // Cell styling
    tdColor: 'transparent',
    tdColorHover: 'rgba(80, 0, 0, 0.05)',
    tdColorStriped: 'rgba(80, 0, 0, 0.03)',
    tdTextColor: '#e8e8e8',

    // Borders
    borderColor: '#3a3a3a',
    borderRadius: '8px',

    // Filter/Sort indicators
    filterColor: '#500000',

    // Loading state
    loadingColor: 'rgba(80, 0, 0, 0.12)',

    // Pagination
    paginationBorderColor: '#3a3a3a',

    // Action column
    actionDividerColor: '#2a2a2a',

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

    color: 'transparent',
    colorHover: 'rgba(80, 0, 0, 0.1)',
    colorPressed: 'rgba(80, 0, 0, 0.15)',
    colorFocus: 'rgba(80, 0, 0, 0.1)',
    colorDisabled: 'transparent',

    border: '1px solid #4a4a4a',
    borderHover: '1px solid #500000',
    borderPressed: '1px solid #3a0000',
    borderFocus: '1px solid #500000',
    borderDisabled: '1px solid #2a2a2a',

    rippleColor: '#500000',

    // Primary button (maroon gradient)
    textColorPrimary: '#ffffff',
    textColorHoverPrimary: '#ffffff',
    textColorPressedPrimary: '#ffffff',
    textColorFocusPrimary: '#ffffff',
    textColorDisabledPrimary: '#5a5a5a',

    colorPrimary: '#500000',
    colorHoverPrimary: '#6a0000',
    colorPressedPrimary: '#3a0000',
    colorFocusPrimary: '#500000',
    colorDisabledPrimary: '#2a2a2a',

    borderPrimary: '1px solid #500000',
    borderHoverPrimary: '1px solid #6a0000',
    borderPressedPrimary: '1px solid #3a0000',
    borderFocusPrimary: '1px solid #500000',
    borderDisabledPrimary: '1px solid #2a2a2a'
  }
}
