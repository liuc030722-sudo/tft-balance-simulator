# Phase 4：简化普通攻击基线验收

状态：**代码实现与用户运行验收通过**。不等同于完整Patch 14.1客户端机制核验。

## 验收范围

使用数据库固定快照的源属性，实现无技能、被动、暴击、装备、羁绊和移动的1v1普通攻击模型。静态属性与动态状态分离；伤害、固定攻速时间和同时结算均采用已明确记录的模型规则。不推导星级，不把原始参数数组索引当作星级范围。

## 实现

| 内容 | 文件 |
|---|---|
| 不可变属性与独立战斗状态 | src/tft_simulator/models/champion.py |
| 物理、魔法、真实伤害计算函数 | src/tft_simulator/combat/damage.py |
| 攻速、可选上下限及攻击时间表 | src/tft_simulator/combat/timing.py |
| 事件驱动普通攻击战斗、结果及日志 | src/tft_simulator/combat/engine.py |
| 对应单元测试 | tests/test_champion_models.py、test_damage.py、test_timing.py、test_engine.py |

魔法与真实伤害函数已实现，普通攻击事件目前只调用物理伤害。法力只初始化并记录，尚不增加或用于施法。

## 用户运行反馈

用户在手动维护的04_basic_combat.ipynb中确认：

1. 基础属性、独立状态与伤害示例输出正确。
2. 60秒上限的Annie对Olaf战斗摘要符合预期：B/Olaf获胜，约15.3846秒结束，Annie剩余0HP，Olaf约353.7037HP，双方各攻击10次。
3. 完整日志共23条，输出正确。
4. 5秒上限截图显示：winner=draw、reason=timeout、duration=5.0，双方各攻击3次，HP分别为312.5和约561.1111，伤害分别为约88.8889和137.5，与预期一致。

## 自动验证记录

此前实际执行完整本地测试：106 passed。默认离线运行结果为90 passed、16 skipped。覆盖间隔、三类伤害、负抗性模型、HP边界、死亡后取消攻击、同时双杀、超时、截止边界、确定性和不污染源属性等。

正式模块的数据库只读集成调用已确认相同输入重复结果/日志一致，数据库数量与源HP不变。本轮只根据用户反馈更新文档，没有修改Python代码或重复执行整套测试。没有创建、修改或执行任何.ipynb。

## 保留的机制限制

- 抗性公式，尤其负抗性扩展，仍未获得完整Patch 14.1一手核验。
- 默认不猜测游戏攻速上下限；可显式配置，但配置接口本身不证明边界正确。
- 第一击等待完整间隔、同时间戳批处理、持续在射程内、浮点不逐击取整，均是模型约定。
- 真实星级语义、前摇、弹道、移动、特殊攻击、技能与被动没有因为本次验收而得到确认。
- 当前无随机性；不提供虚构随机种子，也不能把重复确定性对战当作有额外信息的Monte Carlo实验。

## 运行与下一阶段

从项目根目录运行完整测试：

```powershell
$env:TFT_TEST_DATABASE = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TFT_TEST_DATABASE
```

Notebook运行步骤已在聊天中提供，由用户亲自复制执行。无需再次建表或导入数据。

建议提交：`feat: complete deterministic basic combat engine and phase 4 validation`

Phase 5尚未授权。后续优先逐步处理可复现的随机性与可核验技能；装备仍按用户要求暂缓。不能将尚未实现的机制写成已完成。
