# CI Failure Triage Bot

When a CI run goes red, someone has to work out which failures are real bugs. This tool reads the
run's **JUnit XML reports**, **groups failures by root cause**, labels each group as a **product
bug, test bug, environment problem or flaky test**, and posts the result as a **pull-request comment**
or CI job summary.

Python 3.10+ (standard library only) · JUnit/TestNG/pytest XML · GitHub Actions · optional Amazon Bedrock

## How it decides

1. **Rerun and history first.** A test that fails, then passes on a rerun of the same commit is
   flaky, whatever its error says. Without a rerun, a test that failed in some but not all of
   the last builds is flaky too.
2. **Group by root cause.** Each error is fingerprinted by its type and normalized message
   (numbers, ids and timestamps removed), so `expected [108.25] but found [100.0]` and
   `expected [216.5] but found [200.0]` are one bug hit by two tests. Near-identical messages
   are merged.
3. **Label with rules**, in order:
   - **environment**: connection refused, DNS, 502/503, out of memory, browser failed to start
   - **test**: missing locators, stale elements, exceptions thrown inside test code or test data
   - **product**: 5xx responses and failed assertions on product behaviour
   - **unknown**: nothing matched. Left for a person, or for the LLM step.
4. **Optional LLM step** (`--llm bedrock`): writes a short root-cause summary for every group and
   decides the label only for low-confidence groups. It can pick only from the known labels.

## Try it

```bash
pip install -e ".[dev]"
pytest -q

triagebot analyze --reports "samples/run/*.xml" --rerun "samples/rerun/*.xml" --history "samples/history/*/*.xml"
cat out/triage.md

triagebot evaluate --labels samples/labels.json --reports "samples/run/*.xml" --rerun "samples/rerun/*.xml" --history "samples/history/*/*.xml"
```

The sample is an invented 24-test shop suite with 9 failures: a tax bug hit by 2 tests, an API
returning 500, a database that was down, a broken locator, a null test-data object, and two
flaky tests. The triage puts them in 7 groups and matches all 9 expected labels.

Example output (trimmed):

```
## Test triage: 9 failed tests in 7 groups (24 tests run)

| Category | Groups | Tests |
|---|---|---|
| Product bugs | 2 | 3 |
| Test bugs | 2 | 2 |
| Environment problems | 1 | 2 |
| Flaky tests | 2 | 2 |

### Product bugs
**1. AssertionError** (2 tests, confidence 75%)
- Why: an assertion on product behaviour failed; failed again on rerun
- Error: `expected [108.25] but found [100.0]`
- Tests: `CheckoutTests.totalIncludesTax`, `CheckoutTests.totalIncludesTaxForMultipleItems`
```

## Use it in your own pipeline

```yaml
- name: Triage failures
  if: failure()
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    pip install git+https://github.com/vedant-bakliwal/ci-failure-triage
    triagebot analyze --reports "target/surefire-reports/*.xml" --github-summary \
      --pr-comment ${{ github.event.pull_request.number }}
```

Add `--rerun` with the reports of a rerun of failed tests to detect flaky tests, and
`--fail-on product` to fail the job only when a real product bug is found.

### With Amazon Bedrock

```bash
pip install -e ".[bedrock]"
aws sso login --profile triage
eval "$(aws configure export-credentials --profile triage --format env)"
triagebot analyze --reports "samples/run/*.xml" --rerun "samples/rerun/*.xml" --llm bedrock
```

On-demand calls only, one per failure group. Default model: `us.amazon.nova-lite-v1:0`
(`BEDROCK_MODEL_ID` to change it).

## Layout

| File | What it does |
|---|---|
| `reports.py` | JUnit XML parsing for the current run, a rerun, and build history |
| `signature.py` | Normalization, fingerprints, similarity, top user-code frames |
| `classify.py` | Flakiness evidence and the labelling rules |
| `triage.py` | Grouping and merging |
| `llm.py` | Optional Bedrock review |
| `summary.py`, `cli.py` | Markdown summary, PR comment, job summary, accuracy evaluation |

## License

MIT
