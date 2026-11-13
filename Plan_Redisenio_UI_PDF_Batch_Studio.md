# Plan de rediseño integral de interfaz --- PDF Batch Studio

**Tipo:** Plan de implementación UX/UI\
**Versión:** 1.0\
**Objetivo:** reemplazar la interfaz actual por una experiencia de
escritorio profesional, coherente, visualmente atractiva y eficiente
para trabajar con lotes grandes de PDF.\
**Alcance:** frontend completo. No cambiar el motor de unión ni la
lógica de negocio salvo que sea necesario para exponer correctamente
estados o datos a la interfaz.

------------------------------------------------------------------------

# 1. Diagnóstico de la interfaz actual

La captura actual muestra una pantalla centrada en una columna, con
todos los elementos apilados verticalmente. Aunque las funciones
principales están presentes, la jerarquía visual y la distribución no
permiten entender rápidamente cómo trabajar.

## 1.1 Problemas observados

  -----------------------------------------------------------------------
  Problema                Efecto en la            Corrección requerida
                          experiencia             
  ----------------------- ----------------------- -----------------------
  Todo está centrado en   Se desperdicia espacio  Crear una estructura de
  una sola columna        horizontal y la         aplicación con
                          pantalla parece un      encabezado, área de
                          formulario sin terminar trabajo y paneles

  No hay jerarquía entre  El usuario no sabe      Definir una secuencia
  importación,            dónde mirar ni qué      visual clara de 3 pasos
  documentos, preview y   hacer primero           
  exportación                                     

  La lista de documentos  No parece una           Crear un panel de
  no tiene una superficie herramienta capaz de    archivos con filas
  propia                  manejar grandes lotes   compactas, estados y
                                                  acciones

  La previsualización no  El producto pierde una  Darle un panel amplio
  tiene protagonismo      de sus funciones        con fondo de visor y
                          centrales               controles

  Los botones parecen     La aplicación transmite Implementar un sistema
  controles HTML por      aspecto de prototipo    de componentes visuales
  defecto                                         consistente

  Campos y textos están   Baja legibilidad y      Aplicar escala
  pegados                 sensación de desorden   tipográfica, espaciado
                                                  y alineación

  No existe una zona de   No se entiende el       Mostrar archivos,
  resumen del lote bien   volumen de trabajo      páginas y tamaño en
  definida                cargado                 indicadores compactos

  El área de importación  No comunica claramente  Diseñar una dropzone
  no parece interactiva   drag & drop             con estados hover,
                                                  drag-over y vacío

  La acción de unir está  El flujo de trabajo no  Crear una barra de
  aislada al final        es evidente             acciones de salida
                                                  persistente y clara

  No hay estados visuales Los lotes grandes       Añadir badges,
  para validación y       serían difíciles de     progreso, advertencias
  errores                 diagnosticar            y estados por archivo

  No se distingue qué     La relación entre lista Añadir selección
  elemento está           y preview es débil      evidente y
  seleccionado                                    sincronización entre
                                                  paneles

  El contenido no         La página parece        Usar layout de
  aprovecha la altura     incompleta incluso con  aplicación con paneles
  disponible              ventana grande          de altura controlada
  -----------------------------------------------------------------------

## 1.2 Conclusión

No alcanza con cambiar colores, tipografía o bordes. Se necesita
**replantear la composición completa de la pantalla**, la jerarquía de
acciones y la forma en que se presentan los documentos.

La nueva interfaz debe parecer una aplicación de escritorio terminada,
no una página web con controles apilados.

------------------------------------------------------------------------

# 2. Dirección de diseño propuesta

## 2.1 Concepto: Professional Document Workspace

Una estación de trabajo documental: sobria, precisa, moderna y enfocada
en el contenido.

Referencias conceptuales: - Aplicaciones profesionales de gestión
documental. - Herramientas modernas de productividad de escritorio. -
Editores con panel lateral, canvas central y barra de acciones. -
Interfaces minimalistas con superficies diferenciadas y estados claros.

No copiar literalmente otra aplicación. Usar estos patrones como guía de
usabilidad.

## 2.2 Personalidad visual

