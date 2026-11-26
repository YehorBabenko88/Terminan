# Round 15 — historical research-specification custody, not engine transfer

Source pin: Strattester tree \`37ff7e9d12a4d2dccd788fc493c28557dbe8bcea\`.
Owner: Terminan (agent D). Integration owner: F, sole unified-system PR #166.

The unique legacy metadata that was not preserved by the eight canonical scalp
descriptors is now available as **20 separate immutable SPEC_ONLY** records through
\`terminan.strategy_catalog.historical_strategy_specifications()\`. This preserves
research candidate names, families, literal parameter trees, source Git blobs,
and the two source-defined control baseline markers.

| Original module | Git blob | Historical specifications |
| --- | --- | ---: |
| research_levels.py | ba5a60c867fc0fc6f715a966b1a6ccfbb2ed19d5 | 5 |
| research_poc.py | e1ceb266f1c342504e21a87bad0b267127f63e90 | 4 |
| research_volatility.py | f28ef49806456f6e79481559b1a70c74f08d41d8 | 3 |
| research_smc.py | ddaa04c19a3e4aa703fdb8fafc6ef8034d199ac2 | 8 |
| Common source type | 27665b18590ef56d31e680d43d0bac9b318a8e03 | HypothesisSpec |

The source modules are preserved **byte-for-byte solely under tests/fixtures**.
The new runtime metadata module copies only literal tuples and floats; it
never imports the historical modules or calls their functions. The dynamic test
imports those archived modules and compares every original descriptor and
control flag to the canonical frozen read-only records. The existing eight scalp
descriptors retain exactly four runnable *research* generators and four specs.

**Explicitly not implemented:** trade execution for any of these 20 names,
microstructure/orderflow absorption/sweep detection, new strategy filling,
historical OI/L2 proof, Math kernels, a second PaperEngine or a second registry
of executable strategies. They remain **nontrading, non-authenticating,
SPEC_ONLY historical research metadata**. In particular a historical
\`ORDERFLOW_ABSORPTION_PROXY\` name is not permission to synthesize L2 or trade.

Future implementation work must identify a genuinely unique original callable
and prove causal clocks, Math ownership, source authentication, test parity,
spread/slippage and bounded inputs before an owner approves a new canonical
research generator. Legacy strategy families must not be promoted to
\`RESEARCH_GENERATOR\` by metadata import alone.

No change to Grid, C SQL, Root grants, unified-system integration, installed
production services or user databases. CODE NO_GO / PRODUCTION NO_GO.
