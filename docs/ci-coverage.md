# CI coverage and imported-project debt

The root package is tested as an independently installable, actively maintained application or method. The root CI quality gate explicitly checks its native Python package and root test suite rather than interpreting a blanket check across every consolidated historical project as a valid dependency matrix.

Historical source snapshots under `projects/` may have different optional dependencies (commercial solvers, CUDA, plotting, SciPy, or dataset downloads), Python paths, formatting rules, and test contracts. A root-package green check **does not mean all nested projects are verified or that their previously reported defects are fixed**. To publish or maintain a nested project, its own environment must be installed and tested in an independent scoped job. Preserve source provenance and do not declare imported code CI-clean without running its required checks.

CI migration note (2026-10-10): previous root workflows had linted and/or collected the entire `projects/` archive, stopping native-package testing on errors in unrelated projects. The CI scope was made explicit. Historical lint/import errors in those snapshots remain tracked as engineering work, rather than being represented as solved.

Current validation target: root `src/` + `tests/` (and native examples/scripts when applicable). Root CI also retains its existing smoke tests and Python-version matrix.
