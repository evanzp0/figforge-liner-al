# NOTES — operator 经验库（错误 → 解决）
> 宪法第十二/十三条: 项目收尾把已解决的错误提炼在此; 一条经验一个条目,
> 只写 现象/根因/解决/预防/标签 五要素（非日志: 无日期/次数/统计, 有条目上限）;
> 由 scripts/notes.py add 写入与合并; 检索先看 INDEX.md 或 notes.py show。

## z-ai vision 批量检测 ~30-40 页即 429 风暴熔断 (退出码 43); 单次 probe RECOVERED 不等于批量配额已恢复
- 根因: 账号级共享配额限流, 窗口恢复渐进
- 解决: 43 即停批 (batch.py 自动), scripts/probe-429.sh <源图> 540s 低频探测, RECOVERED 后原样续跑; 恢复首段用小 --maxseconds (≤400) 试水, 立即再熔断就继续等
- 预防: 禁止报复性并发; 恒定单进程前台串行 + 页间隔 (宪法第三/六条)
- 标签: #429 #熔断 #probe

## batch.py 因 43 熔断 sys.exit 时跳过 plan 核销, plan.md 与 run-state 不一致
- 解决: 恢复后按 run-state-<stage>.json 的 ok 清单同步核销: plan.py done --file plan.md <ids> (与 batch.check_off_plan 同逻辑)
- 标签: #plan #断点

## 交付快照里出现仓库不存在的自建项目（mybook）, 与仓库自带项目重复且把交付包体积翻倍
- 根因: batch.py/README/handoff.py 的用法示例硬编码了 --project mybook, 执行时照抄示例跑了 forge.sh new mybook 并复制他项目 src/ 原图
- 解决: 删除 project/mybook, 产物合并回 project/liner-al; 所有脚本与文档示例改为仓库真实项目名 liner-al, 并注明'禁止自建与仓库无关的项目'
- 预防: 开工先确认 project/ 下已有项目; 项目名必须对应真实书源, 示例名不得当真
- 标签: #项目管理 #交付 #示例误导

## detect 已完成页数与转录排版页数长期不同步（detect 151 vs 排版 18）, detect 超前跑空 API
- 根因: batch.py detect 默认阶段一次性扫描 src/ 全部原图, 与转录排版进度无耦合
- 解决: batch.py detect 改为页级锁步: 每次只检测'第一个未完成页'(完成=dest/<page>.html 已产出), 该页排版完成后重跑才推进下一页; --pages 显式指定页为手工兜底不受锁步限制
- 预防: 永远 detect 一页→转录排版一页再推进; 不允许批量 detect 超前
- 标签: #锁步 #批量 #进度同步
