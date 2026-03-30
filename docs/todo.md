---

TODO: Fix favicon rendering in browser search / navigation bar

Context:
- Current icon does not scale consistently across browser UI (tabs, search bar, bookmarks)
- Limited control from frontend, must rely on proper asset setup
- Icon appears too small / unclear at certain sizes

Potential causes:
- Missing required favicon sizes
- Incorrect aspect ratio or padding in source image
- Browser fallback behavior using lowest-quality icon
- Lack of proper <link> tags in index.html

Tasks:
- Generate proper favicon set:
  - favicon-16x16.png
  - favicon-32x32.png
  - apple-touch-icon.png (180x180)
  - optional: android-chrome-192x192.png, 512x512
- Ensure icon has correct padding (not touching edges)
- Optimize for clarity at very small sizes (16px especially)
- Update index.html with all required <link> tags
- Remove old/unused favicon assets to avoid conflicts

Next steps:
- Redesign icon specifically for small-scale readability
- Test across browsers (Chrome, Safari, Edge)
- Verify appearance in:
  - browser tab
  - bookmarks bar
  - mobile home screen (if installed)