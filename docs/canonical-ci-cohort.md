# Canonical SDK source checks

Status: NO_GO until exact-head jobs and remaining native/data gates pass.

The previous workflow was invalid YAML on line 36: an unquoted plain run scalar contained a colon followed by a space in --only-binary=:all:. The dependency command now uses a block scalar. The Math SDK is pinned to de8194f71311a6d7dddb69be9de812030ed1f13f and Data to ecc2c5d95997bfb68dd2242bca4146184e0485f3. The separate historical parity job installs canonical Math because execution and sizing now delegate to that owner.

Windows and Linux wheel jobs compare every runtime member against raw Git blobs before installing the three wheels together outside the source checkout. Checkout conversion is disabled for those exact-source inputs. The check is source consistency, not publisher authentication. Proof JSON is retained as a workflow artifact. The verifier independently accepted the corrected d4bb wheel and rejected its archive-converted predecessor at terminan/__init__.py; no hash was changed to admit the bad wheel.

Local installed-cohort validation ran the existing four history/levels tests using only the canonical isolated wheel site. Native service, installer and protection changes were not run. Full hosted tests, browser flow and process-fault gates remain enabled in CI and require their own current-SHA evidence.

Independent QA found that the installed constructor smoke initially preceded Math installation. The job now installs the three exact built wheels together before any PaperEngine constructor, avoiding a false standalone success or missing-kernel failure.

Feature commits run through pull-request events once; pushes to main retain their own check. Per-PR concurrency cancels superseded runs. This avoids duplicate push/PR matrices for an unchanged candidate. No manual rerun on unchanged code is requested.
