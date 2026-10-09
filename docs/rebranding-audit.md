# Pyulix rebranding audit — 2026-10-09

Scope: the `ajayrakde/Operix` fork, based on `python/java-api-parity`, and public
PyPI JSON metadata for `oculix-operix`. This is a source/packaging audit, not a
trademark clearance or legal opinion about every bundled dependency.

## Findings and changes

| Finding | Resolution |
|---|---|
| Python metadata named Julien Mer and his personal email as package author | Ajay Rakde is author and maintainer; GitHub Issues is the support contact |
| Fork distribution and import namespace contained upstream branding | `pyulix` distribution and namespace; imports, generated stubs, tests, tools and examples migrated |
| Root README described upstream packages and Julien as current maintainer | Replaced with Pyulix documentation and prominent independent-fork notice |
| Python README lacked the same notice | Notice is first content, including in the built PyPI description |
| Python license was a symlink outside the package root | Physical unchanged copy, SPDX metadata, explicit LICENSE/NOTICE inclusion and archive verification |
| Runtime cache remained under `.oculix` | Pyulix downloads use `.pyulix/lib`; Java dependency identities remain unchanged |
| Inherited npm/NuGet metadata and publishing paths claimed upstream identity | Fork maintainer/URLs corrected, npm private, NuGet packing disabled, publishing workflows disabled; sources clearly marked as inherited references |
| Java requirement said 11 despite the engine's Java 17 requirement | Active Python documentation/error message now say Java 17 |
| No gecko file found in tracked source | Original friendly snake/eye artwork added; no upstream mascot copied |
| Shaded JAR could collapse duplicate notices | Added Apache NOTICE merging and a separate copy of the fork LICENSE/NOTICE; full dependency notice verification remains pending |

Original `LICENSE` is unchanged: Copyright (c) 2026 oculix-org. Julien and
contributors remain credited. Technical references to OculiX, Java class names,
Maven coordinates, historical documents and inherited reference sources remain
where necessary; these are not presented as Pyulix's own trademarks or authorship.

## Live services and unresolved items

- Public PyPI metadata still reports `oculix-operix` 1.1.1 as the default version;
  published releases include 1.1.0, 1.1.1 and 1.2.0b1. The default description and
  author email are still the old ones. Source edits do not update those artifacts.
- `pyulix` returned HTTP 404 from PyPI during the check. This is not a reservation,
  guaranteed registry acceptance, or trademark clearance. No package was uploaded
  by this audit.
- Target release is 1.2.0b2, explicitly beta. Publishing needs a token/trusted
  publisher authorized for the new project; an old project-scoped token is not
  sufficient. Do not print or commit tokens.
- The old project needs a migration/deprecation notice and a deliberate retirement
  decision after the replacement works. Do not silently delete existing releases.
- Repository slug remains `ajayrakde/Operix`; all links point to that real fork.
  No upstream repository or release was modified.
- The downloaded JVM bundle contains upstream Java/native dependencies whose own
  licenses apply. A full resolved dependency/native license inventory and inspection
  of the final shaded JAR are still required before claiming complete clearance.
  A README MIT label alone does not establish the license of the entire bundle.
- Local Maven could not resolve Maven Central through its network configuration;
  JVM/desktop checks and final JAR notice inspection were not completed locally.
- The new logo/icon were AI-generated for this fork. No claim of exclusive rights
  or independently verified trademark availability is made.

## Verification

- Generated API/stub consistency check passed: 240 types, 3,420 declared signatures.
- Python suite: 33 passed, 32 skipped (JVM/desktop prerequisites unavailable).
- Wheel and source archive built successfully; `twine check` passed.
- Wheel contains only `pyulix` and its distribution metadata, no `oculix` package.
- Wheel and source archive preserve LICENSE bytes exactly and include NOTICE.
- Clean installation alongside official `oculix` 1.0.0: no overlapping wheel
  paths; both imports work and Pyulix uses its own module identities and cache.

## Packaging references

- https://packaging.python.org/en/latest/specifications/pyproject-toml/
- https://pypi.org/help/#file-name-reuse

PyPI does not allow replacement files with already-used distribution filenames.
Use a new version when publishing corrected package metadata.