-   Profesional, no corporativa en exceso.
-   Minimalista, pero no vacía.
-   Densa en información cuando hay muchos archivos, sin resultar
    agobiante.
-   Clara y predecible.
-   Con animaciones cortas y funcionales.
-   Priorizar el documento y la tarea, no la decoración.

## 2.3 Paleta propuesta

Usar una paleta neutral cálida con acento azul índigo. Evitar fondos
completamente blancos en toda la pantalla y evitar gradientes
decorativos excesivos.

  Token              Color       Uso
  ------------------ ----------- ------------------------------
  `app-bg`           `#F4F6FA`   Fondo general
  `surface`          `#FFFFFF`   Paneles y tarjetas
  `surface-subtle`   `#F8FAFC`   Filas, áreas secundarias
  `surface-hover`    `#F1F5F9`   Hover
  `border`           `#E2E8F0`   Bordes y separadores
  `text-primary`     `#172033`   Títulos y texto principal
  `text-secondary`   `#64748B`   Texto auxiliar
  `text-muted`       `#94A3B8`   Metadatos secundarios
  `accent`           `#4F46E5`   Acción principal y selección
  `accent-hover`     `#4338CA`   Hover de acción
  `accent-soft`      `#EEF2FF`   Selección y fondos suaves
  `success`          `#15803D`   Completado
  `warning`          `#B45309`   Advertencias
  `danger`           `#B91C1C`   Errores

El acento debe usarse con moderación. No colorear todos los botones ni
todos los iconos.

## 2.4 Tipografía

-   Familia recomendada: Inter.
-   Alternativa local: system-ui / Segoe UI.
-   Título de aplicación: 16--18 px, semibold.
-   Título de página: 22--26 px, semibold.
-   Título de panel: 13--14 px, semibold.
-   Texto normal: 13--14 px.
-   Metadatos: 11--12 px.
-   Números de resumen: 18--22 px, semibold.

Evitar que todo el texto tenga el mismo tamaño. No usar títulos gigantes
ni textos auxiliares demasiado grandes.

## 2.5 Forma y profundidad

-   Radio de paneles: 12--14 px.
-   Radio de botones e inputs: 8 px.
-   Bordes de 1 px en superficies.
-   Sombras casi imperceptibles, reservadas para menús flotantes y
    diálogos.
-   Separación interna de paneles: 16--20 px.
-   Espaciado de controles: 8--12 px.
-   No usar tarjetas dentro de tarjetas sin necesidad.

------------------------------------------------------------------------

# 3. Nueva arquitectura visual

## 3.1 Layout general

La pantalla debe ocupar el área disponible de la ventana. La lista y el
visor deben compartir el espacio horizontal.

``` text
┌──────────────────────────────────────────────────────────────────────────────┐
│ PDF Batch Studio     Espacio de trabajo                     Ayuda  Ajustes  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Unir documentos PDF                                    [ Limpiar lote ]     │
│  Organiza, revisa y combina tus archivos localmente.                         │
│                                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                         │
│  │  24 archivos │ │  386 páginas │ │   182 MB     │                         │
│  └──────────────┘ └──────────────┘ └──────────────┘                         │
│                                                                              │
│  ┌──────────────────────────────────────┐ ┌───────────────────────────────┐ │
│  │ DOCUMENTOS                           │ │ PREVISUALIZACIÓN              │ │
│  │ [ + Agregar PDF ] [ Carpeta ]         │ │ informe.pdf                   │ │
│  │ Buscar...                 Ordenar ▾   │ │                               │ │
│  │                                      │ │                               │ │
│  │ ≡  [PDF]  contrato.pdf      12 págs  │ │          página PDF           │ │
│  │ ≡  [PDF]  informe.pdf        8 págs  │ │                               │ │
│  │ ≡  [PDF]  anexos.pdf        24 págs  │ │                               │ │
│  │ ≡  [PDF]  presupuesto.pdf    3 págs  │ │                               │ │
│  │                                      │ │                               │ │
│  │                                      │ │                               │ │
│  │ 24 documentos incluidos              │ │       ‹  1 / 8  ›             │ │
│  └──────────────────────────────────────┘ └───────────────────────────────┘ │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ SALIDA                                                                       │
│ Nombre [ documentos_unidos.pdf                    ] Destino [ Elegir... ]   │
│                                             [ Unir 24 documentos ]           │
└──────────────────────────────────────────────────────────────────────────────┘
```

