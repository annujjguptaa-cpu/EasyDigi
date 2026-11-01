# DocFlow Design System: 'Precision Instrument on Paper'

## 1. Design Direction
Editorial, technical, calm and trustworthy. Uses warm paper tones, razor-thin hairlines, numbered stages, and a single black action button per view.

---

## 2. Design Tokens
Created in `/packages/ui/src/tokens/tokens.css` and mapped into `apps/web/tailwind.config.js`:

| Token | Light Value | Dark Value (Ink-on-Charcoal) | Usage |
|---|---|---|---|
| `--bg-paper` | `#F5F1E8` | `#14130F` | Page background |
| `--bg-surface` | `#FBF9F4` | `#1E1D19` | Cards, panels, input surfaces |
| `--ink-primary` | `#14130F` | `#EDE8DB` | Primary text and headings |
| `--ink-muted` | `#6B675C` | `#A8A396` | Captions, metadata, subtitles |
| `--border-hairline` | `#D9D3C5` | `#2E2C26` | 1px border dividers |
| `--status-verified` | `#2B44D6` | `#6C82FF` | Verified document state |
| `--status-flagged` | `#D9531E` | `#F07E4C` | Mismatches / Anomaly flags |
| `--status-missing` | `#A8A396` | `#7C776D` | Missing document items |
| `--status-error` | `#B3261E` | `#E5534B` | Errors / Denials |
| `--status-success` | `#2E7D4F` | `#4EAD73` | Completed / Approved status |

---

## 3. Djinn Wish Pack Vocabulary Table

| Concept | Traditional Bank Term | Djinn Wish Pack Term | Placement & Rules |
|---|---|---|---|
| **Lending Request** | Bank Request / Case | **Wish** | Titles, badges, metadata rows |
| **Summon Action** | Create / Send Request | **SUMMON YOUR DJINN** | Single black action button |
| **Customer Link** | `/share/{token}` | **`/wish/{token}`** | Single-use signed URL (alias `/share` redirects) |
| **Agent Working** | Processing... | **Djinn is working...** | Fading mono status element |
| **File Completion** | Approved / Done | **Your wish is granted** | Completion headline with mono ref |
| **Customer Footer** | DocFlow Footer | **Powered by Djinn** | Subdued hairline footer strip |
| **Home Loan** | Home Loan | **Foundation Wish** | Topic mapping with required documents |
| **Education Loan** | Student Loan | **Scholar Wish** | Topic mapping with required documents |
| **Personal Loan** | Unsecured Loan | **Opportunity Wish** | Topic mapping with required documents |
| **Business Loan** | Commercial Loan | **Growth Wish** | Topic mapping with required documents |
| **Section Stages** | 01 REQUEST... | **01 WISH, 02 DOCUMENTS, 03 CHECKS, 04 DEPARTMENTS, 05 VERDICT** | Numbered mono headers |

> [!CAUTION]
> **Safety Rule**: Consent specifications, legal notices, and deterministic rejection explanations **ALWAYS** remain in plain literal language. Never use Djinn slang inside legal or consent sentences.

---

## 4. Screen Showcase
Visit `/design` to inspect all components in light and dark mode.
