-- =====================================================================
-- 02_vistas.sql · Vistas de apoyo para consultas y Tableau
-- Nota SQLite: INTEGER / INTEGER es división entera (834 / 41019 = 0).
-- Por eso las tasas multiplican por 1.0 antes de dividir.
-- =====================================================================

-- Restaurante "aplanado": nombres en vez de IDs
DROP VIEW IF EXISTS v_restaurante;
CREATE VIEW v_restaurante AS
SELECT r.id_restaurante,
       r.nombre,
       r.zona,
       c.nombre   AS ciudad,
       p.nombre   AS pais,
       cat.nombre AS categoria,
       r.seguidores_instagram,
       r.engagement_rate,
       r.costo_variable_pct,
       r.url_instagram
FROM restaurante r
JOIN ciudad    c   ON c.id_ciudad      = r.id_ciudad
JOIN pais      p   ON p.id_pais        = c.id_pais
JOIN categoria cat ON cat.id_categoria = r.id_categoria;

-- KPIs por restaurante × sprint (fórmulas de negocio en un solo lugar)
DROP VIEW IF EXISTS v_kpis_sprint;
CREATE VIEW v_kpis_sprint AS
SELECT m.id_restaurante,
       m.id_sprint,
       s.numero                                         AS sprint_num,
       s.fecha_inicio,
       s.fecha_fin,
       m.inversion_pauta,
       m.impresiones,
       m.alcance,
       m.clics,
       m.conversiones,
       m.ticket_promedio,
       r.costo_variable_pct,
       1.0 * m.clics        / NULLIF(m.impresiones, 0)  AS ctr,
       1.0 * m.conversiones / NULLIF(m.clics, 0)        AS tasa_conversion,
       m.inversion_pauta    / NULLIF(m.conversiones, 0) AS cpa,
       m.conversiones * m.ticket_promedio               AS ingresos_atribuidos,
       m.conversiones * m.ticket_promedio * (1 - r.costo_variable_pct)
           - m.inversion_pauta                          AS margen_contribucion,
       m.conversiones * m.ticket_promedio / m.inversion_pauta AS roas,
       (m.conversiones * m.ticket_promedio * (1 - r.costo_variable_pct)
           - m.inversion_pauta) / m.inversion_pauta     AS roi_publicitario
FROM metricas_sprint m
JOIN sprint      s ON s.id_sprint      = m.id_sprint
JOIN restaurante r ON r.id_restaurante = m.id_restaurante;
