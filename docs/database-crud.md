# Phase 3：数据访问与事务

## 接口分工

| 模块 | 职责 |
|---|---|
| connection.py | 从.env读取配置，检查数据库，管理只读/维护连接的生命周期 |
| queries.py | 版本、英雄、技能和数量查询；继续兼容原来的read_connection导入 |
| writes.py | 新增、更新、删除指定英雄记录，不自行提交事务 |
| import_data.py | CSV批量导入；重复键跳过，不覆盖已有源记录 |
| query.py | 命令行查询入口，不提供修改/删除命令 |

## CRUD

- Create：`create_champion(connection, version_id, record)`，返回新增行字典。必填字段是champion_id、name、cost、traits、role_raw以及10个数值属性。重复主键会报错。
- Read：`get_champion`和`list_champions`，分别返回单行字典/None和行字典列表。
- Update：`update_champion(connection, version_id, champion_id, changes)`，只更新指定列，返回更新后的行；查无记录返回None。changes不可为空，不允许修改主键和version_id。
- Delete：`delete_champion(connection, version_id, champion_id)`，删除成功返回True，不存在返回False。存在技能引用时外键拒绝删除，不自动级联删除技能。

维护接口用于经过授权的数据维护。它们不用于Balance Lab、敏感性分析或战斗中的状态变化；那些修改应作用于独立实验配置/内存副本，不覆盖真实源属性。本阶段没有修改或删除15名正式英雄。

## SQL与Python的对应关系

1. SQL的RETURNING *把新增/更新后的记录返回给Python，避免再写一次SELECT。
2. psycopg的dict_row将结果映射为字段名到值的字典。
3. SQL列名不能用普通数值占位符替代。动态更新使用固定字段白名单及sql.Identifier处理列名；属性值仍通过%s参数绑定。
4. 维护函数不调用commit。调用者决定把哪些操作放在同一个事务中。
5. write_connection正常退出会提交，异常退出会回滚；read_connection继续由PostgreSQL强制只读。
6. READ、UPDATE、DELETE始终同时使用version_id和champion_id，防止跨版本误操作。

## 本次如何验证写入

实际测试只创建带TEST_ONLY_前缀、明确标记为人工夹具的记录。这些不是声称来自游戏的英雄数据。

测试在connection.transaction(force_rollback=True)中运行。即使测试成功，也强制回滚测试中新建的英雄及技能。嵌套transaction提供SAVEPOINT，用于验证预期的唯一约束、外键和CHECK错误，而不使整个测试事务失效。

验证内容包括：新增→读取→更新→删除完整流程、重复主键拒绝、有技能引用时拒绝删除、非法生命值更新失败后原值保留、禁止空更新/修改主键/写入NaN、不存在ID不会更新其他记录、只读连接拒绝写入。

测试结束后，又只读比较了正式版本、15名英雄和15条技能与原有来源记录/CSV。值保持一致，TEST_ONLY残留数为0。测试没有新建版本记录，因此也没有通过测试消耗版本表的identity编号。

## 运行测试

从项目根目录的PowerShell运行，不需要Notebook：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

默认13项通过、16项本地数据库测试跳过。完整验证：

```powershell
$env:TFT_TEST_DATABASE = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TFT_TEST_DATABASE
```

2026-10-28实际结果：29 passed。数据库测试需要本地PostgreSQL、正确.env和已经导入的固定快照。不存在的快照不会被测试擅自补建。

本步骤没有新增依赖、修改Notebook或进入Phase 4。
