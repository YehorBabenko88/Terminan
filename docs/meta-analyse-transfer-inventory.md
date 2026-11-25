# Meta Analyse -> owner inventory (Workstream D, unified-system#154)

Source: meta_analyse@b1a4d6a41054f0040a88dc80b585380fb6b4f323 src/meta_analyse (top-level defs).
Compared against Terminan@353d16b (AST body hash, name ignored), then against Grid@bf29f81 (PR #296), unified-system@6c569a0, math@9e6acbd, strattester@3850995.

Status: identical = AST-identical body exists in Terminan; same-name = Terminan has a different definition with that name; absent = nothing in Terminan.

Totals: 231 top-level definitions; identical in Terminan 68; same-name/different 29; absent 134.

| owner | identical | same-name | absent |
|---|---|---|---|
| Terminan | 67 | 22 | 12 |
| Grid | 1 | 3 | 89 |
| Unified | 0 | 4 | 33 |

## Per module

| module | owner | identical | same-name | absent | evidence / decision |
|---|---|---|---|---|---|
| analysis_coordinator | Terminan | 1 | 0 | 0 | fully AST-identical in Terminan |
| analysis_session | Terminan | 0 | 0 | 1 | Terminan UI orchestration over Meta Bybit ingestion; NOT ported (needs Grid feed contract) |
| archive_day_boundary | Grid | 0 | 0 | 3 | market data/ingestion -> Grid (not Terminan scope); DayBoundary: grid=identical:market_data/archive_day_boundary.py, strattester=identical:market_data/archive_day_boundary.py; utc_day_boundary: grid=name:market_data/archive_day_boundary.py, strattester=name:market_data/archive_day_boundary.py; validate_day_audit: grid=identical:market_data/archive_day_boundary.py, strattester=identical:market_data/archive_day_boundary.py |
| archive_db_import | Grid | 0 | 0 | 5 | market data/ingestion -> Grid (not Terminan scope); file_sha256: strattester=name:strattester/runtime/grid_handoff.py |
| archive_file_lock | Grid | 0 | 1 | 4 | market data/ingestion -> Grid (not Terminan scope); archive_file_lock: grid=name:market_data/archive_file_lock.py, strattester=name:market_data/archive_file_lock.py; _lock: grid=identical:market_data/archive_file_lock.py, strattester=identical:market_data/archive_file_lock.py; _unlock: grid=identical:market_data/archive_file_lock.py, strattester=identical:market_data/archive_file_lock.py; async_archive_file_lock: grid=name:market_data/archive_file_lock.py, strattester=name:market_data/archive_file_lock.py; _prepare_lock_file: grid=identical:market_data/archive_file_lock.py, strattester=identical:market_data/archive_file_lock.py |
| archive_ingestion | Grid | 0 | 1 | 7 | market data/ingestion -> Grid (not Terminan scope); ArchiveReceipt: grid=identical:market_data/archive_ingestion.py, strattester=identical:market_data/archive_ingestion.py; _digest: grid=identical:market_data/archive_ingestion.py, unified=name:unified_system/provenance_v11.py, strattester=identical:market_data/archive_ingestion.py; _receipt_path: grid=identical:market_data/archive_ingestion.py, strattester=identical:market_data/archive_ingestion.py; _load_receipt: grid=name:market_data/archive_ingestion.py, strattester=name:market_data/archive_ingestion.py; _write_receipt: grid=identical:market_data/archive_ingestion.py, strattester=identical:market_data/archive_ingestion.py; _to_thread_join_on_cancel: grid=identical:market_data/archive_ingestion.py, strattester=identical:market_data/archive_ingestion.py; acquire_archive: grid=name:market_data/archive_ingestion.py, strattester=name:market_data/archive_ingestion.py; acquire_many: grid=name:market_data/archive_ingestion.py, strattester=name:market_data/archive_ingestion.py |
| archive_partial_state | Grid | 0 | 0 | 6 | market data/ingestion -> Grid (not Terminan scope); PartialMetadata: grid=identical:market_data/archive_partial_state.py, strattester=identical:market_data/archive_partial_state.py; _sha256: grid=identical:market_data/archive_partial_state.py, strattester=identical:market_data/archive_partial_state.py; partial_paths: grid=name:market_data/archive_partial_state.py, strattester=name:market_data/archive_partial_state.py; read_partial: grid=identical:market_data/archive_partial_state.py, strattester=identical:market_data/archive_partial_state.py; save_partial: grid=identical:market_data/archive_partial_state.py, strattester=identical:market_data/archive_partial_state.py; discard_partial: grid=identical:market_data/archive_partial_state.py, strattester=identical:market_data/archive_partial_state.py |
| archive_resumable_download | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope); download_resumable: grid=name:market_data/archive_resumable_download.py, strattester=name:market_data/archive_resumable_download.py |
| archive_resume | Grid | 0 | 0 | 4 | market data/ingestion -> Grid (not Terminan scope); ResumeState: grid=identical:market_data/archive_resume.py, strattester=identical:market_data/archive_resume.py; strong_etag: grid=identical:market_data/archive_resume.py, strattester=identical:market_data/archive_resume.py; resume_headers: grid=name:market_data/archive_resume.py, strattester=name:market_data/archive_resume.py; validate_partial_response: grid=identical:market_data/archive_resume.py, strattester=identical:market_data/archive_resume.py |
| backfill | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| book_summary | Terminan | 1 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| bybit_archive_audit | Grid | 0 | 0 | 3 | market data/ingestion -> Grid (not Terminan scope); ArchiveAudit: grid=identical:market_data/bybit_archive_audit.py, strattester=identical:market_data/bybit_archive_audit.py; audit_trade_gzip: grid=name:market_data/bybit_archive_audit.py, strattester=name:market_data/bybit_archive_audit.py; _LimitedReader: grid=identical:market_data/bybit_archive_audit.py, strattester=identical:market_data/bybit_archive_audit.py |
| bybit_archive_download | Grid | 0 | 0 | 3 | market data/ingestion -> Grid (not Terminan scope); validate_archive_url: grid=identical:market_data/bybit_archive_download.py, strattester=identical:market_data/bybit_archive_download.py; download_archive: grid=name:market_data/bybit_archive_download.py, unified=name:scripts/ci_stopped_service_acceptance.py, strattester=name:market_data/bybit_archive_download.py; download_many: grid=identical:market_data/bybit_archive_download.py, strattester=identical:market_data/bybit_archive_download.py |
| bybit_archive_plan | Grid | 0 | 0 | 3 | market data/ingestion -> Grid (not Terminan scope); ArchiveDay: grid=identical:market_data/bybit_archive_plan.py, strattester=identical:market_data/bybit_archive_plan.py; archive_url: grid=name:market_data/bybit_archive_plan.py, strattester=name:market_data/bybit_archive_plan.py; plan_archive_days: grid=name:market_data/bybit_archive_plan.py, strattester=name:market_data/bybit_archive_plan.py |
| collector | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| core | Terminan | 6 | 5 | 0 | PaperEngine/Position/PaperFill: proven equivalent on valid ordered input (tests/test_meta_paper_differential.py); D1-D6 documented strictness differences. Minute/RollingFlow: Terminan analytics/core.py variants delegate arithmetic to Math (not re-proven here) |
| crossing_quality | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| crossing_service | Terminan | 0 | 0 | 1 | PORTED in this PR -> terminan/analytics/crossing_service.py (tests/test_crossing_service.py; local differential vs Meta 1000 walks) |
| desktop | Terminan | 2 | 1 | 1 | Meta Qt Window: Terminan UI owner; NOT ported - depends on Meta ingestion (BybitPublic/RawPipeline) which must come from Grid; Terminan has its own desktop.py; main: grid=name:scripts/annotate_test_failures.py, unified=name:scripts/ci_unittest.py, math=name:python/history_scientific_worker.py, strattester=name:strattester/marketdata/download_smoke_cli.py |
| desktop_service | Terminan | 0 | 0 | 3 | Terminan UI service; NOT ported (same Grid dependency as desktop.Window) |
| durable_sync | Terminan | 0 | 0 | 2 | Durable level-sync journal; Terminan level_sync intentionally has no durable-store duplicate (docstring); NOT ported by design |
| exchange | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| feed_watchdog | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| flow_bridge | Terminan | 1 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| flow_diff | Terminan | 1 | 0 | 0 | fully AST-identical in Terminan |
| flow_history_storage | Terminan | 5 | 0 | 0 | fully AST-identical in Terminan |
| flow_style | Terminan | 1 | 0 | 0 | fully AST-identical in Terminan |
| footprint | Terminan | 1 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| footprint_engine | Terminan | 0 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| freshness | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| freshness_style | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| grid_history_adapter | Terminan | 5 | 1 | 1 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| headless_service | Unified | 0 | 2 | 12 | infra/PostgreSQL/service host -> Unified (not Terminan scope); need: grid=name:grid/data_first_jobs.py, unified=name:unified_system/release_manifest.py, strattester=name:scripts/ordinary_execution_retirement_custody.py; regular: unified=name:unified_system/service_postgres.py; directory: unified=name:unified_system/data_first_workspace.py; Handler: grid=name:grid/terminan_gateway.py, strattester=name:market_data/history_api.py; main: grid=name:market_data/cli.py, unified=name:unified_system/installation_preview.py, math=name:scripts/history_ci.py, strattester=name:market_data/cli.py |
| health | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| history | Grid | 0 | 0 | 4 | market data/ingestion -> Grid (not Terminan scope); Coverage: grid=name:market_data/sqlite_history.py, strattester=name:strattester/marketdata/coverage.py |
| history_checkpoint | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| history_parallel | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope); BatchOutcome: grid=identical:market_data/history_parallel.py, strattester=identical:market_data/history_parallel.py; bounded_map: grid=name:market_data/history_parallel.py, strattester=name:market_data/history_parallel.py |
| history_progress | Grid | 0 | 0 | 5 | market data/ingestion -> Grid (not Terminan scope); Availability: strattester=name:strattester/runtime/work_schedule.py; coverage: grid=name:market_data/sqlite_history.py, strattester=name:strattester/marketdata/sqlite_store.py |
| history_retention | Unified | 0 | 0 | 3 | infra/PostgreSQL/service host -> Unified (not Terminan scope); plan_retention: unified=name:unified_system/storage/retention.py |
| http_client | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| instruments | Grid | 0 | 1 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| integrity | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| level_publish | Terminan | 1 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| level_quality | Terminan | 1 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| level_sync | Terminan | 0 | 4 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| liquidity | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| market_clock | Terminan | 3 | 0 | 0 | fully AST-identical in Terminan |
| market_collector | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| market_health | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| market_store | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| market_telemetry | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| metascalp_locator | Terminan | 0 | 1 | 0 | MetaScalp discovery; Terminan desktop.find_metascalp/external_terminal exist (different implementation, not re-proven) |
| offline_paper_delivery | Terminan | 0 | 1 | 1 | One-shot Meta->Terminan migration CLI; already writes via terminan.paper_journal/paper_ledger; keep in Meta archive until retirement; main: grid=name:grid/legacy_bootstrap_import.py, unified=name:unified_system/windows_wheels.py, math=name:python/history_scientific_worker.py, strattester=name:strattester/persistence/frozen_results.py |
| ohlcv_research_adapter | Terminan | 7 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| open_interest | Grid | 0 | 0 | 3 | market data/ingestion -> Grid (not Terminan scope); fetch_open_interest: strattester=name:strattester/marketdata/bybit_client.py |
| orderbook | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope); OrderBook: grid=name:market_data/orderbook.py, strattester=name:market_data/orderbook.py |
| orderbook_stream | Grid | 1 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope); BookSnapshot: grid=name:market_data/orderbook_stream.py, strattester=name:market_data/orderbook_stream.py; OrderBookStream: grid=name:market_data/orderbook_stream.py, strattester=name:market_data/orderbook_stream.py |
| orderflow_adapters | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| orderflow_aggregation | Terminan | 3 | 0 | 0 | fully AST-identical in Terminan |
| orderflow_archive_reader | Terminan | 1 | 0 | 0 | fully AST-identical in Terminan |
| orderflow_metrics | Terminan | 3 | 0 | 0 | fully AST-identical in Terminan |
| orderflow_view | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| pg_authorized_connection | Unified | 0 | 0 | 2 | infra/PostgreSQL/service host -> Unified (not Terminan scope) |
| pg_checkpoint_witness | Unified | 0 | 2 | 6 | infra/PostgreSQL/service host -> Unified (not Terminan scope); _identity: grid=name:grid/raw_capture.py, unified=name:unified_system/lab_observation_writer.py, strattester=name:market_data/historical_capture.py; _clock: grid=name:market_data/history_range_audit.py, unified=name:unified_system/gateway_research_identity.py, strattester=name:market_data/history_range_audit.py; _observe: grid=name:grid/authority_assignment_v1.py, unified=name:unified_system/installation_uninstall.py |
| pg_cluster_attestation | Unified | 0 | 0 | 3 | infra/PostgreSQL/service host -> Unified (not Terminan scope) |
| pg_cluster_plan | Unified | 0 | 0 | 3 | infra/PostgreSQL/service host -> Unified (not Terminan scope); PlanRefused: grid=identical:grid/coordination_commands.py, unified=identical:scheduler_components/durable.py |
| pipeline | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| ports | Terminan | 0 | 0 | 1 | MetaScalp client; Terminan external_terminal.py states port from Meta PR82 ports.py |
| raw_store | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| raw_trades | Grid | 0 | 0 | 3 | market data/ingestion -> Grid (not Terminan scope) |
| recovery | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| retention_report | Unified | 0 | 0 | 2 | infra/PostgreSQL/service host -> Unified (not Terminan scope) |
| retirement_receipt | Terminan | 5 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| runtime | Unified | 0 | 0 | 2 | infra/PostgreSQL/service host -> Unified (not Terminan scope) |
| storage | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| storage_migrations | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |
| sync_journal | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| tape_velocity | Terminan | 1 | 1 | 0 | Terminan counterpart differs (earlier port with Math delegation / renamed schema); equivalence not re-proven in this PR |
| terminal_pipeline | Terminan | 0 | 0 | 1 | Wires CrossingService to Meta RawPipeline (Grid-owned); Terminan side = CrossingService (ported); wiring awaits Grid live feed contract |
| trade_archive | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| trade_archive_audit | Grid | 0 | 0 | 2 | market data/ingestion -> Grid (not Terminan scope) |
| wall_tracker | Terminan | 2 | 0 | 0 | fully AST-identical in Terminan |
| write_drain | Grid | 0 | 0 | 1 | market data/ingestion -> Grid (not Terminan scope) |

