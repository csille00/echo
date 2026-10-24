# Static UI mockups (HTML)

Apple-inspired journal app — **no backend**, fake data only.

## Open

```bash
cd mockups
# any static server, or open files directly:
python3 -m http.server 5190
```

Then visit http://127.0.0.1:5190/calendar.html

Or open `calendar.html` in a browser (Chrome/Safari on Mac for best `-apple-system` fonts).

## Screens

| File | Purpose |
|------|---------|
| `calendar.html` | Home — month grid + day entries |
| `browse.html` | Photo grid + search |
| `review.html` | After scan — edit date & OCR text |
| `entry.html` | Read one entry |
| `ask.html` | Chat with cited entries |

Use the sidebar (desktop) or tab bar (phone) to move between main sections. **Scan** opens Review.

Toggle **light / dark** with the control in the sidebar footer.

Color rationale: see [COLORS.md](./COLORS.md) (warm paper + slate accent, not system blue).
