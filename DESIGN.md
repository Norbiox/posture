---
name: Posture
description: The Desk drawn as a live architectural section, on drafting vellum in graphite ink.
colors:
  paper: "oklch(96.6% 0.009 92)"
  paper-2: "oklch(93.6% 0.011 92)"
  ink: "oklch(25% 0.012 255)"
  ink-2: "oklch(46% 0.012 255)"
  rule: "oklch(81% 0.012 92)"
  rule-strong: "oklch(62% 0.012 255)"
  pencil: "oklch(53% 0.19 28)"
  pencil-wash: "oklch(93% 0.035 28)"
typography:
  display:
    fontFamily: "Barlow Condensed, Barlow, ui-sans-serif, sans-serif"
    fontSize: "clamp(2.25rem, 7vw, 4.25rem)"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.01em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Barlow Condensed, Barlow, ui-sans-serif, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.02em"
  figure:
    fontFamily: "Barlow Condensed, Barlow, ui-sans-serif, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.33
    fontFeature: "tnum"
  title:
    fontFamily: "Barlow Condensed, Barlow, ui-sans-serif, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    letterSpacing: "0.06em"
  body:
    fontFamily: "Barlow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Barlow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.45
  table-head:
    fontFamily: "Barlow Condensed, Barlow, ui-sans-serif, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    letterSpacing: "0.06em"
  mono:
    fontFamily: "ui-monospace, SF Mono, Menlo, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.625
rounded:
  none: "0px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "32px"
  xl: "40px"
components:
  button:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 14px"
    height: "36px"
  button-hover:
    backgroundColor: "{colors.paper-2}"
  button-solid:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "0 14px"
    height: "36px"
  button-solid-hover:
    backgroundColor: "{colors.ink-2}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 10px"
    height: "30px"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.none}"
    padding: "0 10px"
    height: "30px"
  button-hold:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "56px"
  button-hold-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  button-stop:
    backgroundColor: "transparent"
    textColor: "{colors.pencil}"
    rounded: "{rounded.none}"
    padding: "0 24px"
    height: "56px"
  button-stop-hover:
    backgroundColor: "{colors.pencil-wash}"
  button-stop-moving:
    backgroundColor: "{colors.pencil}"
    textColor: "{colors.paper}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 10px"
    height: "36px"
  tab:
    textColor: "{colors.ink-2}"
    typography: "{typography.body}"
  tab-active:
    textColor: "{colors.ink}"
---

# Design System: Posture

## Overview

**Creative North Star: "The Section Drawing"**

Posture is a sheet of drafting vellum with one drawing on it: a side elevation of the IKEA IDÅSEN Desk, drawn to scale, with Height shown as a dimension line and Presets as level markers. Everything else on the sheet follows drafting conventions too. Hairline rules split the page into regions, tables are ruled schedules, and labels are set in a condensed technical sans with tabular figures. The UI doesn't report the Desk's state. It draws it.

The palette is graphite ink on warm off-white, with one red pencil. The pencil marks only the Desk moving and the Stop control, so when red appears, something physical is happening. Dark mode inverts the vellum (light ink on graphite) and stays neutral rather than turning blueprint navy. Density is high and direct, built for one owner who glances. Nothing is ornamental: no cards, no shadows, no rounded corners, no coloured status badges.

**Key Characteristics:**
- One signature drawing (the IDÅSEN side elevation) carries live state through geometry, line style and one colour.
- 1px hairlines build the whole layout. A full-ink rule opens a region and a pale rule divides inside it.
- Square corners everywhere (radius 0).
- Barlow for running text, Barlow Condensed for headings, figures and table heads, with tabular numerals throughout.
- Red pencil is a signal, never decoration.

## Colors

Warm-neutral vellum and cool graphite, with a single red pencil kept for motion and Stop.

### Primary
- **Graphite Ink** (ink): text, outline buttons, the drawing's linework, full-weight region rules, solid buttons, selected Workdays, focus rings and selection highlight.

### Secondary
- **Red Pencil** (pencil): used only for the Stop button and for the Desk while it moves (desktop outline, dimension line and Height figure all turn pencil). **Pencil Wash** (pencil-wash) is the Stop button's hover fill.

