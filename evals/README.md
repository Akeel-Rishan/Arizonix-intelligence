# Synthetic evaluation cases

This directory contains small, fictional, offline cases for testing contract integrity and documenting
future behavior expectations. Every case uses `.example` domains, declares `synthetic: true`, fixes an
`as_of` time, and uses domain contract version 1.0.

From `apps/api`, validate the committed JSON Schema and every fixture:

```powershell
uv run python -m arizonix_api.evaluation
```

Regenerate the schema after an intentional model change, then inspect and commit the diff:

```powershell
uv run python -m arizonix_api.evaluation --write-schema
```

Normal validation is read-only, makes no network or model calls, checks schema/contract versions,
Pydantic fields, record references, workspace/company consistency, expectation fields, unique case IDs,
and committed-schema drift. Errors identify the failing file and validation location.

## What a passing command means

A pass means the fixtures are structurally valid. It does **not** mean an agent produced the expected
answer, and it provides no accuracy or hallucination metric. Model behavior evaluation is **not
implemented**.

The future evaluation interface should accept, separately from the fixture:

```text
case_id
system_output_contract_version
actual research outcome
actual versioned claims and evidence references
actual action/audit events
prompt version and model configuration
```

Deterministic evaluators can then check forbidden actions, missing or invented references, ownership,
classification constraints, and exact terminal outcomes. Judgment-based comparisons must report the
evaluator and rubric version and must never copy the fixture's expected result into the actual result.
