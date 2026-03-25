# pytest: skip
#!/usr/bin/env python3
"""Analyze Qiskit code generation benchmark results."""

import json
from collections import defaultdict
from pathlib import Path

# Load benchmark data
benchmark_file = Path("docs/examples/instruct_validate_repair/qiskit_code_validation/benchmarking/run_20260320_174220/benchmark_20260320_174220.json")
with open(benchmark_file) as f:
    data = json.load(f)

results = data["results"]
print(f"Model: {data['model']}")
print(f"Total cases: {data['summary']['total']}")
print(f"Passed: {data['summary']['passed']} ({data['summary']['passed']/data['summary']['total']*100:.1f}%)")
print(f"Failed: {data['summary']['failed']} ({data['summary']['failed']/data['summary']['total']*100:.1f}%)")
print(f"Max repair attempts: {data['max_repair_attempts']}")
print("\n" + "="*80 + "\n")

# 1. Pass rate by context mode
print("1. PASS RATE BY CONTEXT MODE")
print("-" * 80)
context_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
for r in results:
    mode = r["context_mode"]
    context_stats[mode]["total"] += 1
    if r["success"]:
        context_stats[mode]["passed"] += 1
    else:
        context_stats[mode]["failed"] += 1

for mode in ["none", "system_prompt", "grounding", "both"]:
    stats = context_stats[mode]
    pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
    print(f"{mode:15s}: {stats['passed']:3d}/{stats['total']:3d} passed ({pass_rate:5.1f}%)")

# Pass rate by context mode and category
print("\nPass rate by context mode and category:")
context_category_stats = defaultdict(lambda: defaultdict(lambda: {"total": 0, "passed": 0}))
for r in results:
    mode = r["context_mode"]
    cat = r["category"]
    context_category_stats[mode][cat]["total"] += 1
    if r["success"]:
        context_category_stats[mode][cat]["passed"] += 1

categories = sorted(set(r["category"] for r in results))
print(f"\n{'Category':<20s} | {'none':>10s} | {'sys_prompt':>10s} | {'grounding':>10s} | {'both':>10s}")
print("-" * 80)
for cat in categories:
    row = f"{cat:<20s}"
    for mode in ["none", "system_prompt", "grounding", "both"]:
        stats = context_category_stats[mode][cat]
        if stats["total"] > 0:
            rate = stats["passed"] / stats["total"] * 100
            row += f" | {stats['passed']:2d}/{stats['total']:2d} {rate:4.0f}%"
        else:
            row += f" | {'N/A':>10s}"
    print(row)

print("\n" + "="*80 + "\n")

# 2. System prompt variant comparison
print("2. SYSTEM PROMPT VARIANT COMPARISON")
print("-" * 80)
sys_prompt_stats = defaultdict(lambda: {"total": 0, "passed": 0})
for r in results:
    if r["sys_prompt_name"] is not None:
        variant = r["sys_prompt_name"]
        sys_prompt_stats[variant]["total"] += 1
        if r["success"]:
            sys_prompt_stats[variant]["passed"] += 1

for variant in ["inline", "chat", "codegen"]:
    stats = sys_prompt_stats[variant]
    if stats["total"] > 0:
        pass_rate = stats["passed"] / stats["total"] * 100
        print(f"{variant:10s}: {stats['passed']:3d}/{stats['total']:3d} passed ({pass_rate:5.1f}%)")

# By context mode
print("\nSystem prompt variants by context mode:")
sys_prompt_mode_stats = defaultdict(lambda: defaultdict(lambda: {"total": 0, "passed": 0}))
for r in results:
    if r["sys_prompt_name"] is not None:
        variant = r["sys_prompt_name"]
        mode = r["context_mode"]
        sys_prompt_mode_stats[mode][variant]["total"] += 1
        if r["success"]:
            sys_prompt_mode_stats[mode][variant]["passed"] += 1

for mode in ["system_prompt", "both"]:
    print(f"\n{mode}:")
    for variant in ["inline", "chat", "codegen"]:
        stats = sys_prompt_mode_stats[mode][variant]
        if stats["total"] > 0:
            pass_rate = stats["passed"] / stats["total"] * 100
            print(f"  {variant:10s}: {stats['passed']:2d}/{stats['total']:2d} ({pass_rate:5.1f}%)")

print("\n" + "="*80 + "\n")

# 3. Repair efficiency
print("3. REPAIR EFFICIENCY")
print("-" * 80)
attempt_stats = defaultdict(lambda: defaultdict(int))
for r in results:
    mode = r["context_mode"]
    attempts = r["attempts"]
    attempt_stats[mode][attempts] += 1

print("Distribution of attempts by context mode:")
print(f"{'Mode':<15s} | {'1st try':>8s} | {'2-3 tries':>10s} | {'4-6 tries':>10s} | {'7-10 tries':>11s} | {'Avg':>6s}")
print("-" * 80)
for mode in ["none", "system_prompt", "grounding", "both"]:
    stats = attempt_stats[mode]
    first = stats.get(1, 0)
    two_three = sum(stats.get(i, 0) for i in [2, 3])
    four_six = sum(stats.get(i, 0) for i in [4, 5, 6])
    seven_plus = sum(stats.get(i, 0) for i in range(7, 11))
    
    # Calculate average attempts for successful cases
    successful_attempts = [r["attempts"] for r in results if r["context_mode"] == mode and r["success"]]
    avg = sum(successful_attempts) / len(successful_attempts) if successful_attempts else 0
    
    print(f"{mode:<15s} | {first:8d} | {two_three:10d} | {four_six:10d} | {seven_plus:11d} | {avg:6.2f}")

