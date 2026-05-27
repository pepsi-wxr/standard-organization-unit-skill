---
name: standard-organization-unit
description: Standardize Chinese organization/unit records and compare whether institutions are semantically the same. Use when working with organization master data, institution names, unit names, aliases, administrative regions, categories, industries, unified social credit codes, duplicate detection, missing-code filling, or standard organization output for Excel/CSV/database records.
---

# Standard Organization Unit

## Core Workflow

1. Inspect the input fields before judging duplicates. Prefer columns such as full name, short name, unified social credit code, organization id, parent organization id, administrative region, address, longitude/latitude, unit type, organization type, and existing category labels.
2. Normalize names before comparison. Remove whitespace and punctuation, convert full-width characters to half-width, normalize common abbreviations, and preserve meaningful differentiators such as sequence numbers, school numbers, village names, community names, branch names, bureau names, and office/dept suffixes.
3. Separate conclusions into confidence levels:
   - `high`: same valid unified social credit code with consistent name evidence, exact normalized name, or exact official full-name/short-name equivalence.
   - `medium_high`: same administrative region plus explainable synonym/abbreviation match, such as `居民委员会` and `居委会`, `村民委员会` and `村委会`, `管理委员会` and `管委会`, or full official region name and abbreviated region name.
   - `medium`: strong similarity but missing one of code, region, or independent field evidence.
   - `needs_review`: conflicting valid codes, weak fuzzy match, cross-region match, or parent/subordinate organizations that share words but are not necessarily the same unit.
4. Do not treat similar numbered units as duplicates without additional evidence. Examples: `第二小学` vs `第三小学`, `第十社区` vs `第十一社区`, `第一纪检监察组` vs `第二纪检监察组`.
5. Output a standard organization record only with evidence and confidence. Include the original row identifiers so the user can trace each decision.

## Standard Output

Use this schema when the user asks for standard organization content:

- `standard_org_name`: recommended canonical Chinese name.
- `aliases`: known short names and historical/alternate names.
- `is_same_group_id`: duplicate group id when comparing records.
- `same_org_confidence`: `high`, `medium_high`, `medium`, or `needs_review`.
- `same_org_reason`: concise evidence for the grouping.
- `org_category`: organization/unit category.
- `industry`: industry or activity domain.
- `unified_social_credit_code`: cleaned and validated unified social credit code when available.
- `credit_code_status`: `valid_local`, `invalid_local`, `missing`, `suggested_from_same_org`, `official_lookup_required`, or `conflict`.
- `evidence_fields`: fields used for the decision, such as `jgmc`, `jgjc`, `tyshxydm`, `xzqymc`, `jgdz`.
- `source_rows`: source row numbers or ids.

## Same Organization Comparison

Use layered evidence instead of a single fuzzy score:

1. Check unified social credit code with the deterministic validator in `scripts/org_unit_tools.py`.
2. Compare normalized full names.
3. Compare normalized short names against full names within the same administrative region.
4. Apply controlled synonym rules for common government, enterprise, grassroots, and public-institution suffixes.
5. Use address, region, coordinates, parent organization, and type fields as tie-breakers.
6. Flag parent/subordinate pairs separately. `人民政府` and `人民政府办公室`, `委员会` and `委员会办公室`, `局` and `局属中心`, or `支队` and `大队` may share a code or name tokens but are not automatically the same organization.

For repeatable spreadsheet work, run:

```bash
python scripts/org_unit_tools.py audit input.xlsx --sheet Sheet1 --name-col jgmc --short-col jgjc --code-col tyshxydm --area-col xzqymc --out-dir output-dir
```

The script produces audit, semantic duplicate candidate, code conflict, and fill suggestion CSV files.

## Classification

For organization category output, read `references/classification.md` when the task needs a category taxonomy or mapping rules. Keep category output explainable and avoid overfitting to a single keyword when other fields contradict it.

Preferred broad categories:

- Party/government organ
- Public institution
- State-owned enterprise
- Private or mixed-ownership enterprise
- Social organization
- Grassroots self-governance organization
- School or education institution
- Medical/health institution
- Financial institution
- Utility/public service unit
- Other/needs review

## Industry

For industry/domain output, read `references/industry.md`. Output a broad industry when evidence is limited. When official business registration data is available, prefer the registered industry/business scope over name-only inference.

## Unified Social Credit Code

Use local validation for format and check digit. A local check can say whether a code is structurally valid; it cannot prove that the code belongs to a specific organization.

When the code is missing:

1. If the same semantic organization group has exactly one locally valid code, output it as `suggested_from_same_org` with the source row and `needs_review` unless there is strong matching evidence.
2. If multiple different valid codes appear in the same semantic group, mark `conflict` and do not choose automatically.
3. If no same-group code exists, use `official_lookup_required`. For authoritative filling, search or integrate an official source such as the national unified social credit code public query platform; for enterprises, the national enterprise credit information system may also help.
4. Never fabricate a code from an organization name.

## Quality Rules

- Preserve original data and create a reviewed output file or suggestions file rather than overwriting source columns.
- Include row numbers and reasons for every suggested duplicate, category, industry, or code fill.
- Prefer deterministic scripts for batch Excel/CSV analysis; use LLM judgment only for the evidence synthesis and ambiguous cases.
- Make uncertainty explicit. It is better to mark `needs_review` than to merge two real but similarly named units.
