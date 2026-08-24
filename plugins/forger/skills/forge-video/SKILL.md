---
name: forge-video
description: Create or continue a collision-safe Forger Project for planning a short-form video. Use when a Creator wants to develop a video idea, plan shots, or prepare generation-ready materials without submitting a final video-generation job.
---

# Forge Video

Create or resume the Forger Project, then guide the Creator through the Creative Brief Milestone:

1. Use the current workspace unless the Creator selected another workspace. For a new project, choose a short name and run `python3 scripts/forge_video.py --workspace <workspace> --name <project-name>` relative to this file.
2. Gather only unknown intake fields in focused, related rounds of at most three questions. The required fields are idea, purpose, audience, channel, duration, aspect ratio, language, required content, references, and constraints. Do not repeat a known answer. After each round run `python3 scripts/forge_video.py intake --project <projectPath> --answers '<json-object>'`.
3. Decide whether research is warranted. Fictional concepts without factual, cultural, historical, scientific, product, location, trend, or linked-reference claims use `not-warranted`; do not perform research for them. For warranted research, separate Research Claims and citation references from Evidence and Inspiration, and expose Material Contradictions and their resolution state.
4. Create the reviewable brief with `python3 scripts/forge_video.py brief --project <projectPath> --research-disposition not-warranted`, or pass the complete stable research object with `--research '<json-object>'`. Present `artifacts/creative-brief.md` to the Creator.
5. Ask explicitly whether the Creator approves that exact Creative Brief. Rejection or silence does not advance the Milestone. Record acceptance with `python3 scripts/forge_video.py approve --project <projectPath> --creator-approved`. Pass every additional eligibility problem with a repeated `--blocker`; approval advances only when the complete blocker set is empty.
6. On resume, run `python3 scripts/forge_video.py status --project <projectPath>`. An Approval is current only while its Artifact identity, Current Revision, recorded content hash, and on-disk content all match.

Cross no image- or video-generation boundary in this slice. Keyframe generation begins later, after prerequisite Approvals; submitting or managing a Final Video Job remains outside Forger.
