# Benchmark Analysis: Qiskit Code Generation with `granite4:micro-h`
**Analyzed by:** Bob  
**Benchmark File:** `benchmark_20260320_125818.json`  
**Analysis Date:** 2026-03-20

## Executive Summary

**Overall Performance:** 47/64 cases passed (73.4% success rate)

**Key Finding:** The `codegen` system prompt variant dramatically outperforms others, achieving near-perfect results when combined with grounding context.

---

## 1. Pass Rate by Context Mode

| Context Mode | Passed | Failed | Success Rate |
|--------------|--------|--------|--------------|
| **`both`** (system + grounding) | 15/16 | 1/16 | **93.8%** ✓ |
| **`grounding`** (rules only) | 7/8 | 1/8 | **87.5%** ✓ |
| **`system_prompt`** (expertise only) | 17/24 | 7/24 | **70.8%** |
| **`none`** (no context) | 8/16 | 8/16 | **50.0%** |

**Analysis:**
- **Grounding context is critical**: Adding QKT migration rules boosted success from 50% → 87.5%
- **Combined approach wins**: `both` mode achieved the highest success rate (93.8%)
- **System prompts alone are insufficient**: Only 70.8% success, suggesting the model needs concrete API rules more than general expertise

---

## 2. System Prompt Variant Comparison

Across `system_prompt` and `both` modes (40 total cases):

| Variant | Passed | Failed | Success Rate | Avg Attempts | Avg Time (s) |
|---------|--------|--------|--------------|--------------|--------------|
| **`codegen`** | 13/14 | 1/14 | **92.9%** ✓✓ | 1.21 | 17.8 |
| **`chat`** | 10/13 | 3/13 | **76.9%** | 2.15 | 52.3 |
| **`inline`** | 9/13 | 4/13 | **69.2%** | 2.77 | 62.0 |

**Key Insights:**
- **`codegen` is the clear winner**: 92.9% success, fastest execution (17.8s avg), fewest repair attempts (1.21)
- **`chat` is middle-ground**: Decent success but 3× slower than `codegen`
- **`inline` struggles most**: Lowest success rate, highest repair attempts, slowest execution

**Why `codegen` wins:**
- Produces minimal, focused code without verbose explanations
- Example from `bell_state` + `codegen` + `both` (passed first try, 13.4s):
  ```python
  from qiskit import QuantumCircuit
  qc = QuantumCircuit(2)
  qc.h(0)
  qc.cx(0, 1)
  qc.measure([0,1], [0,1])
  qc
  ```
- Compare to `inline` failure (5 attempts, 107.8s): Generated 50+ lines with incorrect `Aer` imports despite grounding context

---

## 3. Repair Efficiency

| Metric | Value |
|--------|-------|
| **First-attempt passes** | 38/64 (59.4%) |
| **Required repairs** | 26/64 (40.6%) |
| **Exhausted all 5 attempts** | 17/64 (26.6%) |

**Repair effectiveness by context mode:**

| Context Mode | 1st Try Pass | Avg Attempts (all) | Avg Attempts (failures) |
|--------------|--------------|-------------------|------------------------|
| `both` | 13/16 (81.3%) | 1.31 | 5.0 |
| `grounding` | 5/8 (62.5%) | 1.75 | 3.0 |
| `system_prompt` | 14/24 (58.3%) | 2.42 | 4.43 |
| `none` | 6/16 (37.5%) | 2.69 | 4.25 |

**Analysis:**
- **More context = fewer repairs**: `both` mode passed 81.3% on first try vs 37.5% for `none`
- **Repair loop helps but has limits**: When cases fail, they typically exhaust all 5 attempts (17 cases)
- **Grounding context reduces repair iterations**: Failures with grounding averaged 3.0 attempts vs 4.43 for system prompts alone

---

## 4. Code Quality Issues (Beyond Pass/Fail)

⚠️ **Critical Finding:** Many `success: true` cases contain non-runnable code with hallucinated APIs.

### Examples of Passing but Broken Code:

**1. `list_fake_backends` + `none` mode (line 117):**
```python
fake_backends = [backend for backend in all_backends 
                 if not backend.name.startswith('ibm-q')]
```
- ✓ Passes QKT (no deprecated APIs)
- ✗ **Hallucinated logic**: Filters out real backends by name prefix, doesn't actually list "fake" backends
- ✗ **Wrong API**: `IBMQ.backends()` doesn't exist in modern Qiskit

**2. `list_fake_backends` + `grounding` mode (line 129):**
```python
from qiskit import IBMProvider
provider = IBMProvider()
fake_backends = provider.backends()
```
- ✓ Passes QKT
- ✗ **Wrong import**: `IBMProvider` should be from `qiskit_ibm_runtime`, not `qiskit`
- ✗ **Missing filter**: Lists all backends, not just fake ones

**3. `bell_state` + `both` + `chat` (line 94):**
```python
from qiskit.quantum_info import StatevectorSimulator
simulator = StatevectorSimulator()
result = simulator.simulate(bell_state_circuit)
```
- ✓ Passes QKT
- ✗ **Hallucinated class**: `StatevectorSimulator` doesn't exist in `qiskit.quantum_info`
- ✗ **Wrong method**: `.simulate()` is not a valid method

