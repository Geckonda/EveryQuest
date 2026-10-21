import type { GlobalThemeOverrides } from 'naive-ui'

/**
 * Палитра «таверны». Светлая — пергамент, чернила и сургуч; тёмная — дерево, золото и свечи.
 * Те же значения продублированы CSS-переменными в assets/main.css — меняйте вместе.
 */
const BODY_FONT = "Alegreya, Georgia, 'Times New Roman', serif"
const HEADING_FONT = "'Cormorant Garamond', Georgia, serif"

const shared: GlobalThemeOverrides = {
  common: {
    fontFamily: BODY_FONT,
    fontSize: '15px',
    fontSizeMedium: '15px',
    borderRadius: '4px',
    borderRadiusSmall: '3px',
  },
  // Размер заголовков — здесь, а не CSS с !important; шрифт — в main.css (токена шрифта нет).
  Card: { titleFontWeight: '700', titleFontSizeMedium: '24px', titleFontSizeSmall: '22px' },
  Dialog: { titleFontWeight: '700', titleFontSize: '24px' },
  Tabs: { tabFontWeightActive: '700' },
  Button: { fontWeight: '600' },
}

export const lightOverrides: GlobalThemeOverrides = {
  ...shared,
  common: {
    ...shared.common,
    // Сургуч
    primaryColor: '#8e2f1c',
    primaryColorHover: '#a63b25',
    primaryColorPressed: '#6f2414',
    primaryColorSuppl: '#a63b25',
    // Зелёные чернила лекаря
    successColor: '#4d7326',
    successColorHover: '#5d8a2f',
    successColorPressed: '#3e5e1f',
    successColorSuppl: '#5d8a2f',
    warningColor: '#a8711a',
    warningColorHover: '#bd8222',
    warningColorPressed: '#8a5c14',
    warningColorSuppl: '#bd8222',
    errorColor: '#9b1f1f',
    errorColorHover: '#b32a2a',
    errorColorPressed: '#7d1818',
    errorColorSuppl: '#b32a2a',
    // «Информация» — чернила с позолотой, а не синий по умолчанию (значки диалогов, сообщения).
    infoColor: '#7a5a22',
    infoColorHover: '#8f6a2b',
    infoColorPressed: '#5f4519',
    infoColorSuppl: '#8f6a2b',
    textColorBase: '#33241a',
    textColor1: '#33241a',
    textColor2: '#4a3726',
    textColor3: '#7a6142',
    placeholderColor: '#9c8664',
    bodyColor: '#efe1bf',
    cardColor: '#fbf3dd',
    modalColor: '#fbf3dd',
    popoverColor: '#fbf3dd',
    tableColor: '#fbf3dd',
    inputColor: '#fffaec',
    inputColorDisabled: '#efe4c8',
    actionColor: '#f3e6c4',
    borderColor: '#c4a46c',
    dividerColor: '#d9c393',
    hoverColor: 'rgba(142, 47, 28, 0.08)',
  },
}

export const darkOverrides: GlobalThemeOverrides = {
  ...shared,
  common: {
    ...shared.common,
    // Золото при свечах
    primaryColor: '#d9a441',
    primaryColorHover: '#e8b856',
    primaryColorPressed: '#b98a30',
    primaryColorSuppl: '#e8b856',
    successColor: '#8fb45a',
    successColorHover: '#a2c76b',
    successColorPressed: '#769846',
    successColorSuppl: '#a2c76b',
    warningColor: '#e0a33c',
    warningColorHover: '#ecb352',
    warningColorPressed: '#c08a2c',
    warningColorSuppl: '#ecb352',
    errorColor: '#e0614f',
    errorColorHover: '#ea7563',
    errorColorPressed: '#c24c3c',
    errorColorSuppl: '#ea7563',
    infoColor: '#c9a46a',
    infoColorHover: '#d8b67e',
    infoColorPressed: '#ab8853',
    infoColorSuppl: '#d8b67e',
    textColorBase: '#f1e3c6',
    textColor1: '#f1e3c6',
    textColor2: '#e2d1ad',
    textColor3: '#b49d77',
    placeholderColor: '#8c7656',
    bodyColor: '#17110b',
    cardColor: '#2a1e14',
    modalColor: '#2a1e14',
    popoverColor: '#33251a',
    tableColor: '#2a1e14',
    inputColor: '#1f1710',
    inputColorDisabled: '#2a2018',
    actionColor: '#30231a',
    borderColor: '#6b4d2c',
    dividerColor: '#4d3820',
    hoverColor: 'rgba(217, 164, 65, 0.1)',
  },
  // Тёмный текст на золотых кнопках читается лучше белого.
  Button: {
    ...shared.Button,
    textColorPrimary: '#1d140c',
    textColorHoverPrimary: '#1d140c',
    textColorPressedPrimary: '#1d140c',
    textColorFocusPrimary: '#1d140c',
  },
}

export { HEADING_FONT }
