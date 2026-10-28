# Phase 5：统一英雄配置入口

目的：将已归档源记录、显式技能模型及缺失机制装配成CombatantProfile。正式入口load_combatant只读数据库；run_matchup只调用现有run_duel，不重复编写战斗算法。

## 支持范围

| 英雄 | enable_skills=True | 尚未实现 |
|---|---|---|
| Annie | simplified_active_only：源MagicDamage索引1的单体魔法主动 | 强化被动、被动攻速、额外目标伤害、法强修正、施法动作/锁蓝 |
| Olaf | simplified_heal_and_missing_hp_speed：源参数回血与缺血攻速 | 法强修正、客户端动作和精确效果顺序 |
| 其余13名当前样本英雄 | unsupported，显式抛NotImplementedError | 各自技能/被动尚未实现 |
| 任意已导入英雄且enable_skills=False | disabled_by_request：显式仅普攻模型 | 所有技能与被动关闭，不代表完整英雄 |

技能模式仅支持Set 10 / Patch 14.1，不自动将模型套到其他版本。技能记录必须匹配英雄ID与版本ID；缺失技能不补造默认值。已支持也只是明确说明的简化，不使用fully_supported标签。

## 接口

load_combatant(connection, version_id, champion_id, enable_skills=False)读取英雄、来源版本及可选技能，返回不可变配置。数据库读取与纯模型构造build_profile分离，便于单元测试和将来的应用复用。

profile.description()提供名称、ID、Set/Patch、skill_status、implemented和omitted供Notebook展示。原始源属性仍在profile.stats中。

run_matchup(a, b, mana_per_attack=None, enable_crit=False, seed=None, max_duration=60, max_events=100000, timing_rules=None)执行一场。主动技能需要显式回蓝量，开启暴击需要显式整数种子，不隐藏实验假设。双方必须使用同一源版本和内容哈希。

metadata新增profiles和source_snapshot，包含来源URL、原始哈希、获取时间与每侧支持状态。输入配置不含数据库凭据，不向源表写回状态。

## 实际单场示例

Set10 / 14.1，Annie A与Olaf B均开启已有简化技能，实验普攻回蓝10，暴击开启，seed42，60秒上限：

- Olaf胜，时长13.422997990740448秒，最终HP372.22222504792387。
- Annie/Olaf普攻8/9次，暴击4/4次，主动技能1/0次。
- Annie实际伤害447.4074045817057；Olaf实际治疗169.62962962962968。
- 结构化日志53条，相同配置重放完整结果相同。

这是单场模型结果，不能当作胜率估计；与之前不同模型的seed42输出不要求一致，因为技能和动态排期改变了战斗轨迹。

## 验证与当前边界

新增14项测试覆盖支持状态、源记录匹配、Patch门禁、不支持英雄不静默回退、显式回蓝、同源快照、查询装配和随机重放。完整本地219项通过；默认203项通过/16项数据库测试跳过。

代码为combat/profiles.py与database/combatants.py，测试为tests/test_profiles.py。真实数据库只读；维护测试仍使用强制回滚人工记录。没有创建、修改或执行Notebook，没有提交/推送GitHub。

这是当前Phase5功能的统一接口，不表示原始完整Phase5已全部实现：法强修正仍待扩展，Annie被动等未实现项继续保留；装备依用户要求暂缓。尚不进入Phase6，不生成批量统计或胜率结论。
