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
| `/hack-approaches [team profile]` | 2–3 genuinely different approaches, justified against the judging criteria. If `.hackathon/equipo.md` exists, it then says how each one fits your team (who covers what, gaps, absences), without changing the approaches. **It never chooses for you**: it asks. | `enfoques.md`, `decision.md` |
| `/hack-scaffold [stack]` | The project's CLAUDE.md, rules, skills, contracts between pieces, README and a hello world that starts with one command. No application logic. It also writes `.claude/settings.json` so commits and PRs made by Claude don't carry its co-author line, unless the rules require declaring AI use. | the repo |
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

## Hackathon OS (optional, experimental, since 0.4.0)

> **Experimental.** Validated without a model (550+ tests and the evals in `evals/coordinacion/`) and in a sandbox with one person simulating the team. **Not yet rehearsed with a real team.**

Keeps the whole team aware of who is doing what, what is already in `main` and where you are about to collide, without asking out loud. Turn it on with `activa: sí` in `.hackathon/os.md`; off, everything behaves as in 0.3.2.

- **Team status.** A daemon per person (no model) reports what happens in their clone, and a relay on the coordinator's laptop puts it together. Each session gets a short «Team» block at start and, on every turn, only what changed and affects it. An `os` MCP server answers `estado`, `tarea` and `colisiones`. Anything stale is shown as stale, with its time.
- **Collision warnings, never blocks:** two people in the same file, incompatible changes before merging (opt-in with `publicar_wip: sí`) and contracts touched by someone who doesn't own them.
- **Work web** (`web_nueva: sí`): each person's daemon serves it on `127.0.0.1`. `hk-os web` opens it. Four views (cockpit, team graph, board, services), plus two actions: **Anotar** (adds a note to `criterios.md` in `origin/main` without touching your copy) and **Reclamar** (assigns the issue with your `gh` and opens one turn in your session). Nobody installs Node: the web ships built.
- **`.hackathon/servicios.md`**: ports, health checks and connections between pieces. A row only shows as confirmed if its owner committed it from their own laptop.
- **Jury coverage and critical path** (since 0.5.0, each with its own switch in `.hackathon/os.md`: `vista_jurado: sí`, `ruta_critica: sí`): which task or evidence covers each note in `criterios.md`, and whether the team reaches the `Entrega:` in `equipo.md` (overdue deadlines and what they drag, the chain, and an estimate with a range only after 3 measured tasks per person). Shown in the work web, as one line each in the team status and through the `jurado` and `ruta` MCP tools. Off, everything is byte for byte as in 0.4.0.
- **Without GitHub:** a team remote on the coordinator's laptop and tasks from `plan.md`.
- **Requirements:** uv, Git (2.38+ on the coordinator's laptop), `gh` signed in with each person's account, bash 5 on macOS (`brew install bash`). The relay speaks plain HTTP: on an untrusted network use Tailscale or ZeroTier.
- Ten-minute startup guide (in Spanish): [docs/hackathon-os/arranque.md](docs/hackathon-os/arranque.md). Design, contracts and decisions: [docs/hackathon-os/](docs/hackathon-os/).

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
- **An `os` MCP server in `/mcp`.** The team-status server of the Hackathon OS is declared by the plugin, so it shows up in `/mcp` in every session, even with the OS off. Then it offers no tools, uses no network and does not need uv.
- **`publicar_wip: sí` uploads your uncommitted work.** In the Hackathon OS, this option in `.hackathon/os.md` pushes tracked changes and new files that `.gitignore` doesn't ignore to the remote. It excludes `.env*`, common keys, data folders and large files, but no list is complete: check your `.gitignore` first. Deleting the ref doesn't delete what was uploaded; rotate any key that gets pushed. It's off by default.
- **The Hackathon OS has not been rehearsed with a real team.** It has been validated without a model and in a sandbox with one person simulating the team. Use it as an experiment and keep talking to each other. The critical-path estimate (3 measured tasks per person, verdict thresholds, measured pace) has not been tried with real data either, and tasks of people without a GitHub account are not measured.

Full list (in Spanish): [docs/limitaciones.md](docs/limitaciones.md).

## Validation

The kit has been tested on six challenges (five real, one synthetic) with a rubric of automatic and judgement checks: [evals/rubrica.md](evals/rubrica.md) (in Spanish). Third-party statements are not published; their sources are listed in [evals/retos/fuentes.md](evals/retos/fuentes.md).

## License

[MIT](LICENSE)
