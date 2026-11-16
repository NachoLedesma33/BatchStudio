# PDF Batch Studio — Plan maestro de mejoras

**Tipo:** Plan general de evolución funcional  
**Estado:** Propuesta pendiente de planificación detallada  
**Enfoque:** Aplicación de escritorio, local-first y orientada al trabajo individual y masivo con documentos PDF.

## 1. Propósito

Este documento reúne las mejoras propuestas para evolucionar PDF Batch Studio desde una herramienta centrada en unir múltiples archivos PDF hacia una solución integral para **organizar, transformar, editar, automatizar y consultar documentos**.

El objetivo es definir qué capacidades podría incorporar el producto y qué necesidad resolvería cada una, sin desarrollar todavía las especificaciones técnicas ni los pasos detallados de implementación.

Cada iniciativa deberá contar posteriormente con su propio plan de implementación, que profundizará en alcance, casos de uso, flujo de usuario, reglas de negocio, diseño UX/UI, arquitectura, dependencias, seguridad, errores, pruebas y criterios de aceptación.

Este archivo funciona como una **hoja de ruta funcional de alto nivel**. No implica implementar todas las funciones simultáneamente.

## 2. Principios rectores

1. **Local-first:** los documentos se procesan en el equipo del usuario; no se envían a servicios externos.
2. **Gratuito:** priorizar bibliotecas y herramientas gratuitas y de código abierto. No introducir servicios pagos ni APIs facturables como requisito.
3. **Privacidad:** documentos, índices, historiales y configuraciones permanecen localmente, salvo exportación explícita.
4. **Procesamiento por lotes:** contemplar operaciones individuales y masivas.
5. **Uso eficiente de recursos:** evitar cargar documentos completos en memoria sin necesidad; utilizar procesamiento por demanda, lotes y caché limitada.
6. **Experiencia consistente:** compartir patrones de interfaz, estados, mensajes y controles entre módulos.
7. **Integridad de originales:** no sobrescribir el original sin confirmación explícita. Por defecto, generar una salida independiente.
8. **Transparencia:** mostrar qué operación se ejecuta, sobre qué archivos, su progreso y sus resultados.
9. **Arquitectura extensible:** incorporar módulos sin convertir la aplicación en una colección desordenada de herramientas.
10. **Compatibilidad:** priorizar una experiencia estable en Windows y no depender de una GPU dedicada.

## 3. Áreas funcionales

### A. Organización y manipulación de documentos

#### A.1. Dividir PDF
Separar un documento en varios archivos mediante rangos definidos por el usuario, una página por archivo, intervalos o grupos personalizados. Permitir estimar cuántos archivos se generarán y definir sus nombres.

#### A.2. Organizador visual de páginas
Incorporar una vista de miniaturas para reordenar páginas mediante arrastrar y soltar, eliminar, duplicar, rotar, extraer páginas y seleccionar rangos o grupos discontinuos. El usuario podrá revisar el resultado antes de guardarlo.

#### A.3. Compresión de PDF
Ofrecer distintos niveles de compresión para reducir el tamaño. Distinguir, cuando sea posible, PDFs textuales de documentos con imágenes o escaneos. Mostrar tamaño original y resultado, además de advertir sobre posibles pérdidas de calidad.

#### A.4. Rotación inteligente
Detectar páginas cuya orientación parezca incorrecta y sugerir una corrección automática. El usuario podrá revisar las páginas detectadas y aceptar o descartar los cambios. Distinguir orientación física de página y orientación del contenido.

#### A.5. Detección y eliminación de páginas en blanco
Identificar páginas que probablemente no contienen contenido relevante y permitir eliminarlas individualmente o en grupo. La detección debe ser conservadora para no descartar páginas con firmas, sellos o pequeñas marcas.

#### A.6. Recorte de páginas
Permitir ajustar visualmente los márgenes visibles de una o varias páginas, con previsualización y aplicación a rangos. Diferenciar el recorte visual de la eliminación irreversible del contenido exterior.

#### A.7. Detección de documentos duplicados
Identificar archivos repetidos dentro de una selección o carpeta. La primera etapa puede comparar hashes para detectar duplicados exactos; una ampliación podría reconocer documentos visual o textualmente similares. Revisar resultados antes de excluir o eliminar archivos.

### B. Conversión de documentos

#### B.1. Exportar PDF a imágenes
Convertir páginas a PNG o JPEG. Incluir selección de páginas, resolución y calidad cuando corresponda. Contemplar una página o el documento completo y evitar conflictos de nombres en conversiones masivas.

