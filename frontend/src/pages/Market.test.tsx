import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Assets } from './Assets';
import { Watchlists } from './Watchlists';
import { Providers } from './Providers';

test('search preserves empty results and exposes provider warnings', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => ({ ok: true, json: async () => String(input).includes('search?') ? { items: [], warnings: ['Alpha Vantage: falta API key'] } : [] }) as Response);
  render(<MemoryRouter><Assets /></MemoryRouter>);
  await userEvent.type(screen.getByLabelText('Buscar activos'), 'AAPL');
  await userEvent.click(screen.getByRole('button', { name: /^Buscar$/ }));
  expect(await screen.findByText('No se encontraron activos')).toBeVisible();
  expect(screen.getByText('Alpha Vantage: falta API key')).toBeInTheDocument();
});

test('watchlist can be created from an empty account', async () => {
  const mock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => ({ ok: true, json: async () => init?.method === 'POST' ? { id: 'new-list', name: 'Energy' } : String(input).endsWith('/items') ? [] : [] }) as Response);
  render(<MemoryRouter><Watchlists /></MemoryRouter>);
  await userEvent.type(screen.getByLabelText('Nombre de watchlist'), 'Energy');
  await userEvent.click(screen.getByRole('button', { name: 'Crear watchlist' }));
  expect(mock).toHaveBeenCalledWith('/api/watchlists', expect.objectContaining({ method: 'POST', body: JSON.stringify({ name: 'Energy' }) }));
});

test('provider failure is an error, not a fabricated status', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 503, json: async () => ({ detail: 'Servicio no disponible' }) } as Response);
  render(<Providers />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Servicio no disponible');
});
