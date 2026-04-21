# Data Linkage Plan

Status: `provisional`
Last updated: `2026-04-21`

## Core principle

在外部面板数据进入仓库之前，任何“企业/城市结果”设计都只能停留在 linkage blueprint，不能假装已经可跑。

## Existing dataset: policy corpus

| Dataset | Present | Unit | Key fields already available or planned | Time field | Geo field | Industry field | Enterprise ID |
|---|---|---|---|---|---|---|---|
| Environment policy PDF corpus | Yes | policy document | `file_id`, `policy_name`, `issue_date`, `effective_date`, `issuing_authority`, `policy_type`, `policy_tools`, `pollutant_types`, `gov_level`, `referenced_policies` | `issue_date` / `effective_date` | issuing authority text; future standardized province/city code | future extracted `target_industries` | none |

## Required future datasets

| Dataset | Present | Likely unit | Primary key | Time | Geo | Industry | Link logic | Main risk |
|---|---|---|---|---|---|---|---|---|
| CEADS / emissions data | No | province-year / city-year / firm-year | admin code + year | year | province/city code | pollutant / sector | geo-year policy exposure merge | exact version not yet in repo |
| Listed-firm panel | No | firm-year | stock code + year | year | registered city / plant city | CSRC / CIC / industry code | firm-city-year exposure | registered location may differ from operating location |
| Industrial enterprise panel | No | firm-year | enterprise id + year | year | county/prefecture code | GB/T industry code | firm-geo-year exposure | identifier consistency across years |
| City macro controls | No | city-year | city code + year | year | city code | optional | city-year baseline controls | admin code harmonization |
| Patent / green innovation data | No | firm-year | firm id + year | year | firm location | patent IPC/CPC | innovation outcome merge | assignee matching and lag structure |

## Minimum linkage sequence

1. Standardize policy corpus metadata:
   - issuing authority to province/city/central code
   - issue year / effective year
   - policy tools
   - target industries
   - pollutant types

2. Build geo-year exposure:
   - central exposure
   - province-year exposure
   - city-year exposure
   - tool-specific and pollutant-specific exposure

3. Build industry-targeted exposure:
   - policy-to-industry mapping
   - pollutant-to-industry mapping
   - central x local interaction terms

4. Merge to city/firm panels:
   - deterministic keys first
   - only then fuzzy/location-repair procedures

## Match-quality metrics that must be recorded

- match rate before manual repair
- match rate after deterministic repair
- share requiring fuzzy match
- share requiring manual confirmation
- duplicate rate
- unmatched rate by year / region / industry
- sample loss relative to original panel

## Manual validation requirements for nondeterministic steps

For fuzzy match, LLM extraction, or text classification:

- save prompt and model id/version
- save parameters
- save input sample / input slice
- save raw output
- save parsed output
- save reviewer name / date
- save validation label: `accept / revise / reject`
- save error type and correction note

See:

- `data/metadata/llm_validation_log_template.csv`
- `memos/ai_workflow_audit.md`

## Current gate verdict

`BLOCKED` for causal city/firm design until at least one structured outcome panel enters the repo.