### Neutral
- **Drafting Vellum** (paper): page ground and input fill.
- **Vellum Shade** (paper-2): button hover, the drawing's body fill, the row being edited, and error rows in Logs.
- **Soft Graphite** (ink-2): secondary text, field labels, table heads, disabled text, inactive tabs, the Stance-threshold chain line.
- **Pale Rule** (rule): row dividers, the column divider, ground hatching, quiet-button borders, unselected level lines.
- **Strong Rule** (rule-strong): input borders, unselected Workday cells, scrollbar thumb.

Dark mode redefines all eight tokens under `prefers-color-scheme: dark`, keeping their roles: the paper becomes graphite and the ink becomes vellum. The `.impeccable/design.json` sidecar lists the dark values.

### Named Rules
**The Red Pencil Rule.** Pencil red appears only when the Desk is moving and on Stop. Destructive actions such as Delete use the soft-graphite `button-danger`, not red.

**The Inverted Vellum Rule.** Dark mode inverts ink and paper and keeps the neutrals neutral. It never becomes a blueprint-blue scheme.

## Typography

**Display Font:** Barlow Condensed (fallback Barlow, ui-sans-serif)
**Body Font:** Barlow (fallback ui-sans-serif, system-ui)
**Label/Mono Font:** ui-monospace (Logs only)

**Character:** This pairing reads like technical lettering on a drawing. The condensed cut carries figures and headings. Regular Barlow carries sentences and controls.

### Hierarchy
- **Display** (600, clamp(2.25rem, 7vw, 4.25rem), 1): the live Height figure beside the dimension line. There is exactly one, and it stays large.
- **Headline** (600, 1.5rem, 1, +0.02em): the "Posture" wordmark.
- **Figure** (600, 1.5rem; 1.25rem in Stats; tabular): sitting and standing totals, the Stats date.
- **Title** (600, 0.9375rem, +0.06em, uppercase): section headings such as Next and Today.
- **Body** (400, 1rem, 1.45): running text, table cells, inputs. Tabs are body at 0.9375rem, weight 500.
- **Label** (400, 0.8125rem, soft graphite): field labels above inputs.
- **Table head** (500, 0.8125rem, +0.06em, uppercase, soft graphite): ruled-schedule column heads.
- **Mono** (12.5px, 1.625): Logs lines only.

### Named Rules
**The Tabular Figure Rule.** Every number (Height, times, durations, Preset heights) uses tabular numerals. Times and heights inside tables use the condensed face.

## Layout

The page is a single column capped at max-w-6xl (72rem), with a 16px side gutter that grows to 24px at 640px and up. The top bar is one ink rule. The active tab's 2px underline sits on that rule, and the status line (Connection and Paused state) moves to the top on phones. On Control at 1024px and up, the sheet splits 7:5. The drawing and its controls sit on the left. The Next and Today panels sit on the right, behind a pale vertical rule with 40px padding. Below 1024px the drawing stacks above the tables. Settings uses two columns at 1024px and up.

Rhythm: 4px between a label and its field, 8px between related controls, 16px from a region's opening ink rule to its content, and 32 to 40px between regions. Stats gives one plot (340px tall) the full width between two ink rules.

### Named Rules
**The Hairline Sheet Rule.** Regions are formed by 1px rules, never by boxes. An ink rule opens a region (border-t ink plus 16px of padding), and pale rules divide rows inside it.

## Elevation & Depth

The system is completely flat. It has no box-shadows and no tonal layering for depth. Hierarchy comes from rule weight (ink vs pale), fill (paper vs paper-2) and type weight. The only "depth" is the drawing's own line conventions: hidden-line dashes for an unknown state and a chain line for a datum.

### Named Rules
**The Flat Sheet Rule.** Nothing floats. There are no shadows, cards, overlays or blur. A state change shows up as a fill swap (paper-2 or ink) or a line-style change.

## Shapes

All corners are square: the theme resets every radius (`--radius-*: initial`). Borders are 1px. The only other strokes are the drawing's 1.5px ground line, its 2px dimension ticks and the tab's 2px underline. Inline SVG icons are drawn the same way as the drawing, as 1.5px outlined triangles and chevrons with miter joins and a filled square for Stop. Level markers are inverted triangles: outlined when idle and filled ink for the current Preset.

## Components

