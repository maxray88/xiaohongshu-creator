# Session Learnings - 2026-05-29

## Day15 Cron Job - Multiple Page Context Issue + `_onSave()` Discovery

### Problem
Running `xhs_publish.py` multiple times in the same Chrome session creates multiple page contexts. The form was filled on Page 0, but subsequent save attempts couldn't locate the correct button state.

### Key Discovery: `_onSave()` Method on `xhs-publish-btn`

The `xhs-publish-btn` Custom Element has **both** `_onPublish()` and `_onSave()` methods accessible directly:

```javascript
// These methods live on the element, NOT in the shadow root
document.querySelector('xhs-publish-btn')._onSave()   // Save draft
document.querySelector('xhs-publish-btn')._onPublish() // Publish
```

**Why this matters**: The shadow DOM is closed (`attachShadow({mode: 'closed'})`), so `shadowRoot` returns `null` and `page.locator('button:has-text("存草稿")')` cannot pierce the boundary. But the public methods ARE accessible on the element itself.

### `xhs-publish-btn` Attributes (confirmed)
```javascript
{
  'data-v-04842b33': '',
  'data-v-74e5df5a-s': '',
  'is-publish': 'true',
  'is-save-draft': 'true',
  'submit-text': '发布',
  'save-text': '暂存离开',
  'submit-disabled': 'false',
  'save-disabled': 'false'
}
```

### `_onSave()` Called Successfully But No Navigation
When calling `_onSave()` directly via `page.evaluate()`:
- The method executes without error
- URL stays on `https://creator.xiaohongshu.com/publish/publish?from=menu&target=image`
- No visible confirmation or navigation occurs

**Possible interpretation**: The draft is being saved but XHS creator platform doesn't navigate away on save, or the save operation completes silently.

### Multi-Page Context Problem
When running `xhs_publish.py` multiple times:
- Each run creates a new page in the Chrome context
- `browser.contexts[0].pages` grows: [Page 0, Page 1, Page 2, ...]
- The form with our content is on Page 0
- But subsequent script executions may interact with wrong pages

**Debugging tip**: To find which page has the filled form:
```javascript
// Find page with filled title
for (const page of browser.contexts[0].pages) {
  const title = await page.evaluate(() => {
    const input = document.querySelector('input[placeholder*="标题"]');
    return input ? input.value : null;
  });
  if (title && title.includes('闲鱼')) {
    console.log('Found form on page:', page.url());
    break;
  }
}
```

### Recommendation for Future Debugging
When save draft fails with "button not found" errors:
1. Check `browser.contexts[0].pages` to see how many pages exist
2. Identify which page has the filled form
3. Use `document.querySelector('xhs-publish-btn')._onSave()` directly via `page.evaluate()`
4. The `xhs-publish-btn` is a custom element with a closed shadow root - methods must be called on the element itself

### Screenshot Path
Debugging screenshots saved to `/tmp/xhs_screenshots/`:
- `page_0.png`, `page_1.png`, `page_2.png` - Different browser pages
- `final_state.png`, `method_check.png` - Form state analysis
- `draft_attempt_2.png` - After save attempt

### Content File
Generated content saved to: `/tmp/xhs_daily/day15/content.txt`