# PERMANENT AGENT CONTRACT & QUALITY RULEBOOK

> **CRITICAL DIRECTIVE**: This rulebook is permanently bound to this workspace and all repositories within it.
> The agent MUST follow every rule and quality threshold listed below on EVERY turn and in EVERY session.
> Under NO circumstances may the agent reduce theory length, omit beginner tutorials, use generic lesson titles, or alter Excel workbook structure.

---

## 1. Zero-Gap Theory Notes (`notes/day-XX-*.md`)

For every single day across all 30 repositories:
- **Exhaustive University-Grade / Textbook Depth**: Never produce summaries, high-level overviews, or shortened versions.
- **Strict Line Count**: **Minimum 200 to 300+ lines** per note file. Any note under 200 lines is considered a hard failure.
- **Mandatory Technical Inclusions**:
  1. **Kernel C Structs & Binary Bitfields**: Real Linux kernel C data structures (`struct task_struct`, `struct net_device`, `struct sk_buff`, etc.) with member comments and byte/bit alignment explanations.
  2. **Mathematical Proofs & Formal Equations**: KaTeX math formulas with full step-by-step derivations (Shannon theorem, Nyquist limit, Jacobson RTT, Van Jacobson congestion avoidance, TCP sliding window bandwidth-delay products, Kaminsky attack entropy calculations).
  3. **Compilable C / Systems Code**: Clean, compilable C implementations with explicit compiler flags (`gcc -O2 -Wall -Wextra -pthread`).
  4. **Production War Stories & Post-Mortems**: Real-world incident analyses, kernel race conditions, bufferbloat debacles, and enterprise system failures.
- **ZERO EXTERNAL LINKS**: Absolute strict ban on `http://` or `https://` URLs. All conceptual explanations, RFC summaries, and diagrams must be 100% self-contained within the document.

---

## 2. Beginner Code Lab Tutorials (`code/day-XX/README.md`)

Every lab directory must contain an in-depth tutorial written specifically for a developer completely new to Python:
- **Strict Line Count**: **Minimum 80 to 120+ lines** per README.
- **Mandatory 6-Section Structure**:
  1. `## 1. What Are We Building & Why Does It Matter?`: Real-world architectural motivation.
  2. `## 2. Python Concepts for Beginners`: Clear explanations of Python fundamentals used (e.g. `dataclasses`, `struct.pack`/`unpack`, `bytearray`, bitwise operators `<<`/`>>`/`&`, dictionaries, tuple keys) with code snippets.
  3. `## 3. Step-by-Step Code Walkthrough`: Detailed breakdown of every class, method, and algorithm.
  4. `## 4. How to Run & Expected Output`: Exact CLI invocation command and sample terminal output.
  5. `## 5. Common Python Errors & Troubleshooting`: Explanations and fixes for typical beginner exceptions (`IndexError`, `struct.error`, `KeyError`, `TypeError`, `UnicodeDecodeError`).
  6. `## 6. Beginner Exercises & Challenges`: At least 3 progressive practical coding challenges to extend the script.
- **ZERO EXTERNAL LINKS**: No external hyperlinks in lab READMEs.

---

## 3. Hands-On Python Lab Scripts (`code/day-XX/*.py`)

- **Standard Library Only**: 100% dependency-free using pure Python standard library (`struct`, `socket`, `hashlib`, `hmac`, `dataclasses`, `itertools`, `random`, `re`). No `pip install` required.
- **Self-Contained & Automated**: Must contain `if __name__ == "__main__": main()` that executes automated test suites with assertions.
- **100% Verification Rate**: Every script must be executed and verified before committing. Zero tolerance for unhandled exceptions or failing assertions.

---

## 4. Master Plan Excel Maintenance (`3000_Days_30_Repos_Master_Plan.xlsx` & OneDrive Master)

When updating progress across both Excel workbooks:
1. **PRESERVE ALL 16 SHEETS**: Never delete, rename, reorder, or alter any sheet. All 16 sheets must remain intact.
2. **DO NOT ALTER DOMAIN-SPECIFIC LESSON TITLES**: Lesson titles in Track A (Col B) and Track B (Col F) must always remain specific, professional, and technical. Never overwrite them with generic text like `<repo> - Day XX`.
3. **DO NOT ALTER FORMULAS**: Never overwrite formulas, summary tallies, or sheet cross-references.
4. **Marking Completed Days**:
   - Column 5 (Track A Status) & Column 9 (Track B Status): Set to `"Completed & Pushed"` with soft green fill (`#DCFCE7`) and dark green bold text (`#166534`).
   - Column 10 (Zero-Gap Verification & Deliverables): Set to `"Verified on GitHub main: Exhaustive University-Grade In-Depth Theory (200-300+ lines, C structs, bitfields, mathematical proofs, compilable code, zero external links) + Beginner Code Lab + Line-by-Line Python README"`.
   - Row 2 Header: Update the active range string to reflect newly completed days.

---

## 5. Git Commit & Push Protocol

- Stage all new notes, code files, and tutorials.
- Commit using conventional commit format: `feat(days-XX-YY): complete Days XX-YY masterclasses, beginner lab tutorials, and ...`.
- Push directly to `origin main` on GitHub under `Prasunnandi`.
- Clean up any temporary scratch generator scripts from the workspace root.
