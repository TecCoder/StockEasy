import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './useAuth';

function SessionControls() {
  const { user, shutdown } = useAuth();
  if (!user) return <span>Sesión cerrada</span>;
  return <button onClick={() => void shutdown()}>Salir</button>;
}

test('shutdown closes the session through the desktop endpoint', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input);
    const body = url.endsWith('/auth/me')
      ? { id: 'user-1', username: 'alice', csrf_token: 'csrf-token' }
      : { ok: true, shutdown: true };
    return { ok: true, status: 200, json: async () => body } as Response;
  });

  render(<AuthProvider><SessionControls /></AuthProvider>);
  await userEvent.click(await screen.findByRole('button', { name: 'Salir' }));

  expect(fetchMock).toHaveBeenLastCalledWith(
    '/api/auth/logout-and-shutdown',
    expect.objectContaining({ method: 'POST' }),
  );
  expect(await screen.findByText('Sesión cerrada')).toBeVisible();
});
