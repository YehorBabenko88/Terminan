# ROUND 19 — exact PEP 517 sdist invocation fix

Pinned Terminan source SHA:
\`89022d7885d279bb1fd2f695b59f2c243b431ad2\`.

Original failed workflow:
\`45892975159\`, two failed wheel-install jobs on Python 3.12:
Windows \`140159905606\`, Ubuntu \`140159905759\`.

Both raw job logs show the exact failure **after successfully building all
three wheels**, on one command:

\`\`\`
python -c "from setuptools import build_meta; build_meta.build_sdist('dist/sdist')"
ModuleNotFoundError: No module named 'setuptools'
\`\`\`

Why: PEP 517's wheel build uses **build isolation**, so Python 3.12's
outer environment need not have setuptools installed. Directly importing
the backend in that environment is inconsistent with the existing declared
\`pyproject.toml\` build system:
\`requires = ["setuptools>=75,<83", "wheel"]\`.

The existing wheel-install job now builds the sdist with:

\`\`\`
python -m pip download --no-deps --no-binary :all: --no-cache-dir --dest dist/sdist .
python tests/check_archive_artifact_exclusion.py --wheel-dir dist/terminan --sdist-dir dist/sdist
\`\`\`

This is a **PEP 517 isolated source distribution build**, using the exact
existing pinned backend constraint. \`--no-deps\` forbids resolving runtime
dependencies; \`--no-binary :all:\` forces sdist output; \`--no-cache-dir\`
prevents a previously cached artifact from satisfying this proof.
\`pip download .\` builds the local project artifact and does not fetch
the project from a registry; build dependencies are resolved by PEP 517
from the existing declared backend constraint.

**Fail closed**: output still must be one actual \`*.tar.gz\` and exactly
one Terminan wheel. The existing archive member scanner checks both
archives; the immutable Git-byte wheel checker, isolated installed wheel
smoke and installed SDK checks all remain. No skipped/removed checks,
no second packager, no production/real orders, no native E2E claims.

Original Python 3.11 Windows/Ubuntu wheel jobs
\`140159905340\` and \`140159905925\` already gave
\`ARCHIVED_HISTORICAL_PYTHON_EXCLUSION=PASS wheel_members=89 sdist_members=226\`.
These prove the original archive scanner worked on two platforms, not
that the new fix has passed Python 3.12. The new HEAD must earn its own CI.

The historical HIGH/LOW adapter remains **post-close retrospective only**,
no \`ResearchSignal\` or earlier decision clock in production; all historical
hypotheses remain SPEC_ONLY.

CODE NO_GO / PRODUCTION NO_GO.


## Correction from independent local pip reproduction
The intermediate isolated \`pip download --no-binary :all: .\` invocation
can complete successfully **without saving any local-project sdist**.
A local pip 25.1.1 reproduction with installed setuptools emitted
"Successfully downloaded" but produced an EMPTY destination directory.
This was detected BEFORE claiming that new HEAD's tests had passed.
The hard exactly-one-sdist archive scanner would fail, but the invocation
is not suitable. Replace the command immediately with an explicit
\`setuptools.build_meta.build_sdist\` call AFTER installing the existing
strict \`pyproject.toml\` backend range to this ephemeral CI job:

\`\`\`
python -m pip install --no-deps --only-binary=:all: "setuptools>=75,<83" "wheel"
python -c "from setuptools import build_meta; build_meta.build_sdist('dist/sdist')"
python tests/check_archive_artifact_exclusion.py --wheel-dir dist/terminan --sdist-dir dist/sdist
\`\`\`

This does not add or import a production dependency: the CI job's Python
environment is disposable. The declared backend constraint is used, no
non-binary build dependencies and no runtime dependency resolution allowed.
Source wheel/sdist archive checks remain required; no PASS is asserted for
this latest revision before its exact workflow logs are inspected.
