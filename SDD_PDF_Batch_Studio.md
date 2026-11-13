# SDD --- PDF Batch Studio

## Aplicación local para unir grandes lotes de archivos PDF

**Versión:** 1.0\
**Estado:** Propuesta funcional y técnica\
**Tipo de producto:** Aplicación de escritorio/local-first\
**Nombre de trabajo:** PDF Batch Studio

------------------------------------------------------------------------

## 1. Resumen ejecutivo

PDF Batch Studio es una aplicación local que permite importar,
organizar, previsualizar y combinar grandes cantidades de archivos PDF
en uno o varios documentos finales. Está pensada para trabajar con lotes
grandes ---desde unos pocos archivos hasta cientos o miles, según el
hardware y el tamaño de los documentos--- sin subir archivos a
servidores externos.

La experiencia debe ser visual y sencilla: el usuario arrastra archivos
o carpetas, ve una lista ordenable con miniaturas y datos de cada PDF,
define el orden final, revisa el resultado y ejecuta la unión. La
aplicación debe informar del progreso, permitir cancelar operaciones
cuando sea seguro y generar un reporte claro si algún archivo falla.

**Principio central:** los archivos y el procesamiento permanecen en el
equipo del usuario. No se requiere cuenta, conexión a Internet ni API
externa.

## 2. Objetivos

### 2.1 Objetivos principales

1.  Unir múltiples PDF en un único PDF final.
2.  Procesar lotes grandes sin cargar todos los documentos completos en
    memoria.
3.  Importar archivos individuales, selecciones múltiples y carpetas
    completas.
4.  Permitir ordenar los PDF antes de unirlos.
5.  Ofrecer previsualización de páginas y documentos.
6.  Mostrar metadatos útiles: nombre, tamaño, número de páginas y
    estado.
7.  Guardar el resultado en una ubicación elegida por el usuario.
8.  Mantener la privacidad mediante procesamiento local.
9.  Informar errores por archivo sin perder el trabajo ya organizado.
10. Tener una interfaz moderna, clara, accesible y fácil de aprender.

### 2.2 Objetivos secundarios

-   Reordenar páginas dentro de un PDF.
-   Excluir archivos o páginas sin eliminarlos del disco.
-   Girar páginas seleccionadas.
-   Dividir el lote en varios PDF por cantidad de páginas o tamaño
    objetivo, si la biblioteca lo permite con fiabilidad.
-   Guardar y volver a abrir una configuración de lote.
-   Detectar archivos duplicados y PDF dañados o protegidos.

### 2.3 Fuera del alcance del MVP

-   OCR y reconocimiento de texto.
-   Edición avanzada del contenido interno del PDF.
-   Firma digital certificada.
-   Compresión agresiva con garantías de conservación visual.
-   Conversión universal entre formatos.
-   Sincronización en la nube o colaboración multiusuario.
-   Envío automático a servicios externos.

Estas funciones pueden evaluarse en versiones posteriores, pero no deben
retrasar la primera versión estable.

## 3. Usuarios y casos de uso

### Usuario objetivo

Personas que necesitan consolidar documentación: estudiantes,
profesionales, administración, estudios contables, oficinas y usuarios
particulares.

### Casos de uso principales

-   Unir 5 PDF en un único documento.
-   Unir 300 PDF ordenados alfabéticamente.
-   Importar una carpeta con subcarpetas y filtrar extensiones.
-   Reorganizar manualmente documentos antes de generar el resultado.
-   Revisar páginas de un documento antes de incluirlo.
-   Detectar cuál archivo falló dentro de un lote de cientos de
    documentos.
-   Generar varios PDF finales a partir de un lote demasiado grande.

## 4. Requisitos funcionales

