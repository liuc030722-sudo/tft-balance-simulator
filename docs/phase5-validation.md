# Phase 5：当前简化范围的工程验收

状态：已声明范围的后台工程验收通过，等待用户阶段确认。不是全部原始Phase5要求已实现，也不表示已完整还原TFT客户端。Phase6尚未开始。

## 本阶段目标

在可测试普通攻击基线上，加入明确范围的技能、随机性及独立实验配置，为以后重复模拟提供稳定的单场接口。正式算法保留在Python模块，Notebook仅用于用户手动探索和展示。

## 文件与职责

所有文件都在原桌面项目中，下列路径相对此项目根目录。

| 文件 | 职责 |
|---|---|
| src/tft_simulator/models/champion.py | 源暴击字段、独立动态状态和有上限/不复活治疗 |
| src/tft_simulator/combat/critical.py | 局部Random生成器下的逐击暴击 |
| src/tft_simulator/combat/mana.py | 显式实验回蓝量、实际回蓝与上限 |
| src/tft_simulator/combat/abilities.py | Annie主动源参数与简化配置 |
| src/tft_simulator/combat/passives.py | Olaf源治疗/缺血攻速参数 |
| src/tft_simulator/combat/timing.py | 保留待执行攻击进度的动态排期 |
| src/tft_simulator/combat/modifiers.py | 相对源效果的独立百分比实验 |
| src/tft_simulator/combat/engine.py | 批次伤害、治疗、法力、技能和死亡顺序 |
| src/tft_simulator/combat/profiles.py | 支持状态、独立配置、统一run_matchup入口 |
| src/tft_simulator/database/combatants.py | 只读load_combatant入口 |
| tests/test_critical.py、test_mana.py、test_abilities.py、test_passives.py、test_dynamic_speed.py、test_profiles.py、test_ability_power.py | 各模型及组合行为测试 |
| tests/test_champion_models.py | 源属性与动态状态边界回归 |
| docs/critical-strikes.md、attack-mana.md、annie-active.md、olaf-healing.md、dynamic-attack-speed.md、combat-profiles.md、ability-power.md | 参数、公式、来源与简化规则 |
| docs/model-scope.md、README.md、AGENTS.md | 当前能力、开发边界和协作约定 |

## 实现与边界

支持可选暴击、显式种子、实验回蓝、Annie主动、Olaf回血与缺血攻速、法强效果比例和完整结构化日志。结果含源快照、模型、输入、种子与未实现部分；普攻模式作为显式基线保留，其他英雄技能不静默回退。

未实现Annie强化被动、其余13名样本英雄技能、真实施法动作/锁蓝、受伤回蓝、完整客户端AP/AD加成与特殊交互。装备依用户要求暂缓；星级、羁绊与移动等仍不在第一版范围。原始“不同装备产生不同结果”的验收项不适用于当前无装备范围，不能记为已经通过。

法强100%只是相对源效果不变；每击10法力是实验假设。抗性与时序仍有明确暂定说明。测试通过证明实现符合声明模型，不证明游戏忠实度，也不产生官方平衡结论。

## 实际执行记录

此前最新完整本地测试235项通过；本次文档收尾未修改算法，因此未无意义重复全部测试。当前默认离线预期219项通过、16项数据库测试跳过。

本次通过统一入口实际运行并重放4种真实来源配置，全部完整结果相等，检查来源Patch14.1、非负生命和未支持英雄拒绝技能模式；源表数量前后均为1个版本、15名英雄、15条技能记录。

| Annie A vs Olaf B | 胜者 | 时长 | Olaf HP |
|---|---|---:|---:|
| 无技能、无暴击基线 | Olaf | 15.3846 | 353.7037 |
| 已支持简化技能、无暴击 | Olaf | 14.9433 | 410 |
| 简化技能、暴击、seed42 | Olaf | 13.4230 | 372.2222 |
| 简化技能、无暴击、Annie效果150% | Olaf | 14.8180 | 328.5185 |

后三项显式使用每普攻10法力的实验配置。四场结果不能作为胜率或显著性估计。

## 运行与学习

在项目根目录使用既有.venv内核运行聊天提供的统一入口Notebook代码，无需另建环境或改数据库。可选PowerShell回归命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

用户本步无需运行诊断代码。所有Notebook从未被助手创建、编辑或执行。

本阶段学习重点：不可变输入与动态状态分离、事件批次和处理顺序、局部随机生成器与重放、参数来源和模型假设区分、治疗/伤害分别累计、百分比效果与真实战斗结果的非线性关系。

## Git与后续

当前Phase5修改保留在本地，未提交或推送；建议英文commit message：`feat: add reproducible combat effects and explicit experiment profiles`。提交前仍需按用户上传请求执行，不能自动上传Notebook或忽略文件。

下一阶段拟实现100/1000/10000场、可复现逐场种子、胜/平率、Wilson区间、时长/伤害/治疗统计；确定性对照不制造随机性。首步优先内存汇总，再按独立步骤处理CSV/数据库持久化。用户确认开始Phase6后才实施。
