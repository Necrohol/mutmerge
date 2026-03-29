# 🧬 MUTMERGE (v1.0-ALPHA) 🐙
> **"Gotta Emerge Them All."**



## 🧪 THE MUTATION PROTOCOL

MutMerge is not a standard package manager. It is a **Genetic Algorithm** for Gentoo Linux. It takes a single `ebuild` and forces it to mutate through thousands of `USE` flag combinations—from "Skinny/Thin" (minimalist) to "Leviathan/Max" (everything-included) features.

### 🧠 The Evolution of the Squid

The **Cyber-Squid** (our mascot) represents the **Recursive Learning Logic**. 
* **One Head (The Brain):** The LXC container managing the **SQLite Memory**.
* **Adaptive Tentacles (The Nerves):** Multiple paths branching out, each holding a different architecture symbol (**RISC-V, ARM64**). If one Rung of the ladder fails, the tentacle adapts and tries the next "Mutation."
* **Inking the Showroom:** The squid consumes source code and inks out a continuous stream of glowing `.gpkg` hex-code to your **Public Binhost (VPS/S3).**

---

## 🏗️ THE INFRASTRUCTURE FLOW



| Component | Responsibility | Action |
| :--- | :--- | :--- |
| **`.woodpecker.yml`**| The Orchestrator | Triggers the Rungs of the Ladder on a `packages.toml` push. |
| **`mutmerge_core.py`**| The Brain | Sequences the mutation based on **SQLite Memory (Weight)**. |
| **`mutmerge_builder.py`**| The Muscle | Spawns ephemeral Alpine-Podman containers for high-speed synthesis. |
| **`fix-binhost.sh`** | The Publisher | A standalone script that "inks" the index (Rebuilds Packages.gz) on the Debian VPS. |

---

## ☣️ OPERATIONAL MODES

1. **The "Thin" Rung:** Targets absolute minimalism. Enables base features, disables optional bloat.
   `./mutmerge --arch riscv64 --max-variants 5 --focus-thin`

2. **The "Max" Rung:** The Infinite Buffet. Enables `USE="*"` logic to ensure *every* feature is compiled and indexed.
   `./mutmerge --arch arm64 --max-variants 100`

---

## ⚠️ ATTENTION REQUIRED
> **"Mutate or Die."**

If a build fails, MutMerge thrives. The log is captured, the circular dependency is mapped, and the "Weight" in the SQLite DB is adjusted so the next iteration is faster. Your fleet **hoovers** the binaries; MutMerge provides the **mutations**.

---

[Glow Effect CSS/HTML for the README]
