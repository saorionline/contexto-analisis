# 📒 Bitácora de negocio y gobernanza · Restaurantes & Publicidad

> Hoja de respuestas externa del proyecto `contexto-analisis/EDA_Restaurantes_Publicidad.ipynb`.
> Aquí se registran decisiones de negocio, supuestos y reglas de datos. El notebook ejecuta; esta bitácora justifica.

**Inicio:** 2026-10-01 · **Autora:** Saori Tovar

---

## 🧾 Enunciado del dataset

Dataset primario de auditoría para análisis de mercado publicitario en el sector gastronómico. Contiene registros crudos (*raw data*) con anomalías simuladas del sector (duplicados, valores nulos y registros vacíos) para evaluar la resiliencia de los flujos de limpieza (ETL) en Python y su posterior ingesta para optimización de presupuestos de pauta y segmentación geoespacial.

---

## Preguntas orientadoras

### 🎯 Objetivo de negocio
- ¿Qué decisión concreta debe habilitar este análisis (reasignar presupuesto, elegir zonas, priorizar categorías)?
- ¿Quién es el cliente o usuario de la decisión (agencia, restaurante, cadena)?
- ¿Cómo se ve el éxito al final del mes de pauta?

_Respuesta:_

### 📍 Zona de influencia
- ¿En qué ciudad o ciudades operan los 10 restaurantes?
- ¿Cómo se definen las zonas (alcaldía/colonia, radio en km, código postal)?
- ¿Qué fuente usaré para latitud/longitud de cada restaurante?

_Respuesta:_

### 📊 KPIs de campaña
- ¿Cuál es la conversión que cuenta (reserva, pedido, visita con cupón, clic a WhatsApp)?
- ¿Qué ROI / ROAS mínimo justifica seguir invirtiendo en un restaurante?
- ¿De dónde saldrá el `costo_variable_pct` real de cada negocio?

_Respuesta:_

### 👥 Audiencia y segmentación
- ¿Qué perfil de cliente busca cada categoría (japonesa, cervecería, heladería, deli…)?
- ¿El engagement en Instagram es buen proxy de demanda local?

_Respuesta:_

### 💰 Presupuesto de pauta
- ¿Presupuesto total del mes y regla de reparto entre los 4 sprints?
- ¿Se reasigna presupuesto entre sprints según desempeño?

_Respuesta:_

### 🧹 Calidad y gobernanza de datos
- ¿Regla para nulos: imputar (mediana por categoría + bandera) o eliminar?
- ¿Qué fuente manda cuando el dato simulado y el real difieren?
- ¿Cada cuánto se actualizan seguidores y engagement?

_Respuesta:_

---

## 🗂️ Registro de decisiones

