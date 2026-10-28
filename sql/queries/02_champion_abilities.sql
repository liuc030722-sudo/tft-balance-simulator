-- 显示同一版本下的英雄与技能，避免跨版本关联。
SELECT v.set_number, v.patch,
       c.champion_id, c.name, c.cost,
       c.hp, c.attack_damage, c.attack_speed, c.armor, c.magic_resist,
       a.ability_name
FROM public.game_versions AS v
JOIN public.champions AS c ON c.version_id = v.version_id
LEFT JOIN public.abilities AS a
    ON a.version_id = c.version_id AND a.champion_id = c.champion_id
ORDER BY v.version_id, c.cost, c.champion_id;
