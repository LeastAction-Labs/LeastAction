# Contributing to LeastAction

Thanks for your interest in contributing. LeastAction is source-available and we welcome contributions — bug fixes, new operators, documentation improvements, and more.

Before your first pull request is merged, you must sign the [LeastAction Contributor License Agreement](CLA.md). This protects you (your contribution is on record), protects other users (the project has clear IP ownership), and allows LeastAction Labs to continue building the product commercially.

---

## How to Contribute

1. **Open an issue first** for anything non-trivial. Describe what you want to fix or add and why. This avoids duplicate work and lets us confirm the direction before you write code.

2. **Fork the repo** and create a branch from `main`.

3. **Make your changes.** Keep the scope focused — one fix or feature per PR.

4. **Sign your commits** with `git commit -s` (DCO sign-off) and confirm you have read and agree to the [CLA](CLA.md) in your PR description.

5. **Open a pull request** against `main`. Include a clear description of what changed and why.

---

## CLA Requirement

All contributors must agree to the [LeastAction Contributor License Agreement](CLA.md) before their contribution can be merged.

To confirm your agreement, add the following line to your pull request description:

```
I have read and agree to the LeastAction Contributor License Agreement.
```

First-time contributors will be reminded automatically if this is missing.

---

## What We Accept

- Bug fixes with a clear reproduction case
- New marketplace operators, actions, or skills (follow existing patterns)
- Documentation improvements and corrections
- Performance improvements with measurable evidence
- Test coverage additions

## What We Don't Accept (Without Prior Discussion)

- Large architectural changes
- New dependencies without justification
- Changes to the license or EE feature boundary
- Breaking changes to the catalog schema or API contracts

---

## Code Style

- Python: follow the existing operator and action contracts (4-method for operators, single `run` method for actions)
- TypeScript: match existing component patterns in `frontend/src`
- No new dependencies without discussion in an issue first

---

## Questions

Open a GitHub issue or reach out at [leastactionlabs.com/contact](https://leastactionlabs.com/contact).
