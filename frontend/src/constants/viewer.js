// Viewer layout mode identifiers
export const LAYOUT = {
  AUTO:       'auto',
  FIT_WIDTH:  'fit-width',
  FIT_HEIGHT: 'fit-height',
  ACTUAL:     'actual',
  CUSTOM:     'custom',
};

// Zoom range and preset values
export const ZOOM_MIN     = 10;
export const ZOOM_MAX     = 400;
export const ZOOM_STEP    = 10;
export const ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200, 300, 400];

// Persist layout preferences to localStorage across sessions
export function _saveLayoutPref(mode, zoom) {
  try { localStorage.setItem('sdoc-layout-mode', mode); } catch {}
  try { localStorage.setItem('sdoc-layout-zoom', String(zoom)); } catch {}
}

export function _loadLayoutPref() {
  let mode = LAYOUT.AUTO, zoom = 100;
  try { const m = localStorage.getItem('sdoc-layout-mode'); if (m) mode = m; } catch {}
  try { const z = parseInt(localStorage.getItem('sdoc-layout-zoom') || '100', 10); if (z >= ZOOM_MIN && z <= ZOOM_MAX) zoom = z; } catch {}
  return { mode, zoom };
}