#### B.2. Crear PDF desde imágenes
Importar imágenes y generar un PDF. Permitir ordenarlas, rotarlas, definir tamaño y orientación de página, ajustar márgenes y elegir cómo adaptar cada imagen al papel.

#### B.3. Extraer texto a TXT
Extraer texto seleccionable de un PDF y guardarlo como TXT. Diferenciar documentos con texto nativo de escaneos que necesitan OCR e informar cómo se obtuvo el texto.

#### B.4. Convertir PDF a DOCX
Ofrecer conversión a documentos editables. Advertir que tablas, columnas, imágenes, fuentes y diseños complejos pueden no conservarse exactamente. Priorizar la legibilidad y estructura del contenido.

#### B.5. Convertir PDF a HTML
Generar una versión HTML del contenido, conservando en la medida de lo posible texto, imágenes y estructura. Definir si la salida será un archivo único o un conjunto de recursos.

#### B.6. Convertir documentos de Office a PDF
Convertir DOCX, XLSX y PPTX a PDF mediante una herramienta local compatible, por ejemplo LibreOffice. Contemplar conversión individual y por lotes, destino y advertencias sobre diferencias de formato.

#### B.7. Exportación PDF/A
Permitir generar documentos compatibles con perfiles PDF/A para conservación a largo plazo. Indicar el perfil utilizado y validar el resultado cuando sea posible. No declarar conformidad sin verificación.

### C. Inteligencia y búsqueda documental

#### C.1. OCR local
Reconocer texto de escaneos o páginas que solo contienen imágenes. Ejecutarse localmente, contemplar selección de idioma, procesamiento por lotes y, cuando corresponda, generación de PDF con capa de texto reconocida. Informar páginas procesadas y limitaciones de calidad.

#### C.2. Búsqueda dentro de PDFs
Buscar palabras o frases dentro de un documento y mostrar coincidencias con número de página y fragmento de contexto. Funcionar con texto nativo y documentos procesados mediante OCR. Abrir el PDF en la página correspondiente desde un resultado.

#### C.3. Búsqueda global
Extender la búsqueda a múltiples archivos o a la biblioteca local. Indicar documento, página y fragmento coincidente. Utilizar, si conviene, un índice local actualizable, reconstruible y eliminable.

#### C.4. Clasificación automática
Sugerir categorías según nombre, metadatos y contenido textual disponible. Ejemplos: facturas, contratos, apuntes, informes y formularios. La clasificación será editable y no moverá ni modificará archivos sin autorización.

#### C.5. Edición de metadatos
Consultar y modificar título, autor, asunto y palabras clave. Permitir limpiar metadatos seleccionados antes de compartir un documento, mostrando qué información se eliminará.

#### C.6. Detección de similitud documental
Identificar documentos que parecen versiones del mismo contenido aunque difieran en formato, compresión o metadatos. Combinar, potencialmente, texto extraído, estructura y características visuales. Mostrar similitud orientativa y permitir comparar.

### D. Edición y acabado profesional

#### D.1. Marca de agua
Agregar marcas de agua de texto o imagen a una o varias páginas. Configurar posición, tamaño, transparencia, rotación y alcance; incluir previsualización y configuraciones reutilizables.

#### D.2. Numeración de páginas
Agregar numeración configurable por posición, formato, número inicial y rangos incluidos o excluidos. Puede incluir formatos como “Página X de Y”. Previsualizar para evitar tapar contenido.

#### D.3. Encabezados y pies de página
Agregar textos o elementos sencillos en la parte superior o inferior, como título, fecha, nombre del documento o numeración. Aplicar a todas las páginas o a rangos.

#### D.4. Firma visual
Insertar una imagen de firma o un trazo dibujado por el usuario. Aclarar que una firma visual no equivale necesariamente a una firma digital criptográfica ni acredita por sí sola identidad o integridad legal.

#### D.5. Protección con contraseña
Proteger un PDF mediante contraseña y configurar permisos compatibles con el formato y motor utilizado. Explicar la diferencia entre contraseña de apertura y restricciones de permisos.

#### D.6. Desbloqueo autorizado
Generar una copia sin restricciones cuando el usuario proporcione una contraseña válida y tenga autorización para modificar el documento. No plantearlo como herramienta para vulnerar contraseñas desconocidas.

#### D.7. Anotaciones
Añadir comentarios, resaltados, subrayados, formas y notas. Diferenciar anotaciones editables de contenido que se aplana o integra visualmente en la página. Previsualizar antes de guardar.

#### D.8. Comparación de versiones
Comparar dos documentos para identificar diferencias. Una primera versión podría comparar número de páginas, texto y metadatos; una ampliación podría señalar diferencias visuales.

