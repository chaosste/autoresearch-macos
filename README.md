# autoresearch-macos

## Local path note

Canonical local working-copy path for the `tomx` branch:

- `/Users/stephenbeale/Projects/autoresearch-macos-tomx`

Compatibility symlink retained for older references:

- `/Users/stephenbeale/Projects/autoresearch-macos` -> `/Users/stephenbeale/Projects/autoresearch-macos-tomx`

Use the `-tomx` path in new notes, scripts, and links when referring to the local checkout.

![teaser](progress.png)

*One day, frontier AI research used to be done by meat computers in between eating, sleeping, having other fun, and synchronizing once in a while using sound wave interconnect in the ritual of "group meeting". That era is long gone. Research is now entirely the domain of autonomous swarms of AI agents running across compute cluster megastructures in the skies. The agents claim that we are now in the 10,205th generation of the code base, in any case no one could tell if that's right or wrong as the "code" is now a self-modifying binary that has grown beyond human comprehension. This repo is the story of how it all began. -@karpathy, March 2026*.

The idea: give an AI agent a small but real LLM training setup and let it experiment autonomously overnight. It modifies the code, trains for 5 minutes, checks if the result improved, keeps or discards, and repeats. You wake up in the morning to a log of experiments and (hopefully) a better model. The training code here is a simplified single-GPU implementation of [nanochat](https://github.com/karpathy/nanochat). The core idea is that you're not touching any of the Python files like you normally would as a researcher. Instead, you are programming the `program.md` Markdown files that provide context to the AI agents and set up your autonomous research org. The default `program.md` in this repo is intentionally kept as a bare bones baseline, though it's obvious how one would iterate on it over time to find the "research org code" that achieves the fastest research progress, how you'd add more agents to the mix, etc. A bit more context on this project is here in this [tweet](https://x.com/karpathy/status/2029701092347630069).

## Open source project worth to look at

Open source collabaration platform for agentic swarms in organizations and communityies.

[SentientWave Automata](https://github.com/sentientwave/automata)

## How it works

The repo is deliberately kept small and only really has a three files that matter:

- **`prepare.py`** — fixed constants, one-time data prep (downloads training data, trains a BPE tokenizer), and runtime utilities (dataloader, evaluation). Not modified.
- **`train.py`** — the single file the agent edits. Contains the full GPT model, optimizer (Muon + AdamW), and training loop. Everything is fair game: architecture, hyperparameters, optimizer, batch size, etc. **This file is edited and iterated on by the agent**.
- **`program.md`** — baseline instructions for one agent. Point your agent here and let it go. **This file is edited and iterated on by the human**.

By design, training runs for a **fixed 5-minute time budget** (wall clock, excluding startup/compilation), regardless of the details of your compute. The metric is **val_bpb** (validation bits per byte) — lower is better, and vocab-size-independent so architectural changes are fairly compared.

## Quick start

**Requirements:** Apple Silicon Mac (M1/M2/M3/M4 with Metal/MPS) or a single NVIDIA GPU, Python 3.10+, [uv](https://docs.astral.sh/uv/).

```bash

# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Download data and train tokenizer (one-time, ~2 min)
uv run prepare.py

# 4. Manually run a single training experiment (~5 min)
uv run train.py
```

If the above commands all work ok, your setup is working and you can go into autonomous research mode.

Verify repo structure and local cache readiness:

```bash
python .codex/skills/autoresearch-lab/scripts/autoresearch_ops.py check-setup --json
python .codex/skills/autoresearch-lab/scripts/autoresearch_ops.py check-setup --json --repo-only
```

Use `--repo-only` when you only need to confirm required files and tooling (for example in CI) without checking downloaded data shards or the trained tokenizer.

## Running the agent

Simply spin up your Claude/Codex or whatever you want in this repo (and disable all permissions), then you can prompt something like:

```text
Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.
```

The `program.md` file is essentially a super lightweight "skill".

There is now also a repo-local Codex skill at `.codex/skills/autoresearch-lab/SKILL.md` that packages the experiment loop with helper scripts for setup checks, branch creation, bounded runs, log parsing, and `results.tsv` updates.

For a thin local launcher/dashboard, run:

```bash
./autoresearch-dashboard
```

That opens a local web UI with:

- a chat-style prompt composer and local transcript for the current autoresearch repo
- a second ToMX profile that reuses the external ToM workspace plus its repo-local agent TOMLs
- a separate `Send To Codex` path so prompt delivery is distinct from direct run buttons
- lightweight buttons for readiness checks and bounded run launching

## Project structure

```text
prepare.py      — constants, data prep + runtime utilities (do not modify)
train.py        — model, optimizer, training loop (agent modifies this)
program.md      — agent instructions
pyproject.toml  — dependencies
```

## Design choices

- **Single file to modify.** The agent only touches `train.py`. This keeps the scope manageable and diffs reviewable.
- **Fixed time budget.** Training always runs for exactly 5 minutes, regardless of your specific platform. This means you can expect approx 12 experiments/hour and approx 100 experiments while you sleep. There are two upsides of this design decision. First, this makes experiments directly comparable regardless of what the agent changes (model size, batch size, architecture, etc). Second, this means that autoresearch will find the most optimal model for your platform in that time budget. The downside is that your runs (and results) become not comparable to other people running on other compute platforms.
- **Self-contained.** No external dependencies beyond PyTorch and a few small packages. No distributed training, no complex configs. One GPU, one file, one metric.

## Platform support

This checkout (`autoresearch-macos-tomx`) is a **macOS-first fork** of [karpathy/autoresearch](https://github.com/karpathy/autoresearch). It keeps the same experiment contract (`prepare.py` fixed, `train.py` edited by agents, 5-minute time budget, `val_bpb` metric).

**Supported accelerators:** Apple Silicon with Metal (MPS) or NVIDIA CUDA. At startup, `prepare.py` and `train.py` call `verify_training_env()` and exit if neither is available.

**Fork differences from upstream:**

- No FlashAttention-3 dependency — uses PyTorch SDPA with sliding-window causal masks when needed
- `torch.compile` enabled on CUDA only (disabled on MPS)
- MPS-oriented memory and optimizer dtype handling

For MLX-native training, see [trevin-creator/autoresearch-mlx](https://github.com/trevin-creator/autoresearch-mlx). For an earlier macOS port, see [miolini/autoresearch-macos](https://github.com/miolini/autoresearch-macos).

If you want cleaner small-scale results, consider swapping in the [TinyStories dataset](https://huggingface.co/datasets/karpathy/tinystories-gpt4-clean) — same parquet format, drop-in replacement for the default training shards.

## Notable forks

- [miolini/autoresearch-macos](https://github.com/miolini/autoresearch-macos)
- [trevin-creator/autoresearch-mlx](https://github.com/trevin-creator/autoresearch-mlx)

## License

MIT
