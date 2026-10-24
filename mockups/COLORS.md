# Color scheme — Journal mockups

**Intent:** warm archive, not cold SaaS gray or default iOS blue.

## Light (“paper”)

| Token | Hex | Use |
|-------|-----|-----|
| Background | `#E8E6E1` | App chrome |
| Elevated | `#F7F6F3` | Lists, cards |
| Secondary surface | `#EFEDE8` | Thumbs, scan preview |
| Text | `#1C1B19` | Primary |
| Accent | `#3D5A73` | Links, buttons, selected day, dots |
| Success | `#2D6A4F` | Completed (when needed) |
| Warning | `#B45309` | Processing |
| Destructive | `#B33A3A` | Failed |

## Dark (“inkwell”)

| Token | Hex | Use |
|-------|-----|-----|
| Background | `#121110` | App chrome |
| Elevated | `#1C1A18` | Lists, cards |
| Text | `#F5F2EB` | Primary |
| Accent | `#7EB3D4` | Links, selection (readable on dark) |

Toggle in sidebar footer. CSS variables live in `styles.css` (`:root` / `[data-theme="dark"]`).