Prioridad: **P0** = imprescindible para MVP; **P1** = importante; **P2**
= posterior.

  -----------------------------------------------------------------------
  ID                      Requisito               Prioridad
  ----------------------- ----------------------- -----------------------
  FR-001                  Importar uno o varios   P0
                          PDF mediante selector   
                          de archivos             

  FR-002                  Arrastrar y soltar      P0
                          archivos PDF en la      
                          aplicación              

  FR-003                  Importar todos los PDF  P0
                          de una carpeta          

  FR-004                  Mostrar lista de        P0
                          archivos con nombre,    
                          tamaño, páginas y       
                          estado                  

  FR-005                  Reordenar documentos    P0
                          mediante drag and drop  

  FR-006                  Quitar elementos de la  P0
                          lista sin borrar el     
                          archivo original        

  FR-007                  Previsualizar el PDF    P0
                          seleccionado            

  FR-008                  Navegar entre páginas y P0
                          mostrar el número de    
                          página actual           

  FR-009                  Unir los documentos     P0
                          respetando el orden     
                          visible                 

  FR-010                  Elegir nombre y destino P0
                          del PDF final           

  FR-011                  Mostrar progreso, etapa P0
                          actual y archivo        
                          procesado               

  FR-012                  Informar errores por    P0
                          archivo y permitir      
                          continuar cuando sea    
                          seguro                  

  FR-013                  Validar archivos        P0
                          vacíos, corruptos, no   
                          PDF o protegidos        

  FR-014                  Cancelar el proceso de  P0
                          forma controlada        

  FR-015                  No modificar ni         P0
                          eliminar los PDF de     
                          origen                  

  FR-016                  Ordenar por nombre,     P1
                          tamaño, fecha y         
                          cantidad de páginas     

  FR-017                  Detectar duplicados por P1
                          hash SHA-256            

  FR-018                  Seleccionar o excluir   P1
                          páginas de cada         
                          documento               

  FR-019                  Rotar páginas antes de  P1
                          la unión                

  FR-020                  Guardar y cargar        P1
                          sesiones de trabajo     

  FR-021                  Exportar un reporte de  P1
                          procesamiento           

  FR-022                  Crear varios archivos   P2
                          de salida según reglas  
                          configurables           

  FR-023                  Comparar visualmente el P2
                          tamaño estimado y final 
  -----------------------------------------------------------------------

## 5. Requisitos no funcionales

### Rendimiento y escalabilidad

-   La aplicación debe admitir lotes grandes sin leer todos los bytes de
    todos los PDF en RAM.
-   El backend debe procesar documentos secuencialmente o en pequeños
    bloques.
-   La interfaz no debe congelarse durante importación, generación de
    miniaturas o unión.
-   Las miniaturas deben generarse bajo demanda y almacenarse en caché
    temporal.
-   La lista debe virtualizarse cuando contenga cientos o miles de
    elementos.
-   El progreso debe actualizarse por etapas y no depender de una única
    operación bloqueante.
-   El rendimiento real dependerá del número de páginas, tamaño,
    complejidad, cifrado y estado de los PDF; no se prometerá una cifra
    universal.

### Privacidad y seguridad

-   Procesamiento 100 % local en el MVP.
-   No enviar archivos, nombres, rutas ni metadatos a servicios
    externos.
-   No incorporar telemetría por defecto.
-   No ejecutar macros, scripts ni contenido activo de documentos.
-   Validar rutas y evitar sobrescribir archivos accidentalmente.
-   Crear el resultado primero en un archivo temporal y renombrarlo al
    finalizar correctamente.
-   No modificar archivos fuente.
-   No registrar contenido del documento en logs.
-   Los archivos temporales deben ubicarse en una carpeta de trabajo
    controlada y limpiarse al terminar o al iniciar una nueva sesión,
    según corresponda.

### Usabilidad y accesibilidad

-   Interfaz en español inicialmente, preparada para
    internacionalización.
-   Acciones principales visibles y con etiquetas claras.
-   Atajos de teclado para importar, quitar, mover y unir.
-   Estados vacíos con instrucciones concretas.
-   Contraste suficiente, foco visible y navegación por teclado.
-   Confirmación antes de acciones destructivas o sobrescrituras.
-   Errores explicados en lenguaje comprensible, con detalle técnico
    expandible.

### Compatibilidad

