# Benchmark --- PDF Batch Studio (Etapa 0)

Prototipo de unión secuencial con PyMuPDF (`backend/app/services/pdf_merger.py`).
PDF de prueba: 1 página cada uno, texto + rectángulo (generados con `scripts/generate_test_pdfs.py`).

## Resultados

| Lote | Inspección (s) | Unión (s) | Pico RAM (MB) | Páginas salida | Errores |
|------|----------------|-----------|---------------|----------------|---------|
| 100  | 0.582          | 0.495     | 52.39         | 100            | 0       |
| 500  | 2.904          | 2.985     | 55.69         | 500            | 0       |
| 1000 | 6.011          | 6.535     | 59.39         | 1000           | 0       |

## Conclusiones

- El procesamiento secuencial (`insert_pdf` por documento, cerrando cada fuente) mantiene el pico de RAM casi constante (~52-59 MB) entre 100 y 1000 PDFs de 1 página.
- El tiempo de unión escala linealmente (~6.5 ms/PDF en este hardware).
- No se detectaron errores ni archivos parciales.
- Decisión: PyMuPDF con unión secuencial es viable para el MVP. Se mantiene la estrategia de archivo temporal + verificación + renombrado atómico.

## Pendiente de medir (Etapa 0 extendida)

- PDFs grandes (20+), con muchas imágenes, escaneados, tamaños de página mixtos.
- PDFs cifrados y corruptos (ya cubiertos por tests unitarios).
- Pico de RAM con documentos de cientos de páginas.