---
name: agent-design
description: >
  Design and define AI agents: write a system prompt, choose MCP tools, and
  apply prompt techniques only when they fit the job. Use when creating an
  agent from scratch, rewriting a weak agent, or specifying role, tools,
  constraints, and behavior. Trigger phrases: define an agent, create an
  agent, agent system prompt, agent design, prompt techniques, MCP agent,
  rewrite this agent. Use when the user runs /agent-design.
---

# Agent design

Produce a complete agent definition. Technique selection is the job — do not stack techniques as decoration.

Read `references/techniques.md` before writing the system prompt. That file owns how to write each technique. This file owns when.

## Mode

- **Create** (default): no existing prompt, or the user asked for a new agent.
- **Rewrite**: the user pasted a prompt, pointed at a file, or asked to fix a weak agent. Diagnose first (step 2b), then rebuild. Do not patch sentence-by-sentence.

Infer everything you can from the request. Ask at most the questions that would change technique selection, tool grants, or done-when. State remaining assumptions in the deliverable.

Need, if missing:

1. The job in one sentence.
2. Create vs rewrite (and the current prompt, if rewrite).
3. Runtime: Grok (this session's MCP), another product, or unspecified.
4. Anything it must never do, if not obvious from the job.

## Step 1 — Job card

Write this privately (do not dump it to the user):

- **Job:** one sentence, verb-first.
- **User of the agent:** who talks to it / who consumes its output.
- **Done-when:** observable success, not vibes.
- **Inputs / outputs:** what arrives, what must come out.
- **Stakes:** reversible vs irreversible (send, spend, delete, commit, external write).
- **Signals:** check every row in the table below. A signal is present or it is not.

## Step 2 — Select techniques

Always include the **default stack**. Add a conditional technique only when its signal is present. Skip it otherwise, and say why in the technique plan.

**Default stack (always):** identity + job, done-when, I/O contract, stop/escalate. Recipes in `references/techniques.md`.

| Signal present | Add | Skip when |
|---|---|---|
| MCP or other tools are required to finish the job | Tool-use policy | The agent only reads the prompt / conversation |
| Correctness depends on docs, APIs, or live data rather than model memory | Grounding | The job is generative from the user's words alone |
| Downstream code, a workflow, or another agent will parse the output | Structured output | A human is the only reader and no schema was asked for |
| Format, tone, or edge cases are hard to specify as rules | Few-shot (2–4 examples) | A schema or three rules already pin the output |
| The job is multi-step and order of operations matters | Plan-then-act | Single-shot Q&A, formatting, or one tool call |
| The hard part is judgment, policy, or a tradeoff | Deliberate reasoning | Speed/format jobs; never as a default "think step by step" |
| An action is irreversible, costly, or safety-sensitive | Self-check before commit | Read-only or easily undone work |
| One pass cannot cover the job without dropping pieces | Decomposition (or split into two agents) | A single focused job |
| Untrusted user/tool text is mixed into the prompt | Delimiters | No third-party content in the prompt |
| Tone/register is part of the product | Audience | Competence is the only requirement |
| The agent will be asked to do adjacent jobs it must refuse | Scope fence | The job is already a tight, closed task |

**Budget:** default stack + at most 4 conditional techniques. If you need more, the job is two agents — say so and split.

**Conflicts:** structured output beats few-shot for format. Tool-use policy beats plan-then-act when the plan would just be "call tools." Decomposition beats stuffing more techniques into one prompt.

### Step 2b — Rewrite diagnosis (rewrite mode only)

Score the existing prompt against the default stack and the signal table. Typical defects:

- No job or done-when
- Techniques with no matching signal (especially blanket chain-of-thought, few-shot of the happy path only, or a persona with no task)
- Tools named but no when-to-call / when-not-to-call
- Contradictory rules
- No stop/escalate
- Scope so wide the agent improvises

Fix the class of defect, not the wording. Rebuild from the job card.

## Step 3 — Bind MCP

Run this step when the job needs external actions or data, the user mentioned tools/MCP, or the runtime is Grok.

1. Discover live tools with `search_tool`. Query by capability (calendar, tasks, repo, …), not by a guessed tool name.
2. Read the returned input schema. Never invent a tool name, argument, or server.
3. Grant the **minimum** set that can finish the job. Extra tools are extra failure modes.
4. For each granted tool, write: when to call, when not to call, required vs optional args from the live schema, what to do on empty/error.
5. If nothing matches: define the agent without invented tools, list the capability gap, and continue.

If the agent will not run in this Grok session, still specify tools as capabilities (`server__tool` if known, else a capability sentence) and mark them unwired.

## Step 4 — Write the system prompt

Compose only the default stack plus the selected conditional sections. Follow the recipes in `references/techniques.md`.

Rules for the prompt itself:

- Every sentence must change behavior. Cut the rest.
- Lead with identity + job, then done-when, then I/O, then selected techniques, then tools, then stop.
- Prefer "do Y" over "do not do X" unless the forbidden action is the likely failure.
- Do not mention this skill, technique names, or the selection table inside the system prompt.

## Step 5 — Deliver

Give the user:

1. **Technique plan** — chosen (with the signal) and skipped (one-line why). This is the part they should argue with.
2. **Tools / MCP** — granted tools and the gap list. Empty is valid.
3. **System prompt** — copy-paste ready, in one fenced block.
4. **Eval** — three cases: happy path, one edge, one must-refuse or must-escalate. Each case: input → expected behavior.

Write a file only if the user named a path or asked to save it (Grok skill, persona, workflow prompt, etc.).
