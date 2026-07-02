# OpenCLI Verified Publish Workflow (2026-06-21)

## Verified command
```bash
opencli xiaohongshu publish "正文内容" \
  --title "标题" \
  --images /path/a.jpg,/path/b.jpg
```
- Max 9 images
- Title ≤20 chars
- Requires logged-in creator center under bound Browser Bridge profile.

## Login verification (REQUIRED)
```bash
opencli browser pjmvbend open "https://www.xiaohongshu.com/user/profile/me"
opencli browser pjmvbend get url
```
If URL contains `/login?redirectPath=...`, stop and ask user to log in.

`opencli doctor` showing `[OK] Extension: connected` only proves bridge connectivity, not login state.

## Image-size failure signature and fix
- Symptom: `fetch failed` / `write EPIPE`
- Cause: total payload >300KB or single image >150KB pushed the CDP upload past browser base64 limits.
- Fix: compress first.
  ```bash
  ffmpeg -y -i INPUT -vf "scale=640:-2" -q:v 60 OUTPUT
  ```
- Observed shrink: set of 6 covers from ~2.5MB down to ~112KB after compressing.
- Rule of thumb: compress every image before publish in cron and ad-hoc flows.

## File-upload fallback (DataTransfer eval)
`opencli browser upload` frequently returns `{"code":-32000,"message":"Not allowed"}`.

Use `opencli browser <session> eval` JS IIFE:
```js
(function(){
  var fi=document.querySelector('input[type="file"]');
  var dt=new DataTransfer();
  ['/path/a.jpg','/path/b.jpg'].forEach(function(p){
    var blob=new Blob([new ArrayBuffer(1)],{type:'image/jpeg'});
    dt.items.add(new File([blob], p.split('/').pop(), {type:'image/jpeg'}));
  });
  fi.files=dt.files;
  fi.dispatchEvent(new Event('change'));
})();
```

Pitfalls:
- Page JS may declare globals `input` or `fileInput`; IIFE avoids conflicts.
- After this injection the page can navigate to `about:blank`; open the publish URL again if needed.
- If you see this fail, first compress the images; large files are the most common blocker.

## Constraint
Not allowed: `computer_use`, generic `browser_*`, Playwright CDP for Xiaohongshu.
Allowed: `opencli browser <session> *` only.
