## Plan: Enterprise Dual-Theme UI (Tools-first)

1) Theme system (light + dark, enterprise palette)
- Define tokenized color system with deep blue primary and teal accent, neutrals, semantic states; paired dark surfaces/contrast.
- Add lightTheme/darkTheme in `frontend/lib/core/theme/app_theme.dart`, include typography, spacing/elevation, focus rings.
- Introduce `ThemeController` (ChangeNotifier) to toggle/persist ThemeMode; wire `MaterialApp` to theme/darkTheme/themeMode in `frontend/lib/main.dart`.
- Ensure component themes (buttons, inputs, cards, dialogs, chips, table rows) support both modes.

2) App shell layout
- Refine top bar: title/breadcrumb, environment badge, search/command field, theme toggle, primary CTA (Create Tool).
- Tighten left nav (icons+labels, high-contrast active/hover states, compact width).
- Normalize paddings/margins (12–16px grid) across shell.

3) Tools list view (cards primary, table secondary)
- Redesign cards: denser layout, higher contrast, clear meta (params, timeout, updated), action affordances; add optional table view toggle.
- Filter/search bar: type chips, owner/tag filters, sort control; consistent in dark mode.
- Implement table view: sortable columns (Name, Type, Version, Params, Timeout, Updated, Actions) with compact rows.

4) Tool detail experience
- Convert detail panel to tabbed layout (Overview, Parameters, Reliability, Dynamic Vars, History).
- Improve header summary (type badge, version, updated, quick actions).
- Dark-mode-aware code/JSON sections with monospace styling.

5) Tool create/edit dialog
- Densify wizard with left step rail and right content; sticky footer actions.
- Section dividers, compact inputs, inline validation; dark-friendly code editor pane.
- Keep schema-driven form logic; adjust spacing/labels/error states for enterprise look.

6) QA/Polish
- Run `flutter analyze` and quick smoke in both themes.
- Validate contrast and focus states in dark mode.


