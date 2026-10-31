# Universal Multi-Asset Collision Engine & Domain Reducers Specification

## Problem Statement

In real-world software engineering, repositories do not consist solely of programming language source code. Everyday production projects are composed of a heterogeneous fabric of assets:
- **Dependency manifests & lockfiles** (`package.json`, `pnpm-lock.yaml`, `Cargo.toml`, `pyproject.toml`)
- **Database schema definitions & migrations** (`.sql` DDL, Alembic `versions/*.py`, Prisma `schema.prisma`, Flyway, Rails `db/migrate/*.rb`)
- **Documentation & engineering records** (`.md`, `.rst`, ADRs, changelogs, runbooks)
- **Declarative CI/CD & Infrastructure as Code** (`.github/workflows/*.yml`, `Dockerfile`, Kubernetes manifests, `terraform/*.tf`)

Currently, GDSS operates under an AST-first paradigm strictly scoped to a subset of programming language source files (`SOURCE_EXTENSIONS`). Any file outside this list is silently dropped from trajectory operators. This leads to critical production failure modes:

1. **False "All Clear" ($\Omega_{ij} = 0.0$)**: When two pull requests concurrently edit `package.json` or `.env.example`, GDSS reports no collisions, yet Git merge immediately crashes with textual conflicts.
2. **The Database "Split-Head" Disaster**: When two pull requests add new migration files branched off the same reference parent, Git merges them with zero textual conflict because the filenames differ. However, in staging or production, migration engines (Alembic, Prisma, Flyway) crash at startup with `MultipleHeadRevisionsError`. GDSS is blind to this because it treats migration files as unrelated ASTs rather than an ordered Directed Acyclic Graph (DAG).
3. **Lockfile Diff Hallucination**: When AI convergence assistants attempt to textually diff or reconcile 10,000-line lockfiles, they hallucinate cryptographic package hashes and break package integrity.
4. **Documentation Merge Friction**: Concurrent edits to markdown changelogs or README feature lists are flagged either as untracked files or as raw textual clashes, rather than being parsed as structured section additions that can be cleanly combined.

Developers need GDSS to act as a universal repository intelligence radar that understands all production assets, guarantees zero false negatives on concurrent edits, and uses domain-aware semantics to reconcile manifests, migrations, SQL, and documentation.

---

## Solution

GDSS evolves from a pure code AST engine into a **Universal Multi-Asset Collision Engine** governed by three core architectural pillars:

1. **Foundational Invariant: 100% Git Ingestion (Zero Files Dropped)**:
   - The ground truth is Git itself (`GitObserver.get_file_diffs_between_commits()`), which inherently tracks 100% of all added, modified, deleted, or renamed files in the repository.
   - The trajectory extractor eliminates all hardcoded extension gatekeepers (`SOURCE_EXTENSIONS` filters are removed).
   - **Every single modified file in a repository is ingested into the trajectory pipeline**, ensuring that no file is ever silently ignored.

2. **Content-First Autonomous Sniffing (Never Rely on Path Guessing Alone)**:
   - Because production repositories have unpredictable, bespoke, or nested directory structures (monorepos, polyglot layouts, non-standard folder names), GDSS does not rely solely on path guessing.
   - If a file path matches standard advisory patterns (e.g. `alembic.ini`, `drizzle.config.*`, `package.json`), it is routed immediately to the appropriate domain engine.
   - For all other files, GDSS applies **Content-First Autonomous Sniffing**:
     - **JSON / TOML Structure**: Inspects root keys (`dependencies`, `devDependencies`, `version`) to identify manifests anywhere in the tree.
     - **Migration Signatures**: Inspects file contents for DAG revision pointers (`down_revision =`, `dependencies =`, `_journal.json` schema, `CREATE TABLE / ALTER TABLE` blocks) regardless of what folder they reside in.
     - **SQL DDL Syntax**: Sniffs for SQL schema definition keywords (`CREATE TABLE`, `ALTER TABLE`, `ADD COLUMN`).
     - **Markdown / Prose**: Sniffs for ATX headings (`#`, `##`) and document structure.
     - **Shebangs & Language Syntax**: Sniffs for language indicators (`#!/usr/bin/env ...`) and Tree-sitter parsable grammars.

3. **Universal Lexical Safety Net (Guarantee of Zero False Negatives)**:
   - If a file is completely unrecognized (e.g. bespoke config, proprietary domain DSL, `.env`, `.yaml`, raw text), it is routed to the `UniversalLexicalReducer`.
   - The lexical engine calculates line-range diff chunks and content hashes.
   - **Strict Guarantee**: If two branches concurrently touch ANY identical file in a repository, GDSS will **never** return $\Omega_{ij} = 0.0$ ("All Clear"). It will always report a `lexical_concurrent` overlap on the Collision Radar.

---

## User Stories

