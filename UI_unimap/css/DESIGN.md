---
name: Flat Academic Guidance
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#434655'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#747686'
  outline-variant: '#c4c5d7'
  surface-tint: '#2151da'
  primary: '#0037b0'
  on-primary: '#ffffff'
  primary-container: '#1d4ed8'
  on-primary-container: '#cad3ff'
  inverse-primary: '#b7c4ff'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#3d445a'
  on-tertiary: '#ffffff'
  tertiary-container: '#545c72'
  on-tertiary-container: '#cdd5ef'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b7c4ff'
  on-primary-fixed: '#001551'
  on-primary-fixed-variant: '#0039b5'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#dae2fd'
  tertiary-fixed-dim: '#bec6e0'
  on-tertiary-fixed: '#131b2e'
  on-tertiary-fixed-variant: '#3f465c'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display:
    fontFamily: Be Vietnam Pro
    fontSize: 3rem
    fontWeight: '700'
    lineHeight: 3.5rem
    letterSpacing: -0.02em
  display-mobile:
    fontFamily: Be Vietnam Pro
    fontSize: 2rem
    fontWeight: '700'
    lineHeight: 2.5rem
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 2rem
    fontWeight: '700'
    lineHeight: 2.5rem
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Be Vietnam Pro
    fontSize: 1.5rem
    fontWeight: '700'
    lineHeight: 2rem
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Be Vietnam Pro
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: '0'
  title-md:
    fontFamily: Be Vietnam Pro
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.625rem
    letterSpacing: '0'
  body-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 1.125rem
    fontWeight: '400'
    lineHeight: 1.75rem
    letterSpacing: '0'
  body-md:
    fontFamily: Be Vietnam Pro
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: '0'
  body-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
    letterSpacing: '0'
  label-md:
    fontFamily: Be Vietnam Pro
    fontSize: 0.875rem
    fontWeight: '600'
    lineHeight: 1.25rem
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 0.75rem
    fontWeight: '600'
    lineHeight: 1rem
    letterSpacing: 0.02em
  data-metric:
    fontFamily: Be Vietnam Pro
    fontSize: 1.5rem
    fontWeight: '700'
    lineHeight: 1.75rem
    letterSpacing: -0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system is tailored for an AI-driven academic advisory platform supporting grade-12 students navigating university and major selections. The emotional posture balances institutional authority with accessible clarity: reliable, objective, stress-reducing, and forward-looking.

### Design Style: Pure Flat & Data-First
- **Absolute Flatness:** No gradients, no frosted glass, no heavy ambient drop shadows, and no decorative skeuomorphism. 
- **Structural Integrity:** Separation of surfaces and hierarchical weight rely entirely on solid color boundaries, disciplined typography, precise structural outlines (`#E2E8F0`), and pure tonal contrast.
- **Data Legibility:** UI chrome is restrained to allow 5-year historical admission scores, admission probability calculations, and admission quota tiers to stand out unambiguously.

## Colors

The palette employs authoritative solid tones designed to meet strict WCAG 2.1 AA/AAA contrast guidelines, avoiding any optical degradation from blurs or multi-color gradients.

### Core Roles
- **Primary (`#1D4ED8`):** Royal Blue. Used for definitive primary CTAs, active states, key data markers, and focused interactive inputs.
- **Secondary (`#0284C7`):** Sky/Slate Blue. Used for secondary actions, interactive informational chips, and progress indicators.
- **Tertiary (`#0F172A`):** Deep Navy/Slate. Reserved for maximum-contrast headings, primary text, and structural data column headers.
- **Neutral Background (`#F8FAFC`):** Canvas base. Pairs with pure white (`#FFFFFF`) card surfaces to maintain crisp architectural hierarchy.
- **Neutral Stroke (`#E2E8F0`):** Hairline borders establishing component boundaries without visual clutter.

### Functional Academic Probability Tiers (SRS Standard)
Admission recommendation cards and badges strictly conform to a three-tier semantic color system:
- **Safe Tier ($p \ge 0.80$):** Text/Border `#16A34A`, Solid Surface `#DCFCE7`. Denotes low-risk choices based on 5-year trend analysis.
- **Target Tier ($0.40 \le p < 0.80$):** Text/Border `#D97706`, Solid Surface `#FEF3C7`. Denotes realistic, competitive alignment.
- **Reach / Ambition Tier ($p < 0.40$):** Text/Border `#DC2626`, Solid Surface `#FEE2E2`. Denotes high-stretch choices requiring strong exam execution.

## Typography

**Be Vietnam Pro** is selected across all roles to ensure native Vietnamese diacritics render with exact optical balance and zero vertical alignment clipping.

### Hierarchy & Data Formatting
- **Display & Headlines:** Set in bold and semi-bold weights with negative letter-spacing for sharp, editorial precision in overview dashboards and admission calculators.
- **Data Metric Level:** Dedicated exclusively to score benchmarks, historical point cutoffs (e.g., `27.45`), and percentile deltas. Numbers must be rendered with tabular figures (`font-variant-numeric: tabular-nums`) to ensure vertical alignment across five-year historical comparison tables.
- **Labels & Microcopy:** Used for metadata tags, tier indicators, and input field descriptors with enhanced tracking for readability at small sizes.

## Layout & Spacing

The system relies on a responsive 12-column grid system built around a strict 8px spacing rhythm. 

