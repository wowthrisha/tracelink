export const C = {
  bg: '#080B0C',
  surface: '#0E1416',
  surfaceAlt: '#0B0F10',
  surfaceMid: '#131C1E',
  surface2: '#192224',
  surface3: '#1E2A2C',
  border: 'rgba(90,200,208,0.1)',
  borderMed: 'rgba(90,200,208,0.18)',
  borderHover: 'rgba(90,200,208,0.28)',
  borderActive: 'rgba(90,200,208,0.45)',
  teal0: '#C8F4F8',
  teal1: '#8BE2EA',
  teal2: '#5AC8D0',
  teal3: '#3A8A90',
  teal4: '#255A60',
  slate1: '#6B8A8E',
  slate2: '#4A6266',
  slate3: '#2C3E40',
  accentBg: 'rgba(90,200,208,0.07)',
  accentBgHover: 'rgba(90,200,208,0.12)',
  textPrimary: '#F0F2F1',
  textSecondary: '#B0C4C8',
  textMuted: '#6E8C90',
  textDim: '#3A5558',
  success: '#3DD68C',
  successBg: 'rgba(61,214,140,0.08)',
  successBdr: 'rgba(61,214,140,0.22)',
  error: '#E05A45',
  errorBg: 'rgba(224,90,69,0.08)',
  errorBdr: 'rgba(224,90,69,0.22)',
  warning: '#E09A45',
  warningBg: 'rgba(224,154,69,0.08)',
  warningBdr: 'rgba(224,154,69,0.22)',
  info: '#5AC8D0',
  infoBg: 'rgba(90,200,208,0.08)',
  infoBdr: 'rgba(90,200,208,0.22)',
};

export const mono = { fontFamily: "'DM Mono', monospace" };

// Spacing scale — use for new padding/margin/gap values instead of a raw
// number. Values chosen to match the sizes that had already organically
// converged across the app (V7.0 frontend-maturity review found 44 distinct
// padding pairs and 13 distinct gap values with no shared scale). Existing
// call sites are NOT retrofitted here — that's a broad mechanical sweep
// better done as its own pass — but new code has something to reach for now.
export const S = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
};
