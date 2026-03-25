# Qiskit Code Generation Benchmark Analysis Report

**Model:** `granite4:micro-h`  
**Date:** March 20, 2026  
**Total Cases:** 360 (45 prompts × 8 context configurations)  
**Overall Pass Rate:** 85.8% (309/360)

---

## Executive Summary

This benchmark evaluated a small LLM's ability to generate Qiskit quantum computing code that passes `flake8-qiskit-migration` (QKT) validation rules. The model was tested across 8 context configurations combining system prompts (none/inline/chat/codegen) with grounding context (QKT migration rules).

**Key Findings:**
- **Best configuration:** `both` mode (system prompt + grounding) with `inline` variant achieved **93.3% pass rate**
- **Repair loop effectiveness:** 56.3% first-try success rate; average 1.97 attempts for successful cases
- **Critical limitation:** `success: true` does NOT guarantee runnable code—many passing cases contain hallucinated APIs
- **Hardest prompt:** `multi-deprecated-basicaer-01` (37.5% pass rate) requiring simultaneous fixes across multiple QKT rules

---

## 1. Pass Rate by Context Mode

| Context Mode | Pass Rate | Passed/Total |
|--------------|-----------|--------------|
| **both** (system + grounding) | **89.6%** | 121/135 |
| **system_prompt** | 85.9% | 116/135 |
| **none** | 82.2% | 37/45 |
| **grounding** | 77.8% | 35/45 |

### Analysis
- **`both` mode is the clear winner**, providing the best overall pass rate
- Adding grounding context alone (`grounding` mode) actually **decreased** performance vs. no context (`none`)
- System prompts alone (`system_prompt`) provided moderate improvement
- The combination of both (`both`) showed synergistic benefits

### Pass Rate by Category

| Category | none | system_prompt | grounding | both |
|----------|------|---------------|-----------|------|
| **general** | 83% (5/6) | 78% (14/18) | 67% (4/6) | **94% (17/18)** |
| **multi_rule** | 50% (1/2) | 67% (4/6) | 50% (1/2) | **83% (5/6)** |
| **qiskit1_imports** | **100% (8/8)** | 83% (20/24) | 62% (5/8) | 83% (20/24) |
| **qiskit1_kwargs** | **100% (3/3)** | **100% (9/9)** | **100% (3/3)** | 89% (8/9) |
| **qiskit1_methods** | 83% (5/6) | 89% (16/18) | 83% (5/6) | **100% (18/18)** |
| **qiskit2_imports** | 88% (7/8) | **92% (22/24)** | 88% (7/8) | 83% (20/24) |
| **qiskit2_kwargs** | 67% (4/6) | 89% (16/18) | **100% (6/6)** | **100% (18/18)** |
| **qiskit2_methods** | 67% (4/6) | 83% (15/18) | 67% (4/6) | 83% (15/18) |

**Insights:**
- `both` mode excels at **general** tasks (94%) and **multi-rule** fixes (83%)
- Simple import fixes (qiskit1_imports) work well even without context
- Keyword argument fixes (kwargs) have high success across all modes
- Method deprecations are more challenging, especially for Qiskit 2.x

---

## 2. System Prompt Variant Comparison

### Overall Performance

| Variant | Pass Rate | Passed/Total |
|---------|-----------|--------------|
| **inline** | **92.2%** | 83/90 |
| **chat** | 87.8% | 79/90 |
| **codegen** | 83.3% | 75/90 |

### By Context Mode

**system_prompt mode:**
- `inline`: 91.1% (41/45)
- `chat`: 91.1% (41/45)
- `codegen`: 75.6% (34/45)

**both mode:**
- `inline`: **93.3% (42/45)** ← Best overall
- `chat`: 84.4% (38/45)
- `codegen`: 91.1% (41/45)

### Analysis
- **`inline` variant consistently outperforms** across both modes
- The condensed, focused `inline` prompt (22 lines) beats the verbose `chat` (83 lines) and `codegen` (227 lines) prompts
- `codegen` performs poorly in `system_prompt` mode but recovers when combined with grounding context
- **Recommendation:** Use `inline` variant for best results with this model size