print("\n" + "="*80 + "\n")

# 4. Code quality issues (sample failed cases with success=true)
print("4. CODE QUALITY REVIEW (Sample of passing cases)")
print("-" * 80)
print("Checking for potential hallucinations in 'success: true' cases...\n")

# Sample some passing cases to check for quality issues
suspicious_patterns = []
for r in results[:50]:  # Check first 50 for efficiency
    if r["success"]:
        code = r["generated_code"].lower()
        issues = []
        
        # Check for common hallucination patterns
        if "from qiskit import aer" in code and "qiskit.aer" not in code:
            issues.append("Deprecated 'from qiskit import Aer' pattern")
        if "get_backend" in code and "aer" in code:
            issues.append("Using deprecated get_backend() method")
        if "statevector_simulator" in code:
            issues.append("Using deprecated simulator name")
            
        if issues:
            suspicious_patterns.append({
                "prompt_id": r["prompt_id"],
                "context_mode": r["context_mode"],
                "issues": issues,
                "code_snippet": r["generated_code"][:200]
            })

if suspicious_patterns:
    for sp in suspicious_patterns[:5]:  # Show first 5
        print(f"Prompt: {sp['prompt_id']} ({sp['context_mode']})")
        print(f"Issues: {', '.join(sp['issues'])}")
        print(f"Code: {sp['code_snippet']}...")
        print()
else:
    print("No obvious quality issues detected in sampled passing cases.")

print("\n" + "="*80 + "\n")

# 5. Failure patterns
print("5. FAILURE PATTERNS")
print("-" * 80)
failed_cases = [r for r in results if not r["success"]]
print(f"Total failed cases: {len(failed_cases)}\n")

# Count QKT rule violations
rule_violations = defaultdict(int)
for r in failed_cases:
    errors = r["validation_errors"]
    # Extract QKT codes (e.g., QKT100, QKT110)
    import re
    qkt_codes = re.findall(r'QKT\d+', errors)
    for code in qkt_codes:
        rule_violations[code] += 1

print("Most common QKT rule violations in failed cases:")
for rule, count in sorted(rule_violations.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {rule}: {count} violations")

# Failed cases by context mode
print("\nFailed cases by context mode:")
failed_by_mode = defaultdict(int)
for r in failed_cases:
    failed_by_mode[r["context_mode"]] += 1
for mode in ["none", "system_prompt", "grounding", "both"]:
    print(f"  {mode:15s}: {failed_by_mode[mode]:2d} failures")

print("\n" + "="*80 + "\n")

# 6. Prompt difficulty
print("6. PROMPT DIFFICULTY")
print("-" * 80)
prompt_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
for r in results:
    pid = r["prompt_id"]
    prompt_stats[pid]["total"] += 1
    if r["success"]:
        prompt_stats[pid]["passed"] += 1
    else:
        prompt_stats[pid]["failed"] += 1

# Find hardest prompts (lowest pass rate)
prompt_difficulty = []
for pid, stats in prompt_stats.items():
    pass_rate = stats["passed"] / stats["total"] * 100
    prompt_difficulty.append((pid, pass_rate, stats["passed"], stats["total"]))

prompt_difficulty.sort(key=lambda x: x[1])

print("Hardest prompts (lowest pass rate across all configurations):")
for pid, rate, passed, total in prompt_difficulty[:10]:
    print(f"  {pid:<35s}: {passed:2d}/{total:2d} ({rate:5.1f}%)")

print("\nPrompts that no configuration could pass:")
impossible = [p for p in prompt_difficulty if p[1] == 0]
if impossible:
    for pid, rate, passed, total in impossible:
        print(f"  {pid}")
else:
    print("  None - all prompts had at least one passing configuration")

print("\n" + "="*80 + "\n")

# 7. Recommendation
print("7. RECOMMENDATION")
print("-" * 80)
print("Based on the benchmark results:\n")

# Find best overall context mode
best_mode = max(context_stats.items(), key=lambda x: x[1]["passed"] / x[1]["total"])
print(f"Best overall context mode: '{best_mode[0]}'")
print(f"  Pass rate: {best_mode[1]['passed']}/{best_mode[1]['total']} ({best_mode[1]['passed']/best_mode[1]['total']*100:.1f}%)")

# Find best system prompt variant
best_variant = max(sys_prompt_stats.items(), key=lambda x: x[1]["passed"] / x[1]["total"])
print(f"\nBest system prompt variant: '{best_variant[0]}'")
print(f"  Pass rate: {best_variant[1]['passed']}/{best_variant[1]['total']} ({best_variant[1]['passed']/best_variant[1]['total']*100:.1f}%)")

# Calculate repair efficiency for best mode
best_mode_results = [r for r in results if r["context_mode"] == best_mode[0]]
first_try_success = sum(1 for r in best_mode_results if r["success"] and r["attempts"] == 1)
print(f"\nRepair efficiency for '{best_mode[0]}':")
print(f"  First-try success: {first_try_success}/{len(best_mode_results)} ({first_try_success/len(best_mode_results)*100:.1f}%)")

avg_attempts = sum(r["attempts"] for r in best_mode_results if r["success"]) / sum(1 for r in best_mode_results if r["success"])
print(f"  Average attempts (successful cases): {avg_attempts:.2f}")

print("\n" + "="*80)