-   Primera plataforma objetivo: Windows 10/11 de 64 bits.
-   Arquitectura preparada para Linux y macOS en el futuro.
-   No depender de GPU dedicada.
-   No requerir Internet para las funciones principales.

## 6. Experiencia de usuario y diseño de interfaz

### Dirección visual

Diseño de escritorio moderno, limpio y profesional. Evitar una interfaz
recargada o con apariencia de panel técnico.

**Estilo sugerido:** - Fondo gris muy claro o gris azulado. -
Superficies blancas para paneles y tarjetas. - Un color de acento azul o
violeta para acciones principales. - Verde para tareas completadas,
ámbar para advertencias y rojo para errores. - Bordes suaves, sombras
discretas y espaciado consistente. - Iconografía lineal y tipografía
legible. - Tema claro inicial y tema oscuro como mejora P1.

### Estructura principal

``` text
┌────────────────────────────────────────────────────────────────────┐
│ PDF Batch Studio                         Ayuda   Ajustes   ─ □ ×   │
├────────────────────────────────────────────────────────────────────┤
│  Unir PDF                                                           │
│  Combina documentos en el orden que elijas.                         │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │       Arrastra tus PDF aquí                                  │  │
│  │       o selecciona archivos / importar carpeta               │  │
│  │                     [ + Agregar PDF ]                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Documentos (128)       Buscar...       Ordenar: Manual             │
│  ┌──────────────────────────────┐ ┌─────────────────────────────┐  │
│  │ ≡  miniatura  documento.pdf  │ │                             │  │
│  │              12 páginas      │ │       PREVISUALIZACIÓN      │  │
│  │              2.4 MB          │ │                             │  │
│  │                              │ │       Página 1 de 12        │  │
│  │ ≡  miniatura  informe.pdf    │ │                             │  │
│  │              8 páginas       │ │       [ página PDF ]        │  │
│  │              1.1 MB          │ │                             │  │
│  │                              │ │       ‹  1 / 12  ›          │  │
│  │ ...                          │ │                             │  │
│  └──────────────────────────────┘ └─────────────────────────────┘  │
│                                                                    │
│  128 archivos · 2.340 páginas · 418 MB                             │
│  Guardar como: [ documentos_unidos.pdf           ] [Elegir...]     │
│                                       [ Unir PDF ]                  │
└────────────────────────────────────────────────────────────────────┘
```

### Pantallas y componentes

1.  **Inicio / espacio de trabajo**
    -   Zona de arrastre.
    -   Botones para agregar archivos y carpetas.
    -   Lista de documentos.
    -   Resumen del lote.
    -   Panel de previsualización.
    -   Configuración de salida y botón de unión.
2.  **Lista de documentos**
    -   Miniatura de primera página.
    -   Nombre, páginas y tamaño.
    -   Indicador de estado.
    -   Control para reordenar.
    -   Menú contextual: previsualizar, quitar, abrir ubicación.
    -   Selección múltiple.
3.  **Previsualizador**
    -   Render de página con zoom.
    -   Anterior / siguiente.
    -   Indicador `página actual / total`.
    -   Ajustar a ancho y ajustar a página.
    -   Fondo neutro y controles discretos.
    -   Renderizado bajo demanda; no renderizar todas las páginas
        simultáneamente.
4.  **Panel de salida**
    -   Nombre del archivo.
    -   Selector de destino.
    -   Resumen de documentos y páginas.
    -   Opción para no sobrescribir.
    -   Botón principal "Unir PDF".
5.  **Procesamiento**
    -   Barra de progreso.
    -   Etapa: validando, preparando, uniendo, verificando o guardando.
    -   Documento actual y contador.
    -   Tiempo transcurrido.
    -   Botón cancelar.
6.  **Resultado**
    -   Estado final.
    -   Ruta del archivo generado.
    -   Tamaño final y cantidad de páginas.
    -   Acciones: abrir PDF, abrir carpeta, volver al lote.
    -   Reporte de advertencias o errores.