---

## 3. Repair Efficiency

### First-Try Success vs. Repair Iterations

| Context Mode | 1st Try | 2-3 Tries | 4-6 Tries | 7-10 Tries | Avg Attempts |
|--------------|---------|-----------|-----------|------------|--------------|
| **both** | 76 (56.3%) | 30 | 8 | 21 | **1.97** |
| **none** | 25 (55.6%) | 6 | 4 | 10 | 1.95 |
| **grounding** | 22 (48.9%) | 9 | 2 | 12 | 1.91 |
| **system_prompt** | 68 (50.4%) | 24 | 16 | 27 | 2.37 |

### Analysis
- **More context does NOT significantly reduce repair iterations**
- `both` mode has highest first-try success (56.3%) but similar average attempts (1.97)
- `system_prompt` mode actually requires MORE attempts on average (2.37)
- The repair loop is effective: most cases pass within 3 attempts
- **21 cases in `both` mode required 7-10 attempts**, suggesting some prompts are inherently difficult

---

## 4. Code Quality Issues (Beyond Pass/Fail)

### ⚠️ CRITICAL FINDING: Hallucinations in Passing Cases

**The QKT validator only checks for deprecated API usage—it cannot detect:**
- Incorrect but non-deprecated imports
- Hallucinated classes/methods that don't exist
- Wrong constructor arguments
- Logic errors

### Examples of Passing Code with Quality Issues