### E. Automatización y procesamiento masivo

#### E.1. Procesamiento por lotes
Ejecutar operaciones compatibles sobre muchos archivos. Mostrar estado por archivo, progreso general, errores y elementos completados. Un fallo aislado no debería cancelar todo el lote salvo que exista una dependencia que lo exija.

#### E.2. Vigilar carpetas
Detectar archivos nuevos en una carpeta seleccionada y ejecutar una regla configurada. Ejemplos: combinar PDFs recibidos, generar copias comprimidas o clasificarlos. Incluir controles para activar, pausar y desactivar.

#### E.3. Reglas de unión automática
Guardar reglas para combinar documentos sin repetir la configuración: carpeta de entrada, orden, filtros por nombre, exclusión de duplicados exactos, nombre y destino de salida y comportamiento ante errores.

#### E.4. Ordenamiento automático
Ordenar por nombre, fecha, tamaño, número de páginas o patrones definidos. Mostrar el orden aplicado y permitir modificarlo antes de ejecutar.

#### E.5. Agrupación por patrones
Agrupar archivos por prefijos, sufijos, fechas, palabras clave o patrones de nombre. Mostrar los grupos detectados para revisión previa.

#### E.6. Renombrado masivo
Renombrar mediante plantillas que combinen texto fijo, nombre original, fecha, número correlativo y otros datos. Mostrar una vista previa y detectar conflictos antes de aplicar.

#### E.7. Reglas reutilizables
Guardar configuraciones de operaciones frecuentes para repetirlas. Cada regla debe poder editarse o duplicarse. Las acciones sensibles no se ejecutarán silenciosamente.

#### E.8. Cola de trabajos
Administrar operaciones largas o múltiples desde una cola central. Mostrar estado, archivos asociados, progreso, duración y resultado. Contemplar pausa o cancelación cuando sea técnicamente posible.

### F. Productividad y experiencia de uso

#### F.1. Historial de operaciones
Registrar fecha, tipo de acción, archivos de entrada, destino y resultado. Facilitar la consulta de trabajos anteriores y apertura de resultados, sin almacenar el contenido completo de los documentos.

#### F.2. Deshacer y rehacer
Permitir deshacer y rehacer acciones reversibles de la sesión, como reordenar o excluir elementos. Deshacer una acción de interfaz no debe borrar archivos del disco sin confirmación.

#### F.3. Guardado automático de sesiones
Guardar el estado de trabajo para recuperar selección, orden, opciones y documento activo después de cerrar la aplicación. Guardar referencias a archivos en lugar de duplicar originales.

#### F.4. Atajos de teclado
Incorporar atajos para agregar archivos, quitar elementos, navegar páginas, iniciar operaciones y abrir preferencias. Deben ser consistentes y visibles.

#### F.5. Apertura de ubicación
Permitir abrir la carpeta de origen o destino y localizar archivos desde el explorador del sistema.

#### F.6. Recuperación ante interrupciones
Detectar sesiones o trabajos interrumpidos por cierres inesperados. Al iniciar, informar tareas incompletas y permitir revisar resultados parciales antes de reintentar.

#### F.7. Reportes de procesamiento
Generar resúmenes de lotes con archivos procesados, omitidos y fallidos, advertencias, tamaños antes y después y ubicación de resultados. Visualizar y exportar en TXT, CSV o JSON.

#### F.8. Tema claro y oscuro
Ofrecer temas claro y oscuro con contraste y legibilidad consistentes. Guardar la preferencia entre sesiones.

#### F.9. Preferencias generales
Centralizar carpeta de salida, comportamiento al agregar archivos, confirmaciones, idioma de OCR, tema, límites de procesamiento y opciones de previsualización.

### G. Biblioteca documental local

#### G.1. Carpetas favoritas
Registrar carpetas habituales para acceder rápidamente. Funcionan como accesos directos: agregarlas no debe copiar ni mover archivos.

#### G.2. Documentos recientes
Mostrar archivos abiertos o procesados recientemente, con acceso a ubicación y operaciones disponibles. La lista debe poder limpiarse y su persistencia ser configurable.

#### G.3. Etiquetas y colecciones
Organizar referencias a documentos mediante etiquetas y colecciones personalizadas, sin alterar la estructura física de carpetas.

#### G.4. Filtros documentales
Filtrar por nombre, extensión, fecha, tamaño, cantidad de páginas, etiquetas y metadatos. Permitir combinar filtros.

#### G.5. Índice local
Mantener un índice local de metadatos y, si el usuario lo habilita, texto extraído u OCR. Contemplar actualización, reconstrucción, eliminación y detección de archivos movidos o desaparecidos.

