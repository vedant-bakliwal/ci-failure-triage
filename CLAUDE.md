# ci-failure-triage

Python 3.10+, standard library only (boto3 is optional for the LLM step). Reads JUnit XML,
groups failures by root cause and labels each group product / test / environment / flaky.

- Tests: `pip install -e ".[dev]" && pytest -q`
- Try it: `triagebot analyze --reports "samples/run/*.xml" --rerun "samples/rerun/*.xml" --history "samples/history/*/*.xml"`
- Accuracy: `triagebot evaluate --labels samples/labels.json ...` must stay at 100% on the samples.

Rules for changes:
- A new rule needs a sample failure and an expected label in `samples/labels.json`.
- Rerun and history evidence always beat error-text rules.
- The LLM may only pick from the known labels and only overrides low-confidence rule labels.
- Tests never call the network; use the `FakeBedrock` client.
- Sample reports are invented (a fictional "shop" test suite).
