import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Login } from './Login';
import { AuthProvider } from '../hooks/useAuth';

test('login sends credentials and shows authentication errors', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'Usuario o contraseña incorrectos' }) } as Response);
  render(<AuthProvider><Login /></AuthProvider>);
  await userEvent.type(screen.getByLabelText('Usuario'), 'alice');
  await userEvent.type(screen.getByLabelText('Contraseña'), 'wrong');
  await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Usuario o contraseña incorrectos');
  expect(fetchMock).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({ body: JSON.stringify({ username: 'alice', password: 'wrong' }) }));
});