## Non-identical definitions

| module | name | status | Terminan nearest |
|---|---|---|---|
| market_collector | MarketCollector | absent |  |
| bybit_archive_plan | ArchiveDay | absent |  |
| bybit_archive_plan | archive_url | absent |  |
| bybit_archive_plan | plan_archive_days | absent |  |
| retention_report | RetentionSummary | absent |  |
| retention_report | summarize_retention | absent |  |
| footprint_engine | FootprintEngine | same-name | analytics/footprint_engine.py:6 sim=0.70 |
| storage_migrations | initialize_archive_schema | absent |  |
| book_summary | summarize_book | same-name | analytics/book_summary.py:19 sim=0.79 |
| integrity | Quality | absent |  |
| integrity | ExecutionAggregator | absent |  |
| pg_authorized_connection | authorized_private_connection | absent |  |
| pg_authorized_connection | validate_connection_parameters | absent |  |
| storage | initialize_schema | absent |  |
| storage | Store | absent |  |
| history | Coverage | absent |  |
| history | validate_fixed_interval | absent |  |
| history | yearly_from_daily | absent |  |
| history | collect_history | absent |  |
| metascalp_locator | find_metascalp | same-name | desktop.py:240 sim=0.04 |
| ohlcv_research_adapter | _analyze | same-name | analytics/ohlcv_research.py:51 sim=0.99 |
| retirement_receipt | archive_paper_fills | same-name | migration/state_receipt.py:119 sim=0.99 |
| archive_resumable_download | download_resumable | absent |  |
| trade_archive | ArchiveManifest | absent |  |
| trade_archive | verify_archive | absent |  |
| history_progress | Availability | absent |  |
| history_progress | Segment | absent |  |
| history_progress | Progress | absent |  |
| history_progress | coverage | absent |  |
| history_progress | combined_readiness | absent |  |
| history_parallel | BatchOutcome | absent |  |
| history_parallel | bounded_map | absent |  |
| archive_db_import | file_sha256 | absent |  |
| archive_db_import | iter_rows | absent |  |
| archive_db_import | parse_trade | absent |  |
| archive_db_import | _validate_receipt | absent |  |
| archive_db_import | import_verified_archive | absent |  |
| analysis_session | AnalysisSession | absent |  |
| terminal_pipeline | build_terminal_pipeline | absent |  |
| pg_cluster_attestation | AttestationRefused | absent |  |
| pg_cluster_attestation | ExpectedCluster | absent |  |
| pg_cluster_attestation | attest_connected_cluster | absent |  |
| open_interest | OIPoint | absent |  |
| open_interest | parse_oi | absent |  |
| open_interest | fetch_open_interest | absent |  |
| runtime | DurableSinksRequired | absent |  |
| runtime | Runtime | absent |  |
| core | Minute | same-name | analytics/core.py:51 sim=0.47 |
| core | Position | same-name | paper.py:28 sim=1.00 |
| core | PaperFill | same-name | paper.py:40 sim=1.00 |
| core | PaperEngine | same-name | paper.py:84 sim=0.04 |
| core | RollingFlow | same-name | analytics/core.py:96 sim=0.99 |
| orderbook | OrderBook | absent |  |
| instruments | Instrument | absent |  |
| instruments | parse_instrument | absent |  |
| instruments | instruments | same-name | data.py:85 sim=0.12 |
| trade_archive_audit | TradeAudit | absent |  |
| trade_archive_audit | audit_trade_csv | absent |  |
| recovery | RecoveryDecision | absent |  |
| recovery | decide_recovery | absent |  |
| level_quality | verified_levels | same-name | analytics/level_quality.py:24 sim=0.21 |
| write_drain | drain_thread_write | absent |  |
| archive_ingestion | ArchiveReceipt | absent |  |
| archive_ingestion | _digest | same-name | history_protocol.py:41 sim=0.35 |
| archive_ingestion | _receipt_path | absent |  |
| archive_ingestion | _load_receipt | absent |  |
| archive_ingestion | _write_receipt | absent |  |
| archive_ingestion | _to_thread_join_on_cancel | absent |  |
| archive_ingestion | acquire_archive | absent |  |
| archive_ingestion | acquire_many | absent |  |
| history_retention | RetentionRecord | absent |  |
| history_retention | RetentionDecision | absent |  |
| history_retention | plan_retention | absent |  |
| ports | MetaScalp | absent |  |
| orderbook_stream | BookSnapshot | absent |  |
| orderbook_stream | OrderBookStream | absent |  |
| pg_cluster_plan | PlanRefused | absent |  |
| pg_cluster_plan | ClusterPlan | absent |  |
| pg_cluster_plan | plan_only | absent |  |
| tape_velocity | TapeVelocity | same-name | analytics/tape_velocity.py:17 sim=0.10 |
| raw_trades | RawExecution | absent |  |
| raw_trades | parse_public_trade | absent |  |
| raw_trades | RawTradeStream | absent |  |
| archive_partial_state | PartialMetadata | absent |  |
| archive_partial_state | _sha256 | absent |  |
| archive_partial_state | partial_paths | absent |  |
| archive_partial_state | read_partial | absent |  |
| archive_partial_state | save_partial | absent |  |
| archive_partial_state | discard_partial | absent |  |
| bybit_archive_download | validate_archive_url | absent |  |
| bybit_archive_download | download_archive | absent |  |
| bybit_archive_download | download_many | absent |  |
| bybit_archive_audit | ArchiveAudit | absent |  |
| bybit_archive_audit | audit_trade_gzip | absent |  |
| bybit_archive_audit | _LimitedReader | absent |  |
| level_sync | signature | same-name | metascalp_levels.py:19 sim=0.71 |
| level_sync | owned_id | same-name | metascalp_levels.py:28 sim=0.86 |
| level_sync | parse_rows | same-name | metascalp_levels.py:42 sim=0.55 |
| level_sync | LevelSync | same-name | analytics/level_sync.py:52 sim=0.25 |
| history_checkpoint | HistoryKey | absent |  |
| history_checkpoint | HistoryCheckpoint | absent |  |
| archive_day_boundary | DayBoundary | absent |  |
| archive_day_boundary | utc_day_boundary | absent |  |
| archive_day_boundary | validate_day_audit | absent |  |
| durable_sync | generation_for | absent |  |
| durable_sync | DurableLevelSync | absent |  |
| archive_resume | ResumeState | absent |  |
| archive_resume | strong_etag | absent |  |
| archive_resume | resume_headers | absent |  |
| archive_resume | validate_partial_response | absent |  |
| raw_store | RawStore | absent |  |
| collector | CollectorService | absent |  |
| grid_history_adapter | analyze_grid_history | absent |  |
| grid_history_adapter | _analyze | same-name | analytics/market_history.py:17 sim=0.45 |
| market_store | MarketStore | absent |  |
| footprint | Footprint | same-name | analytics/footprint.py:19 sim=0.40 |
| backfill | BackfillCoordinator | absent |  |
| headless_service | need | absent |  |
| headless_service | regular | absent |  |
| headless_service | directory | absent |  |
| headless_service | Identity | absent |  |
| headless_service | SourceVerifier | absent |  |
| headless_service | owned_profile | absent |  |
| headless_service | attest_module | absent |  |
| headless_service | selfcheck | absent |  |
| headless_service | strict_json | absent |  |
| headless_service | admitted_result | absent |  |
| headless_service | admitted_ohlcv_result | absent |  |
| headless_service | PrivateServer | absent |  |
| headless_service | Handler | same-name | server.py:20 sim=0.05 |
| headless_service | main | same-name | research_replay.py:65 sim=0.15 |
| exchange | BybitPublic | absent |  |
| crossing_service | CrossingService | absent |  |
| desktop_service | DesktopSnapshot | absent |  |
| desktop_service | _client_operation | absent |  |
| desktop_service | DesktopService | absent |  |
| http_client | ManagedAsyncClient | absent |  |
| market_telemetry | TelemetrySnapshot | absent |  |
| market_telemetry | MarketTelemetry | absent |  |
| health | StreamHealth | absent |  |
| health | HealthTracker | absent |  |
| archive_file_lock | archive_file_lock | absent |  |
| archive_file_lock | _lock | same-name | analytics/level_sync.py:54 sim=0.08 |
| archive_file_lock | _unlock | absent |  |
| archive_file_lock | async_archive_file_lock | absent |  |
| archive_file_lock | _prepare_lock_file | absent |  |
| level_publish | publication_decision | same-name | metascalp_levels.py:59 sim=0.35 |
| desktop | Window | absent |  |
| desktop | main | same-name | desktop.py:525 sim=0.29 |
| offline_paper_delivery | deliver | absent |  |
| offline_paper_delivery | main | same-name | migration/research_results.py:154 sim=0.24 |
| pipeline | RawPipeline | absent |  |
| pg_checkpoint_witness | WitnessTicket | absent |  |
| pg_checkpoint_witness | WitnessResult | absent |  |
| pg_checkpoint_witness | _lsn | absent |  |
| pg_checkpoint_witness | _identity | same-name | migration/paper_receipts.py:18 sim=0.41 |
| pg_checkpoint_witness | _clock | same-name | history_protocol.py:25 sim=0.58 |
| pg_checkpoint_witness | _observe | absent |  |
| pg_checkpoint_witness | capture_witness | absent |  |
| pg_checkpoint_witness | verify_witness | absent |  |
| flow_bridge | FlowBridge | same-name | analytics/flow_bridge.py:21 sim=0.93 |
| sync_journal | SyncRecord | absent |  |
| sync_journal | SyncJournal | absent |  |
