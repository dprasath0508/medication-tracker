"""Inline Phosphor-style SVG icons.

Streamlit has no native Phosphor integration, so we ship inline SVGs with
consistent 1.5px stroke width and ``currentColor`` fill so they inherit theme
tokens via CSS.

Usage:

    from ui.icons import icon
    st.markdown(icon("pill", size="lg"), unsafe_allow_html=True)

Sizes: ``sm`` (16), ``md`` (20, default), ``lg`` (24), ``xl`` (32).
"""

_SIZES = {"sm": 16, "md": 20, "lg": 24, "xl": 32}

_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" '
    'style="display:inline-block;vertical-align:middle;color:{color}">{body}</svg>'
)

# Phosphor-style paths. Simplified for inlining but visually consistent.
_ICONS = {
    "pill": '<path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12,7 12,12 15.5,14"/>',
    "check": '<polyline points="5,12.5 10,17.5 19,7"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><polyline points="8,12.5 11,15.5 16,9.5"/>',
    "x": '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    "user-plus": '<circle cx="10" cy="8" r="4"/><path d="M2 21c0-4 4-6 8-6s8 2 8 6"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-3 3-5 7-5s7 2 7 5"/><path d="M16 4a3.5 3.5 0 0 1 0 7"/><path d="M22 20c0-2.5-2-4.5-5-4.5"/>',
    "heart": '<path d="M12 21s-8-5-8-11a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-10 11-10 11Z"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M5 5l2 2M17 17l2 2M2 12h3M19 12h3M5 19l2-2M17 7l2-2"/>',
    "arrow-left": '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12,5 5,12 12,19"/>',
    "arrow-right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12,5 19,12 12,19"/>',
    "chevron-right": '<polyline points="9,5 16,12 9,19"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "sign-out": '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10,17 15,12 10,7"/><line x1="15" y1="12" x2="3" y2="12"/>',
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M5 5l1.5 1.5M17.5 17.5 19 19M3 12h2M19 12h2M5 19l1.5-1.5M17.5 6.5 19 5"/>',
    "phone": '<path d="M5 3h3l2 5-2.5 1.5a12 12 0 0 0 6 6L15 13l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2"/>',
    "lock": '<rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><polyline points="3,7 12,13 21,7"/>',
    "info": '<circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="8.01"/><path d="M12 12v5"/>',
    "sparkle": '<path d="M12 3v18M3 12h18M6 6l12 12M18 6 6 18"/>',
    "house": '<path d="M3 11 12 4l9 7v8a2 2 0 0 1-2 2h-4v-6h-6v6H5a2 2 0 0 1-2-2Z"/>',
    "palette": '<path d="M12 3a9 9 0 0 0 0 18h1a3 3 0 0 0 0-6h-1a3 3 0 0 1 0-6h4a5 5 0 0 0-4-6Z"/><circle cx="7.5" cy="10.5" r="1"/><circle cx="10.5" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/>',
    "moon-stars": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/><path d="M17 4h.01M20 8h.01"/>',
    "list-checks": '<line x1="10" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="10" y1="18" x2="21" y2="18"/><polyline points="3,6 4,7 6,5"/><polyline points="3,12 4,13 6,11"/><polyline points="3,18 4,19 6,17"/>',
    "leaf": '<path d="M20 4c0 12-8 16-16 16 0-8 4-16 16-16Z"/><path d="M20 4C10 4 4 14 4 20"/>',
}


def icon(name: str, size: str = "md", color: str = "currentColor") -> str:
    """Return an inline SVG string for the given icon name.

    ``size`` accepts a preset (``sm``/``md``/``lg``/``xl``) or a pixel int as a string.
    Falls back to a subtle placeholder if the name isn't registered.
    """
    if name not in _ICONS:
        body = '<circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="8.01"/><path d="M12 12v5"/>'
    else:
        body = _ICONS[name]

    if size in _SIZES:
        px = _SIZES[size]
    else:
        try:
            px = int(size)
        except (TypeError, ValueError):
            px = _SIZES["md"]

    return _SVG_TEMPLATE.format(size=px, body=body, color=color)


def icon_button_label(name: str, text: str, size: str = "md") -> str:
    """Compose a label string with an icon + text for use in HTML contexts."""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:0.5rem;'
        f'font-family:var(--font-body);color:inherit;">'
        f"{icon(name, size)}<span>{text}</span></span>"
    )
