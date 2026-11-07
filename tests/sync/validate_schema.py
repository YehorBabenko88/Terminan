"""Preliminary schema validation, never endpoint/Windows acceptance."""
import json
import subprocess
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
ROOT = Path(__file__).resolve().parents[2]
def main():
    fixtures = json.loads(subprocess.check_output(["node", "-e", "const f=require('./tests/sync/fixtures.cjs');console.log(JSON.stringify({snapshot:f.snapshot(),event:f.event()}))"], cwd=ROOT, text=True))
    result = []
    for name, instance in [("snapshot", fixtures["snapshot"]), ("event-envelope", fixtures["event"]), ("error", {"schema_version":"1.0", "request_id":"fixture-request", "code":"RESYNC_REQUIRED", "reason":"CURSOR_EXPIRED", "retry_after_ms":1000, "evidence_refs":[]})]:
        schema = json.loads((ROOT / "docs/sync" / (name + ".schema.json")).read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        validator.validate(instance)
        assert list(validator.iter_errors({})), "empty instance accepted"
        invalid = dict(instance, unexpected=True)
        assert list(validator.iter_errors(invalid)), "unknown envelope field accepted"
        result.append({"schema":name, "meta_schema":"PASS", "positive_fixture":"PASS", "empty_and_unknown_rejection":"PASS"})
    print(json.dumps({"qualification":"SYNTHETIC_SCHEMA_ONLY", "results":result}, indent=2))
if __name__ == "__main__": main()