### Breakpoints & Viewport Reflow
- **Desktop (1200px+):** 12 columns, `margin: 2rem`, `gutter: 1.5rem`. Split view layouts: left-hand parameter controls (combination of subjects, simulated scores) occupy 4 columns; right-hand analytical recommendations and 5-year trend cards occupy 8 columns.
- **Tablet (768px - 1199px):** 8 columns, `margin: 1.5rem`, `gutter: 1.25rem`. Control bars collapse into structured horizontal filter trays above data listings.
- **Mobile (< 768px):** 4 columns, `margin-mobile: 1rem`, `gutter-mobile: 1rem`. Multi-year comparison charts and comparison cards stack vertically; tables switch to compact card lists with horizontal sub-metrics.

### Spacing Rules
- Use `space-xs` (4px) and `space-sm` (8px) for micro-gap alignments: badge contents, icon-to-label offsets, and inline status indicators.
- Use `space-md` (16px) for interior card padding and form field grouping.
- Use `space-lg` (24px) for card body separation and table cell breathing room.
- Use `space-xl` (40px) exclusively for primary section breaks on the dashboard canvas.

## Elevation & Depth

This design system adheres to a strict flat architecture. Shadows and blurred trans-surfaces are entirely prohibited.

### Tonal Hierarchy & Outlines
1. **Base Layer (Canvas):** Solid `#F8FAFC`. Provides a cool, light grey foundation that eliminates glare during long study sessions.
2. **Container Layer (Cards & Surfaces):** Solid `#FFFFFF`. High contrast against the canvas, explicitly framed by a 1px solid `#E2E8F0` border.
3. **Interactive Hover & Focus:** No floating elevation. Hover states trigger a stroke transition from `#E2E8F0` to `#1D4ED8` (or `#0284C7`), paired with an optional light fill shift (`#F1F5F9`).
4. **Modals & Overlays:** Solid white dialogs framed with a 2px `#0F172A` border and placed over a flat, unblurred `#0F172A` scrim at 40% solid opacity.

## Shapes

The geometric personality is defined by crisp, structured corners (`roundedness: 1` / Soft). This avoids both the clinical austerity of razor-sharp rectangles and the overly informal toy-like appearance of large circular radii.

### Border Radius Rules
- **Micro Elements (Chips, Checkboxes, Indicators):** `0.25rem` (4px).
- **Standard Controls (Inputs, Buttons, Dropdowns):** `0.25rem` (4px).
- **Surface Containers (Major Cards, Score Panels, Tables):** `0.5rem` (8px, `rounded-lg`).
- **Modal Containers & Main View Banners:** `0.75rem` (12px, `rounded-xl`).
- **Pills / Circles:** Permitted only for circular step numbers and avatar icons. Chips and pill badges must remain rectangular with `0.25rem` radius.

## Components

### Buttons
- **Primary:** Solid `#1D4ED8` background, `#FFFFFF` text, 0px shadow, `rounded: 0.25rem`. Hover state: `#1E40AF`. Active state: `#1E3A8A`.
- **Secondary / Outline:** Background transparent, 1.5px solid `#1D4ED8`, text `#1D4ED8`. Hover state: solid `#EFF6FF`.
- **Ghost / Tertiary:** Background transparent, text `#0F172A`. Hover: `#F1F5F9`.

### Chips & Semantic Tier Badges
Flat status labels classifying admission chance tiers:
- **Safe Tag:** Background `#DCFCE7`, border 1px solid `#16A34A`, text `#16A34A`, font weight 600.
- **Target Tag:** Background `#FEF3C7`, border 1px solid `#D97706`, text `#D97706`, font weight 600.
- **Reach Tag:** Background `#FEE2E2`, border 1px solid `#DC2626`, text `#DC2626`, font weight 600.
- Padding: `0.25rem 0.5rem`, `rounded: 0.25rem`.

### Form Controls (Inputs, Selectors, Radios)
- **Input Fields:** Flat `#FFFFFF` surface, 1px solid `#CBD5E1` border, `rounded: 0.25rem`. Focus: 2px solid `#1D4ED8`, outline none.
- **Subject Combination Multi-select:** Tags with clear 'x' buttons inside an outlined container; no gradient dropdowns.
- **Checkboxes & Radios:** Sharp geometry (`0.25rem` radius for checkboxes; full round for radio dots), solid `#1D4ED8` fill when selected, `#CBD5E1` unchecked border.

### Recommendation Cards
- Structure: 1px solid `#E2E8F0` on white background, `rounded: 0.5rem`.
- Header: School logo placeholder, University code (`e.g., QHI`), Major name in `headline-sm`, followed by the probability chip (`Safe`, `Target`, or `Reach`).
- Data Matrix: A 5-column inline comparison grid showing historical cutoff marks from 2021 through 2025. The current candidate's score is visually pinned against historical medians via high-contrast solid lines without blur.

### 5-Year Data Visualization & Tables
- **Score Trend Blocks:** Solid step-line graphs or tabular numeric grids. Lines must be 2px solid primary or semantic colors; no fill gradients beneath lines.
- **Table Grids:** Explicit horizontal borders (`1px solid #E2E8F0`), alternating zebra row backgrounds (`#FFFFFF` to `#F8FAFC`) to maximize scan speed across dense tabular data.