La ilustración es una guía estructural, no una especificación rígida de
píxeles.

## 3.2 Distribución

-   Header: altura aproximada de 56--64 px.
-   Cabecera de página: título, descripción y acción secundaria.
-   Resumen del lote: una fila de indicadores compactos.
-   Workspace: dos paneles.
    -   Documentos: 38--42 % del ancho.
    -   Previsualización: 58--62 % del ancho.
-   Barra de salida: zona inferior claramente diferenciada.
-   La zona de documentos y el visor deben poder desplazarse
    independientemente.
-   La barra de salida debe permanecer visible cuando la ventana lo
    permita.
-   No permitir que el contenido empuje el botón principal fuera de
    pantalla.

## 3.3 Comportamiento responsive

Aunque el objetivo principal es escritorio: - En ventanas menores a 1000
px, reducir la proporción del panel de documentos. - En ventanas muy
estrechas, convertir los paneles en pestañas "Documentos" y "Vista
previa". - Evitar que los controles se solapen. - Mantener accesibles
las acciones principales.

------------------------------------------------------------------------

# 4. Rediseño detallado de componentes

## 4.1 Header

Debe ser discreto y consistente.

Elementos: - Icono de PDF de marca. - Nombre "PDF Batch Studio". -
Etiqueta pequeña "LOCAL" o "En este dispositivo". - Acceso a ayuda. -
Acceso a ajustes.

No colocar el nombre del producto como un título enorme en el centro de
la página. El header es una barra de aplicación, no una portada
publicitaria.

## 4.2 Cabecera del workspace

Título: **Unir documentos PDF**

Descripción: "Organiza tus archivos, revisa su contenido y genera un
único documento."

Acciones: - "Limpiar lote" como acción secundaria/destructiva, con
confirmación si hay documentos cargados. - No repetir botones de
importación en múltiples lugares.

## 4.3 Resumen del lote

Tres indicadores compactos: 1. Archivos. 2. Páginas. 3. Tamaño total.

Reglas: - Mostrar valores reales, no placeholders. - Formatear tamaños
en KB, MB o GB. - Actualizar al incluir, excluir o quitar archivos. - No
utilizar tarjetas grandes que resten espacio al workspace. - Si no hay
documentos, mostrar `0` con una presentación visual neutra.

## 4.4 Dropzone

La zona de importación debe ser útil, no ocupar media pantalla
permanentemente.

Estado vacío: - Área con borde discontinuo. - Icono de archivo y flecha
de carga. - Texto principal: "Arrastrá tus PDF aquí". - Texto
secundario: "o seleccioná archivos desde tu equipo". - Botones: "Elegir
archivos" y "Elegir carpeta".

Estado con documentos: - Reducir la dropzone a una franja compacta o
permitir importar desde la toolbar. - No mantener una caja enorme
ocupando espacio si el lote ya está cargado.

Estados: - Normal. - Hover. - Drag over (borde y fondo de acento
suave). - Importando. - Error de importación. - Límite o archivo no
compatible.

Debe aceptar varios archivos y comunicar claramente qué formatos se
admiten. No fingir que una carpeta se importó si el backend no devolvió
resultados.

## 4.5 Panel de documentos

Este panel es central para el producto.

Toolbar: - Título "Documentos". - Contador de elementos. - Botones
compactos de agregar PDF y carpeta. - Campo de búsqueda. - Selector de
orden: Manual, Nombre, Tamaño, Páginas, Fecha.

Cada fila debe mostrar: - Handle de drag and drop. - Icono/miniatura
PDF. - Nombre truncado con tooltip para el nombre completo. - Número de
páginas. - Tamaño. - Estado. - Menú de acciones.

Estados por fila: - Preparando. - Listo. - Advertencia. - Protegido. -
Error. - Excluido. - Procesando. - Completado.

Interacciones: - Click selecciona el documento y actualiza el visor. -
Drag permite reordenar. - Checkbox o acción explícita permite
incluir/excluir. - Menú contextual permite previsualizar, quitar y
consultar detalles. - Selección múltiple para quitar o excluir varios
elementos. - No eliminar el archivo físico al quitarlo del lote.