#### G.6. Favoritos
Marcar documentos para acceder rápidamente. Guardar referencias a los archivos y señalar cuando una ruta deja de estar disponible.

### H. Perfiles y flujos de trabajo predefinidos

#### H.1. Perfiles de trabajo
Agrupar configuraciones frecuentes para simplificar tareas repetitivas. Un perfil puede establecer operaciones, opciones, nombres de salida y reglas de organización. Antes de ejecutar, revisar las acciones previstas.

#### H.2. Perfil académico
Orientado a apuntes, capítulos, bibliografía y material de estudio. Podría combinar documentos, ordenar archivos, numerar páginas, extraer texto y generar una salida organizada.

#### H.3. Perfil profesional
Orientado a informes, propuestas y documentación administrativa. Podría combinar archivos, optimizar tamaño, actualizar metadatos, agregar encabezados o numeración y aplicar protección cuando corresponda.

#### H.4. Perfil de documentos escaneados
Orientado a escaneos o fotografías. Podría sugerir rotación, detectar páginas en blanco, ejecutar OCR, comprimir y generar una versión con texto reconocible.

#### H.5. Perfil de archivo y conservación
Orientado a preparar documentos para almacenamiento a largo plazo. Podría revisar metadatos, generar una versión optimizada, comprobar compatibilidad PDF/A cuando esté disponible y producir un reporte.

#### H.6. Constructor de perfiles personalizados
Permitir crear perfiles combinando operaciones compatibles y guardando parámetros. Explicar el orden de ejecución y advertir sobre dependencias.

## 4. Estructura de navegación propuesta

| Sección | Responsabilidad |
|---|---|
| Inicio | Acciones frecuentes, recientes y accesos a perfiles |
| Organizar | Unir, dividir, ordenar, extraer, rotar y administrar páginas |
| Convertir | PDF a otros formatos e imágenes a PDF |
| Editar | Marcas de agua, numeración, anotaciones, metadatos y protección |
| Automatizar | Lotes, reglas, carpetas vigiladas y cola de trabajos |
| Biblioteca | Carpetas favoritas, colecciones, etiquetas y búsqueda global |
| Historial | Operaciones anteriores, resultados y reportes |
| Preferencias | Apariencia, rutas, privacidad y comportamiento general |

La navegación definitiva deberá validarse con el volumen real de funcionalidades. No es necesario mostrar todas las secciones desde la primera versión.

## 5. Tecnologías y herramientas candidatas

La selección definitiva se realizará durante el plan de implementación de cada iniciativa. Estas son candidatas, no dependencias obligatorias:

| Herramienta | Posible responsabilidad |
|---|---|
| PyMuPDF | Lectura, renderizado, extracción de texto y operaciones sobre PDF |
| pypdf | Unión, división, manipulación y lectura de estructuras PDF |
| PDF.js | Previsualización de documentos en la interfaz |
| Tesseract OCR | Reconocimiento óptico de caracteres local |
| LibreOffice | Conversión local de documentos de Office a PDF |
| qpdf | Operaciones de bajo nivel, validación y transformaciones compatibles |
| SQLite | Sesiones, historial, perfiles y biblioteca local |
| SQLite FTS5 | Índice y búsqueda de texto local |
| OpenCV | Análisis de imágenes y páginas escaneadas |

Antes de incorporar una herramienta se deberá verificar compatibilidad, mantenimiento, licencias, redistribución, tamaño de instalación y comportamiento en Windows.

## 6. Priorización orientativa

Esta priorización es una propuesta inicial basada en valor para el usuario, reutilización de componentes y complejidad relativa. No representa una estimación de horas ni una decisión irreversible.

### Prioridad 1 — Ampliar el núcleo
- Organizador visual de páginas.
- Dividir PDF.
- Rotación manual e inteligente.
- Compresión de PDF.
- Detección de páginas en blanco.
- Exportar PDF a imágenes.
- Crear PDF desde imágenes.
- Historial de operaciones.
- Guardado automático de sesiones.
- Cola de trabajos y procesamiento por lotes.

### Prioridad 2 — Herramienta documental
- OCR local.
- Extracción de texto a TXT.
- Búsqueda dentro de documentos.
- Búsqueda global.
- Edición de metadatos.
- Marca de agua.
- Numeración de páginas.
- Encabezados y pies de página.
- Protección con contraseña.
- Renombrado masivo.
- Reportes de procesamiento.

### Prioridad 3 — Biblioteca y automatización
- Biblioteca documental local.
- Carpetas favoritas y documentos recientes.
- Etiquetas y colecciones.
- Clasificación automática.
- Reglas reutilizables.
- Agrupación por patrones.
- Carpetas vigiladas.
- Perfiles predefinidos y personalizados.
- Detección de duplicados y similitud.

