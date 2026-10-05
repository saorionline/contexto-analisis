-- =====================================================================
-- Q00 · Plantilla (copiar como QNN_nombre_corto.sql)
-- ❓ Pregunta de negocio:
-- 🔍 Nivel de detalle (una fila por…):
-- 📊 Métricas:
-- 🏷️ Agrupar / filtrar por:
-- 🗂️ Tablas / vistas: v_kpis_sprint, v_restaurante
-- =====================================================================
SELECT r.nombre, k.id_sprint, k.roi_publicitario
FROM v_kpis_sprint k
JOIN v_restaurante r USING (id_restaurante)
LIMIT 5;