La fila seleccionada debe tener fondo `accent-soft`, borde o indicador
lateral discreto. No depender solamente del color del texto.

### Densidad de información

Para cientos de documentos, cada fila debe ser compacta (aprox. 60--72
px). Las miniaturas no deben ser tan grandes que limiten la cantidad
visible.

La lista debe virtualizarse para lotes extensos. No renderizar cientos o
miles de componentes pesados simultáneamente.

## 4.6 Previsualizador PDF

Debe ser el elemento visual más amplio del workspace.

Estructura: - Toolbar superior con nombre del archivo y metadatos. -
Canvas central sobre fondo gris neutro. - Página PDF centrada, con
sombra muy sutil. - Controles inferiores o superiores para página y
zoom.

Controles mínimos: - Página anterior. - Página siguiente. - Campo
`página actual / total`. - Zoom menos / más. - Ajustar a ancho. -
Ajustar a página. - Indicador de carga.

Estados: - Sin documento seleccionado: ilustración/icono y texto
"Seleccioná un documento para previsualizar". - Cargando: skeleton o
spinner pequeño. - Página disponible: render nítido. - Error:
explicación y opción de reintentar. - Documento protegido: indicar que
requiere contraseña si el backend ofrece soporte.

Requisitos de rendimiento: - Renderizar la página visible, no todas las
páginas. - Cancelar renderizados obsoletos al cambiar rápidamente de
documento. - Cachear páginas recientes con límite. - No bloquear la
lista mientras se renderiza. - Mantener zoom y página dentro de límites
válidos.

## 4.7 Barra de salida

La salida debe sentirse como el último paso del flujo.

Campos: - Nombre final, con extensión `.pdf` validada. - Carpeta
destino. - Botón "Elegir carpeta". - Resumen de elementos incluidos. -
Botón principal "Unir X documentos".

El botón principal: - Debe tener color de acento sólido. - Debe tener
icono de unión/exportación. - Debe mostrar cantidad real de
documentos. - Deshabilitado si no hay documentos válidos suficientes. -
Mostrar estado loading durante la unión. - Evitar doble envío.

No usar el campo de ruta como un input pequeño pegado a un texto largo.
La carpeta debe elegirse con diálogo nativo y mostrarse de forma
legible, truncando el centro si es necesario y permitiendo copiar la
ruta.

## 4.8 Progreso de unión

Al iniciar: - Mostrar una vista o panel de progreso sin destruir el
workspace. - Indicar etapa actual: validando, preparando, uniendo,
verificando y guardando. - Mostrar progreso total y contador de
documentos. - Mostrar nombre del archivo actual. - Permitir cancelar. -
Diferenciar progreso indeterminado de progreso cuantificado real.

No inventar porcentajes. Si el motor no permite calcular avance exacto,
mostrar una barra indeterminada y el contador real.

## 4.9 Resultado

Al terminar correctamente: - Estado de éxito claro. - Nombre del archivo
generado. - Ruta de salida. - Tamaño y cantidad de páginas. - Botones
"Abrir PDF" y "Abrir carpeta". - Acción secundaria "Volver al espacio de
trabajo".

Si hubo fallos parciales: - Mostrar cantidad de documentos unidos y
omitidos. - Listar errores concretos. - No indicar éxito total si el
resultado no contiene todo lo solicitado.

------------------------------------------------------------------------

# 5. Sistema de diseño y componentes

Crear componentes reutilizables. No implementar estilos aislados en cada
pantalla.

## 5.1 Componentes sugeridos

``` text
AppShell
├── AppHeader
├── WorkspacePage
│   ├── PageHeading
│   ├── BatchSummary
│   ├── ImportDropzone
│   ├── WorkspaceGrid
│   │   ├── DocumentPanel
│   │   │   ├── DocumentToolbar
│   │   │   ├── DocumentSearch
│   │   │   ├── DocumentSortSelect
│   │   │   ├── VirtualDocumentList
│   │   │   └── DocumentRow
│   │   └── PdfPreviewPanel
│   │       ├── PreviewToolbar
│   │       ├── PdfPageCanvas
│   │       └── PreviewPagination
│   └── OutputBar
├── MergeProgressDialog
├── MergeResultDialog
├── ConfirmDialog
├── SettingsDialog
└── ToastViewport
```

