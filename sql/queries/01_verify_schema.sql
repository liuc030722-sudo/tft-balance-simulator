-- 建表后运行：应返回三行，row_count均为0；数据将在下一步导入。
SELECT current_database() AS database_name,
       'game_versions' AS table_name, COUNT(*) AS row_count
FROM public.game_versions
UNION ALL
SELECT current_database(), 'champions', COUNT(*) FROM public.champions
UNION ALL
SELECT current_database(), 'abilities', COUNT(*) FROM public.abilities;
