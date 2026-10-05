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
| | | | |

## 📝 Notas de sesión

### Sesión 1 · 2026-10-01
- Estructura del notebook, datasets crudos (CSV + MD) y limpieza base.

### Sesión 2 · pendiente
- Puente SQL (`sqlite3`), consultas de negocio, export para Tableau.