### Prioridad 4 — Edición y conversión avanzada
- PDF a DOCX.
- PDF a HTML.
- Office a PDF.
- Exportación PDF/A.
- Anotaciones.
- Firma visual.
- Recorte de páginas.
- Comparación de versiones.
- Desbloqueo autorizado.
- Recuperación avanzada de trabajos.

La prioridad podrá cambiar luego de validar necesidades reales y complejidad técnica.

## 7. Plantilla para futuros planes de implementación

Cada iniciativa seleccionada deberá contar con su propio documento. Se recomienda esta estructura:

1. **Identificación:** nombre, área, prioridad y estado.
2. **Problema que resuelve:** necesidad concreta del usuario.
3. **Objetivo:** resultado que se busca conseguir.
4. **Alcance:** qué incluye y qué queda fuera.
5. **Casos de uso:** situaciones concretas y actores.
6. **Flujo de usuario:** pasos desde el inicio hasta el resultado.
7. **Comportamiento funcional:** reglas, opciones, validaciones y estados.
8. **Diseño UX/UI:** pantallas, componentes, interacciones y estados vacíos.
9. **Diseño técnico:** módulos, servicios, contratos y persistencia.
10. **Dependencias:** bibliotecas, herramientas locales y licencias.
11. **Rendimiento:** límites, memoria, concurrencia, caché y pruebas con lotes.
12. **Seguridad e integridad:** archivos originales, rutas, permisos y datos temporales.
13. **Errores y recuperación:** fallos previsibles y respuesta del sistema.
14. **Pruebas:** unitarias, integración, interfaz, regresión y rendimiento.
15. **Criterios de aceptación:** condiciones verificables para considerar terminada la función.
16. **Etapas de implementación:** entregas pequeñas y comprobables.
17. **Riesgos y decisiones pendientes:** aspectos que requieren investigación o validación.

## 8. Criterios generales de aceptación

Una mejora no se considerará terminada únicamente porque exista un botón o una pantalla. Según corresponda:

- La operación produce un resultado real y verificable.
- Los estados de carga, éxito, advertencia y error están representados.
- Los errores de un archivo no provocan pérdidas en otros archivos.
- El usuario identifica claramente entradas y salidas.
- Los originales se conservan por defecto.
- Las operaciones largas no bloquean innecesariamente la interfaz.
- El consumo de memoria se mantiene controlado en lotes grandes.
- La función opera sin conexión cuando su naturaleza lo permite.
- La interfaz es coherente con el resto de la aplicación.
- Existen pruebas para casos normales, límites y errores.
- Se documentan limitaciones de fidelidad o compatibilidad.

## 9. Límites y precauciones

- **Conversión:** PDF a DOCX, HTML u otro formato editable puede alterar diseño, tablas, fuentes o distribución. Comunicar estas limitaciones.
- **OCR:** la precisión depende de resolución, inclinación, idioma y calidad del escaneo.
- **Compresión:** reducir tamaño puede implicar pérdida de calidad, especialmente al recomprimir imágenes.
- **Firmas:** una firma visual no debe presentarse como firma digital criptográfica.
- **Contraseñas:** limitar el desbloqueo a documentos para los que el usuario proporcione credenciales válidas y tenga autorización.
- **PDF/A:** declarar conformidad solo cuando el archivo haya sido validado.
- **Automatización:** las reglas deben ser visibles y controlables; no deben realizar cambios destructivos silenciosos.
- **Duplicados:** la similitud puede producir falsos positivos; revisar antes de descartar archivos.
- **Biblioteca:** registrar una carpeta o archivo no debe implicar moverlo, copiarlo ni modificarlo.

## 10. Resultado esperado

La evolución propuesta busca que PDF Batch Studio pase de ser un unificador de PDFs a una plataforma de escritorio para el trabajo cotidiano con documentos, con cuatro capacidades centrales:

1. **Organizar:** combinar, dividir, reordenar, extraer y limpiar documentos.
2. **Transformar:** convertir, comprimir, reconocer texto y preparar archivos.
3. **Administrar:** buscar, clasificar, consultar historial y mantener una biblioteca local.
4. **Automatizar:** procesar lotes, reutilizar perfiles y ejecutar reglas controladas.

La implementación deberá ser progresiva. Cada iniciativa tendrá su propio plan detallado, pruebas y criterios de aceptación. Este documento funciona como catálogo de mejoras y referencia común para decidir qué construir, en qué orden y con qué objetivo.
