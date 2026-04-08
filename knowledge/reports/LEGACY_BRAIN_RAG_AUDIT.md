# LEGACY_BRAIN_RAG_AUDIT

- Date: 2026-03-30
- Collection: `roxy_legacy`
- Source Root: `~/.roxy/brain/06_legacy`
- Indexer: `~/.roxy/rebuild_rag_index.py`
- Scope: RLBR-001 / RLBR-002 / RLBR-003 closeout

## Summary

The legacy brain archive is now indexed into a dedicated `roxy_legacy` Chroma collection.
The scoped indexer supports direct dry-run and scoped clear/rebuild for `roxy_legacy` without requiring a rebuild of unrelated collections.

## Observed Counts

- Legacy markdown files discovered on disk: `120`
- Legacy chunks indexed into `roxy_legacy`: `1016`
- Dry-run summary mode: `120 files / 1016 chunks`

## Collection Integrity

Post-backfill collection inventory on ROXY:

- `mindsong_docs`: `4320`
- `roxy_protocols`: `24`
- `roxy_onboarding`: `11`
- `roxy_systems`: `12`
- `roxy_api`: `19`
- `roxy_legacy`: `1016`

Observed result: unrelated collections remained present and populated after the scoped `--clear --collection roxy_legacy` run. No broad collection wipe was observed.

## Retrieval Probes

### Probe 1: architecture
Query: `FULL_CONTROL_ARCHITECTURE architecture blueprint`

Top results:
1. `FULL_CONTROL_ARCHITECTURE.md`
2. `PROJECT_SKYBEAM.md`
3. `SKYBEAM_CONSOLIDATION_PROPOSAL.md`

Verdict: strong hit quality. The intended architecture blueprint is returned as the top result.

### Probe 2: deployment
Query: `CITADEL_DEPLOYMENT_SUMMARY deployment summary`

Top results:
1. `CITADEL_COMPLETE.md`
2. `CITADEL_DEPLOYMENT_SUMMARY.md`
3. `CITADEL_MCP_ENHANCEMENTS.md`

Verdict: useful but not perfectly title-exact. Deployment-related retrieval is clearly in-family, but the title-exact target did not rank first.

### Probe 3: performance
Query: `CURSOR_PERFORMANCE_FORENSIC_REPORT cursor performance forensic report`

Top results:
1. `CURSOR_PERFORMANCE_FORENSIC_REPORT.md`
2. `CURSOR_SLOWDOWN_TOP_100_SUSPECTS.md`
3. `MAXIMUM_PERFORMANCE_STATUS.md`

Verdict: strong hit quality. The intended forensic report is returned as the top result.

## Known Gaps And Notes

- Earlier handoff notes cited roughly `110` markdown files. Live ROXY discovery now reports `120`. The audit uses the current observed count.
- Retrieval quality is good enough to be useful, but ranking is not perfectly title-exact for every query. The deployment probe demonstrates this.
- Chroma/ONNX emitted a GPU discovery warning during some query operations. It did not block indexing or retrieval.
- This pass did not rewrite or normalize the legacy source corpus. Retrieval quality still depends on the historical file naming and chunk boundaries already present in the archive.

## Acceptance Check

- Dedicated collection exists: yes (`roxy_legacy`)
- Scoped dry-run works: yes
- Scoped clear/reindex works: yes
- Indexed chunk count exceeds source file count: yes (`1016 >= 120`)
- Audit report exists and documents queries, retrieval quality, and gaps: yes

## Follow-up Recommendation

No immediate schema or collection redesign is required. If future quality tuning is needed, the clean next lever is ranking/chunk-shape improvement for the `roxy_legacy` collection rather than widening scope to unrelated collections.
