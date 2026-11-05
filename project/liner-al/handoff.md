# HANDOFF — 角色交接板（非日志, 宪法第十三条）
> 每个 发→收 只保留最新一条, send 就地更新; 开工先读上一棒 NEXT（scripts/handoff.py show）。只允许更新自己发出的条目。

## 2026-11-05 13:30 | operator → transcriber
- SEND: bug 修复完成: ①自建 mybook 已删除, 产物归位 liner-al; ②batch.py detect 改页级锁步(detect 一页→转录排版一页)并经 019 页全链验证(检测/转录/排版/对照通过)。现 dest/ 共 19 页最终件(001-019 + img/007,018,019), plan/state/dest 三者一致
- STATE: run-state-detect ok=001-019, run-state-html ok=html:001-019; 锁步规则: 重跑 batch detect 只推进第一个未完成页(020)
- NEXT: 继续锁步: 重跑 batch.py detect(自动测 020) → 转录 020 写 text.md(第零条分块核对) → batch --stage html → 循环

## 2026-11-05 13:30 | operator → compositor
- SEND: dest/019.html 已交付并通过第九条自检+第七条版式对照(标题右对齐/列矩阵公式/双图带/整行图注/空格标点照录); 001-018 沿用上一棒已验收件
- STATE: dest/<page>.html + dest/img/ 同仓自洽; 019 中间件已随批归档 backup/project-20261105-132824.tar.gz
- NEXT: 后续页排版完成后按同款自检对照; 需矢量重绘时由 figure-artisan 供 spec 跑 px2svg