7.  **Ajustes**
    -   Tema.
    -   Idioma.
    -   Carpeta temporal.
    -   Política de caché de miniaturas.
    -   Confirmación de sobrescritura.
    -   Límites de uso de memoria configurables solo si son necesarios.

## 7. Arquitectura técnica propuesta

### Recomendación para el MVP

Construir una aplicación local con frontend web y backend local:

-   **Frontend:** React + TypeScript + Vite.
-   **Estilos:** Tailwind CSS + componentes accesibles (por ejemplo,
    shadcn/ui).
-   **Estado:** Zustand o Context reducido; evitar sobrearquitectura.
-   **Drag and drop:** dnd-kit.
-   **Previsualización:** PDF.js.
-   **Backend:** Python + FastAPI.
-   **Procesamiento PDF:** PyMuPDF (fitz) como motor principal.
-   **Validación/operaciones complementarias:** pypdf cuando aporte una
    capacidad concreta.
-   **Comunicación:** API HTTP en `127.0.0.1` y eventos SSE o WebSocket
    para progreso.
-   **Persistencia de sesión:** SQLite o JSON local; para el MVP, JSON
    puede ser suficiente.
-   **Empaquetado futuro:** instalador de escritorio con Tauri o
    alternativa equivalente.

**Motivo de esta elección:** permite construir rápidamente una interfaz
rica y una previsualización fluida, mientras Python y PyMuPDF realizan
el trabajo pesado en el equipo. No requiere GPU ni servicios pagos. La
primera entrega puede ejecutarse en localhost; el empaquetado como
aplicación instalable se aborda después de estabilizar el flujo.

### Diagrama de alto nivel

``` text
┌──────────────────────────────┐
│ React + TypeScript           │
│                              │
│ Workspace / File List        │
│ Drag & Drop / PDF Preview    │
│ Progress / Output Settings   │
└──────────────┬───────────────┘
               │ HTTP + SSE
               ▼
┌──────────────────────────────┐
│ FastAPI (localhost)          │
│                              │
│ Import / Validation          │
│ Batch Manager                │
│ Preview / Thumbnail API      │
│ Merge Job / Progress         │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ PDF Processing Layer         │
│                              │
│ PyMuPDF / pypdf               │
│ Sequential Merge             │
│ Validation / Verification    │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Local File System            │
│ Source PDFs / Temp / Output  │
│ Session Data / Thumbnail Cache│
└──────────────────────────────┘
```

### Estructura de carpetas sugerida

``` text
pdf-batch-studio/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── dropzone/
│   │   │   ├── file-list/
│   │   │   ├── pdf-preview/
│   │   │   ├── progress/
│   │   │   └── output/
│   │   ├── features/
│   │   │   ├── import/
│   │   │   ├── batch/
│   │   │   ├── preview/
│   │   │   └── merge/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── stores/
│   │   ├── types/
│   │   └── styles/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── pdf_inspector.py
│   │   │   ├── pdf_preview.py
│   │   │   ├── pdf_merger.py
│   │   │   ├── batch_manager.py
│   │   │   └── validation.py
│   │   ├── workers/
│   │   └── main.py
│   └── tests/
├── docs/
├── scripts/
├── .gitignore
└── README.md
```

## 8. Modelo de dominio

### PdfDocument

Representa un PDF incorporado al lote.

  Campo           Tipo               Descripción
  --------------- ------------------ -----------------------------------
  id              UUID               Identificador interno
  path            string             Ruta local de origen
  name            string             Nombre visible
  size_bytes      integer            Tamaño del archivo
  page_count      integer nullable   Cantidad de páginas
  sha256          string nullable    Hash para detectar duplicados
  status          enum               Estado de validación
  error_message   string nullable    Motivo de fallo
  included        boolean            Si participa en la unión
  order_index     integer            Posición en el lote
  metadata        object             Metadatos no sensibles necesarios

Estados sugeridos: `pending`, `inspecting`, `ready`, `warning`,
`invalid`, `protected`, `processing`, `completed`, `failed`.

### MergeJob