## 5.2 Reglas de componentes

-   Un componente debe tener una responsabilidad clara.
-   Extraer componentes cuando tengan lógica o estilos reutilizables.
-   Mantener la lógica de negocio en hooks o servicios, no en JSX.
-   Evitar componentes monolíticos.
-   Evitar pasar props innecesarias por múltiples niveles; usar estado
    global solo para estado compartido real.
-   Mantener contratos TypeScript estrictos.
-   Centralizar tokens de color, espaciado, radios y tipografía.
-   No duplicar botones, inputs, menús o diálogos con implementaciones
    distintas.

## 5.3 Librerías candidatas

Usar lo que ya exista en el proyecto si está bien implementado. No
reinstalar librerías por moda.

-   Tailwind CSS para estilos.
-   shadcn/ui + Radix para primitives accesibles.
-   Lucide React para iconografía.
-   dnd-kit para reordenamiento.
-   TanStack Virtual o equivalente para listas grandes.
-   PDF.js para visor.
-   Zustand si ya existe una necesidad clara de estado compartido.
-   Sonner o sistema propio de toasts.

Antes de agregar dependencias, revisar `package.json`, versiones y
compatibilidad con el proyecto actual.

------------------------------------------------------------------------

# 6. Interacciones y microdetalles

La calidad percibida depende de estados consistentes, no de animaciones
llamativas.

-   Hover de filas y botones: 120--180 ms.
-   Transiciones de paneles: 160--220 ms.
-   Drag and drop con indicador claro del lugar donde se insertará el
    documento.
-   Skeletons para carga de metadatos y preview.
-   Toasts breves para acciones terminadas.
-   Confirmación para limpiar el lote si contiene documentos.
-   Tooltips en iconos sin etiqueta.
-   Focus ring visible para teclado.
-   Respeto por `prefers-reduced-motion`.
-   No usar animaciones de rebote, brillos constantes, gradientes
    animados ni efectos innecesarios.

------------------------------------------------------------------------

# 7. Arquitectura frontend y estado

No modificar innecesariamente el backend. Crear una capa de servicios
que traduzca la API actual a modelos claros de UI.

## 7.1 Estado mínimo

-   `documents`: documentos importados.
-   `selectedDocumentId`: documento seleccionado.
-   `sortMode`: orden actual.
-   `searchQuery`: filtro.
-   `previewPage`: página visible.
-   `previewZoom`: nivel de zoom.
-   `outputName`: nombre del resultado.
-   `outputDirectory`: carpeta de destino.
-   `mergeJob`: estado de unión.
-   `isImporting`: estado de importación.
-   `dialogState`: diálogo abierto.

Evitar duplicar datos derivados. Por ejemplo, cantidad de páginas y
tamaño total deben calcularse a partir de los documentos incluidos,
salvo que exista una razón de rendimiento para mantenerlos memoizados.

## 7.2 Estados visuales como contrato

El frontend debe recibir estados explícitos del backend. No deducir un
error por ausencia de datos ni marcar como completado un archivo que
solo fue importado.

Definir tipos discriminados para: - Documento válido. - Documento con
advertencia. - Documento inválido. - Trabajo en curso. - Trabajo
finalizado. - Trabajo cancelado. - Trabajo fallido.

## 7.3 Rendimiento

-   Usar virtualización para listas grandes.
-   Evitar renderizados de toda la lista ante cambios de progreso.
-   Memoizar filas solo si el profiling demuestra beneficio.
-   Usar `URL.createObjectURL` con revocación correcta si se usa para
    previsualización.
-   Liberar canvases y buffers al cambiar de documento.
-   Debounce en búsqueda.
-   No ejecutar hashing completo en el hilo principal.
-   No generar todas las miniaturas al importar un lote.

------------------------------------------------------------------------

# 8. Accesibilidad y usabilidad

-   Todos los botones deben tener texto accesible.
-   Los botones solo con icono necesitan `aria-label` y tooltip.
-   La selección de documento debe ser perceptible sin depender
    exclusivamente del color.
