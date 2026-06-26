# PLAN-M-013 任务组拆分（Segments）

---
plan_id: PLAN-M-013
segments_of: PLAN-M-013-UIUX靛蓝专业克制改造.md
created: 2026-06-26
execution_mode: --auto
---

## 拆分说明

依据 Phase 依赖链拆为 6 个任务组（TG）。TG 内步骤串行，TG 间按依赖推进。无前端自动化测试，每组以 `node --check` + 人工冒烟验证。

```
TG-0（令牌重调）──> TG-1（视觉规范化）──> TG-2（三态组件）──> TG-3（⌘K 面板）
                                      └──────────────────> TG-4（A11y/响应式/性能）
TG-0..4 ──> TG-5（验收收尾）
```

并行机会：TG-2 与 TG-4 可在 TG-1 完成后并行（触及不同文件）。

---

## TG-0 · 靛蓝专业克制令牌重调（Phase 0）

**文件**：`views/index.html`（`<style> .theme-classic` 块、`tailwind.config backgroundImage`）

- [ ] 0-1 `.theme-classic` accent 三色 → 靛蓝（`#4F46E5`/`#4338CA`/保留 soft `#eef2ff`、medium `#c7d2fe`）
- [ ] 0-2 中性色 gray→slate（bg-base/surface-alt/hover/border/text-primary/secondary/tertiary/focus-ring）
- [ ] 0-3 阴影柔化（`--shadow-card`/`--shadow-card-hover`）
- [ ] 0-4 `gradient-brand` 收敛为同色系微渐变 `#4F46E5→#6366F1`
- [ ] 0-5 `node --check`（内联脚本无法直接 check，改用 grep 校验变量值）+ 浏览器目测 5 主题

**验证**：grep 确认无 `#667eea`/`#764ba2` 残留于 classic；默认主题呈靛蓝；4 套其它主题不受影响。

---

## TG-1 · 视觉规范化（Phase 1）

**文件**：`views/index.html`（head 字体、body 字体栈、侧边栏 nav-item）、`views/utils/ui-components.js`

- [ ] 1-1 引入 Inter 字体（preconnect + link）；body 字体栈
- [ ] 1-2 等宽字体 JetBrains Mono（代码/atom-id 场景）
- [ ] 1-3 侧边栏激活态：左 3px `bg-accent` 条 + `bg-accent-soft` 底（改 x-for 模板的 class 绑定）
- [ ] 1-4 侧边栏宽度 192→240px 评估与调整
- [ ] 1-5 ui-components.js 圆角/遮罩/间距微调（createModal 遮罩 black/40、宽度档；createBadge 保持语义浅底）
- [ ] 1-6 `node --check ui-components.js` + 冒烟

**验证**：Inter 生效；激活项有主色条；弹窗/徽章观感与 mockup 一致。

---

## TG-2 · 三态组件（Phase 2.1）

**文件**：`views/utils/ui-components.js`

- [ ] 2-1 新增 `createEmptyState({ icon, title, desc, action })`
- [ ] 2-2 新增 `createSkeleton({ rows, type })`（列表/卡片骨架）
- [ ] 2-3 挂载 `window.UI` + 导出
- [ ] 2-4 在 ≥2 个列表/表格视图替换裸 spinner / 空白（示范接入）
- [ ] 2-5 `node --check` + 冒烟

**验证**：空数据显示 EmptyState；加载显示 Skeleton；多主题适配。

---

## TG-3 · ⌘K 命令面板（Phase 2.2/2.3）

**文件**：`views/components/command-palette.js`（新增）、`views/index.html`（引入 + 顶栏搜索条打通）

- [ ] 3-1 新建 command-palette.js：复用 nav-config 渲染"跳转"分组
- [ ] 3-2 "知识原子"分组：对接 `/api/search`+`/api/suggest`（无结果/加载用三态组件）
- [ ] 3-3 键盘：⌘K/Ctrl+K 唤起、ESC 关闭、↑↓ 选择、Enter 执行
- [ ] 3-4 顶栏搜索条点击唤起面板
- [ ] 3-5 `node --check` + 冒烟（含键盘焦点）

**验证**：⌘K 唤起；跳转分组可用；搜索分组返回结果或规范空/错误态。

> 若时间受限：3-1/3-3/3-4（外观+跳转+键盘）先行，3-2（搜索 API 对接）标注为子任务后续完成。

---

## TG-4 · A11y / 响应式 / 性能校验（Phase 3）

**文件**：`views/index.html`、`views/css/responsive.css`、`views/utils/loader.js`

- [ ] 4-1 全局 `:focus-visible` 焦点环（accent 色）
- [ ] 4-2 交互元素 `aria-label` 补齐；键盘可达走查
- [ ] 4-3 对比度审计（记录结果）
- [ ] 4-4 触控目标 ≥44px、表格→卡片堆叠校验
- [ ] 4-5 模块加载缓存：`?t=Date.now()` → 版本号（评估，避免破坏开发热更）
- [ ] 4-6 `prefers-reduced-motion` 支持

**验证**：键盘走查通过；焦点环可见；对比度达标。

---

## TG-5 · 验收与收尾（plan-verify）

- [ ] 5-1 全量 `node --check`（所有改动 JS）
- [ ] 5-2 grep 校验（无紫调残留、Inter 生效、组件被引用）
- [ ] 5-3 多主题 × 三角色 × 双端 冒烟清单
- [ ] 5-4 回填计划"发现与记录""完成总结"
- [ ] 5-5 更新 `.claude/project.md` 计划状态 → completed
- [ ] 5-6 **ship 前停顿**：向用户汇报，确认后再 `/supercode:ship`（部署为外向操作，不自动执行）

---

## 执行进度

| TG | 状态 | 备注 |
|----|:----:|------|
| TG-0 | ✅ | 令牌重调完成（含 3 处紫调残留清理） |
| TG-1 | ✅ | Inter/Mono 字体接入；侧边栏选中态既有保留 |
| TG-2 | ✅ | createEmptyState / createSkeleton 已加 |
| TG-3 | ✅ | command-palette.js 外观+键盘+跳转+搜索降级 |
| TG-4 | 🔄 | 焦点环+reduced-motion 已落地；对比度/触控/键盘走查待浏览器 |
| TG-5 | 🔄 | node --check + grep 通过；多主题/三角色冒烟与 ship 待确认 |
