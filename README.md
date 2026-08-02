# medication-tracker

A warm, semi-formal Streamlit + Supabase app for elderly patients (55+, often
75+) and their family support circle. Built to help someone open the app once
a day, see exactly which medications to take, mark them done, and close it
again.

Backend runs on Supabase in production, SQLite locally.

## Run

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run src/web_app.py
```

The app auto-selects Supabase when `SUPABASE_URL` and `SUPABASE_KEY` are set,
and falls back to SQLite (`data/medications.db`) for local development.

## Security model

Authorization is enforced in the application's data layer, not in the database.
Understanding why is the point of this section.

**Trust boundary.** Streamlit runs entirely server-side. The Supabase service
key (`SUPABASE_KEY`) lives only in the server environment and never reaches a
browser — the client only ever receives rendered HTML. Every database access
goes through the Python process, so that process is the boundary that has to
decide who sees what.

**The chokepoint.** Every patient-scoped data method — read or write, on both
the SQLite and Supabase backends — calls `_assert_can_access_patient` in
[`src/utils/authz.py`](src/utils/authz.py) as its first statement. A patient
always reaches their own data; anyone else needs the right permission in a
family circle shared with the patient (`view` to read, `manage_meds` to write).
Denial raises `AuthorizationError`, never a silent empty result — an empty list
reads as "no data" and would hide the bug. There is no bypass variant, by
design: a bypass method is how this regresses in six months.

**Why not Row Level Security?** Supabase RLS looks like the obvious answer and
is deliberately not used. This app rolls its own auth (custom `users` table,
bcrypt credentials, session tokens) rather than Supabase Auth, so there is no
Supabase JWT and `auth.uid()` is always NULL. The app also connects with the
service key, which bypasses RLS entirely. Any policy written today would either
never evaluate (service key) or deny everything (anon key) — security theater
either way. `supabase_schema.sql` therefore ships with RLS off and documents
the reasoning inline.

**Migration path.** The real fix is to adopt Supabase Auth so requests carry a
JWT, connect from the browser with the anon key, then enable RLS with per-table
policies as defense in depth *behind* the application chokepoint. That is future
work, not this sprint.

## Design system

Full spec in [`design-system/MASTER.md`](design-system/MASTER.md). Per-page
overrides live in [`design-system/pages/`](design-system/pages).

Highlights:

- **Typography** — Fraunces (optical-size serif, headings) + Instrument Sans
  (humanist body). Both Google Fonts. Body copy is always **≥ 17px** — this
  app is used by patients who need to read it.
- **Shape** — no hard edges. 12px minimum radius on cards, buttons, inputs.
  Sheets are 24px. Softness signals care.
- **Motion** — CSS-driven page transitions, staggered list entrance, spring
  micro-interactions. Every animation respects `prefers-reduced-motion`.
- **Aesthetic** — warm, welcoming, semi-formal. Cream backgrounds, muted
  accents. Never clinical, never playful, never AI-purple.

Constraint contract for future contributors: [`CLAUDE.md`](CLAUDE.md).

## Themes

The app ships four themes; users switch anytime from **Settings**. Choice is
persisted per user in the `users.theme` column.

| Theme          | Feel                                | Use when                          |
|----------------|-------------------------------------|-----------------------------------|
| `warm-cream`   | Cream + terracotta (default)        | Everyday use                      |
| `cool-sage`    | Sage + caring teal + warm orange    | Prefer calmer, cooler tones       |
| `twilight`     | Deep plum-navy + amber (soft dark)  | Evening use, low-light rooms      |
| `high-contrast`| WCAG AAA black/white/amber          | Low vision, bright environments   |

Themes are swapped via `[data-theme="..."]` on `<html>`; every color in the
app is a CSS custom property (`var(--surface-card)`, `var(--text)`,
`var(--accent)`, etc.), never a hardcoded hex.

### Adding a theme

1. Add the token block to `design-system/MASTER.md` § 3.
2. Add the same block scoped under `[data-theme="your-name"]` in the global
   CSS in `src/ui/theme.py`.
3. Add the theme to the picker's option list in `src/pages/settings.py`.
4. Verify every token × role combo passes WCAG AA (AAA if the theme is
   accessibility-oriented). Add a screenshot to `docs/themes/`.

## Structure

```
src/
├── web_app.py            # thin entry — st.navigation router
├── main.py               # background reminder service
├── pages/                # one file per route
├── ui/                   # theme.py, icons.py, primitives.py, motion.py
├── models/               # domain models (untouched by UI work)
├── services/             # auth, notifications, scheduler (untouched by UI work)
└── utils/                # db factory + SQLite/Supabase backends (untouched by UI work)

design-system/
├── MASTER.md             # source of truth
└── pages/                # per-route overrides

.claude/
└── skills/
    └── ui-ux-pro-max/    # installed skill (design intelligence)
```

## The ui-ux-pro-max skill

This repo has the [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
skill vendored under `.claude/skills/`. It's a Python-stdlib-only search engine
over CSV databases of design guidance (styles, colors, typography, GSAP snippets,
UX rules, per-stack best practices).

Use it whenever making a design decision:

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  "healthcare warm welcoming" --design-system --variance 4 --motion 6 --density 3
```

Documented in [`CLAUDE.md`](CLAUDE.md) § The skill.
