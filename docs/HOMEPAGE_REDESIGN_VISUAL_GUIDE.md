# Homepage Redesign - Visual Guide

## Current vs Proposed Layout

### Current Problems

```
┌─────────────────────────────────────────┐
│  Homepage (Infinite Scroll - CURRENT)   │
├─────────────────────────────────────────┤
│  [Hero Banner]                          │
├─────────────────────────────────────────┤
│  Article 1: Just Text                   │ ← No image
│  Article 2: Just Text                   │ ← No image
│  Article 3: Just Text                   │ ← No image
│  ...                                    │ ← All 500+ articles loaded
│  ...                                    │ ← DOM grows unbounded
│  ...                                    │ ← Performance degrades
│  Article 500: Just Text                 │ ← Mobile = lag
│  (Page keeps scrolling endlessly)       │
└─────────────────────────────────────────┘

Issues:
❌ All articles in DOM
❌ No images
❌ Poor performance (20+ sec load)
❌ Mobile laggy
❌ No pagination
```

### Proposed Solution

```
┌─────────────────────────────────────────┐
│  Homepage (Paginated with Images)       │
├─────────────────────────────────────────┤
│  [Hero Banner]                          │
├─────────────────────────────────────────┤
│  ┌──────────────────────────────────┐   │
│  │ [Cover Image]                    │   │ ← Image now visible!
│  ├──────────────────────────────────┤   │
│  │ Article Title                    │   │
│  │ "Insightful content about..."    │   │
│  │ 2 days ago • technology          │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │ [Cover Image]                    │   │
│  ├──────────────────────────────────┤   │
│  │ Another Article Title            │   │
│  │ "More great insights..."         │   │
│  │ 1 day ago • science              │   │
│  └──────────────────────────────────┘   │
│                                          │
│  (... 10 more cards ...)                │
│                                          │
├─────────────────────────────────────────┤
│  ← Previous  [1] [2] [3] ...  Next →    │ ← Clean pagination!
└─────────────────────────────────────────┘

Benefits:
✅ Only 12 articles per page
✅ Professional card layout with images
✅ Clear pagination for navigation
✅ Fast load time (<5 seconds)
✅ Smooth mobile experience
✅ Bookmarkable/shareable pages
```

---

## Technical Changes Overview

```
Site Publisher Container
│
├── hugo-config/
│   │
│   ├── config.toml
│   │   └── ADD: [pagination] pagerSize = 12
│   │
│   ├── layouts/
│   │   ├── index.html                    ← DELETE (use PaperMod default)
│   │   ├── _default/
│   │   │   ├── list.html
│   │   │   └── single.html
│   │   │
│   │   └── partials/
│   │       ├── post_card.html            ← DELETE (use PaperMod .post-entry)
│   │       ├── hero-attribution.html
│   │       └── source-attribution.html
│   │
│   ├── assets/css/
│   │   └── custom.css
│   │       └── REMOVE: .post-entry CSS rules
│   │       └── REMOVE: .first-entry CSS rules
│   │       └── KEEP: .home-info hero styling
│   │
│   └── themes/
│       └── PaperMod/                     ← Theme provides homepage + pagination
│           ├── layouts/
│           │   ├── index.html            ← Now used (was overridden)
│           │   └── partials/
│           │       └── post-entry.html   ← Now used (images supported!)
│           │
│           └── assets/
│               └── css/
│                   └── main.css          ← Images handled here
```

---

## Data Flow - From Collection to Homepage

```
┌──────────────────────────────────────────────────────────┐
│ 1. Content Collection (Reddit, RSS, Mastodon, Web)       │
└──────────────────────────────────────────────────────────┘
                            ↓
                   Article JSON blob
                   {
                     "title": "Article Title",
                     "content": "...",
                     "tags": ["ai"],
                     "source_metadata": {...}
                   }
                            ↓
┌──────────────────────────────────────────────────────────┐
│ 2. Markdown Generator (containers/markdown-generator)    │
│    - Fetches Unsplash image for article                  │
│    - Includes image URL in frontmatter                   │
└──────────────────────────────────────────────────────────┘
                            ↓
                   Markdown file with YAML frontmatter:
                   ---
                   title: "Article Title"
                   date: 2025-10-19
                   cover:
                     image: "https://images.unsplash.com/photo-xyz"
                     alt: "Descriptive alt text"
                     caption: "Photo by John Doe on Unsplash"
                   tags: ["ai", "technology"]
                   ---
                   # Article content...
                            ↓
┌──────────────────────────────────────────────────────────┐
│ 3. Site Publisher - Hugo Build                           │
│    - Reads markdown files with cover image              │
│    - Uses PaperMod theme to render                       │
│    - Pagination: 12 articles per page                    │
│    - Images displayed in card layout                     │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│ 4. Final Homepage                                        │
│    ✅ Paginated (Page 1, 2, 3...)                       │
│    ✅ Images visible on cards                            │
│    ✅ Professional layout                                │
│    ✅ Fast loading                                       │
│    ✅ Mobile friendly                                    │
└──────────────────────────────────────────────────────────┘
```

**Key Insight**: Images are ALREADY flowing through the entire pipeline!  
We're just not displaying them on the homepage. That's the only issue to fix.