-   Drag and drop debe tener alternativa mediante botones de subir/bajar
    o menú.
-   Los inputs deben tener label.
-   Los diálogos deben gestionar foco correctamente.
-   Los mensajes de progreso deben ser anunciables por tecnologías de
    asistencia sin emitir actualizaciones excesivas.
-   Contraste mínimo WCAG AA para texto normal.
-   No usar texto gris claro sobre blanco para información importante.

------------------------------------------------------------------------

# 9. Plan de implementación por fases

## Fase 1 --- Auditoría del frontend actual

Antes de modificar: 1. Inspeccionar estructura de carpetas y
componentes. 2. Revisar `package.json` y dependencias instaladas. 3.
Identificar endpoints y contratos backend existentes. 4. Identificar qué
componentes funcionan y cuáles son placeholders. 5. Tomar capturas de
referencia de la versión actual. 6. Confirmar cómo se seleccionan
archivos y carpetas en el entorno local.

**Entregable:** mapa de componentes y plan de cambios sin romper
funcionalidades.

## Fase 2 --- Fundaciones visuales

1.  Crear tokens de diseño.
2.  Definir tipografía, paleta y escalas de espaciado.
3.  Crear botones, inputs, badges, tooltips, diálogos y toasts.
4.  Definir estados hover, focus, disabled y loading.
5.  Configurar layout base y altura completa de aplicación.

**Entregable:** sistema visual consistente.

## Fase 3 --- Workspace principal

1.  Implementar header.
2.  Implementar cabecera de página.
3.  Implementar resumen del lote.
4.  Implementar panel de documentos.
5.  Implementar panel de previsualización.
6.  Implementar barra de salida.
7.  Conectar todos los paneles al estado real.

**Entregable:** pantalla principal completa y funcional.

## Fase 4 --- Importación y lista avanzada

1.  Diseñar dropzone con estados.
2.  Implementar importación de archivos y carpetas.
3.  Crear filas compactas.
4.  Añadir búsqueda y ordenamiento.
5.  Añadir reordenamiento drag and drop.
6.  Añadir inclusión/exclusión.
7.  Añadir virtualización.
8.  Implementar estados de error y advertencia.

**Entregable:** gestión usable de lotes grandes.

## Fase 5 --- Previsualización

1.  Integrar visor PDF.
2.  Crear toolbar de navegación.
3.  Implementar zoom y ajuste.
4.  Añadir carga bajo demanda.
5.  Gestionar errores y cancelación de render.
6.  Verificar consumo de memoria con documentos extensos.

**Entregable:** visor integrado y estable.

## Fase 6 --- Salida y procesamiento

1.  Rediseñar campos de salida.
2.  Integrar selector de carpeta.
3.  Implementar botón de acción principal.
4.  Crear modal/panel de progreso.
5.  Conectar progreso real.
6.  Añadir cancelación.
7.  Crear vista de resultado y errores parciales.

**Entregable:** flujo completo desde importación hasta resultado.

## Fase 7 --- Pulido y QA

1.  Probar ventanas de distintos tamaños.
2.  Probar 1, 10, 100, 500 y 1.000 documentos.
3.  Probar nombres largos y rutas extensas.
4.  Probar errores de importación y preview.
5.  Probar teclado y accesibilidad.
6.  Verificar que no haya scroll horizontal accidental.
7.  Verificar que la barra de salida no desaparezca.
8.  Revisar consistencia visual de todos los estados.
9.  Ejecutar lint, typecheck y tests.
10. Comparar capturas antes/después.

**Entregable:** frontend listo para uso cotidiano.

------------------------------------------------------------------------

# 10. Criterios de aceptación visual

El rediseño no se considera terminado hasta cumplir todos estos puntos:

-   [ ] La pantalla ya no es una columna de controles centrados.
-   [ ] La jerarquía visual permite identificar título, documentos,
    preview y salida en pocos segundos.
-   [ ] La lista y el visor comparten el espacio horizontal.
-   [ ] El panel de preview tiene espacio suficiente para leer páginas.
-   [ ] La dropzone se adapta al estado vacío o con documentos.
-   [ ] Los botones, campos, menús y diálogos comparten el mismo
    lenguaje visual.
