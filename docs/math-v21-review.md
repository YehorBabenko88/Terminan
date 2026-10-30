# Math v2.1 independent review record

Reviewer performed read-only review of the working increment against exact PR52. Two important findings were reproduced with self-consistent forged digests:

1. A formula availability timestamp could move before its source availability after recomputing outputSHA256. Added a RED regression and temporal metadata propagation checks; GREEN covers pointwise, lag, rolling, binary/overlay/compare and calculus boundaries. No numerical sample values are recalculated.
2. A declared dimensionless formula result could be relabeled USD with a matching output hash. Added a RED regression and exact declared-unit/port-type checks; GREEN. No unit algebra is duplicated; compound syntax remains server-owned.

Additional regression verifies that a downstream formula consuming comparison:mae uses that scalar port's hash, not comparison's default series hash. Source/provenance/reference and false authority flags remain bound. No deferred important findings in this reviewed scope.

Ruling: request audit data for every actual dependency and default output. This is necessary to recompute data SHA256 instead of trusting an opaque trace claim. Cost: additional output bytes/value budget, subject to stricter local64-output/2MiB limits and independent Math work/value limits. Visual results exclude audit-only outputs, while snapshots retain the verified raw reply.

Ruling: preserve legacy editor model as a user formula; new engine-model maps to pinned fixed Math model contracts. Cost: two explicitly different block kinds rather than silent schema reinterpretation. V2.0 pin is preserved in a separate lock and tested against the real old engine. All new operations require revision/features/named-port support.