---

## Before & After Metrics

```
Performance Comparison
┌──────────────────────────────┬──────────┬─────────┐
│ Metric                       │ Current  │ Target  │
├──────────────────────────────┼──────────┼─────────┤
│ Page Load Time               │ 20+ sec  │ < 5 sec │
│ DOM Elements                 │ 500+     │ ~50     │
│ Memory Usage                 │ 50+ MB   │ ~10 MB  │
│ Time to Interactive          │ 15+ sec  │ < 5 sec │
│ First Contentful Paint       │ 10+ sec  │ < 2 sec │
│ Lighthouse Score             │ ~40      │ > 75    │
│ Mobile Smoothness            │ Laggy    │ Smooth  │
│ Image Coverage               │ 0%       │ 100%    │
└──────────────────────────────┴──────────┴─────────┘
```

---

## Implementation Phases

### Phase 1: Configuration (5 min)
```bash
# File: containers/site-publisher/hugo-config/config.toml
# ADD: pagination config
[pagination]
  pagerSize = 12
```

### Phase 2: Template Cleanup (4 min)
```bash
# DELETE:
rm containers/site-publisher/hugo-config/layouts/index.html
rm containers/site-publisher/hugo-config/layouts/partials/post_card.html

# MODIFY:
# containers/site-publisher/hugo-config/assets/css/custom.css
# Remove .post-entry, .first-entry CSS rules
```

### Phase 3: Testing (30 min)
```bash
# Build locally
cd containers/site-publisher
hugo

# Verify:
# - Pagination appears
# - Images show on cards
# - Mobile responsive
# - No CSS conflicts
```

### Phase 4: Deployment (CI/CD)
```bash
git checkout -b feature/homepage-pagination
git add containers/site-publisher/
git commit -m "Homepage: Pagination + PaperMod defaults

- Add pagination config (12 articles/page)
- Delete custom index.html template
- Delete custom post_card.html partial  
- Clean up unnecessary CSS overrides"
git push origin feature/homepage-pagination

# Create PR → CI/CD → Merge → Auto-deploy
```

---

## CSS Changes Detail

### Current CSS Problems
```css
/* These are trying to fix things in the wrong place */
.post-entry .entry-cover {
  max-height: 180px;  /* Limits image size */
}

.first-entry {
  max-height: 320px;  /* Adds complex layout rules */
}

.main {
  max-width: calc(...);  /* Overrides theme sizing */
}
```

### Solution: Remove These
```css
/* DELETE THESE BLOCKS ↓ */
/* .post-entry .entry-cover { ... } */
/* .first-entry { ... } */
/* .main { ... } */

/* KEEP: Hero section branding */
.home-info {
  background-image: linear-gradient(...), url(...);
  /* Your hero styling - looks good! */
}
```

**Why**: PaperMod's CSS already handles post-entry sizing perfectly.

---

## Frontmatter Comparison

### Current (Generated by markdown-generator)
```yaml
---
title: "Article Title"
date: 2025-10-19T12:00:00Z
cover:
  image: "https://images.unsplash.com/photo-xyz?w=800&q=75"
  alt: "Image description"
  caption: "Photo by John Doe on Unsplash"
tags: ["technology", "ai"]
categories: ["Tech"]
---
```

### Homepage Rendering
| Field | Usage |
|-------|-------|
| `title` | Card heading |
| `date` | Metadata (when published) |
| `cover.image` | Card background/header image ← KEY! |
| `cover.alt` | Accessibility (alt text) |
| `cover.caption` | Credit line |
| `tags` | Category badges |

**Status**: ✅ All data is already there!  
**Change Needed**: Just render it with PaperMod (delete custom templates).

---

## Rollback Plan (If Needed)

```bash
# If issues arise, rollback is simple (5 minutes):

git revert <commit-hash>
# or
git checkout HEAD -- containers/site-publisher/

# Git will restore:
# - layouts/index.html
# - layouts/partials/post_card.html
# - Original CSS
# - Original config.toml

# Site reverts to current state (no data loss)
```

---

## Success Checklist

### Pre-Implementation
- [ ] Reviewed this guide
- [ ] Confirmed 12 articles/page is OK
- [ ] Team agrees with approach

### Implementation
- [ ] config.toml updated with pagination
- [ ] layouts/index.html deleted
- [ ] layouts/partials/post_card.html deleted
- [ ] custom.css cleaned up
- [ ] Commit message is clear

### Testing
- [ ] Hugo builds (no errors)
- [ ] Homepage loads (no 404)
- [ ] Pagination visible
- [ ] Images show on cards
- [ ] Mobile responsive
- [ ] No CSS conflicts
- [ ] Links work

### Deployment
- [ ] PR created
- [ ] CI/CD passes
- [ ] Approved by team
- [ ] Merged to main
- [ ] Auto-deployed

### Post-Deployment
- [ ] Check production homepage
- [ ] Verify performance improved
- [ ] Monitor for 1 hour
- [ ] No user complaints
- [ ] Document completed in TODO.md

---

_Guide Created: October 19, 2025_  
_Ready to Implement: Yes_  
_Estimated Duration: 60-90 minutes_  
_Risk Level: LOW_
