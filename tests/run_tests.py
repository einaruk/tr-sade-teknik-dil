#!/usr/bin/env python3
"""Run labeled cases against sade-lint.py.

Usage:
    run_tests.py                      # regression: tests/cases.json must pass 100%
    run_tests.py --measure FILE.json  # measurement: print rates, always exit 0
    run_tests.py --failures           # also list every failing case
    run_tests.py --parity UPSTREAM.py FILE [FILE ...]   # English findings == upstream

Case format: {"id", "text", "expect": [rules], "forbid": [rules], "note", "lang"?}
  expect = rules that must be flagged, forbid = rules that must not be flagged.
"""
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(linter, cases):
    """Return per-rule counters and the list of failures."""
    stats = {}
    failures = []
    for case in cases:
        findings, _ = linter.lint(case["text"], lang=case.get("lang", "auto"))
        found = {f["rule"] for f in findings}
        for rule in case.get("expect", []):
            row = stats.setdefault(rule, {"expect": 0, "hit": 0, "forbid": 0, "false": 0})
            row["expect"] += 1
            if rule in found:
                row["hit"] += 1
            else:
                failures.append((case["id"], "KAÇTI", rule, case["text"], ""))
        for rule in case.get("forbid", []):
            row = stats.setdefault(rule, {"expect": 0, "hit": 0, "forbid": 0, "false": 0})
            row["forbid"] += 1
            if rule in found:
                row["false"] += 1
                match = "; ".join(f["match"] for f in findings if f["rule"] == rule)
                failures.append((case["id"], "YANLIŞ ALARM", rule, case["text"], match))
    return stats, failures


def print_table(title, stats):
    print(f"**{title}**\n")
    print("| # | Kural | Beklenen | Yakalanan | Yakalama % | Yasak | Yanlış alarm | Yanlış alarm % |")
    print("|---|---|---|---|---|---|---|---|")
    total = {"expect": 0, "hit": 0, "forbid": 0, "false": 0}
    for index, rule in enumerate(sorted(stats), 1):
        row = stats[rule]
        for key in total:
            total[key] += row[key]
        print(f"| {index} | {rule} | {row['expect']} | {row['hit']} | {pct(row['hit'], row['expect'])} | "
              f"{row['forbid']} | {row['false']} | {pct(row['false'], row['forbid'])} |")
    print(f"| | **Toplam** | {total['expect']} | {total['hit']} | {pct(total['hit'], total['expect'])} | "
          f"{total['forbid']} | {total['false']} | {pct(total['false'], total['forbid'])} |")
    return total


def pct(part, whole):
    return f"{part * 100 / whole:.0f}" if whole else "—"


def parity(linter, upstream_path, files):
    upstream = load(upstream_path, "upstream_lint")
    keys = ("file", "line", "col", "rule", "level", "match", "message")
    ok = True
    for path in files:
        text = pathlib.Path(path).read_text(encoding="utf-8")
        ours, our_words = linter.lint(text, filename=path, lang="en")
        theirs, their_words = upstream.lint(text, filename=path)
        same = ([{k: f[k] for k in keys} for f in ours] == [{k: f[k] for k in keys} for f in theirs]
                and our_words == their_words)
        ok = ok and same
        print(f"{'AYNI' if same else 'FARKLI'}  {len(theirs)} bulgu  {path}")
    return ok


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    linter = load(HERE.parent / "scripts" / "sade-lint.py", "sade_lint")
    if "--parity" in argv:
        index = argv.index("--parity")
        return 0 if parity(linter, argv[index + 1], argv[index + 2:]) else 1
    measure = "--measure" in argv
    path = pathlib.Path(argv[argv.index("--measure") + 1]) if measure else HERE / "cases.json"
    cases = json.loads(path.read_text(encoding="utf-8-sig"))
    stats, failures = run(linter, cases)
    total = print_table(f"Tablo: sade-lint.py sonuçları ({path.name}, {len(cases)} vaka)", stats)
    if "--failures" in argv or not measure:
        for case_id, kind, rule, text, match in failures:
            print(f"\n{case_id} {kind} [{rule}] {match}\n    {text!r}")
    failed = total["expect"] - total["hit"] + total["false"]
    print(f"\n{len(cases)} vaka, {failed} hatalı etiket")
    return 0 if measure or failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