**1. Deprecated `get_backend()` still used (passes QKT but won't run):**
```python
from qiskit.aer import Aer
backend = Aer.get_backend('statevector_simulator')  # Deprecated method
```
- **Issue:** QKT100 only checks import path, not method usage
- **Found in:** Multiple configurations including `none`, `system_prompt`, `both`

**2. Missing imports for used classes:**
```python
from qiskit import QuantumCircuit, AerSimulator  # AerSimulator not in qiskit
sim = AerSimulator()  # Should be from qiskit_aer
```
- **Issue:** Hallucinated import path
- **Found in:** `both` mode with `inline` variant

**3. Potentially incorrect API usage:**
```python
# Uses StatevectorSimulator without proper import
# May be hallucinating the class name
```

### Recommendation
**Manual code review is essential** even for `success: true` cases. The 85.8% pass rate is inflated—actual runnable code rate is likely **significantly lower**.

---

## 5. Failure Patterns

### Most Common QKT Rule Violations (in failed cases)

| Rule | Violations | Description |
|------|------------|-------------|
| **QKT100** | 60 | Qiskit 1.x import path issues (Aer, execute, etc.) |
| **QKT200** | 25 | Qiskit 2.x import path issues |
| **QKT201** | 5 | Qiskit 2.x channel/pulse API changes |
| **QKT101** | 3 | Qiskit 1.x method deprecations (e.g., `.cnot()`) |

### Failed Cases by Context Mode

| Mode | Failures |
|------|----------|
| **system_prompt** | 19 |
| **both** | 14 |
| **grounding** | 10 |
| **none** | 8 |

### Analysis
- **QKT100 (Qiskit 1.x imports) is the biggest challenge**, accounting for 60 violations
- The model struggles with `qiskit.Aer` → `qiskit_aer.Aer` migration
- `qiskit.execute` removal is particularly difficult to fix correctly
- Syntax errors appear in some cases (e.g., malformed dictionaries)

### Example Failed Case: Syntax Error
```python
# Prompt: QKT100-opflow-fix-01 (grounding mode)
# Error: Invalid Python syntax: closing parenthesis ')' does not match opening parenthesis '{'
from qiskit import Aer
operator = Aer.pauli_sum.PauliSum([({'ZZ', 1.0), ('XX', 0.5)}])  # Malformed dict/tuple
```

---

## 6. Prompt Difficulty Analysis

### Hardest Prompts (Lowest Pass Rate)

| Prompt ID | Pass Rate | Category | Issue |
|-----------|-----------|----------|-------|
| **multi-deprecated-basicaer-01** | **37.5% (3/8)** | multi_rule | Multiple simultaneous fixes required |
| **QKT100-execute-fix-01** | 50.0% (4/8) | qiskit1_imports | `execute()` removal + Aer migration |
| **QKT100-generate-01** | 50.0% (4/8) | qiskit1_imports | Generate code with correct Aer imports |
| **QKT200-generate-02** | 50.0% (4/8) | qiskit2_imports | Qiskit 2.x import generation |
| **QKT201-generate-01** | 50.0% (4/8) | qiskit2_imports | Pulse/channel API generation |
| **QKT201-generate-02** | 50.0% (4/8) | qiskit2_imports | Pulse/channel API generation |

### Hardest Prompt Deep Dive: `multi-deprecated-basicaer-01`

This prompt requires fixing multiple deprecated patterns simultaneously:
- `qiskit.Aer` → `qiskit_aer.Aer`
- `qiskit.execute()` removal
- Potentially `.cnot()` → `.cx()` method changes

**Results by configuration:**
- ❌ `none` mode: Failed (10 attempts)
- ❌ `grounding` mode: Failed (10 attempts)
- ✅ `system_prompt` + `inline`: **Passed** (3 attempts)
- ❌ `system_prompt` + `chat`: Failed (10 attempts)
- ❌ `system_prompt` + `codegen`: Failed (10 attempts)
- ✅ `both` + `inline`: **Passed** (7 attempts)
- ❌ `both` + `chat`: Failed (10 attempts)
- ✅ `both` + `codegen`: **Passed** (6 attempts)

**Only 3/8 configurations succeeded**, and all required multiple repair attempts.

### Good News
**All prompts had at least one passing configuration**—no prompt was impossible for the model.

---

## 7. Recommendations

### Default Configuration
**Use `both` mode with `inline` system prompt variant**
- **Pass rate:** 93.3% (42/45)
- **First-try success:** 56.3%
- **Average attempts:** 1.97
- **Best balance** of performance and efficiency

### Alternative Configurations

**For resource-constrained scenarios:**
- Use `none` mode (82.2% pass rate, no context overhead)
- Surprisingly effective for simple import fixes

**For maximum reliability on complex tasks:**
- Use `both` mode with `codegen` variant (91.1% pass rate)
- Better at multi-rule fixes than `chat` variant

### Critical Warnings

1. **⚠️ Manual validation required:** `success: true` ≠ runnable code
   - Implement additional validation beyond QKT rules
   - Test generated code execution, not just linting

2. **⚠️ Hallucination detection needed:**
   - Check for imports from non-existent modules
   - Verify method signatures against actual Qiskit API
   - Watch for deprecated methods that QKT doesn't catch

3. **⚠️ Multi-rule fixes are challenging:**
   - Only 37.5% success on hardest prompt
   - Consider breaking complex fixes into smaller steps
   - May need human review for multi-rule scenarios

### Future Improvements

1. **Enhance validation:**
   - Add import resolution checking
   - Verify method signatures
   - Test code execution in sandbox

2. **Improve grounding context:**
   - Current grounding alone (77.8%) underperforms no context (82.2%)
   - May need better formatting or filtering of QKT rules
   - Consider examples-based grounding instead of rule dumps

3. **Optimize repair loop:**
   - 21 cases required 7-10 attempts in best mode
   - Add early stopping for syntax errors
   - Provide more specific repair guidance

4. **Model selection:**
   - Consider larger models for complex multi-rule fixes
   - Test if model size correlates with hallucination rate
   - Evaluate specialized code models

---

## Conclusion

The `granite4:micro-h` model achieves **85.8% QKT validation pass rate** with the best configuration reaching **93.3%**. However, this metric is misleading—many passing cases contain hallucinated APIs that won't execute.

**The Instruct-Validate-Repair pattern is effective** (average 1.97 attempts), but the validation layer needs strengthening beyond deprecated API detection.

**For production use:**
- Deploy with `both` + `inline` configuration
- Add execution-based validation
- Implement hallucination detection
- Require human review for multi-rule fixes
- Monitor and log all generated code for quality analysis

The benchmark reveals both the promise and limitations of small LLMs for code generation—they can learn patterns but struggle with API accuracy and complex multi-step reasoning.