### Buttons
- **Shape:** square (0), 1px ink border, 36px minimum height, 14px horizontal padding, weight 500.
- **Default (outline):** transparent fill with ink text and border. On hover the fill becomes vellum shade. Background and colour transition over 120ms ease-out.
- **Solid:** ink fill with paper text, softening to ink-2 on hover. Used for the primary save action in a form, and for "Resume Automations" while paused.
- **Quiet:** pale-rule border, for secondary row actions and Stats navigation.
- **Danger:** soft-graphite text and pale border that go to full ink on hover. Danger is shown by wording, not red.
- **Small:** 30px tall, 10px padding, 0.875rem text.
- **Disabled:** pale border, soft-graphite text, not-allowed cursor, no hover.
- **Focus:** a global 2px ink outline, offset 2px.

### Hold and Stop
Hold-to-move Up and Down are 56px outline buttons that fill solid ink while pressed (`touch-none`, no context menu). Stop is a 56px button that is always visible and always enabled. It has a pencil border and pencil text, pencil-wash on hover, and becomes solid pencil with paper text while the Desk moves.

### Inputs / Fields
- **Style:** paper fill, 1px strong-rule border, square, 36px tall, 10px padding, tabular numerals. The label sits 4px above the input in 0.8125rem soft graphite.
- **Hover:** the border goes to ink. **Focus:** the global ink outline.
- **Errors:** a 1px ink box with weight 500 text and `role="alert"`, with no red.

### Ruled Schedule (tables)
These are collapsed tables with no box. The head row is condensed uppercase soft-graphite text over an ink rule, and body rows are separated by pale rules. Text is left-aligned and the last column is right-aligned. The next row is set semibold. Paused rows go soft graphite with line-through.

### Segmented Cells (Workdays)
These are adjacent square cells (36px, 1px gap) with a strong-rule border. A checked cell is solid ink with paper text.

### Navigation
Text tabs sit on the header's ink rule. Inactive tabs are soft graphite with a transparent 2px bottom border. The active tab is ink with a 2px ink underline. On phones the tab row scrolls horizontally with the scrollbar hidden. Connection status uses a 10px circle, filled when connected and dashed and hollow when disconnected. "Paused today" is a 1px ink-bordered tag.

### Desk Elevation (signature)
This is a to-scale side view of the IKEA IDÅSEN in a 600×400 viewBox at 2.6px per cm, with the floor at y=380. The parts are a floor beam with two end pads, two diagonal struts, three round column stages standing on the beam (the middle stage travels half as far as the top stage), an under-top bracket, a front paddle and an 80×3 cm desktop. The parts are filled paper-2 and stroked ink.
- **Ground:** a 1.5px ink line with pale 45° hatching at a 10px pitch.
- **Dimension line:** runs from the floor to the desktop at the left, with 2px 45° architectural ticks. The display Height figure sits beside it in HTML (so it stays readable at phone width), with the unit beneath: "cm", "cm, moving" or "last known, cm".
- **Level markers:** one per Preset on the right. Each has a pale level line and an inverted-triangle marker, with a clickable label made of the condensed "+height" and the underlined Preset name. The current Preset gets a filled marker, an ink-2 line and semibold text. Labels push apart by at least 32px, while the markers stay on their true level.
- **Stance threshold:** a full-width chain line (dash 14 4 2 4) in ink-2, labelled "Standing from ...".
- **States:** while moving, the desktop outline, dimension line and figure turn pencil. While disconnected, the Desk's linework switches to hidden-line dashes (5 4).
- **Motion:** the desktop and stages move with transforms over 280ms linear. With `prefers-reduced-motion`, nothing animates.

### Stats Plot
A uPlot chart with a stepped ink line at 1.5px, the threshold as the same chain dash in ink-2, pale grid and ticks, 12px Barlow axis text, and a drag selection tinted with 9% ink. Daily bars are solid ink for standing time, stacked on an outlined paper-2 block for sitting time.

## Do's and Don'ts

### Do:
- **Do** build regions from 1px rules: an ink rule opens a region and pale rules divide within it.
- **Do** keep every corner square and every surface flat.
- **Do** use drafting conventions for state: chain line for a datum, hidden-line dashes for unknown, filled versus outlined triangles for current versus other.
- **Do** set every number in tabular figures, and use the condensed face for figures and headings.
- **Do** keep Stop visible and enabled at all times, in pencil.
- **Do** keep the Desk drawing true to the IDÅSEN side profile and to scale (2.6px per cm).

### Don't:
- **Don't** use pencil red for anything except the Desk moving and Stop, and that includes destructive actions.
- **Don't** add shadows, cards, rounded corners or coloured status badges.
- **Don't** make dark mode blueprint navy. Invert the vellum instead.
- **Don't** shrink or remove the large Height figure.