Representa una operación de unión.

  Campo                 Tipo                Descripción
  --------------------- ------------------- -------------------------------
  id                    UUID                Identificador del trabajo
  document_ids          UUID\[\]            Documentos incluidos en orden
  output_path           string              Destino
  status                enum                Estado del proceso
  progress              number              Progreso 0--100
  current_document      string nullable     Archivo actual
  total_pages           integer             Páginas estimadas
  processed_documents   integer             Documentos procesados
  error_count           integer             Errores
  started_at            datetime            Inicio
  finished_at           datetime nullable   Finalización

### BatchSession

Contiene el estado recuperable de una sesión: lista ordenada,
exclusiones, opciones y destino. No debe guardar el contenido binario de
los PDF.

## 9. Flujo principal de procesamiento

### 9.1 Importación

1.  El usuario agrega archivos o una carpeta.
2.  El frontend envía las rutas seleccionadas al backend local.
3.  El backend comprueba existencia, extensión, tamaño y accesibilidad.
4.  Inspecciona el PDF y obtiene cantidad de páginas y metadatos
    mínimos.
5.  Devuelve un resultado individual por archivo.
6.  El frontend incorpora los documentos válidos y marca advertencias o
    errores.

No bloquear la interfaz mientras se inspeccionan los archivos. La
importación debe procesarse en segundo plano y publicar actualizaciones
parciales.

### 9.2 Previsualización

1.  El usuario selecciona un documento.
2.  El frontend solicita la página necesaria.
3.  El backend o PDF.js obtiene/renderiza solo la página solicitada.
4.  La miniatura se guarda en caché temporal.
5.  Al cambiar de página, se solicita la siguiente sin volver a cargar
    el documento completo innecesariamente.

Evaluar dos estrategias: - **PDF.js en frontend:** entregar el archivo
local al visor mediante un mecanismo controlado. - **Render del
backend:** generar imágenes de páginas con PyMuPDF y servirlas desde
endpoints locales.

Elegir una estrategia única para el MVP tras una prueba de rendimiento.
No duplicar renderizadores sin necesidad.

### 9.3 Unión

1.  Validar que haya al menos dos documentos incluidos (permitir uno
    solo si se decide que también sirve como copia).
2.  Confirmar destino y política de sobrescritura.
3.  Crear un trabajo de unión.
4.  Abrir el destino temporal en la misma carpeta del destino final.
5.  Procesar los PDF en el orden de la lista.
6.  Incorporar páginas de forma secuencial, evitando mantener múltiples
    copias completas en RAM.
7.  Cerrar y verificar el documento temporal.
8.  Renombrar atómicamente al destino final si la verificación fue
    exitosa.
9.  Publicar resultado y reporte.

**Importante:** probar el comportamiento de memoria de PyMuPDF con lotes
reales. El procesamiento secuencial reduce picos de memoria, pero no
garantiza memoria constante para todos los tipos de PDF. Si aparecen
límites en lotes extremos, evaluar escritura incremental, qpdf o un
motor alternativo.

### 9.4 Cancelación y recuperación

-   La cancelación debe comprobarse entre documentos o bloques seguros.
-   No dejar un PDF parcial presentado como resultado válido.
-   El temporal debe eliminarse o conservarse como archivo de
    recuperación claramente identificado.
-   Si la aplicación se cierra inesperadamente, el siguiente inicio debe
    detectar trabajos incompletos y ofrecer limpiar temporales.
-   No reanudar una unión parcial salvo que la arquitectura pueda
    garantizar integridad.

## 10. API local propuesta

