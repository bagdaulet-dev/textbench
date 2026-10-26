# Textbench workspace design

A focused editing desk for writers and developers. The main job is to inspect,
clean up, and keep track of short text without building an account system.

## Tokens

- Canvas #f2f5fa, surfaces #ffffff, ink #182b43, primary #315be8,
  secondary #137568, separators #dce4ef.
- Trebuchet MS for headings; system sans-serif for controls; Georgia for the
  editor. Local fonts keep the workspace independent of external font services.
- Left aligned content, roomy editor, a quieter results column, 44px touch
  targets, clear focus, and no decorative motion.

## Layout

```text
Brand                    Editor / Tools / History          API guide

A little clarity, for every word.            Save only when you choose.

+-----------------------------------------+------------------------+
| Text editor       Import / Example      | Analysis       Export  |
|                                         | words / reading time   |
|                                         | count details          |
| Undo / Clear     Save checkbox / Analyze | frequent-word bars     |
+-----------------------------------------+------------------------+
| Text transformations                    | Result / Copy / Use    |
+------------------------------------------------------------------+
| History   Search          count / Refresh / Delete all             |
| Saved text preview                       Restore / Delete          |
+------------------------------------------------------------------+
```

## Review against the brief

Keep the brand and blue palette so the improvement remains recognizably
Textbench. Replace tiny frequency chips with labelled native progress bars;
keep a single analysis panel rather than a collection of generic metric cards.
A gentle dotted editor surface is functional stationery, not decorative imagery.
The visible improvements earn their space: undo protects drafts, search finds
saved work, export makes results useful, and privacy controls explain storage.

Mobile stacks the editor and results, wraps the tool controls, and gives every
action a comfortable tap target. Errors appear beside the editor. Empty, loading,
unavailable, stale-result, and success states are designed explicitly.
