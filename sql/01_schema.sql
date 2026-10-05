-- =====================================================================
-- 01_schema.sql · Modelo relacional (SQLite)
-- Esquema estrella: metricas_sprint (hechos) + dimensiones.
--
--   pais (1) ──< ciudad (1) ──< restaurante >── (1) categoria
--                                    │
--                                   (1)
--                                    ^
--                            metricas_sprint >── (1) sprint
--
-- Se puede re-ejecutar: borra y recrea todo (hijos antes que padres).
-- =====================================================================
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_kpis_sprint;
DROP VIEW  IF EXISTS v_restaurante;
DROP TABLE IF EXISTS metricas_sprint;
DROP TABLE IF EXISTS sprint;
DROP TABLE IF EXISTS restaurante;
DROP TABLE IF EXISTS categoria;
DROP TABLE IF EXISTS ciudad;
DROP TABLE IF EXISTS pais;

-- ---------- Dimensiones geográficas ----------
CREATE TABLE pais (
    id_pais   INTEGER PRIMARY KEY,
    nombre    TEXT NOT NULL UNIQUE
);

CREATE TABLE ciudad (
    id_ciudad INTEGER PRIMARY KEY,
    nombre    TEXT    NOT NULL,
    id_pais   INTEGER NOT NULL REFERENCES pais (id_pais),
    UNIQUE (nombre, id_pais)          -- puede haber dos "Santiago" en países distintos
);

-- ---------- Dimensión de negocio ----------
CREATE TABLE categoria (
    id_categoria INTEGER PRIMARY KEY,
    nombre       TEXT NOT NULL UNIQUE
);

-- ---------- Dimensión principal ----------
-- costo_variable_pct vive aquí: es constante por restaurante (el ETL lo verifica).
CREATE TABLE restaurante (
    id_restaurante                TEXT    PRIMARY KEY,
    nombre                        TEXT    NOT NULL,
    zona                          TEXT,  -- zona dentro de la ciudad (Centro, Norte…)
    id_ciudad                     INTEGER NOT NULL REFERENCES ciudad (id_ciudad),
    id_categoria                  INTEGER NOT NULL REFERENCES categoria (id_categoria),
    seguidores_instagram          INTEGER CHECK (seguidores_instagram >= 0),
    engagement_rate               REAL    CHECK (engagement_rate BETWEEN 0 AND 100),  -- en %
    costo_variable_pct            REAL    NOT NULL CHECK (costo_variable_pct >= 0 AND costo_variable_pct < 1),
    url_instagram                 TEXT    UNIQUE,
    seguidores_instagram_imputado INTEGER NOT NULL DEFAULT 0 CHECK (seguidores_instagram_imputado IN (0, 1)),
    engagement_rate_imputado      INTEGER NOT NULL DEFAULT 0 CHECK (engagement_rate_imputado IN (0, 1))
);

-- ---------- Dimensión de tiempo ----------
CREATE TABLE sprint (
    id_sprint    TEXT    PRIMARY KEY,          -- 'S1'…'S4'
    numero       INTEGER NOT NULL UNIQUE,
    fecha_inicio TEXT    NOT NULL,             -- ISO 8601: 'YYYY-MM-DD'
    fecha_fin    TEXT    NOT NULL,
    CHECK (fecha_fin >= fecha_inicio)
);

-- ---------- Hechos: una fila por restaurante × sprint ----------
-- Solo se guardan las ENTRADAS; los KPIs se derivan en v_kpis_sprint.
CREATE TABLE metricas_sprint (
    id_restaurante  TEXT    NOT NULL REFERENCES restaurante (id_restaurante),
    id_sprint       TEXT    NOT NULL REFERENCES sprint (id_sprint),
    inversion_pauta REAL    NOT NULL CHECK (inversion_pauta > 0),
    impresiones     INTEGER NOT NULL CHECK (impresiones >= 0),
    alcance         INTEGER NOT NULL CHECK (alcance >= 0),
    clics           INTEGER NOT NULL CHECK (clics >= 0),
    conversiones    INTEGER NOT NULL CHECK (conversiones >= 0),
    ticket_promedio REAL    NOT NULL CHECK (ticket_promedio >= 0),
    PRIMARY KEY (id_restaurante, id_sprint),
    CHECK (alcance      <= impresiones),
    CHECK (clics        <= impresiones),
    CHECK (conversiones <= clics)
);
