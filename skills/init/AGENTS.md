# Repository Guidelines

## Project Structure & Module Organization
This is a Node.js project written in TypeScript. The application entry point is `src/index.ts`; keep runtime source under `src/` and avoid placing production code in test directories. Tests live in `__tests__/` and should mirror the source area they exercise when possible.

## Build, Test, and Development Commands
Use the npm scripts as the source of truth for local validation:

- `npm install` - install dependencies from the lockfile before first use.
- `npm run build` - compile the TypeScript project and catch type or emit errors.
- `npm test` - run the test suite in `__tests__/`.
- `npm run lint` - run ESLint checks for TypeScript source and tests.

Before handing off code, run `npm run lint`, `npm run build`, and `npm test`; this matches the validation expected by GitHub Actions CI.

## Coding Style & Naming Conventions
Use TypeScript throughout `src/` and tests. Let ESLint and Prettier settle formatting and style decisions rather than hand-formatting around them. Prefer clear module names that describe behavior, and keep exports from `src/index.ts` intentional so the main entry remains easy to audit.

## Testing Guidelines
Place tests under `__tests__/` and name them after the unit or behavior being covered. Use `npm test` for the full suite; when narrowing tests, keep the final validation to the full npm script so local results line up with CI.

## Commit & Pull Request Guidelines
CI runs on GitHub Actions, so PRs should be ready to pass the npm build, test, and lint scripts. Mention any behavior change and the validation commands run in the PR description so reviewers can reproduce the result quickly.
