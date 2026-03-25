# pytest: skip
import json
from collections import defaultdict

with open('benchmark_20260320_125818.json', 'r') as f:
    data = json.load(f)

results = data['results']

# 1. Pass rate by context mode
mode_stats = defaultdict(lambda: {'total': 0, 'passed': 0})
prompt_category_stats = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'passed': 0}))

# 2. System prompt variant comparison
sys_prompt_stats = defaultdict(lambda: {'total': 0, 'passed': 0})

# 3. Repair efficiency
repair_stats = defaultdict(lambda: {'attempts': [], 'first_attempt_pass': 0})

# 6. Prompt difficulty
prompt_stats = defaultdict(lambda: {'total': 0, 'passed': 0})

for res in results:
    mode = res['context_mode']
    success = res['success']
    prompt = res['prompt_name']
    sys_prompt = res['sys_prompt_name']
    
    # Mode stats
    mode_stats[mode]['total'] += 1
    if success:
        mode_stats[mode]['passed'] += 1
        
    # Sys prompt stats
    if sys_prompt:
        sys_prompt_stats[sys_prompt]['total'] += 1
        if success:
            sys_prompt_stats[sys_prompt]['passed'] += 1
            
    # Repair stats
    repair_stats[mode]['attempts'].append(res['attempts'])
    if res['attempts'] == 1 and success:
        repair_stats[mode]['first_attempt_pass'] += 1
        
    # Prompt stats
    prompt_stats[prompt]['total'] += 1
    if success:
        prompt_stats[prompt]['passed'] += 1

print("--- Pass Rate by Context Mode ---")
for mode, stats in mode_stats.items():
    rate = stats['passed'] / stats['total'] * 100
    print(f"{mode}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

print("\n--- System Prompt Variant Comparison ---")
for variant, stats in sys_prompt_stats.items():
    rate = stats['passed'] / stats['total'] * 100
    print(f"{variant}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

print("\n--- Repair Efficiency ---")
for mode, stats in repair_stats.items():
    avg_attempts = sum(stats['attempts']) / len(stats['attempts'])
    first_pass_rate = stats['first_attempt_pass'] / len(stats['attempts']) * 100
    print(f"{mode}: Avg Attempts: {avg_attempts:.2f}, First Try Pass: {first_pass_rate:.1f}%")

print("\n--- Prompt Difficulty ---")
sorted_prompts = sorted(prompt_stats.items(), key=lambda x: x[1]['passed'] / x[1]['total'])
for prompt, stats in sorted_prompts:
    rate = stats['passed'] / stats['total'] * 100
    print(f"{prompt}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

# 5. Failure patterns
print("\n--- Failure Patterns ---")
failure_errors = defaultdict(int)
for res in results:
    if not res['success']:
        errors = res['validation_errors'].split('\n')
        for e in errors:
            if e.strip():
                # Extract QKT code if present
                code = e.split(':')[0] if ':' in e else e
                failure_errors[code] += 1

for code, count in sorted(failure_errors.items(), key=lambda x: x[1], reverse=True):
    print(f"{code}: {count}")