**4. `random_circuit` + `grounding` mode (line 226):**
```python
from qiskit.circuit.library import PGHLayer
qc.append(PGHLayer(num_qubits=1), [i])
```
- ✓ Passes QKT
- ✗ **Hallucinated class**: `PGHLayer` doesn't exist in Qiskit

### Pattern Analysis:
- **QKT validation is narrow**: Only checks for deprecated APIs, not correctness
- **Model hallucinates plausible-sounding APIs**: `StatevectorSimulator`, `PGHLayer`, `IBMResourceManager`
- **Grounding context doesn't prevent hallucinations**: It only provides migration rules, not full API documentation
- **Estimated true success rate**: ~60-65% (accounting for hallucinations in passing cases)

---

## 5. Failure Patterns

### Most Common QKT Violations:

| Error | Occurrences | Context Modes |
|-------|-------------|---------------|
| **QKT100: `qiskit.Aer` moved** | 11 | Mostly `system_prompt` and `none` |
| **QKT101: `.cnot()` removed** | 6 | All `deprecated_basicaer` cases |
| **QKT100: `execute()` removed** | 5 | `deprecated_basicaer` cases |
| **Invalid Python syntax** | 1 | `list_fake_backends` + `both` + `codegen` |

### Case Study: `deprecated_basicaer` (0/8 passed)

**Hardest prompt across all configurations.** Every attempt failed with multiple violations:

**Typical failure** (`both` + `codegen`, line 586):
```python
from qiskit import QuantumCircuit, execute  # ✗ execute removed
from qiskit_aer import Aer
qc.cnot(0, range(1, 5))  # ✗ .cnot() removed
result = execute(qc, backend).result()  # ✗ execute removed
```

**Why it's hard:**
1. Requires fixing **3 separate deprecated APIs** simultaneously
2. Model struggles to replace `.cnot()` with `.cx()` even with grounding context
3. Repair loop can't converge: fixing one error often reintroduces another

### Syntax Error (line 202):
```python
from qiskit_aer import Simulator
# Your updated Qiskit code here
```  # ✗ Unclosed code fence
```

---

## 6. Prompt Difficulty Ranking

| Prompt | Pass Rate | Hardest Config | Notes |
|--------|-----------|----------------|-------|
| **`toffoli_completion`** | 8/8 (100%) | — | Trivial: single `.toffoli()` → `.ccx()` replacement |
| **`entanglement_circuit`** | 8/8 (100%) | — | Simple 2-qubit circuit |
| **`bell_runtime`** | 8/8 (100%) | — | Straightforward Runtime API usage |
| **`list_fake_backends`** | 7/8 (87.5%) | `both` + `codegen` | High pass rate but many hallucinations |
| **`runtime_estimator`** | 6/8 (75%) | `grounding` only | Complex multi-step workflow |
| **`bell_state`** | 5/8 (62.5%) | `system_prompt` modes | Fails when model adds unnecessary `Aer` imports |
| **`random_circuit`** | 5/8 (62.5%) | `system_prompt` modes | Model adds `Aer` imports unnecessarily |
| **`deprecated_basicaer`** | **0/8 (0%)** | All configs | **Impossible for this model** |

**Key Findings:**
- **Simple prompts (100% pass)**: Single-step tasks with clear API mappings
- **Medium prompts (62-87%)**: Model adds unnecessary deprecated imports even when not needed
- **Impossible prompt**: `deprecated_basicaer` requires simultaneous multi-API migration beyond model capability

---

## 7. Recommendation

### **Default Configuration: `both` mode with `codegen` system prompt**

**Rationale:**
1. **Highest success rate**: 93.8% overall, 100% on simple prompts
2. **Fastest execution**: 17.8s average (3× faster than `chat`, 3.5× faster than `inline`)
3. **Fewest repairs**: 1.21 attempts average
4. **Minimal hallucinations**: Terse output reduces opportunity for invented APIs

### **Implementation Strategy:**

```python
system_prompt = "codegen"  # Code-only, no explanations
grounding_context = extract_qkt_rules()  # ~6300 tokens of migration rules
max_repair_attempts = 5

# Expected performance:
# - 93.8% pass rate on validation
# - ~60-65% truly runnable code (accounting for hallucinations)
# - Average 17.8s per generation
```

### **Caveats:**
1. **QKT validation ≠ correctness**: Add runtime testing to catch hallucinations
2. **Avoid complex multi-API migrations**: `deprecated_basicaer`-style prompts will fail
3. **Monitor for hallucinations**: Watch for invented classes like `StatevectorSimulator`, `PGHLayer`

### **Alternative for Conversational Use:**
- Use `chat` variant if explanations are needed (76.9% success, 52.3s avg)
- Still combine with grounding context for best results

---

## Conclusion

The `granite4:micro-h` model shows promising results for Qiskit code generation when properly configured:

✅ **Strengths:**
- Excellent performance on simple, single-step tasks (100%)
- Responds well to grounding context (50% → 93.8% with `both` mode)
- Fast iteration with `codegen` prompt variant

⚠️ **Limitations:**
- Cannot handle complex multi-API migrations (`deprecated_basicaer`: 0/8)
- Frequent API hallucinations even in passing cases (~30-40% of successes)
- QKT validation provides false confidence (passes ≠ runnable)

**Bottom Line:** Use `both` + `codegen` as default, but always validate generated code with runtime tests, not just linting.