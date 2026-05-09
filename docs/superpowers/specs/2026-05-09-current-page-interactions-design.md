# YuKit Current Page Interactions Design

## Goal

Complete the visible interactions on the existing YuKit frontend workspace without a broad routing or component architecture rewrite.

The page already exposes controls for command search, theme, help, tags, favorites, run/copy actions, output tabs, options, and recent history. The implementation should make each visible control respond with useful behavior and clear UI state.

## Scope

In scope:

- Command search opens a keyboard-accessible command menu.
- Search filters tools by title, metadata, and tags.
- Tool and command choices switch the active tool.
- Tag chips filter the visible tool list.
- Favorites section shows signed-in favorites, empty state, and a sign-in hint when anonymous.
- Favorite actions update the sidebar and current tool state.
- Help opens a lightweight help popover/dialog explaining the current tool and privacy/history behavior.
- Theme button toggles light/dark/system-style state locally and updates the page class.
- Copy result gives visible success/failure feedback and uses a fallback when Clipboard API is unavailable.
- Recent history items can restore an output/result preview and switch to the matching tool.
- System status can refresh by checking `/api/health`.
- Escape closes overlays; Ctrl/Cmd+K opens command search.

Out of scope:

- Multi-page router, separate history/settings pages, or a component library refactor.
- Schema-driven renderer replacement.
- New backend endpoints.
- New tools.

## Approach

Keep the current single `App.vue` workspace and add focused reactive state plus helper functions. This minimizes churn while making the displayed UI behave like a complete workspace.

The implementation should preserve the current visual direction and avoid changing backend contracts. It may add tests around pure helpers and Playwright coverage around visible UI behavior.

## UX Details

### Command Search

The top search button opens an overlay. The overlay includes a text input, matching tools, and utility commands such as run current tool, copy result, toggle theme, show help, and refresh system status.

Keyboard:

- `Ctrl+K` or `Cmd+K`: open command search.
- `Escape`: close command search or help.
- `Enter` on a highlighted tool or command: execute it.

### Theme

Theme cycles through light, dark, and system. The choice is stored in `localStorage`. The button label or title reflects the next action. CSS uses `data-theme` on the document root.

### Help

Help opens a small popover/dialog with current tool purpose, access mode, run mode, and input storage policy. It should not block ordinary tool usage.

### Tags And Favorites

Tag chips filter the tool list. The active tag is visibly selected. Favorites show in their own section when signed in. Anonymous users see a compact sign-in hint rather than an empty non-functional area.

### History

Recent run items in the options panel are clickable. Clicking one switches to the execution's tool, restores its result into the output panel, sets status/duration, and shows the raw output.

### Feedback

Run, copy, refresh, and favorite actions should surface short status text. Ordinary failures stay inline and preserve input.

## Testing

Add frontend tests for interaction helpers where practical:

- Tool filtering by query and tag.
- Theme cycling and storage value mapping.
- History result serialization.

Add or extend Playwright smoke coverage for:

- Command menu opens from the visible search control.
- Theme button changes document theme.
- Tag chip filters the tool list.

Run `pnpm test` and `pnpm build` after implementation.
