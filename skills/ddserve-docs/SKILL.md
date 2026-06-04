---
name: ddserve-docs
description: Use this skill for coding, debugging, configuration, tests, migrations, or dependency/API questions where current library, framework, runtime, CLI, or platform documentation would improve the answer. Use ddserve CLI searches to find vague topics, exact slugs, DevDocs paths, and installed doc pages before relying on memory.
allowed-tools: Bash(ddserve:*) Bash(jq:*) Bash(sed:*) Bash(head:*) Bash(grep:*) Bash(awk:*) Read(*)
---

# ddserve Documentation Lookup

Use `ddserve` to ground coding work in up-to-date installed DevDocs documentation instead of relying only on model memory.

## Use this skill for

- Implementing, debugging, migrating, or configuring code that depends on framework/runtime/library behavior.
- API questions where version-specific details matter, such as React hooks, TypeScript compiler options, Node APIs, Playwright locators, Vite config, Python standard library, Rust traits, SQL syntax, or CLI flags.
- Resolving uncertainty after errors, lint failures, deprecations, or dependency upgrades.

Do not use it for repository-internal facts that can be answered directly from local source files.

## Workflow

1. Identify likely technologies from the user's request, repo files, imports, lockfiles, config, or error output.
2. Check installed docsets before searching:

   ```bash
   ddserve docs installed
   ```

3. When freshness matters for a known installed docset, update it before relying on it:

   ```bash
   ddserve docs update react
   ```

4. Start with a broad semantic search when the exact page is unknown:

   ```bash
   ddserve search "react hooks dependency array" --limit 5
   ```

5. Narrow with an installed slug or language when you know the likely docset:

   ```bash
   ddserve search --slug react "useEffect dependencies" --limit 5 --format json
   ddserve search --language typescript "moduleResolution bundler" --limit 5 --format json
   ```

6. When results include a promising `pagePath`, run a slug-specific query for that path or nearby terms:

   ```bash
   ddserve search --slug react "reference/react/useeffect" --limit 3 --format json
   ddserve search --slug react "useEffect cleanup dependencies" --limit 3 --format json
   ```

7. Use the JSON fields to cite and inspect the right source:
   - `docsetSlug`, `docsetName`, `pageName`, `pagePath`, and `pageType` identify the page.
   - `text` contains the retrieved documentation chunk.
   - `installedFilePath` points to the local Markdown page when you need more surrounding context than the search chunk.
8. If a needed docset is not installed, check availability, then install only the needed slug:

   ```bash
   ddserve docs available --offline | grep -i "astro"
   ddserve docs install astro
   ```

9. If semantic search looks stale or empty for an installed docset, check embeddings:

   ```bash
   ddserve embeddings status react
   ddserve embeddings refresh react
   ```

10. Apply the docs to the coding task. Prefer documentation-backed APIs and call out the relevant docset/page in your reasoning or final answer when it influenced the solution.

## Search strategy

- Use both natural-language and symbol/path queries. For example, search `"server actions form status"` and `"useActionState"` for React form work.
- Prefer `--format json` for implementation work because it exposes full chunk text and local file paths.
- Repeat `--slug` or comma-separate slugs for cross-library questions:

  ```bash
  ddserve search --slug react,typescript "jsx children type" --limit 8 --format json
  ```

- If `--slug` fails, the slug is not installed. Use `ddserve docs installed` for exact installed slug names such as `python~3.14`, `react_router`, or `fish~4.7`.
- Keep result limits small at first. Increase only when top results are off-target.

## Output expectations

When using this skill, produce answers or code changes that reflect the retrieved docs. Do not dump raw search output unless the user asked for documentation excerpts; summarize the relevant rules, APIs, version notes, or examples and cite the docset/page names that mattered.