1. As a full-stack developer, I want GDSS to detect when two open PRs modify `package.json`, so that dependency conflicts are surfaced before merge.
2. As a frontend engineer, I want GDSS to automatically recognize when two branches add non-overlapping dependencies to `package.json`, so that it recommends a conflict-free union merge without manual intervention.
3. As a developer, I want GDSS to alert me when two PRs specify conflicting version ranges for the same package, so that we can agree on a shared version before landing.
4. As a DevOps engineer, I want GDSS to never hallucinate lockfile diffs, but instead regenerate `pnpm-lock.yaml` or `package-lock.json` in the validation sandbox using native package manager commands.
5. As a backend engineer using Alembic or Django, I want GDSS to detect when two concurrent PRs branch from the same database migration revision, so that we prevent "split-head" deployment failures in production.
6. As a database administrator, I want GDSS to suggest an automated migration re-parenting command when a migration split-head is detected, so that one migration's `down_revision` seamlessly chains to the other.
7. As a data engineer writing `.sql` migrations, I want GDSS to parse `CREATE TABLE` and `ALTER TABLE` statements into schema symbols, so that column renames and drops are tracked as contractual changes.
8. As a backend engineer, I want GDSS to alert me if my branch queries a table column that another branch deletes in a `.sql` migration, preventing runtime query errors.
9. As an open-source maintainer, I want GDSS to parse Markdown documentation by headings, so that two PRs adding entries to the same `CHANGELOG.md` or `README.md` section are merged as commutative list additions.
10. As a documentation writer, I want Markdown collisions to carry a low, non-blocking risk score ($\Omega \le 0.3$), so that doc edits do not block automated CI gates.
11. As a cloud architect, I want GDSS to warn me if two concurrent PRs edit the same GitHub Actions workflow (`.github/workflows/*.yml`) or Dockerfile, so that CI/CD configuration collisions are caught before merge.
12. As a repository administrator, I want GDSS to guarantee that if two branches touch *any* identical file in the repository, the Collision Radar will never claim "All Clear", eliminating false negatives.
13. As a developer using unsupported languages (e.g. Kotlin, Swift, Scala, Elixir), I want GDSS to fall back gracefully to indentation-based chunking and lexical diff analysis rather than completely ignoring the files.
14. As an engineer in an offline environment, I want all domain reducers (Manifests, Migrations, SQL, Markdown) to operate 100% deterministically and offline with zero LLM token bleed.
15. As a PR reviewer, I want the PR Collision Radar comment to clearly classify whether a collision is `AST Code Divergence`, `Database Migration Split-Head`, `Package Manifest Conflict`, or `Lexical Config Overlap`.

---

## Implementation Decisions

### Decision 1: Two-Tier Collision Architecture (Universal Reducer Registry)
GDSS will decouple trajectory operator extraction from hardcoded `SOURCE_EXTENSIONS`. Instead, file evaluation routes through a `DomainReducerRegistry`:
- If a specialized `DomainReducer` exists for the file type, it extracts domain-specific semantic operators.
- If a Tree-sitter language grammar exists, it extracts code AST operators.
- Otherwise, the file is routed to the `UniversalLexicalReducer`, ensuring that every concurrently modified file produces an operator and contributes to $\Omega_{ij}$.

### Decision 2: Pluggable `DomainReducer` Protocol
All domain engines adhere to a common structural interface:
- Input: file path, historical content at base commit, and content at branch head.
- Output: list of domain `SemanticOperator` records with clear symbol names, line anchors, and operator types (`add_dependency`, `modify_schema_column`, `split_head_migration`, `append_doc_section`, `lexical_edit`).

### Decision 3: The Manifest Reducer Engine
- Parses JSON, TOML, and YAML key-value structures.
- Compares dependency dictionaries. Non-conflicting additions are tagged with commutativity $[\mathcal{T}_A, \mathcal{T}_B] = 0$.
- Conflicting version constraints (e.g. `^1.0.0` vs `^2.0.0`) are tagged as non-commutative with high risk ($\Omega \ge 0.8$).

### Decision 4: Migration DAG Engine, Framework Auto-Discovery & Metadata Journal Tracking
- **Framework Auto-Discovery & Config Sniffers**:
  GDSS automatically sniffs the repository's migration framework and custom directory paths from root configuration files:
  - `alembic.ini`: extracts `script_location` (e.g. `script_location = alembic/versions` or `migrations/versions`)
  - `drizzle.config.{ts,js,json}`: extracts `out` folder (e.g. `./drizzle`, `./db/migrations`)
  - `prisma/schema.prisma` or `schema.prisma`: detects Prisma migration directories (`prisma/migrations/**`)
  - `knexfile.{js,ts}`: extracts `migrations.directory`
  - `flyway.conf`: extracts `flyway.locations` (e.g. `filesystem:db/migration`)
  - `manage.py` / `settings.py`: auto-discovers Django app migration packages (`**/migrations/**`)
  - `package.json` / `pyproject.toml`: detects ORM packages (`drizzle-orm`, `prisma`, `typeorm`, `alembic`, `django`, `tortoise-orm`) to calibrate path patterns.
  - `.gdss.yml`: allows explicit user overrides via `migrations.paths` and `migrations.framework`.
