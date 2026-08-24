---
name: forge-video
description: Create or continue a collision-safe Forger Project for planning a short-form video. Use when a Creator wants to develop a video idea, plan shots, or prepare generation-ready materials without submitting a final video-generation job.
---

# Forge Video

Create the walking-skeleton Forger Project before developing the Creator's idea:

1. Use the current workspace unless the Creator selected another workspace. Choose a short project name from the request.
2. Run `python3 scripts/forge_video.py --workspace <workspace> --name <project-name>`, resolving the script relative to this file. The command is complete when it prints JSON containing `projectPath` and `phase`.
3. Tell the Creator where the Forger Project was created and that it is ready for the next workflow slice.

This walking-skeleton slice initializes project state only. Cross no image- or video-generation boundary. Keyframe generation begins later, after its prerequisite approvals exist; submitting or managing a Final Video Job remains outside Forger.
