# Organization Classification Reference

Use this reference when outputting `org_category` for Chinese organization/unit master data.

## Broad Categories

| Category | Typical evidence |
| --- | --- |
| Party/government organ | `人民政府`, `委员会`, `办公室`, `局`, `厅`, `委`, `人大`, `政协`, `法院`, `检察院`, `公安`, `司法`, `税务局`, `市场监督管理局`; existing type such as `党政机关` |
| Public institution | `中心`, `站`, `所`, `院`, `馆`, `队`, `服务中心`, `管理中心`, `事业单位`; public-service institution labels |
| State-owned enterprise | `国有`, `国投`, `城投`, `交投`, `文旅投`, `水务集团`, `燃气公司`, `供排水`; enterprise plus government ownership evidence |
| Private or mixed-ownership enterprise | `有限公司`, `有限责任公司`, `股份有限公司`, `集团有限公司`, `合作社`; enterprise labels without clear state-owned evidence |
| Social organization | `协会`, `学会`, `商会`, `基金会`, `联合会`, `促进会`, `民办非企业` |
| Grassroots self-governance organization | `村民委员会`, `村委会`, `居民委员会`, `居委会`, `社区` when used as a self-governance body |
| School or education institution | `学校`, `小学`, `中学`, `幼儿园`, `职业学校`, `学院`, `大学`, `教育局`; use government category for education bureaus |
| Medical/health institution | `医院`, `卫生院`, `疾控中心`, `妇幼保健`, `卫生健康委员会`; use government category for health commissions |
| Financial institution | `银行`, `信用社`, `保险`, `证券`, `金融监管`, `融资担保`, `小额贷款` |
| Utility/public service unit | `供水`, `供热`, `燃气`, `电力`, `公交`, `环卫`, `污水处理`, `公路管理`, `市政` |
| Other/needs review | Insufficient or conflicting evidence |

## Tie-Breakers

- Prefer explicit source fields (`jgdwlx_mc`, `zzjglx_mc`, `sbhmc`) over name-only inference.
- If a name contains both a government body and a subordinate public institution, classify the actual record subject, not the parent body mentioned in the name.
- `中心`, `站`, `所`, and `队` are ambiguous; inspect surrounding words and source fields.
- `社区` alone may be a place label or a self-governance unit. Treat as grassroots only when the record context indicates a unit, or when paired with `居民委员会`/`居委会`.
