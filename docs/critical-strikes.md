# Phase 5 / Step 1：普通攻击暴击与随机种子

状态：正式模块和测试通过；用户将在自己手动创建的05_critical_strikes.ipynb中运行示例，输出待反馈。没有编辑或执行任何Notebook，没有修改数据库，也未提交或推送GitHub。

## 参数与模型边界

本轮读取已归档源属性：Annie和Olaf的crit_chance均为0.25，crit_multiplier均为1.399999976158142。显示时可近似为25%和1.4倍，计算不取整。

数据库字段并不是新编造的英雄属性。ChampionStats.from_record现在必须读取这两个字段，缺失时不会填造；直接构造类的默认0%/1倍仅服务于无暴击模型和人工测试夹具。

独立逐击判定、乘暴击倍率后再交给抗性函数的调用顺序，是当前模型规则，不代表已还原所有TFT暴击、被动、装备和特殊攻击交互。机会超过100%的转换机制不在范围内，当前输入限制为0到1。

## 数学与实现

每次攻击从局部伪随机生成器取得U，0<=U<1。p表示暴击概率，C表示暴击倍率，AD表示基础攻击力。

```text
U < p：D_raw = AD × C
U >= p：D_raw = AD
```

例如p=0.25、C=1.4、AD=40，U=0.10时暴击，护甲前伤害56；U=0.60时不暴击，护甲前伤害40。这是数学示例；实际计算保留源倍率的完整精度。

Python正式实现为roll_critical_hit，返回CriticalHit，包括基础伤害、暴击后伤害、是否暴击及随机数。之后调用physical_damage，再调用take_damage扣血。

每次攻击消耗一个随机数，包括0%与100%两种边界。相同时间批次仍先确定双方攻击，之后统一扣血和死亡。

## 可复现性

引擎版本basic_duel_v0.2；暴击模型attack_crit_v0.1。

- 默认enable_crit=False，保留Phase 4无随机性基线；此时不接收无效seed。
- 启用enable_crit=True时必须明确传入整数seed。
- 每场独立创建random.Random(seed)，不调用全局random.seed。
- 随机数按时间顺序消耗；严格同刻时A先取数、B后取数。这个顺序会记录在metadata中，交换A/B位置不能承诺逐场结果仍完全对应。
- 重放需要相同输入、种子、引擎/模型和环境；metadata记录输入快照、Python版本与种子。
- 不同种子改变随机轨迹，不保证改变胜负；25%也不意味着每4击恰好1次暴击。

Python标准库说明：https://docs.python.org/3.13/library/random.html

## 日志字段

- base_attack_damage：未乘暴击倍率的基础AD。
- is_critical：本击是否暴击；开始/结束等非攻击事件为False。
- critical_roll：本击随机数；关闭暴击时为None。
- raw_damage：已包含本击暴击倍率、尚未经过护甲的伤害。
- damage_after_resistance：抗性计算后的伤害。
- damage：实际生命损失，不包含过量部分。

摘要新增critical_hits_a和critical_hits_b，其余原字段保持可用。

## 实际示例：Annie vs Olaf，60秒上限

| 配置 | 胜者 | 时长约值 | Olaf剩余HP约值 | Annie/Olaf暴击次数 |
|---|---|---:|---:|---|
| 无暴击 | Olaf | 15.3846 | 353.7037 | 0 / 0 |
| seed=42 | Olaf | 12.3077 | 389.2593 | 2 / 5 |
| seed=2026 | Olaf | 15.3846 | 306.2963 | 4 / 1 |

相同seed=42重放的完整结果和日志一致。首击Annie的U约0.6394，不暴击；Olaf的U约0.0250，暴击。数据库记录数量保持1/15/15。

这是当前简化模型的输出，不是玩家胜率或真实英雄整体强弱结论；本轮没有批量Monte Carlo、技能、法力获取、装备或羁绊。

## 测试与使用

新增28项模型/暴击测试通过，完整本地测试134项通过；默认118项通过、16项数据库测试跳过。覆盖概率边界、非法输入、随机重放、全局状态隔离、暴击日志、双杀和无暴击回归。

正式文件：models/champion.py、combat/critical.py、combat/engine.py。Notebook调用代码在聊天中提供。无新第三方依赖。

Phase 5尚未完成。用户反馈后再决定下一步机制；装备仍暂缓，GitHub更新需另行请求。