Todos los endpoints deben escuchar únicamente en `127.0.0.1`, salvo que
exista una decisión explícita posterior.

  --------------------------------------------------------------------------------------
  Método                  Endpoint                               Función
  ----------------------- -------------------------------------- -----------------------
  POST                    `/api/files/import`                    Importar una lista de
                                                                 rutas

  POST                    `/api/folders/import`                  Importar PDF de una
                                                                 carpeta

  GET                     `/api/documents`                       Obtener documentos de
                                                                 la sesión

  GET                     `/api/documents/{id}`                  Obtener detalle

  GET                     `/api/documents/{id}/preview/{page}`   Obtener vista de una
                                                                 página

  DELETE                  `/api/documents/{id}`                  Quitar de la sesión, no
                                                                 del disco

  PATCH                   `/api/documents/order`                 Actualizar orden

  PATCH                   `/api/documents/{id}`                  Cambiar inclusión u
                                                                 opciones

  POST                    `/api/merge-jobs`                      Iniciar unión

  GET                     `/api/merge-jobs/{id}`                 Consultar estado

  GET                     `/api/merge-jobs/{id}/events`          Recibir progreso por
                                                                 SSE

  POST                    `/api/merge-jobs/{id}/cancel`          Solicitar cancelación

  GET                     `/api/merge-jobs/{id}/report`          Obtener reporte

  POST                    `/api/sessions/save`                   Guardar sesión

  POST                    `/api/sessions/load`                   Cargar sesión
  --------------------------------------------------------------------------------------

### Ejemplo conceptual de respuesta de importación

``` json
{
  "id": "uuid",
  "name": "informe.pdf",
  "size_bytes": 2457600,
  "page_count": 12,
  "status": "ready",
  "included": true,
  "order_index": 0
}
```

No devolver rutas absolutas al frontend si no son necesarias para la
operación. Validar que toda ruta recibida provenga de una selección
explícita del usuario y no de una entrada arbitraria.

## 11. Manejo de errores

  -----------------------------------------------------------------------
  Situación                           Comportamiento esperado
  ----------------------------------- -----------------------------------
  Archivo inexistente                 Marcar como inválido y mostrar el
                                      nombre

  Extensión distinta de PDF           Rechazar o ignorar con explicación

  PDF corrupto                        Marcar error y permitir quitarlo

  PDF cifrado con contraseña          Solicitar contraseña solo si se
                                      implementa soporte; nunca intentar
                                      eludir protección

  Contraseña incorrecta               Mostrar error específico

  Sin permisos de lectura             Informar y permitir reintentar

  Disco sin espacio                   Detener de forma segura y conservar
                                      fuentes

  Destino existente                   Pedir confirmación o proponer otro
                                      nombre

  Error durante la unión              No publicar el temporal como
                                      resultado final

  Archivo duplicado                   Advertir; no excluir
                                      automáticamente

  Archivo muy grande                  Procesar sin cargarlo completo en
                                      memoria y mostrar estado
  -----------------------------------------------------------------------

Los errores deben tener dos niveles: mensaje breve para usuario y
detalle técnico expandible para diagnóstico.

## 12. Seguridad local

Aunque no exista servidor remoto, la aplicación expone un backend local
y debe protegerlo.

-   Bind exclusivo a `127.0.0.1`.
-   CORS limitado al origen del frontend.
-   Token aleatorio de sesión o mecanismo equivalente para evitar que
    páginas web arbitrarias invoquen operaciones locales.
-   Validación estricta de rutas y operaciones.
-   Límites razonables de cantidad de archivos y longitud de rutas.
-   No aceptar comandos de sistema ni rutas de salida arbitrarias sin
    validación.
-   No ejecutar JavaScript, formularios ni contenido activo de los PDF.
-   Mantener dependencias actualizadas y fijar versiones.
-   No registrar contraseñas ni contenido de documentos.
-   Eliminar archivos temporales de forma segura cuando sea posible.

## 13. Pruebas y criterios de aceptación

### Pruebas funcionales

-   Importar un archivo.
-   Importar múltiples archivos.
-   Importar una carpeta con subcarpetas.
-   Reordenar 100 documentos.
-   Excluir y volver a incluir un documento.
-   Previsualizar páginas iniciales, intermedias y finales.
-   Unir archivos con distinto tamaño y número de páginas.
-   Comprobar que el orden de páginas final coincide con el orden de la
    lista.
