---
name: forge-video
description: Create or continue a collision-safe Forger Project for planning a short-form video. Use when a Creator wants to develop a video idea, plan shots, or prepare generation-ready materials without submitting a final video-generation job.
---

# Forge Video

Create or resume the Forger Project, then guide the Creator through the Creative Brief, Creative Direction, and Shot Sequence Milestones:

1. Use the current workspace unless the Creator selected another workspace. For a new project, choose a short name and run `python3 scripts/forge_video.py --workspace <workspace> --name <project-name>` relative to this file.
2. Gather only unknown intake fields in focused, related rounds of at most three questions. The required fields are idea, purpose, audience, channel, duration, aspect ratio, language, required content, references, and constraints. Do not repeat a known answer. After each round run `python3 scripts/forge_video.py intake --project <projectPath> --answers '<json-object>'`.
3. Decide whether research is warranted. Fictional concepts without factual, cultural, historical, scientific, product, location, trend, or linked-reference claims use `not-warranted`; do not perform research for them. For warranted research, separate Research Claims and citation references from Evidence and Inspiration, and expose Material Contradictions and their resolution state.
4. Create the reviewable brief with `python3 scripts/forge_video.py brief --project <projectPath> --research-disposition not-warranted`, or pass the complete stable research object with `--research '<json-object>'`. Present `artifacts/creative-brief.md` to the Creator.
5. Ask explicitly whether the Creator approves that exact Creative Brief. Rejection or silence does not advance the Milestone. Record acceptance with `python3 scripts/forge_video.py approve --project <projectPath> --creator-approved`. Pass every additional eligibility problem with a repeated `--blocker`; approval advances only when the complete blocker set is empty.
6. Develop exactly three Creative Directions with one recommendation. Make them meaningfully distinct treatments: vary the story engine or structure and the visual grammar, then state each difference in non-empty narrative and aesthetic axes. A paraphrase, renamed motif, or palette swap is the same direction and must be reworked. Record the three with `python3 scripts/forge_video.py directions --project <projectPath> --directions '<json-array>'`, then present all three together.
7. Ask the Creator to select one direction and explain each rejection. Record the decision with `python3 scripts/forge_video.py select-direction --project <projectPath> --selected <direction-id> --rejection-reasons '<json-object>'`. Preserve prior rejection history when a rejected direction is later reconsidered. Ask for Approval of the selected Artifact and record it with `python3 scripts/forge_video.py approve --project <projectPath> --artifact <direction-id> --creator-approved`.
8. Build a Reference Bible with stable entity IDs, then author a provider-neutral Shot Sequence. Every Shot supplies identity, duration in seconds, purpose, composition, framing, camera motion, subject action, lighting, continuity, transition, audio, dialogue, captions, edit notes, Visual Board references, and Reference Bible entity IDs. Preserve approved dialogue verbatim. Record it with `python3 scripts/forge_video.py shots --project <projectPath> --shots '<json-array>' --reference-bible '<json-array>' --required-story-beat-count <count>`.
9. Treat a timing refusal as a Shot Sequence decision only. Present the arithmetic and concrete correction from the script, revise the timing inputs with the Creator, and leave the approved Creative Brief and Creative Direction untouched. Once feasible, present the complete Shot Sequence and Reference Bible, ask for Approval, and record it with `python3 scripts/forge_video.py approve --project <projectPath> --artifact shot-sequence --creator-approved`.
10. On resume, run `python3 scripts/forge_video.py status --project <projectPath>`. An Approval is current only while its Artifact identity, Current Revision, recorded content hash, and on-disk content all match. A dependent Approval also requires the Approval bound to each declared Dependency Revision to remain current.

## Verification boundary

Two acceptance criteria require model judgment and are verified manually rather than by automated tests:

- Materially distinct Creative Direction alternatives: the script enforces exactly three directions, exactly one recommendation, non-empty axes, and non-identical narrative/aesthetic axis pairs. A competent paraphrase can satisfy all four checks, so the model must still judge whether the alternatives differ materially.
- Complete recurring-entity declarations: the script verifies only that declared `referenceBibleEntityIds` resolve to Reference Bible entries. A Shot with an empty list validates regardless of its content, so the model must still verify that every featured recurring entity is declared.

Cross no image- or video-generation boundary in this slice. Keyframe generation begins later, after prerequisite Approvals; submitting or managing a Final Video Job remains outside Forger.
