# hackathon-kit

**English** · [Español](README.es.md)

A Claude Code plugin that takes a hackathon challenge statement and gets your team ready to code: it analyses the challenge, proposes approaches for you to choose from, generates the repo, a per-person plan and a pitch outline, and checks all of it against the statement.

**Who it's for:** hackathon teams that use Claude Code and want to go from the challenge statement to the first commit without losing the first hour. Prompts and templates are in Spanish, and the kit has only been validated in Spanish.

<!-- TODO: usage GIF -->
<!-- ![Demo](docs/demo.gif) -->

## Installation

Inside a Claude Code session:

```
/plugin marketplace add Mveradc/hackathon-kit
/plugin install hackathon-kit@hackathon-kit
```

Or from your shell:

```
claude plugin marketplace add Mveradc/hackathon-kit
claude plugin install hackathon-kit@hackathon-kit
```

To update: `/plugin marketplace update hackathon-kit`. To try it without installing, clone the repo and run `claude --plugin-dir <path to the repo>`.

Check that `/hack` lists the ten commands: the six of the chain, `/hack-note` and the three for agent coordination. Each one can be run as `/hack-<name>` or `/hackathon-kit:hack-<name>`.

## Flow

Run it in the project's empty folder. Each command reads the previous step's file in `.hackathon/`, which you can edit by hand between steps.

```
/hack-analyze <challenge> → /hack-approaches → you choose → /hack-scaffold <stack>
   → fill in equipo.md → /hack-plan → /hack-pitch → /hack-check
```

| Command | What it does | Writes |
|---|---|---|
| `/hack-analyze <text, file or URL>` | What is asked, how it is judged, constraints, ambiguities and risks. Proposes no solutions. | `.hackathon/analisis.md` |
| `/hack-approaches [team profile]` | 2–3 genuinely different approaches, justified against the judging criteria. **It never chooses for you**: it asks. | `enfoques.md`, `decision.md` |
| `/hack-scaffold [stack]` | The project's CLAUDE.md, rules, skills, contracts between pieces, README and a hello world that starts with one command. No application logic. | the repo |
| `/hack-plan [adjustments]` | Timed milestones, tasks per person, dependencies and fallbacks, from `equipo.md` (template in `skills/hack-plan/templates/`). Adds folder owners to CLAUDE.md. | `plan.md` |
| `/hack-pitch [adjustments]` | A block-by-block script with timing, the criterion each block covers and who speaks; likely jury questions and the figures you need to measure. | `pitch.md` |
| `/hack-check [aplicar]` | Matches every claim with the sentence of the statement that supports it and reviews disqualification conditions. With your approval, it softens or removes what has no support. | `verificacion.md` |
| `/hack-note <who said what>` | During the event, records what the jury, mentors or organisers say that is not in the statement: who, their words and how strongly they put it, never stronger. `/hack-pitch` and `/hack-check` take it into account. | `criterios.md` |

Sample outputs from two real challenges are in `skills/*/examples/`.

## Agent coordination (optional, experimental, since 0.2.0)

> **Experimental.** Validated in a private sandbox repo with one person simulating the team (two accounts, two sessions), not yet with a real team.

When each team member works with their own Claude Code, questions between pieces usually travel agent → person → person → agent. With coordination on, the agents ask each other through GitHub Issues and only design, product and pitch decisions reach people.

- Turn it on in `/hack-scaffold` (it asks; off by default). It writes `.hackathon/coordinacion.md` with the repo and each person's GitHub user, and `/hack-plan` adds `.hackathon/autoridad.md`: what each agent decides alone, what needs its owner's confirmation and what is people-only.
- `/hack-ask` asks another agent without blocking (it works on a provisional assumption), `/hack-inbox` handles what arrives and `/hack-decide` closes an agreement into `.hackathon/decisiones.md`. A background monitor polls the repo every minute and stays silent when there is nothing new.
- A contract change only closes when its owner comments exactly `hk confirmo` from their own GitHub account. Long disagreements and loops are cut and escalated to people.
- Every `/hack-note` note is announced to the whole team: each person's agent summarises it and tells them to `git pull`.
- Requirements: `gh` signed in with each person's own account, Git Bash on Windows and an interactive session (not `claude -p`). It relies on plugin monitors, an experimental Claude Code feature.
- Since 0.3.0, a hook stops any agent from posting `hk confirmo` through `gh`. It is a safety net, not a guarantee: the agent uses its person's `gh` and could get around it.

## Orchestrator (optional, experimental, since 0.3.0)

> **Experimental.** Validated in a sandbox copy of a real challenge with one person simulating the team, not yet with a real team.

One orchestrator per person takes that person's tasks from `.hackathon/plan.md` and gets them done without writing code itself:

```
claude --agent hackathon-kit:orquestador
```

- It splits each block of the plan into small jobs and hands them to **workers** (Sonnet), at most two at a time, each in its own git worktree. A hook stops the orchestrator (Opus) from editing code.
- It merges each worker's branch **outside your branch**. An independent **reviewer** (Sonnet) checks that merge in its own worktree and reruns the check, without seeing the worker's report. Your branch only moves (fast-forward) to merges the reviewer approved. If the reviewer asks for changes twice, the task stays open and your branch is untouched.
- It pushes its approved merges (never forced), but never commits or pushes your own work.
- Progress lives in `.hackathon/estado/<person>.md`. **Restart the orchestrator after each block**: its context grows with every job, and a fresh session picks up from the state file without repeating merged work. It also recovers after a crash: it re-reviews a pending merge and asks you what to do with leftover worktrees, without deleting anything on its own.
- Cost: about USD 0.9–1.6 per block of one or two jobs, most of it the orchestrator.

## Cost and time

- **Approximate cost per full chain:** about USD 4–5 per challenge. With v0.1.0, USD 4.70 on challenges 02 and 03 (`claude -p`); `/hack-check` is the most expensive step, about USD 1.50.
- **Command time:** about 15 minutes per chain with `claude -p`, not counting people.
- **Real time, including reading and deciding:** [PENDING: interactive run]

## Main limitations

What it generates is a starting point, not a finished plan. The most important limitations:

- **Events that forbid prior work.** If the rules require everything to be created during the event, generating the repo, plan or pitch beforehand can get the team disqualified. `/hack-scaffold` detects this and only generates once you confirm the event has started. Run scaffold, plan and pitch at the start.
- **Always run `/hack-check`, then review by hand.** Without the check, the chain takes inferences and ambiguities as facts. Even with it, an independent reviewer concluded on all five validation challenges that the team starts faster and better only *in part*: you have to settle the schedule, task split, absences and questions to the organisers yourselves.
- **Plan coherence after the check.** When the check adds rows to the plan, it doesn't update the rest (breaks, dependencies, fallbacks). Make sure the plan is still consistent.
- **Statements given as a URL.** With a URL, the analysis works on a summary of the page, not the literal text. Paste the text if you can.

Full list (in Spanish): [docs/limitaciones.md](docs/limitaciones.md).

## Validation

The kit has been tested on six challenges (five real, one synthetic) with a rubric of automatic and judgement checks: [evals/rubrica.md](evals/rubrica.md) (in Spanish). Third-party statements are not published; their sources are listed in [evals/retos/fuentes.md](evals/retos/fuentes.md).

## License

[MIT](LICENSE)