-   Verificar que los originales no fueron modificados.
-   Probar archivos corruptos, protegidos y duplicados.
-   Cancelar una operación en curso.
-   Verificar el archivo final después de cerrar y volver a abrir la
    aplicación.

### Pruebas de rendimiento

Crear un conjunto reproducible con: - 100 PDF pequeños. - 500 PDF
pequeños. - 1.000 PDF pequeños. - 20 PDF grandes. - PDF con muchas
imágenes. - PDF escaneados. - PDF con diferentes tamaños de página.

Registrar: - Tiempo de importación. - Tiempo de generación de
miniaturas. - Tiempo de unión. - Pico de RAM. - Uso de CPU. - Tamaño del
resultado. - Número de errores.

No fijar límites absolutos antes de medir en el equipo objetivo. Definir
presupuestos de rendimiento después de crear el benchmark.

### Criterios de aceptación del MVP

1.  Un usuario puede importar una carpeta y ver todos los PDF
    reconocidos.
2.  Puede ordenar y excluir documentos sin modificar los originales.
3.  Puede previsualizar cualquier página de un documento válido.
4.  Puede unir el lote en el orden mostrado.
5.  La interfaz permanece operativa durante el procesamiento.
6.  Se muestra progreso y resultado verificable.
7.  Los errores individuales se identifican claramente.
8.  Un fallo no deja un archivo parcial presentado como terminado.
9.  El proceso no necesita Internet ni una API externa.
10. El consumo de memoria se mide y documenta con lotes de prueba.

## 14. Plan de desarrollo por etapas

### Etapa 0 --- Validación técnica

-   Crear prototipo de unión con PyMuPDF.
-   Medir RAM y tiempo con lotes de 100, 500 y 1.000 archivos.
-   Probar PDF cifrados, corruptos y con imágenes grandes.
-   Comparar PDF.js frontend contra render de miniaturas en backend.
-   Documentar límites y decisiones.

**Entregable:** benchmark y decisión técnica documentada.

### Etapa 1 --- MVP funcional

-   Crear frontend React + TypeScript.
-   Crear backend FastAPI.
-   Importación de archivos y carpetas.
-   Inspección y listado.
-   Reordenamiento drag and drop.
-   Previsualización básica.
-   Unión secuencial.
-   Selector de salida.
-   Progreso, cancelación segura y reporte de errores.

**Entregable:** aplicación local capaz de unir lotes y verificar el
resultado.

### Etapa 2 --- Experiencia de usuario

-   Pulir diseño visual y estados vacíos.
-   Miniaturas con caché.
-   Búsqueda y ordenamiento.
-   Selección múltiple.
-   Atajos de teclado.
-   Tema oscuro.
-   Mejoras de accesibilidad.

**Entregable:** interfaz de uso cotidiano.

### Etapa 3 --- Edición previa y sesiones

-   Selección/exclusión de páginas.
-   Rotación.
-   Detección de duplicados.
-   Guardar y cargar sesiones.
-   Reportes exportables.

**Entregable:** flujo avanzado de preparación de lotes.

### Etapa 4 --- Distribución

-   Empaquetar frontend y backend.
-   Crear instalador para Windows.
-   Configurar inicio y cierre controlado del backend.
-   Probar rutas con espacios, permisos y antivirus.
-   Firmado del instalador si en el futuro existe certificado.
-   Preparar builds para Linux/macOS si se priorizan.

**Entregable:** aplicación instalable, sin necesidad de abrir terminal.

## 15. Decisiones técnicas que deben respetarse

1.  **Local-first real:** ninguna operación principal debe depender de
    Internet.
2.  **No subir archivos:** no usar almacenamiento cloud ni APIs
    externas.
3.  **Procesamiento fuera del hilo de UI:** toda tarea pesada va al
    backend o worker.
4.  **Memoria controlada:** evitar leer todos los PDF y todas las
    páginas simultáneamente.
5.  **Previsualización bajo demanda:** renderizar solo las páginas
    visibles o solicitadas.
6.  **Fuentes inmutables:** nunca editar ni borrar los documentos de
    origen.
