import { render, screen, fireEvent, within } from '@testing-library/react';
import { WebhooksScreen } from '../WebhooksScreen.jsx';
import { ToastProvider } from '../../contexts/toast.jsx';

// BUG-007 regression: the global `input, textarea, select { width: 100%;
// padding: 9px 12px; ... }` rule in SecureDoc.html (meant for text inputs)
// has no `input[type="checkbox"]` exclusion, so it also stretched the "New
// Webhook" > "Events to Subscribe" checkboxes to fill their row, breaking
// alignment with the label text next to each one. LinksPanel.jsx's checkbox
// already carries an inline override that neutralizes this; WebhooksScreen's
// was just missing the same treatment.

function renderScreen() {
  return render(
    <ToastProvider>
      <WebhooksScreen />
    </ToastProvider>
  );
}

describe('WebhooksScreen — New Webhook checkbox alignment (BUG-007)', () => {
  beforeEach(() => {
    window.SecureDocAPI.listWebhooks = vi.fn().mockResolvedValue({ webhooks: [] });
  });

  test('every "Events to subscribe" checkbox has a fixed size and does not stretch to fill the row', async () => {
    renderScreen();
    fireEvent.click(await screen.findByText('+ New Webhook'));
    const heading = await screen.findByText('Events to subscribe');
    const checkboxes = within(heading.closest('div').parentElement).getAllByRole('checkbox');
    expect(checkboxes.length).toBe(3);
    checkboxes.forEach(cb => {
      expect(cb.style.width).toBe('13px');
      expect(cb.style.height).toBe('13px');
      expect(cb.style.flexShrink).toBe('0');
    });
  });

  test('checkbox styling matches the established fix already used by LinksPanel\'s checkbox', async () => {
    renderScreen();
    fireEvent.click(await screen.findByText('+ New Webhook'));
    const checkboxes = await screen.findAllByRole('checkbox');
    // accentColor is the same token LinksPanel.jsx already uses (#5ac8d0).
    expect(checkboxes[0].style.accentColor).toBe('rgb(90, 200, 208)');
  });
});
