# Video Preproduction

Forger turns a Creator's rough short-form video idea into a reviewable, generation-ready audiovisual plan while keeping creative intent separate from provider-specific execution.

## Language

**Creator**:
The person who develops, reviews, edits, and approves a Forger Project.
_Avoid_: Client, customer

**Forger Project**:
The durable body of creative work for one video idea, including its artifacts, history, and decisions.
_Avoid_: Session, job

**Artifact**:
A Creator-reviewable piece of a Forger Project that can change independently and participate in approvals or dependencies.
_Avoid_: Output, blob

**Revision**:
One identified state of an Artifact's content in project history.
_Avoid_: Copy, duplicate

**Dependency**:
A declared relationship from one Artifact Revision to a specific Revision of another Artifact.
_Avoid_: Reference, association

**Current Revision**:
An active, non-Superseded Revision whose every Dependency points to the Current Revision of the depended-on Artifact. “Current Artifact” is shorthand for the Artifact's Current Revision.
_Avoid_: Latest Revision, valid file

**Stale Revision**:
A preserved, non-Superseded Revision with at least one Dependency that no longer points to the Current Revision of the depended-on Artifact, and which therefore requires Reconciliation before reuse. “Stale Artifact” is shorthand for an Artifact with a Stale Revision.
_Avoid_: Deleted Revision, invalid file

**Superseded Revision**:
A preserved Revision that the Creator or workflow has deliberately replaced with another Revision; it is historical rather than Current or Stale.
_Avoid_: Stale Revision, deleted version

**Approval**:
A Creator's explicit acceptance of one exact Artifact Revision at a Milestone. An Approval is current while that Artifact's Current Revision is the bound Revision and its content hash still matches the bound hash.
_Avoid_: Confirmation, sign-off without revision identity

**Milestone**:
A named decision boundary in a Forger Project that requires its approval blockers to be resolved before the workflow advances. The four Milestones are Creative Brief, selected Creative Direction, Shot Sequence, and Visual Board.
_Avoid_: Phase, task

**Reconciliation**:
The process of bringing recorded project state into agreement with Creator-edited authoritative Artifacts while preserving project history.
_Avoid_: Overwrite, regeneration

**Creative Brief**:
The Artifact that states the video's purpose, audience, channel, requirements, constraints, and relevant research context.
_Avoid_: Prompt, intake form

**Creative Direction**:
A coherent proposed treatment of the Creative Brief, defining the video's narrative and aesthetic approach.
_Avoid_: Style preset, mood

**Reference Bible**:
The Artifact that defines recurring characters, products, locations, props, palette, and style used to preserve continuity.
_Avoid_: Asset folder, mood board

**Shot Sequence**:
The ordered, provider-neutral editorial plan for the video's visuals, timing, continuity, audio, dialogue, captions, transitions, and edit intent.
_Avoid_: Provider prompt list, clip list

**Shot**:
One editorial unit in a Shot Sequence, defined by its storytelling and audiovisual purpose rather than a provider's generation limits.
_Avoid_: Generation Clip, provider segment

**Visual Board**:
The ordered Artifact used to review Keyframes for every Shot across the complete sequence.
_Avoid_: Image gallery, loose storyboard

**Keyframe**:
A polished final-look image that represents a Shot, or a required endpoint within that Shot, at the intended aspect ratio.
_Avoid_: Thumbnail, sketch

**Generation Package**:
The approved, generation-ready collection of creative artifacts, provider instructions, and assembly guidance for one Forger Project.
_Avoid_: Final video, generation job

**Generation Clip**:
A provider-valid generation unit derived from a Shot and linked back to its editorial and assembly position.
_Avoid_: Shot, final clip

**Provider Profile**:
A versioned description of one video provider's verified consumer workflow, supported controls, constraints, prompt conventions, and translation preferences.
_Avoid_: API integration, model preset

**Research Claim**:
A factual statement used by a Forger Project that must remain traceable to supporting Evidence.
_Avoid_: Creative assertion, inspiration

**Evidence**:
Sourced material used to support or challenge a Research Claim.
_Avoid_: Inspiration, reference aesthetic

**Inspiration**:
Material that influences creative choices without serving as factual support for a Research Claim.
_Avoid_: Evidence, citation

**Material Contradiction**:
A conflict among Research Claims, Evidence, or project requirements that could change a Milestone decision if left unresolved.
_Avoid_: Minor discrepancy, creative alternative

**Final Video Job**:
A provider action that submits instructions or assets for final video generation and manages the resulting run. Generating a Keyframe image is not a Final Video Job.
_Avoid_: Generation Package, Generation Clip
