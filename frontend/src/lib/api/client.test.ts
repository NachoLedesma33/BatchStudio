import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiClientError, readToken, request, setToken } from './client';

beforeEach(() => {
  setToken(null);
  window.sessionStorage.clear();
  window.history.replaceState(null, '', '/');
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('readToken', () => {
  it('lee el token del fragmento, lo guarda y limpia la URL', () => {
    window.location.hash = '#token=abc123';
    expect(readToken()).toBe('abc123');
    expect(window.sessionStorage.getItem('pdfbs_token')).toBe('abc123');
    expect(window.location.hash).toBe('');
  });

  it('reutiliza el token guardado en sessionStorage', () => {
    window.sessionStorage.setItem('pdfbs_token', 'guardado');
    expect(readToken()).toBe('guardado');
  });
});

describe('request', () => {
  it('agrega el token local a cada llamada', async () => {
    setToken('tok');
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await request<{ status: string }>('/health');
    expect(result.status).toBe('ok');

    const call = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(call[0]).toBe('/api/health');
    const headers = new Headers(call[1].headers);
    expect(headers.get('X-PDFBS-Token')).toBe('tok');
  });

  it('convierte el envelope de error en ApiClientError', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(
        JSON.stringify({
          detail: {
            code: 'NO_DOCUMENTS',
            message: 'No hay documentos incluidos en el lote.',
            hint: 'Agregá al menos un PDF.',
          },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      ),
    ));

    await expect(request('/merge-jobs')).rejects.toMatchObject({
      name: 'ApiClientError',
      code: 'NO_DOCUMENTS',
      message: 'No hay documentos incluidos en el lote.',
      hint: 'Agregá al menos un PDF.',
    });
    await expect(request('/merge-jobs')).rejects.toBeInstanceOf(ApiClientError);
  });

  it('usa un código HTTP cuando la respuesta no es JSON', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('caído', { status: 503 })));
    await expect(request('/documents')).rejects.toMatchObject({
      code: 'HTTP_503',
      message: 'caído',
    });
  });
});
