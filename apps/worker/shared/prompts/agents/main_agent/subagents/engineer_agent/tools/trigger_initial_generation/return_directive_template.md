BUILD INSTRUCTION — START THE BUILD NOW

The user confirmed building the app. Side effects already in motion:
- Logo generation: in progress (will appear at product.logo)
- Prototype preview: in progress (will appear in the App Preview tab)
- State: INITIAL_GENERATION_STARTED

[CRITICAL TIME CONSTRAINT — MVP APP IN 10 MINUTES]:
You have a maximum of 10 minutes to ship a **working MVP app** — the real product the user asked for — not to call completion on an empty app or a marketing landing page alone.

**MVP minimum (required before `complete_initial_generation(status="success")`):**
1. **Working MVP app** — functional UI, configurables-driven branding, primary user journey that makes preview feel like "this is what I need."
2. **Core P0 feature(s)** from the brief / implementation plan — wired and usable end-to-end, not stubbed.
3. **NOT enough:** template shell, empty routes, or a static brochure/landing page with no interactive core feature.

**Defer to future goals (Partner creates via create_goal / detail_goal / create_proposal_goals):**
- Polish, extra pages, admin panels, analytics, nice-to-haves, and any feature beyond the P0 slice above.

If time runs out approaching the limit:
1. Do NOT bail out with an empty template — sprint core app flow + P0 first.
2. `app_runtime_checker` — fix blocking errors; never leave the app broken.
3. commit+push, then `complete_initial_generation`.
4. Return to Partner: **Completed:** (MVP shipped) + **Not completed (Partner should create goals):** (deferred work).

Forbidden: `complete_initial_generation(status="success")` when no core P0 feature works or the result is only a landing page with no app functionality.

Build the full application using these instructions. Use Read/Write/Edit/Bash/Glob/Grep
directly on the workspace cwd.

# CONFIGURABLES MODULE — MANDATORY, NON-NEGOTIABLE:
This repository includes a pre-built configurables module at `app/modules/configurables/`.
**You MUST read `app/modules/configurables/RULES.md` FIRST before writing ANY code.**

The whole purpose of this template is that app owners can customize their app WITHOUT code changes — entirely through the configurables module.
If you hardcode ANY value that could differ between two app instances, you are defeating the purpose of this system.

## What MUST go through `useConfigurables()` — NO EXCEPTIONS:
- **Branding**: app name (required), tagline, description, slogan, about text
- **Colors**: primary color (Required), secondary color (Required), accent color (Required), background colors, surface colors, text colors, header/footer background colors
- **Images**: logo, hero image, banner image, favicon, OG image, gallery images
- **Text/Copy**: section headings, CTA button labels, placeholder texts, footer text, welcome messages, onboarding copy
- **Simple data**: menu/section items, category names, feature lists, navigation labels, social media links, contact info, business hours, addresses
- **Feature flags**: toggles like "show testimonials section", "enable dark mode", "show pricing"
- **Layout config**: number of items per row/page, default sort order, default language

If a value appears in the UI and could be different for another app owner — it belongs in the schema, not in your code.

## How to use:
1. Add the field to `configurableSchemas.formSchema` in `configurables.schema.ts` (see RULES.md §5 for all 11 field types: string, number, boolean, object, array, color, url, enum, datetime, file, files)
2. Add matching default to `defaultConfigurablesData` in `configurables.default.ts`
3. Add matching type to `TDefaultConfigurableData`
4. Consume via `useConfigurables()` hook — `<ConfigurablesProvider>` is already in `root.tsx`
5. Always handle `loading` state to prevent SSR hydration mismatch

The existing schema has: `appName` (string), `logoUrl` (url), `brandColor` (object with primary/secondary/accent). Extend it for ALL your app's owner-facing values.

## VIOLATION CHECK — ask yourself before writing any component:
"Am I hardcoding a string, color, image URL, or section content that the app owner might want to change?"
If YES → add it to the schema and read it from `useConfigurables()`.
If you skip this, the middle editor in the portal will be empty and the owner cannot customize their app.

# SCAFFOLD DISCOVERY (MANDATORY FIRST STEP):
1. Use the `search_scaffolds` tool to search for relevant scaffolds based on the product requirements.
2. For EVERY scaffold found, call `inject_scaffold(slug=<slug>)` to vendor it into the workspace.
   - `inject_scaffold` is NOT a high-level codegen tool — it is a filesystem operation that clones
     and wires the scaffold. You MUST call it directly, do not skip or replace it with manual file writing.
3. Immediately after EACH `inject_scaffold` call, do integration work for that scaffold:
   - Read `app/modules/<slug>/README.md` first (and any usage docs inside that module).
   - Wire the scaffold into the current app code so it is actually used by runtime behavior.
   - Adjust existing code as needed (routes, pages, providers, handlers, or feature flow wiring) to utilize the scaffold.
4. Verify each injected scaffold is utilized before completion.
   - If a scaffold is injected but still unused, continue integrating and do NOT finish yet.
5. Only write code manually for parts that have no matching scaffold.

# MODULE FOLDER RULES (MANDATORY):
- Do NOT manually create any new top-level folder under `app/modules/*` (for example `app/modules/new-module`).
- Top-level `app/modules/<slug>` folders must be created only by `inject_scaffold`.
- You MAY edit files and add subfolders inside an injected module (`app/modules/<slug>/*`) as needed for integration/composability.
- If you need a brand-new non-scaffold area, create it outside `app/modules/*` (for example under `app/*` directly).

CRITICAL: After finish code generation, call `app_runtime_checker` tool first, to ensure the codegen not leaving any runtime error.

# IMPLEMENTATION PLAN — CORE FEATURES

The build node's `implementation_plan` field contains a list of core feature goals
pre-defined during the Dream Preview phase. These are the COMPOSITE milestones
you MUST implement. The Partner agent has already marked them as `IN_PROGRESS`.

**Before building**, read the build node's `implementation_plan` via the
`get_detail_goal` tool (or ask Partner for the plan). Each entry follows this format:
```
# Finish These Core Features First:
1. <Goal Title> | Node_ID: <mongodb_id>
2. <Goal Title> | Node_ID: <mongodb_id>
...
```

Implement ALL listed core features. Each corresponds to a real Goal node in the
goal system that tracks progress.

# RETURN FORMAT — REQUIRED

After calling `complete_initial_generation`, you MUST return a structured summary
to the Partner agent that includes:

```
finished_goals:
  - Node_ID: <mongodb_id> — <goal title> (completed)
  - Node_ID: <mongodb_id> — <goal title> (completed)

unfinished_goals:
  - Node_ID: <mongodb_id> — <goal title> (reason: <why not finished>)
```

If ALL core features were completed, `unfinished_goals` can be empty.

Tell the Partner agent: "Please update the goal statuses using
`mcp__qb-partner__update_goal_status` — mark finished goals as DONE
and unfinished goals as PENDING."

CRITICAL: After you finish building, you MUST call `complete_initial_generation`
with status ('success' or 'failure') and a brief summary. The completion tool
fires confetti and other side effects, then returns control to PARTNER who
will deliver the celebratory message to the user.
Do not call `complete_initial_generation(status="success")` until injected scaffolds are actually utilized in the app flow.

APP PREVIEW RESTRICTION DURING INITIAL GENERATION:
- You are currently running the first initial generation. You MUST NEVER call any app preview tools (`reload_app_preview`, `get_app_preview_status`, `get_app_preview_logs`) during this initial build process.
- The `complete_initial_generation` tool will automatically initialize the preview server and perform the final push for you once called.
- Calling preview tools during initial generation is strictly forbidden as the preview environment is not finalized yet.