7.  **Salida transaccional:** generar temporal, verificar y luego
    publicar.
8.  **Separación de responsabilidades:** UI, API, inspección,
    renderizado, unión y persistencia deben ser módulos independientes.
9.  **Errores recuperables:** un documento defectuoso no debe invalidar
    silenciosamente todo el lote.
10. **Sin promesas de rendimiento no medidas:** validar con benchmarks
    reproducibles.

## 16. Riesgos técnicos

  -----------------------------------------------------------------------
  Riesgo                  Impacto                 Mitigación
  ----------------------- ----------------------- -----------------------
  PDF con estructuras     Fallos o lentitud       Suite de documentos
  internas complejas                              variados y motor
                                                  alternativo evaluado

  Consumo elevado de RAM  Bloqueos                Procesamiento
                                                  secuencial, límites de
                                                  concurrencia y
                                                  benchmark

  PDF cifrados            No se pueden unir sin   Flujo explícito de
                          autorización            contraseña; no eludir
                                                  protección

  Miniaturas de muchos    Uso de disco y CPU      Caché limitada y
  documentos                                      generación bajo demanda

  Cierre inesperado       Temporales incompletos  Escritura temporal,
                                                  limpieza y recuperación

  Rutas con permisos      Importación fallida     Errores por archivo y
  especiales                                      pruebas de Windows

  Backend local expuesto  Riesgo de invocación no Loopback, CORS y token
                          autorizada              local
  -----------------------------------------------------------------------

## 17. Dependencias candidatas

### Frontend

-   React
-   TypeScript
-   Vite
-   Tailwind CSS
-   shadcn/ui o biblioteca equivalente
-   dnd-kit
-   PDF.js
-   Zustand
-   Lucide Icons

### Backend

-   Python 3.12
-   FastAPI
-   Uvicorn
-   PyMuPDF
-   pypdf (solo para operaciones complementarias justificadas)
-   Pydantic
-   pytest
-   SQLite (si la persistencia supera un simple JSON)

Fijar versiones compatibles en los archivos de dependencias. Revisar
licencias y condiciones de redistribución antes de empaquetar.

## 18. Instrucciones para el agente de desarrollo

El agente debe trabajar por etapas y no intentar implementar todo de una
sola vez.

### Reglas de implementación

-   Antes de programar, revisar el repositorio y describir su estado.
-   Crear un plan técnico breve y validar la estructura de carpetas.
-   Implementar primero el benchmark de PDF y documentar resultados.
-   Mantener TypeScript estricto.
-   Mantener tipado explícito en los contratos frontend/backend.
-   No mezclar lógica de PDF dentro de componentes React.
-   No crear componentes gigantes.
-   No duplicar lógica de validación.
-   No bloquear el hilo principal.
-   Añadir pruebas unitarias para validación, orden y unión.
-   Añadir pruebas de integración para los endpoints y trabajos.
-   Ejecutar lint, typecheck y tests al finalizar cada etapa.
-   No introducir servicios pagos, APIs externas ni dependencias cloud.
-   No afirmar que una operación funciona sin probarla con archivos
    reales.
-   Documentar cualquier desviación respecto de este SDD.

### Primera tarea concreta

Construir un prototipo técnico que: 1. Reciba una lista ordenada de
rutas PDF. 2. Valide cada documento. 3. Una los archivos
secuencialmente. 4. Verifique el resultado y el número total de páginas.
5. Registre tiempo y pico de memoria. 6. Ejecute pruebas con 100, 500 y
1.000 PDF pequeños.

No avanzar al diseño completo hasta conocer el comportamiento del motor
con lotes grandes.

------------------------------------------------------------------------

## 19. Resultado esperado del producto

Una aplicación local para Windows con una interfaz visual pulida y
simple, que permita arrastrar cientos de PDF, revisar su contenido en
una previsualización, ordenar el lote y generar un único documento final
de forma controlada. La prioridad es la fiabilidad, la privacidad y el
rendimiento medido, no acumular funciones innecesarias.
