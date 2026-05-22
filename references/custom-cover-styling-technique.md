# Custom Cover Styling Technique (突破默认样式限制)

## 场景

当 `xhs_image_pipeline.py` 的内置模板无法满足特定设计需求时（例如需要：
- 关键点区域垂直居中而非顶部固定位置
- 关键点字体大小与标题同级（>88px）
- 特定关键词的精细高亮控制（多层阴影、下划线装饰）
- 非标准布局）

则使用本技术：自定义HTML+CSS + Playwright直接渲染。

## 核心步骤

1. **提取原始模板HTML结构**  
   参考 `xhs_image_pipeline.py` 中的 `build_cover_html()` 函数，复制完整的HTML+CSS模板。

2. **针对性CSS修改**  
   通过字符串替换或直接编辑，调整以下规则：

   ```css
   /* 关键点区域居中 */
   .kp-wrap { top: 600px; left: 80px; right: 80px; }
   
   /* 关键点文字放大至标题尺寸 */
   .kp-text { font-size: 92px; padding: 30px 40px; }
   
   /* 关键词高亮强化 */
   .kp-text .kw { font-size: 110px; color: #e07850; 
                  text-shadow: 1px 1px 0 rgba(224,120,80,0.1); }
   .kp-text .kw::after { /* 下划线装饰 */ }
   
   /* 徽章尺寸同步放大 */
   .kp-badge { width: 80px; height: 80px; font-size: 36px; }
   ```

3. **关键词高亮标记**  
   在关键点文本中使用 `**关键词**` 或 `<关键词>` 语法，模板会将其包裹在 `<span class="kw">` 中。

4. **Playwright渲染与截图**
   ```python
   from playwright.sync_api import sync_playwright
   with sync_playwright() as p:
       browser = p.chromium.launch(headless=True)
       page = browser.new_page(viewport={'width':1080,'height':1440})
       page.set_content(html_string)  # 注入自定义HTML
       page.wait_for_timeout(2000)    # 等待字体加载
       page.screenshot(path='cover.jpg', full_page=False)
       browser.close()
   ```

## 使用建议

- 将此技术封装为独立脚本 `customize_cover.py`，支持命令行参数覆盖尺寸、位置、高亮词
- 原始模板版权属于设计系统，仅作技术参考，商业发布需遵守原技能许可
- 保持与S6手绘风一致：暖色调、手绘字体、轻微旋转、纸张纹理背景

## 案例参考

- 会话 2026-05-22：职场搞钱博主Day1封面优化
  - 需求：关键点"真实记录 拒绝画饼"放大、居中、关键词高亮
  - 实现：top从390px改为600px，kp-text从38px改为92px，kw从44px改为110px
  - 结果：27.6KB JPEG，视觉冲击力显著提升

## 注意事项

- Playwright需使用venv Python：`/Users/maochundong/.hermes/hermes-agent/venv/bin/python3`
- 截图视口固定为1080x1440（小红书封面尺寸）
- 若需要更大的关键词装饰（如下划线），可进一步修改 `.kw::after` 的高度和颜色

---
**相关技能**: `xiaohongshu-creator`, `make-money-xiaohongshu`