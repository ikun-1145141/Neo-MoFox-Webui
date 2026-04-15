# Design System Specification: Editorial Precision

## 1. Overview & Creative North Star
### Creative North Star: "The Curated Canvas"
This design system reimagines the foundational elements of the iconic brand—simplicity, utility, and color—through an editorial lens. We are moving away from the "utility-first" appearance of early web design toward a "High-End Editorial" experience. 

The goal is to move beyond the grid-heavy, boxed-in layouts of the past. By leveraging intentional asymmetry, expansive white space, and sophisticated tonal layering, we create a UI that feels like a premium digital publication. This system is defined by its "Curated Canvas" approach: every element is given the breath it needs to be seen, ensuring the interface remains approachable yet undeniably high-end.

---

## 2. Colors
Our palette utilizes a sophisticated expansion of the classic primary tones, balanced by a wide range of neutral surfaces that provide depth without noise.

### The "No-Line" Rule
**Strict Mandate:** Standard 1px solid borders for sectioning are prohibited. 
In this design system, boundaries are defined by the collision of surfaces. Use background shifts (e.g., a `surface-container-low` section abutting a `surface` background) to define the edge of a workspace. This creates a seamless, modern flow that mimics high-end interior architecture.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like stacked sheets of fine paper. 
- **Base Level:** `surface` (#f7f9ff)
- **Nested Depth:** Place a `surface-container-lowest` (#ffffff) card on a `surface-container-high` (#e5e8ee) background to create a crisp, natural lift.
- **Glassmorphism:** For floating modals or navigation bars, utilize `surface-variant` with a 70% opacity and a `backdrop-blur(20px)` effect. This ensures the colorful accents of the background bleed through subtly, softening the digital edge.

### Signature Textures
Avoid flat blocks of color for high-impact areas. For primary CTAs or hero sections, use a subtle linear gradient transitioning from `primary` (#0058bd) to `primary_container` (#2771df) at a 135-degree angle. This provides a tactile "soul" to the component that flat hex codes cannot achieve.

---

## 3. Typography
The typography system pairs the geometric authority of **Plus Jakarta Sans** with the functional clarity of **Inter**.

*   **Display & Headlines (Plus Jakarta Sans):** These are the "editorial" voices. Use `display-lg` (3.5rem) and `headline-lg` (2rem) with generous letter spacing (-0.02em) to command attention. They represent the brand's modern confidence.
*   **Body & Titles (Inter):** These are the "narrative" voices. `body-lg` (1rem) provides a comfortable reading rhythm, while `title-md` (1.125rem) serves as the perfect anchor for sub-sections.
*   **The Hierarchy:** High contrast in scale is encouraged. Pair a `display-md` headline directly with a `body-sm` label to create an asymmetrical, sophisticated layout that breaks the visual monotony.

---

## 4. Elevation & Depth
Elevation is achieved through light and tone, not structural lines.

*   **The Layering Principle:** Instead of a shadow, place a `surface-container-lowest` element inside a `surface-container` background. The slight shift in brightness creates an organic sense of elevation.
*   **Ambient Shadows:** For floating elements (menus, floating action buttons), use "Ambient Light" shadows. 
    *   *Values:* `0px 20px 40px rgba(24, 28, 32, 0.06)`
    *   Note how the shadow color is a low-opacity tint of the `on-surface` color (#181c20), making it feel like part of the environment.
*   **The Ghost Border Fallback:** If a border is required for extreme accessibility needs, use `outline-variant` (#c2c6d5) at 15% opacity. Never use 100% opaque borders.
*   **Roundedness:** Embrace the `xl` (3rem) and `full` (9999px) roundedness tokens for buttons and containers to maintain the "approachable" and "modern" brand profile.

---

## 5. Components

### Buttons
*   **Primary:** High-pill shape (`full`), using the signature gradient (`primary` to `primary_container`). White text.
*   **Secondary:** `surface-container-highest` background with `on-surface` text. No border.
*   **Tertiary:** `tertiary` (#b51b15) text on a transparent background. Use only for destructive or high-alert actions.

### Cards
*   **Mandate:** Zero borders. Zero dividers. 
*   **Separation:** Use a `1.5rem` (`md`) padding and separate cards using vertical white space.
*   **Interaction:** On hover, shift the background from `surface-container-low` to `surface-container-highest` and apply a subtle Ambient Shadow.

### Input Fields
*   **Style:** Minimalist underline or soft-filled container (`surface-container-low`).
*   **Focus State:** The label should transition to a `primary` (#0058bd) color, and the "Ghost Border" becomes 100% opaque `primary`.

### List Items
*   Avoid the "Horizontal Rule" (HR) line. Group list items by proximity. If a separator is needed, use a 4px vertical gap with a subtle background color change on every second item (zebra striping at 2% opacity).

---

## 6. Do's and Don'ts

### Do
*   **DO** use white space as a structural element. If a layout feels crowded, double the padding.
*   **DO** lean into the multi-color palette for functional accents (e.g., a `secondary` green for success, `tertiary` red for errors).
*   **DO** use `plusJakartaSans` for all large-scale headings to ensure the premium editorial feel.

### Don't
*   **DON'T** use 1px solid black or grey borders. This immediately destroys the "high-end" aesthetic.
*   **DON'T** use standard drop shadows (e.g., `0px 2px 4px`). They feel dated and "heavy."
*   **DON'T** trap content in boxes. Let the typography and background shifts define the space.
*   **DON'T** use `Arial` unless as a system fallback. Rely on the specified typography scale for all intentional design.