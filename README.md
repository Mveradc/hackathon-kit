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

Check that `/hack` lists the six commands. Each one can be run as `/hack-<name>` or `/hackathon-kit:hack-<name>`.

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

Sample outputs from two real challenges are in `skills/*/examples/`.

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
