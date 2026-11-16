import { render, screen } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

import AppShell from './AppShell';

vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: ({ count }: { count: number }) => ({
    getTotalSize: () => count * 64,
    getVirtualItems: () =>
      Array.from({ length: count }, (_, index) => ({ index, start: index * 64, size: 64, key: index })),
    scrollToIndex: vi.fn(),
  }),
}));

const server = setupServer(
  http.get('*/api/documents', () => HttpResponse.json({ documents: [] })),
);

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('AppShell', () => {
  it('conserva los textos y la estructura de la unión', async () => {
    render(<AppShell />);

    expect(screen.getByRole('heading', { name: 'Unir documentos PDF' })).toBeInTheDocument();
    expect(await screen.findByText('Arrastrá tus PDF aquí')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Agregar PDF' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Atajos de teclado' })).toBeInTheDocument();
    expect(screen.getByText('archivos')).toBeInTheDocument();
    expect(screen.getByText('páginas')).toBeInTheDocument();
  });

  it('muestra documentos y permite excluirlos del lote', async () => {
    server.use(
      http.get('*/api/documents', () =>
        HttpResponse.json({
          documents: [
            {
              id: 'doc-1',
              path: 'C:/docs/a.pdf',
              name: 'a.pdf',
              size_bytes: 2048,
              page_count: 3,
              sha256: 'hash',
              status: 'ready',
              error_message: null,
              included: true,
              order_index: 0,
              metadata: {},
            },
          ],
        }),
      ),
    );

    render(<AppShell />);

    expect(await screen.findByText('a.pdf')).toBeInTheDocument();
    expect(screen.getByText('3 págs')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Excluir del lote' })).toBeInTheDocument();
  });
});
