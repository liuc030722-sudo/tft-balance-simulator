-- Phase 3 / schema version 1: run once against tft_balance_simulator.
-- No database creation, deletion, table replacement, or data import.
BEGIN;

-- 一个版本记录对应一份明确的 Set / Patch / 原始数据快照。
CREATE TABLE public.game_versions (
    version_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    set_number SMALLINT NOT NULL CHECK (set_number > 0),
    patch TEXT NOT NULL CHECK (btrim(patch) <> ''),
    source_url TEXT NOT NULL,
    source_sha256 TEXT NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    retrieved_at_utc TIMESTAMPTZ NOT NULL,
    release_date DATE,
    UNIQUE (set_number, patch, source_sha256)
);

-- 只保存源属性；暂不建立星级、装备、羁绊效果和战斗状态表。
CREATE TABLE public.champions (
    version_id INTEGER NOT NULL REFERENCES public.game_versions (version_id),
    champion_id TEXT NOT NULL,
    name TEXT NOT NULL,
    cost SMALLINT NOT NULL CHECK (cost BETWEEN 1 AND 5),
    traits TEXT[] NOT NULL,
    role_raw TEXT,
    hp DOUBLE PRECISION NOT NULL CHECK (hp > 0),
    attack_damage DOUBLE PRECISION NOT NULL CHECK (attack_damage >= 0),
    attack_speed DOUBLE PRECISION NOT NULL CHECK (attack_speed > 0),
    armor DOUBLE PRECISION NOT NULL,
    magic_resist DOUBLE PRECISION NOT NULL,
    attack_range DOUBLE PRECISION NOT NULL CHECK (attack_range > 0),
    initial_mana DOUBLE PRECISION NOT NULL CHECK (initial_mana >= 0),
    max_mana DOUBLE PRECISION NOT NULL CHECK (max_mana >= 0),
    crit_chance DOUBLE PRECISION NOT NULL CHECK (crit_chance BETWEEN 0 AND 1),
    crit_multiplier DOUBLE PRECISION NOT NULL CHECK (crit_multiplier >= 0),
    PRIMARY KEY (version_id, champion_id),
    CHECK (initial_mana <= max_mana)
);

-- JSONB保留技能参数结构；保存参数不代表技能机制已实现。
CREATE TABLE public.abilities (
    version_id INTEGER NOT NULL,
    champion_id TEXT NOT NULL,
    ability_name TEXT,
    description_raw TEXT,
    variables JSONB CHECK (jsonb_typeof(variables) = 'array'),
    PRIMARY KEY (version_id, champion_id),
    FOREIGN KEY (version_id, champion_id)
        REFERENCES public.champions (version_id, champion_id)
);

-- 复合主键已经覆盖版本与英雄ID查询；额外索引用于按费用筛选。
CREATE INDEX idx_champions_version_cost
    ON public.champions (version_id, cost);

COMMIT;
