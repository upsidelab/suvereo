---
name: technical-decision
description: Spec-driven workflow for a technical decision or a feature with design choices. Draft a spec in specs/, iterate on it with the user, then implement against it. Use when asked to design, plan, propose or write a spec for something that involves choosing between approaches, and when asked to tighten an existing spec.
---

# Technical decision

Design work starts as a spec in `specs/<kebab-case-name>.md`. The user iterates on the spec; code follows the agreed spec. The spec is a repo file, not a chat answer and not a hosted page.

## Workflow

1. **Understand.** Read the code the change touches and the nearby specs. Ask the user only for what the code cannot tell you: the problem, constraints, what must not change.
2. **Draft.** Write the spec from the template below, with every design fork marked as a decision. Status: `Draft`.
3. **Iterate.** The user comments; revise the spec, not just the chat. Open questions stay in the spec until answered; an answered question moves into Design or a decision.
4. **Record.** Remarkable decisions deserve an ADR; fixes and smaller features do not. When the user settles one, add an ADR in `adrs/` before implementing: next number, slugged filename, the sections and statuses from `adrs/README.md`, and a line in its index. A decision that replaces an earlier one sets the old ADR to `Superseded by ADR-NNNN`.
5. **Implement.** Start only once the user accepts the spec. Implement phase by phase, in the order of the Phases section. When the implementation forces a design change, change the spec first and say so.
6. **Close.** After the implementing PRs merge, set the status to `Implemented` and link them. A spec that the code has outgrown is marked `Superseded` with a link to its replacement; a stale spec misleads as much as a stale `AGENTS.md`.

A narrow question about one part of a spec (e.g. "does this decision block read right?") is answered in chat.

## Template

```markdown
# <Title>

**Status:** Draft | Implemented | Superseded by <link>
**PRs:** <links, once they exist>

## Summary

<2-4 sentences: what is broken or missing, why now, and what this spec proposes.>

## Design

<Components, how data moves between them, what is new and what is reused. A diagram (mermaid or ASCII) once there are more than ~3 components. Decision blocks inline where the forks are.>

## Phases

### Phase 1 — <name>
<What lands, in a shippable increment.>

## Out of scope

- <Boundaries that would otherwise cause confusion.>

## Open questions

- <Only what is genuinely unresolved.>
```

Drop sections that do not apply. Goals and requirements go in Summary or Design when they shape a decision; do not add empty headings.

## Writing rules

**1. Concise.** Every sentence carries a fact. Cut any sentence that could go without losing information. Paragraphs of 2-4 sentences, leading with the point, not the setup.

**2. No fluff.** Cut throat-clearing ("It's important to note that...", "As mentioned above..."), intros that restate the request, and summaries that repeat the paragraph they close.

**3. No generic tech-speak.** Avoid words that sound technical and describe nothing: leverage, utilize, robust, seamless, elegant, powerful, cutting-edge, state-of-the-art, streamlined, unlock, empower, holistic, synergy, "under the hood", "dive into", "moving forward". Say "gated by" only when you name what checks or blocks. Replace each with the mechanism: not "a robust, seamless integration" but "writes retry three times, then land in the dead-letter queue".

**4. Mark decisions, show both sides.** Every fork (a technology pick, a pattern choice) is called out as a decision, not buried in prose. List the benefit and the drawback of every option, including the chosen one and the rejected ones:

```markdown
**Decision: <what is being decided>**
- **Option A** — Benefit: ... Drawback: ...
- **Option B** — Benefit: ... Drawback: ...

**Chosen: <option>** — <reason, tied to a stated goal>
```

**5. Describe what it is.** State the design directly. Explain a component by what it does, and keep scope boundaries in Out of scope. Two sentences in a row starting with "this doesn't" or "this isn't" are a signal to rewrite them as positive statements.

- Bad: "This service doesn't handle retries, isn't responsible for auth, and doesn't replace the job queue."
- Good: "The gateway routes requests and stamps a trace ID. The client retries; the session service handles auth."

**6. Ground it in the code.** Name the real modules, classes, settings and extension points the design touches (`suvereo-common` contracts, registries, `account.authorization`). Follow the conventions in `AGENTS.md`; a design that needs a new abstraction layer where an extension point exists must justify it in a decision block.

## Before finishing, check

- Any sentence that could be deleted without losing a fact? Delete it.
- Any word from rule 3? Replace it with the mechanism.
- Any decision without an explicit label and both sides of the trade-off? Fix it.
- Any paragraph defined by what it is not? Rewrite it around what it is.
- Does the status line match reality, and do the phases match what was or will be built?
