# CLAUDE.md

## Project

This project compares schema-free LightRAG extraction against ontology-guided
extraction on a fixed 2WikiMultiHopQA subset, using a local open model via
Ollama. Work is tracked in Jira project SCRUM.

## Git rules

- After a fresh clone, run `git config core.hooksPath .githooks` to enable the
  commit-msg hook. At the start of each session, check that
  `git config core.hooksPath` prints `.githooks`; if it does not, tell me
  before doing anything else.
- One branch per story, named `story/SCRUM-<n>-<short-name>`.
- Stop and show the diff before every commit.
- Use plain commit messages.
- Merge into main only with `--no-ff`, and only after approval.
- Never push unless told to.
- Never use `--force`, `--no-verify`, `reset --hard`, or `rebase`.
- Never touch the `backup-main` or `backup-feature` branches.
- Never add `Co-Authored-By` or `Claude-Session` trailers.

## Data rules

- Raw datasets and model files stay out of git. Commit download scripts instead.
- Pin package versions.

## Working rule

Each story has acceptance criteria in Jira. Before declaring a story done, check
every criterion and report pass or fail for each one.

Write downloaded files only to absolute paths under /tmp or data/raw/; never with a
relative output path in the repo.