- **Exhaustive Directory Path Patterns**:
  Normalizes and monitors all historical and modern directory naming variations:
  - `**/migrations/**`, `**/migration/**`, `**/migrate/**`, `**/db/migrate/**`, `**/db/migrations/**`, `**/database/migrations/**`
  - `alembic/versions/**`, `alembic/**`
  - `prisma/migrations/**` (timestamped folders containing `migration.sql`)
  - `drizzle/**`, `db/migrations/meta/*.json`, `drizzle/meta/*.json`
  - `supabase/migrations/**`, `hasura/migrations/**`
  - `typeorm/migrations/**`, `src/migration/**`
  - `flyway/sql/**`, `db/migration/**` (e.g. `V1__*.sql`, `V2__*.sql`)
  - `goose/migrations/**`, `golang-migrate` (`*.up.sql`, `*.down.sql`)
- **Metadata Journal & Snapshot Collisions (`db/migrations/meta/*.json`, `_journal.json`)**:
  - In modern toolchains like Drizzle ORM, schema transitions are logged in `_journal.json` with sequential entry indices (`idx: 0, 1, 2...`) and schema snapshots (`meta/*_snapshot.json`).
  - The reducer parses `_journal.json` and snapshot files: if two branches independently append entries with the same `idx` or claim the same sequence number, GDSS flags a **`MigrationJournalClash`** with precise index conflict details.
- **Topological Parent Matching & Split-Head Detection**:
  - Extracts parent identifiers across all flavors:
    - Alembic: `down_revision = '...'` or tuple of revisions
    - Django: `dependencies = [('app_name', '0001_initial')]`
    - Drizzle: `entries[].idx` sequence and snapshot tags in `_journal.json`
    - Prisma / Rails / Flyway / Supabase: timestamp prefixes (`YYYYMMDDHHMMSS_*` or `V<version>__*.sql`)
  - If two branches create new migration files sharing the identical parent revision or colliding sequence numbers, GDSS synthesizes a `SplitHeadHazard` operator with critical severity ($\Omega = 1.0$) and generates an automated re-parenting command for rebasing.

### Decision 5: Sandboxed Lockfile Regeneration Policy
- The AI Convergence Assistant is strictly forbidden from outputting unified diffs for lockfiles (`pnpm-lock.yaml`, `package-lock.json`, `poetry.lock`, `Cargo.lock`).
- When a manifest patch is validated in the ephemeral Git sandbox, the test runner detects lockfile presence and executes the corresponding native lockfile update command before running syntax and test gates.

### Decision 6: SQL Schema Semantic Extractor
- Implements a deterministic DDL tokenizer for `CREATE TABLE`, `ALTER TABLE`, `ADD COLUMN`, `DROP COLUMN`, `RENAME TO`.
- Emits symbols formatted as `table::<table_name>` and `column::<table_name>.<column_name>`.
- Enables cross-file dependency call graph links between application queries and database schema definitions.

---

## Testing Decisions

### What Makes a Good Test
- Tests must verify external behavior through public APIs (`extract_trajectory_operators`, `audit_pr_collisions`, `compute`), not private internal regexes or helper methods.
- Tests must use realistic multi-file fixtures (real `package.json` diffs, real Alembic migration files, real SQL DDL schemas).
- Tests must prove that non-code concurrent edits produce non-zero $\Omega_{ij}$ scores and actionable collision details.

### Modules to Test
- `gdss/reducers/manifest_reducer.py`: Test non-overlapping additions, overlapping version clashes, and malformed JSON/TOML handling.
- `gdss/reducers/migration_reducer.py`: Test Alembic two-head detection, Prisma migration sequence collisions, and sequential migrations that do not conflict.
- `gdss/reducers/sql_reducer.py`: Test DDL table/column extraction, schema modifications, and syntax errors.
- `gdss/reducers/markdown_reducer.py`: Test heading-based chunking and commutative list additions.
- `gdss/core/trajectory.py`: Test that non-code files now generate semantic operators and are not discarded.
- `gdss/validation/pr_audit.py`: Test end-to-end PR Collision Radar generation across manifest and migration collisions.

### Prior Art
- `tests/core/test_ast_parser.py`: Multi-language Tree-sitter AST tests.
- `tests/conflict/test_commutativity.py`: Commutativity matrix verification.
- `tests/validation/test_pr_audit.py`: PR radar comment generation and risk scoring.

---

## Out of Scope

- **Arbitrary Binary Files**: Image assets (`.png`, `.jpg`), audio/video files, and compiled binaries (`.wasm`, `.jar`) will only be reported as file-level collisions; deep binary semantic merging is out of scope.
- **Automated Database Migration Execution**: GDSS will detect split-heads and recommend re-parenting, but will never execute database migrations against a live database instance.
- **Deep Semantic Proofs for Complex SQL Queries**: Full SQL query rewriting and semantic relational algebra equivalence proofs belong to future research tracks.

---

## Further Notes

This specification transforms GDSS into a production-complete platform capable of operating across heterogeneous enterprise codebases. It eliminates the single largest class of real-world false negatives while honoring the core GDSS invariants: zero token bleed for deterministic analysis, sandboxed validation before human review, and never auto-merging without explicit human consent.
