import { describe, expect, it } from 'vitest';

import type { PdfDocument } from '@/lib/api';
import { findDuplicates } from './duplicates';

function doc(id: string, sha256: string | null): PdfDocument {
  return {
    id,
    path: `C:/docs/${id}.pdf`,
    name: `${id}.pdf`,
    size_bytes: 1024,
    page_count: 1,
    sha256,
    status: 'ready',
    error_message: null,
    included: true,
    order_index: 0,
    metadata: {},
  };
}

describe('findDuplicates', () => {
  it('no marca nada cuando no hay hashes', () => {
    const info = findDuplicates([doc('a', null), doc('b', null)]);
    expect(info.groupCount).toBe(0);
    expect(info.flagged.size).toBe(0);
    expect(info.extras.size).toBe(0);
  });

  it('marca todas las copias de un grupo de dos', () => {
    const info = findDuplicates([doc('a', 'hash'), doc('b', 'hash'), doc('c', 'otro')]);
    expect(info.groupCount).toBe(1);
    expect([...info.flagged].sort()).toEqual(['a', 'b']);
    expect([...info.extras]).toEqual(['b']);
    expect(info.groupSize.get('a')).toBe(2);
    expect(info.groupSize.get('b')).toBe(2);
    expect(info.groupSize.has('c')).toBe(false);
  });

  it('cuenta grupos de tres copias', () => {
    const info = findDuplicates([doc('a', 'x'), doc('b', 'x'), doc('c', 'x'), doc('d', 'y')]);
    expect(info.groupCount).toBe(1);
    expect(info.groupSize.get('c')).toBe(3);
    expect([...info.extras].sort()).toEqual(['b', 'c']);
  });

  it('separa grupos por hash distinto', () => {
    const info = findDuplicates([
      doc('a', 'x'), doc('b', 'x'),
      doc('c', 'y'), doc('d', 'y'),
    ]);
    expect(info.groupCount).toBe(2);
    expect([...info.extras].sort()).toEqual(['b', 'd']);
  });
});