-   [ ] Los documentos muestran nombre, páginas, tamaño y estado.
-   [ ] La selección y el orden de documentos son evidentes.
-   [ ] La lista soporta lotes grandes mediante virtualización.
-   [ ] El progreso representa datos reales del backend.
-   [ ] La barra de salida está claramente separada y accesible.
-   [ ] Los estados vacío, cargando, error, advertencia y éxito están
    diseñados.
-   [ ] No hay textos cortados sin tooltip o alternativa.
-   [ ] No hay controles HTML por defecto sin estilizar.
-   [ ] No hay scroll innecesario en toda la página cuando deberían
    desplazarse solo los paneles.
-   [ ] La interfaz funciona con teclado y tiene foco visible.
-   [ ] El diseño se mantiene coherente en ventanas grandes y medianas.

------------------------------------------------------------------------

# 11. Restricciones para el agente

1.  **No tocar el backend ni el motor PDF** salvo que una integración
    visual requiera un cambio mínimo y justificado.
2.  No eliminar funcionalidades existentes para conseguir una captura
    más limpia.
3.  No reemplazar datos reales por mocks en la versión final.
4.  No simular progreso ni estados de éxito.
5.  No agregar animaciones decorativas que perjudiquen el rendimiento.
6.  No usar emojis como sustituto de iconografía de interfaz.
7.  No introducir imágenes de stock en el workspace.
8.  No usar gradientes intensos, glassmorphism excesivo, neón o sombras
    grandes.
9.  No dejar estilos inline repetidos: usar tokens y componentes.
10. No instalar dependencias sin revisar primero el proyecto.
11. Mantener la aplicación local y compatible con el backend existente.
12. No dar por finalizada una fase sin ejecutar las verificaciones
    correspondientes.
13. Mantener el idioma y las expresiones de la interfaz en español
    argentino, con consistencia terminológica.
14. Si una funcionalidad backend todavía no existe, diseñar un estado
    honesto de "no disponible" y documentar la dependencia; no fingir
    que funciona.

------------------------------------------------------------------------

# 12. Prompt operativo para el agente de código

Implementá un rediseño integral del frontend de PDF Batch Studio
siguiendo este documento.

La interfaz actual es un prototipo visual: todo está centrado en una
columna, la lista de documentos no tiene una estructura clara, la
previsualización carece de espacio y los controles parecen HTML sin
diseñar. No intentes resolverlo cambiando solamente colores o
tipografía. Replanteá la composición completa.

Primero auditá el proyecto existente y preservá las funcionalidades que
ya funcionan. Después implementá un workspace de escritorio profesional
con: - Header de aplicación compacto. - Cabecera de página y resumen del
lote. - Panel izquierdo de documentos con búsqueda, ordenamiento, filas
compactas y drag and drop. - Panel derecho amplio de previsualización
PDF. - Barra inferior de salida con nombre, destino y acción
principal. - Estados completos de importación, carga, progreso, errores
y éxito.

Aplicá el sistema visual definido en este documento: superficies claras,
fondo gris azulado, acento índigo moderado, tipografía Inter o Segoe UI,
bordes sutiles, radios consistentes y espaciado profesional.

Usá componentes reutilizables, TypeScript estricto, accesibilidad y
virtualización para listas grandes. El visor debe renderizar páginas
bajo demanda. No bloquees la interfaz.

No modifiques el comportamiento de unión ni inventes funcionalidades.
Conectá el diseño a los datos y endpoints reales existentes. Si falta
una capacidad backend, documentala y representá su estado correctamente.

Trabajá por fases. Después de cada fase ejecutá lint, typecheck y tests
disponibles. Al terminar, presentá: 1. Resumen de cambios. 2. Archivos
creados y modificados. 3. Dependencias agregadas y motivo. 4.
Funcionalidades preservadas. 5. Pruebas ejecutadas y resultados. 6.
Limitaciones pendientes.

**Definición de terminado:** la aplicación debe parecer una herramienta
de escritorio profesional, no un formulario web centrado. La mejora debe
ser evidente en composición, jerarquía, densidad, consistencia, estados
y facilidad de uso.
