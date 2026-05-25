# Leavitt chaos benchmark (2026-05-25)

Real runs against the OpenTelemetry Demo. Ground truth: the demo's flagd flag descriptions.
Leavitt = Kimi driving a Theodosia-enforced FSM. Baseline = same model, raw MCP tool calls, no FSM.

| scenario | condition | arm | report | found cause | disposition | false positive | recoveries |
|---|---|---|---|---|---|---|---|
| cart_failure | multi_fail | leavitt | Y | N | inconclusive | no | 1 |
| payment_failure | single_down | leavitt | Y | N | degraded | no | 1 |
| product_catalog_failure | multi_fail | leavitt | Y | N | inconclusive | no | 1 |
| payment_failure | single_down | baseline | Y | N | inconclusive | no | 0 |
| cart_failure | clean | baseline | Y | Y | resolved | no | 0 |
| ad_failure | clean | baseline | Y | Y | resolved | no | 0 |
| ad_failure | single_down | leavitt | Y | N | degraded | no | 1 |
| product_catalog_failure | single_down | baseline | Y | Y | degraded | no | 0 |
| ad_failure | clean | leavitt | Y | Y | resolved | no | 0 |
| ad_failure | multi_fail | baseline | Y | N | inconclusive | no | 0 |
| product_catalog_failure | clean | baseline | Y | Y | resolved | no | 0 |
| payment_failure | multi_fail | baseline | Y | N | inconclusive | no | 0 |
| payment_failure | multi_fail | leavitt | Y | N | inconclusive | no | 1 |
| recommendation_cache_failure | clean | baseline | Y | Y | resolved | no | 0 |
| cart_failure | single_down | baseline | Y | Y | degraded | no | 0 |
| recommendation_cache_failure | clean | leavitt | Y | Y | resolved | no | 0 |
| cart_failure | multi_fail | baseline | Y | N | inconclusive | no | 0 |
| recommendation_cache_failure | single_down | leavitt | Y | N | degraded | no | 1 |
| product_catalog_failure | clean | leavitt | Y | Y | resolved | no | 0 |
| product_catalog_failure | single_down | leavitt | Y | Y | degraded | no | 1 |
| recommendation_cache_failure | single_down | baseline | Y | N | inconclusive | no | 0 |
| product_catalog_failure | multi_fail | baseline | Y | N | inconclusive | no | 0 |
| recommendation_cache_failure | multi_fail | baseline | Y | N | inconclusive | no | 0 |
| payment_failure | clean | baseline | Y | Y | resolved | no | 0 |
| cart_failure | clean | leavitt | Y | Y | resolved | no | 0 |
| ad_failure | multi_fail | leavitt | Y | N | inconclusive | no | 1 |
| ad_failure | single_down | baseline | Y | N | inconclusive | no | 0 |
| recommendation_cache_failure | multi_fail | leavitt | Y | N | inconclusive | no | 1 |
| cart_failure | single_down | leavitt | Y | Y | degraded | no | 1 |
| payment_failure | clean | leavitt | Y | Y | resolved | no | 0 |

## Summary (found root cause / produced report / false positives)

| condition | Leavitt | Baseline |
|---|---|---|
| clean | 5/5 found, 0 FP | 5/5 found, 0 FP |
| multi_fail | 0/5 found, 0 FP | 0/5 found, 0 FP |
| single_down | 2/5 found, 0 FP | 2/5 found, 0 FP |
