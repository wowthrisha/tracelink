import { render, screen } from '@testing-library/react';
import { KpiCard } from '../KpiCard.jsx';

// BUG-008 regression: the "?" help icon on Analytics Overview metric cards
// had an aria-label but was a plain, non-focusable <span> — keyboard and
// screen-reader users could never Tab to it, so the aria-label was never
// announced during normal navigation despite looking accessible in markup.
// The fix makes it a real <button>, which is natively focusable and
// triggers its `title` tooltip on focus (not just hover) in modern browsers.

describe('KpiCard — help icon accessibility (BUG-008)', () => {
  test('renders the help icon as a real, focusable button when a tooltip is provided', () => {
    render(<KpiCard k={{ label: 'Blocked Attempts (Today)', value: '0', icon: '⊗', tooltip: 'Prints, copies, downloads blocked today.' }} />);
    const help = screen.getByRole('button', { name: 'Info: Prints, copies, downloads blocked today.' });
    expect(help.tagName).toBe('BUTTON');
    expect(help.tabIndex).toBe(0);
  });

  test('help button carries a native title so it also works as a hover/focus tooltip', () => {
    render(<KpiCard k={{ label: 'Views Today', value: '12', icon: '▦', tooltip: 'Number of document page views recorded today.' }} />);
    const help = screen.getByRole('button', { name: /Info:/ });
    expect(help.title).toBe('Number of document page views recorded today.');
  });

  test('renders no help icon at all when a card has no tooltip (nothing to explain)', () => {
    render(<KpiCard k={{ label: 'Active Docs', value: '4', icon: '◈' }} />);
    expect(screen.queryByRole('button', { name: /Info:/ })).not.toBeInTheDocument();
  });

  test('card value and label still render correctly alongside the help button', () => {
    render(<KpiCard k={{ label: 'Completion', value: '82%', icon: '⊕', tooltip: 'Average completion rate.' }} />);
    expect(screen.getByText('Completion')).toBeInTheDocument();
    expect(screen.getByText('82%')).toBeInTheDocument();
  });
});
