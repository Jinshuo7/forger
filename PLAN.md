# Build Forger as a Codex Video-Preproduction Plugin

## Summary

Create a repository-backed Codex marketplace containing **Forger**, a discoverable skill that turns a rough short-form video idea into a researched, generation-ready audiovisual package.

Forger will guide solo creators through adaptive rounds of at most three questions, generate required final-look storyboard frames, and export model-neutral and provider-specific deliverables. It will prepare assets for Seedance 2.0 and MiniMax Hailuo 03/H3 but will not generate final videos.

## Implementation Changes

### Plugin and documentation

- Structure this repository as a team marketplace with `plugins/forger`, a validated `.codex-plugin/plugin.json`, and an `AVAILABLE` marketplace entry named `forger`.
- Add one discoverable `forge-video` skill with progressively disclosed references for workflow rules, project schema, research standards, visual-board generation, and provider profiles.
- Add `CONTEXT.md` defining canonical terms including Creator, Forger Project, Generation Package, Shot, Generation Clip, Reference Bible, Visual Board, Keyframe, Provider Profile, Approval, Current Artifact, and Stale Artifact. Avoid using “client” as a synonym for Creator.
- Record concise ADRs for:
  1. Codex-hosted plugin instead of a standalone web app.
  2. Model-neutral source artifacts with versioned provider adapters.
  3. Creator-edited artifacts as authoritative, with manifest-based dependency tracking.

### Guided workflow

Implement a resumable phase machine:

1. Create `<workspace>/forger-projects/<slug>/` without overwriting existing projects.
2. Capture minimal intake: idea, purpose, audience, intended channel, duration, aspect ratio, language, required content, references, and constraints.
3. Decide whether research is warranted. For factual, cultural, historical, scientific, product, location, trend, or linked-reference material, prefer primary sources, cite claims inline, separate evidence from inspiration, and expose contradictions.
4. Produce and approve the Creative Brief.
5. Offer one recommended Creative Direction plus two meaningful alternatives; archive rejected directions and reasons.
6. Build and approve the model-neutral Shot Sequence, reference bible, continuity rules, audio plan, dialogue, captions, transitions, and edit notes.
7. Generate a polished keyframe for every Shot at the target aspect ratio. Add start/end frames when transformation, transition, continuity, or provider behavior requires them. Save every approved image inside the project and review the complete sequence as a grid.
8. Approve the Visual Board, validate the entire package, and produce exports only when all four approval hashes are current.

Conflicting requirements must pause the affected milestone, explain the tradeoff, and recommend a concrete resolution. Technical controls use plain-language defaults with expandable expert detail.

### Project artifacts and interfaces

Treat editable Markdown and storyboard images as authoritative content. Use `forger.project.json` only for workflow state and provenance; derive machine exports from the approved artifacts.

The manifest will include:

- Schema version, project identity, language, current phase, timestamps, and selected provider profiles.
- Artifact records containing stable ID, path, type, revision, content hash, dependencies, and `draft | current | stale | approved` status.
- Approval records containing artifact ID, revision, hash, and approval time.
- Research sources and provider-profile verification metadata.

On resume, compare artifact hashes. Creator edits or replaced images increment the affected revision and mark transitive dependents stale without overwriting them. Reconcile clear edits automatically; ask only when an edit creates ambiguity or contradiction.

The canonical package schema will include:

- Project and technical specification.
- Creative Brief and selected Creative Direction.
- Research claims and citations.
- Reference entities for characters, products, locations, props, palette, and style.
- Ordered Shots with timing, purpose, composition, lens/framing, camera motion, subject action, lighting, continuity, transitions, audio, dialogue, captions, and board references.
- Provider-specific Generation Clips linked back to their editorial Shot.
- Assembly and post-production instructions.

Each Generation Clip contains a profile ID, valid duration and format settings, first/last-frame references, localized provider prompt, readable translation, constraints, continuity handoff, and assembly position.

### Exports and provider profiles

- Produce required Markdown, canonical JSON, and visually verified PDF exports.
- Declare Codex’s PDF capability as a required plugin dependency; a failed PDF render or visual verification blocks final completion.
- Include generic, `seedance-2.0-consumer-2026-08`, and `minimax-hailuo-h3-consumer-2026-08` exports.
- Treat Seedance and H3 as version-stamped manual consumer-workflow profiles, not APIs. Verify their current controls during implementation and record sources, verification date, supported inputs, durations, ratios, audio behavior, and prompt conventions.
- Keep editorial Shots independent of provider limits. Adapters split them into provider-valid Generation Clips and add continuity and assembly instructions.
- Run the interview and human documents in the creator’s language, preserve spoken text verbatim, and localize generator prompts to the profile’s preferred language with a readable translation.

## Test Plan

- Validate the skill, plugin manifest, marketplace entry, schemas, references, and absence of scaffold placeholders.
- Unit-test project initialization, collision-safe naming, manifest migration, hashing, transitive staleness, approvals, clip segmentation, schema validation, and deterministic exports.
- Forward-test in isolated workspaces with:
  - A wholly fictional 15-second vertical concept that correctly skips research.
  - A factual 60-second concept with primary-source citations and conflicting evidence.
  - A multilingual video preserving dialogue while localizing provider prompts.
  - An impossible duration/story-beat request that blocks with a recommended correction.
  - Manual document and image edits followed by manifest-driven resume.
  - Recurring characters/products requiring reference preservation and conditional endpoint frames.
  - Seedance 2.0 and H3 fixtures that reject unsupported or unverified controls.
  - Missing or malformed artifacts, interrupted image generation, stale approvals, and PDF-render failure.
- Acceptance requires no more than three related questions per round, four current approvals, one approved frame per Shot, every Shot mapped to valid Generation Clips, traceable factual claims, successful Markdown/JSON/PDF output, and no final-video submission.

## Assumptions and Defaults

- Version `0.1.0`, marketplace category `Creativity`, installation `AVAILABLE`, authentication `ON_INSTALL`, and no product gating.
- Short-form scope is 5 seconds through 3 minutes across marketing, social, music, explainer, and narrative uses.
- Codex supplies conversation, web research, built-in image generation, and PDF tooling through the creator’s eligible environment; Forger stores no external credentials.
- V1 excludes a standalone web app, hosted accounts, billing, direct video generation, video-job management, and multi-user collaboration.
