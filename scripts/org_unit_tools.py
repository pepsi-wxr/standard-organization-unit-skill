#!/usr/bin/env python3
"""中国机构主数据标准化工具。

本文件中的辅助函数刻意保持确定性，用来完成技能中可重复执行的部分：
机构名称规范化、统一社会信用代码校验、候选重复机构分组、缺失代码补充建议。
存在歧义的机构匹配仍然需要人工或模型复核。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


USCC_CHARS = "0123456789ABCDEFGHJKLMNPQRTUWXY"
USCC_WEIGHTS = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
PLACEHOLDERS = {"", "0", "1", "无", "暂无", "NULL", "NAN", "NONE", "-", "--"}


def clean_text(value: object) -> str:
    """清洗单个值，便于比对，同时保留有意义的文本。"""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if text.lower() == "nan":
        return ""
    text = re.sub(r"\s+", "", text)
    return text


def strip_punctuation(value: object) -> str:
    """去除等价名称中常见的差异性标点。"""
    text = clean_text(value)
    return re.sub(r"[（）()【】\[\]{}《》、，,。.;；:：\"'“”‘’·\-_/\\]", "", text)


def canonical_name(value: object) -> str:
    """返回便于比对的机构名称，并使用受控同义词归一化。

    替换规则覆盖常见行政区简称和机构尾缀变体。这里刻意避免宽泛模糊改写，
    防止把带编号的学校、社区、大队、科室等不同机构误合并。
    """
    text = strip_punctuation(value)
    replacements = [
        ("新疆维吾尔自治区", "新疆"),
        ("伊犁哈萨克自治州", "伊犁州"),
        ("昌吉回族自治州", "昌吉州"),
        ("巴音郭楞蒙古自治州", "巴州"),
        ("博尔塔拉蒙古自治州", "博州"),
        ("克孜勒苏柯尔克孜自治州", "克州"),
        ("有限责任公司", "有限公司"),
        ("集团有限责任公司", "集团有限公司"),
        ("人民政府", "政府"),
        ("村民委员会", "村委会"),
        ("居民委员会", "居委会"),
        ("社区居民委员会", "社区居委会"),
        ("管理委员会", "管委会"),
        ("科学技术", "科技"),
        ("文化体育广播电视和旅游", "文广旅游"),
        ("住房和城乡建设", "住建"),
        ("人力资源和社会保障", "人社"),
        ("卫生健康委员会", "卫健委"),
        ("市场监督管理", "市场监管"),
        ("城市管理行政执法", "城管执法"),
        ("发展和改革委员会", "发改委"),
        ("纪律检查委员会", "纪委"),
        ("网络安全和信息化委员会办公室", "网信办"),
        ("政法委员会", "政法委"),
        ("人民代表大会常务委员会", "人大常委会"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r"中共(.+?)委员会", r"\1委", text)
    text = re.sub(r"中国共产党(.+?)委员会", r"\1委", text)
    return text


def canonical_core(value: object) -> str:
    """返回更严格的核心名称，只处理尾缀差异导致的等价写法。

    适用于“某某社区”和“某某社区居民委员会”这类成对写法。
    这里只处理少量通常指向同一基层或街道单位的组织尾缀。
    """
    core = canonical_name(value)
    for old, new in [
        ("社区居委会", "社区"),
        ("居委会", ""),
        ("村委会", "村"),
        ("街道办事处", "街道"),
        ("街道办", "街道"),
    ]:
        if core.endswith(old):
            return core[: -len(old)] + new
    return core


def validate_uscc(value: object) -> dict[str, str | bool]:
    """按统一社会信用代码校验位规则进行本地校验。

    这只能证明代码结构有效，不能证明该代码一定属于传入的机构名称。
    """
    raw = clean_text(value).upper()
    if raw in PLACEHOLDERS:
        return {"clean": raw, "status": "缺失", "valid": False, "expected_check_char": ""}
    if len(raw) != 18:
        return {"clean": raw, "status": "长度不是18位", "valid": False, "expected_check_char": ""}
    bad = sorted({c for c in raw if c not in USCC_CHARS})
    if bad:
        return {
            "clean": raw,
            "status": "包含非法字符:" + "".join(bad),
            "valid": False,
            "expected_check_char": "",
        }
    # 统一社会信用代码校验位：对前17位字符做加权求和。
    total = sum(USCC_CHARS.index(raw[i]) * USCC_WEIGHTS[i] for i in range(17))
    expected = USCC_CHARS[(31 - total % 31) % 31]
    if raw[-1] != expected:
        return {
            "clean": raw,
            "status": "校验位错误",
            "valid": False,
            "expected_check_char": expected,
        }
    return {"clean": raw, "status": "本地校验通过", "valid": True, "expected_check_char": expected}


def load_table(path: Path, sheet: str | None) -> list[dict[str, object]]:
    """读取逗号分隔文件或电子表格，并将每一行保留为字典。"""
    if path.suffix.lower() in {".xlsx", ".xls"}:
        try:
            import pandas as pd
        except ImportError as exc:
            raise SystemExit("读取电子表格需要当前运行环境安装 pandas 和 openpyxl。") from exc
        frame = pd.read_excel(path, sheet_name=sheet or 0, dtype=str).fillna("")
        return frame.to_dict(orient="records")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """写出带签名的 UTF-8 逗号分隔文件，方便表格软件正确打开中文。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def audit(args: argparse.Namespace) -> None:
    """执行完整批量核对，并写出所有结果文件。"""
    rows = load_table(Path(args.input), args.sheet)
    out_dir = Path(args.out_dir)
    enriched: list[dict[str, object]] = []

    for idx, row in enumerate(rows, start=2):
        # 表格第1行通常是表头，所以数据行从第2行开始计数。
        name = row.get(args.name_col, "")
        short = row.get(args.short_col, "") if args.short_col else ""
        code = row.get(args.code_col, "") if args.code_col else ""
        area = row.get(args.area_col, "") if args.area_col else ""
        check = validate_uscc(code)
        enriched.append(
            {
                **row,
                "excel_row": idx,
                "norm_name": canonical_name(name),
                "norm_short": canonical_name(short),
                "core_name": canonical_core(name),
                "core_short": canonical_core(short),
                "area_key": canonical_name(area),
                "uscc_clean": check["clean"],
                "uscc_status": check["status"],
                "uscc_expected_check_char": check["expected_check_char"],
                "uscc_valid_local": check["valid"],
            }
        )

    semantic_groups = find_semantic_groups(enriched)
    code_conflicts = find_code_conflicts(enriched)
    suggestions = find_fill_suggestions(enriched, semantic_groups)

    write_csv(out_dir / "organization_audit.csv", enriched)
    write_csv(out_dir / "semantic_duplicate_candidates.csv", semantic_groups)
    write_csv(out_dir / "uscc_duplicate_conflicts.csv", code_conflicts)
    write_csv(out_dir / "uscc_fill_suggestions.csv", suggestions)

    summary = {
        "rows": len(enriched),
        "valid_local_uscc": sum(1 for row in enriched if row["uscc_valid_local"]),
        "missing_uscc": sum(1 for row in enriched if row["uscc_status"] == "缺失"),
        "invalid_nonblank_uscc": sum(
            1 for row in enriched if row["uscc_status"] not in {"缺失", "本地校验通过"}
        ),
        "semantic_duplicate_rows": len(semantic_groups),
        "semantic_duplicate_groups": len({row["group_id"] for row in semantic_groups}),
        "uscc_conflict_rows": len(code_conflicts),
        "uscc_conflict_groups": len({row["group_id"] for row in code_conflicts}),
        "fill_suggestions": len(suggestions),
        "out_dir": str(out_dir),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def find_semantic_groups(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """根据规范化名称证据查找候选相同机构组。"""
    buckets: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    variant_buckets: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        area = str(row["area_key"])
        # 同一区域内规范化名称或核心名称完全一致，是较强信号。
        for key in ["norm_name", "core_name"]:
            value = str(row[key])
            if value:
                buckets[(area, value)].append(row)
        # 交叉比对全称和简称，用来发现别名式重复。
        for key in ["norm_name", "norm_short", "core_name", "core_short"]:
            value = str(row[key])
            if len(value) >= 6:
                variant_buckets[(area, value)].append(row)

    group_rows: list[dict[str, object]] = []
    seen: set[tuple[int, str]] = set()
    group_id = 1
    for source, reason, confidence in [
        (buckets, "同一区域内规范化名称或核心名称相同", "高"),
        (variant_buckets, "同一区域内全称和简称规范化后互相命中", "中高"),
    ]:
        for (_area, key), members in source.items():
            ids = sorted({int(row["excel_row"]) for row in members})
            if len(ids) < 2:
                continue
            marker = tuple(ids)
            if (hash(marker), reason) in seen:
                continue
            seen.add((hash(marker), reason))
            for row in sorted(members, key=lambda item: int(item["excel_row"])):
                group_rows.append(
                    {
                        "group_id": group_id,
                        "confidence": confidence,
                        "reason": reason,
                        "match_key": key,
                        "excel_row": row["excel_row"],
                        "name": row.get("jgmc", row.get("name", "")),
                        "short_name": row.get("jgjc", row.get("short_name", "")),
                        "uscc_clean": row["uscc_clean"],
                        "area": row.get("xzqymc", ""),
                    }
                )
            group_id += 1
    return group_rows


def find_code_conflicts(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """列出出现在多行中的有效统一社会信用代码，供复核。"""
    by_code: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["uscc_valid_local"]:
            by_code[str(row["uscc_clean"])].append(row)
    conflicts: list[dict[str, object]] = []
    group_id = 1
    for code, members in by_code.items():
        if len(members) < 2:
            continue
        for row in members:
            conflicts.append(
                {
                    "group_id": group_id,
                    "uscc_clean": code,
                    "excel_row": row["excel_row"],
                    "name": row.get("jgmc", row.get("name", "")),
                    "short_name": row.get("jgjc", row.get("short_name", "")),
                    "area": row.get("xzqymc", ""),
                    "issue": "同一有效代码出现在多行，需要核实是同一机构还是数据冲突",
                }
            )
        group_id += 1
    return conflicts


def find_fill_suggestions(
    rows: list[dict[str, object]], semantic_group_rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    """当语义重复组内只有一个有效代码时，为缺失项提出补充建议。"""
    by_row = {int(row["excel_row"]): row for row in rows}
    by_group: dict[object, list[dict[str, object]]] = defaultdict(list)
    for row in semantic_group_rows:
        by_group[row["group_id"]].append(row)

    suggestions: list[dict[str, object]] = []
    for group_id, members in by_group.items():
        source_rows = [by_row[int(member["excel_row"])] for member in members]
        valid_codes = sorted({str(row["uscc_clean"]) for row in source_rows if row["uscc_valid_local"]})
        if len(valid_codes) != 1:
            # 没有代码时需要官方查询；多个代码时说明存在冲突。
            continue
        for row in source_rows:
            if row["uscc_valid_local"]:
                continue
            suggestions.append(
                {
                    "group_id": group_id,
                    "target_excel_row": row["excel_row"],
                    "target_name": row.get("jgmc", row.get("name", "")),
                    "current_uscc": row.get("tyshxydm", ""),
                    "suggested_uscc": valid_codes[0],
                    "confidence": "需复核",
                    "basis": "同一语义重复组内只有一个本地校验通过的代码",
                }
            )
    return suggestions


def main() -> None:
    parser = argparse.ArgumentParser(description="核对并标准化中国机构记录。")
    subparsers = parser.add_subparsers(required=True)

    validate_parser = subparsers.add_parser("validate-code")
    validate_parser.add_argument("code")
    validate_parser.set_defaults(func=lambda args: print(json.dumps(validate_uscc(args.code), ensure_ascii=False)))

    normalize_parser = subparsers.add_parser("normalize-name")
    normalize_parser.add_argument("name")
    normalize_parser.set_defaults(
        func=lambda args: print(
            json.dumps(
                {"norm_name": canonical_name(args.name), "core_name": canonical_core(args.name)},
                ensure_ascii=False,
            )
        )
    )

    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("input")
    audit_parser.add_argument("--sheet")
    audit_parser.add_argument("--name-col", default="jgmc")
    audit_parser.add_argument("--short-col", default="jgjc")
    audit_parser.add_argument("--code-col", default="tyshxydm")
    audit_parser.add_argument("--area-col", default="xzqymc")
    audit_parser.add_argument("--out-dir", default="org-unit-audit-output")
    audit_parser.set_defaults(func=audit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