| Fecha | Decisión | Motivo | Impacto |
|---|---|---|---|
| 2026-10-01 | Datos de Hoja 1 y Hoja 2 simulados (seguidores 10k–50k) | Permitir construir el ETL antes de capturar datos reales | Reemplazar al empalmar por `url_instagram` |
| 2026-10-01 | Nulos numéricos → mediana por categoría + columna `_imputado` (provisional) | No perder restaurantes del catálogo | Revisar en Sesión 2 |
| 2026-10-01 | Orden de limpieza: espacios → vacíos → duplicados → nulos | Evitar duplicados ocultos por espacios | — |
| 2026-10-05 | Esquema estrella: `pais`, `ciudad`, `categoria`, `restaurante`, `sprint` + hechos `metricas_sprint` | Normalizar a 3FN y facilitar Tableau | `sql/01_schema.sql` |
| 2026-10-05 | `ciudad`, `pais` y `costo_variable_pct` se mueven a `restaurante` | Dependen solo del restaurante, no del sprint (el ETL lo verifica) | Si el costo variable cambia por sprint, vuelve a `metricas_sprint` |
| 2026-10-05 | KPIs no se guardan; se calculan en la vista `v_kpis_sprint` | Evitar valores desactualizados al capturar datos reales | `sql/02_vistas.sql` |
| 2026-10-05 | `zona` queda como columna de `restaurante` | "Centro" de Miami ≠ "Centro" de Bogotá | Revisar al agregar coordenadas |
| 2026-10-06 | Proyecto **Trisectorial Estacional**: 4 sectores (resto, fitness, retail, tech) × 4 seasons (oct-2025 → sep-2026) | Comparar comportamiento entre mercados con los mismos índices | `src/<sector>-csv/seasonN_campana_<sector>_raw.csv` |
| 2026-10-06 | Cada season = 3 meses en 13 sprints semanales; el S13 absorbe los días sobrantes (8, 6, 7 u 8 días) | Los trimestres reales tienen 90–92 días | El pipeline debe normalizar por días al comparar sprints |
| 2026-10-06 | Los archivos crudos traen solo datos capturados; los KPIs los calcula el pipeline | Evitar KPIs desactualizados | — |
| 2026-10-06 | Llave común `id_entidad` en campañas y catálogos nuevos; `restaurantes_raw.csv` conserva `id_restaurante` | Mismos índices entre sectores sin reescribir el catálogo original | El pipeline mapea `id_restaurante → id_entidad` |
| 2026-10-06 | En tech, `conversiones` = clientes cerrados; `leads` y `leads_calificados` son etapas previas del embudo | Que ingresos = conversiones × ticket valga igual en todos los sectores | CPL = inversión / leads se calcula aparte |
| 2026-10-06 | En fitness, `ticket_promedio` = cuota mensual y la rentabilidad real usa LTV = ticket × `meses_retencion_promedio` | Con un solo mes de cuota el ROI sale negativo | Comparar ROI de 1 mes vs. ROI con LTV |
| 2026-10-06 | Errores sembrados a propósito en todos los archivos, con registro en `src/simulacion/anomalias_sembradas.csv` | Probar el pipeline de limpieza contra una lista de respuestas conocida | 179 anomalías, 11 tipos |
| 2026-10-06 | Contador `src/registro_tamano.csv` (filas, bytes en disco, bytes en memoria, segundos) | Vigilar el crecimiento y el tiempo de cálculo | — |
| 2026-10-06 | Sector Marca y `coffee_sales_raw.csv` quedan fuera por ahora | Enfocar el estudio en 4 sectores | Retomar más adelante |
| 2026-10-06 | Nomenclatura: **mercado** = Restaurantes, Fitness, Retail o Tecnología; **geografía** = ubicación en 3 niveles: país (USA / Colombia), ciudad y zona | Usar "mercado" para dos cosas confundiría al pipeline | Pendiente: diccionario en `docs/modelado/`, renombrar el eje de Q04 a "geografía" y nunca llamar `mercado` a una columna de ubicación |
| 2026-10-06 | **Limitación de alcance:** `canal` y `campana` no se crean como entidades propias. El estudio mide la inversión en pauta en **redes sociales** en general; las fichas impresas quedan fuera. La campaña sigue implícita: una entidad en una season | El objetivo es la inversión digital; no hay datos del canal impreso | No se agregan columnas a los crudos ni se regenera la simulación. Se retoma solo si el estudio se amplía a otros canales |
| | | | |

## 📝 Notas de sesión

### Sesión 1 · 2026-10-01
- Estructura del notebook, datasets crudos (CSV + MD) y limpieza base.

### Sesión 2 · 2026-10-05
- Modelo relacional, carga a SQLite y diseño de consultas Q01–Q05 (en el prototipo).

### Sesión 3 · 2026-10-06
- Simulador del proyecto Trisectorial Estacional: catálogos y campañas de 4 sectores × 4 seasons.
- Siguiente: pipeline M1 en `src/modelado/` (Definición → Recopilación → Exploración → Preprocesamiento).
