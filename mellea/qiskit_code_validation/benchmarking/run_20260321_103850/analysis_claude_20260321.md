# Qiskit Model Baseline Analysis
**Run:** `benchmark_20260321_103850.json`
**Model:** `hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest` (none/none, 45 prompts)
**Comparison:** `granite4:micro-h` none/none from `benchmark_20260320_174220.json`

---

## Pass Rate Comparison

| Model | Mode | Passed | Pass rate |
|---|---|---|---|
| Qiskit (large, specialized) | none/none | 44/45 | **97.8%** |
| granite4:micro-h | none/none | 37/45 | 82.2% |
| granite4:micro-h | best (both/inline) | 42/45 | 93.3% |

The Qiskit model without any context (97.8%) outperforms granite's best configuration (93.3%). It also nearly matches what we'd expect from a model with Qiskit knowledge baked in — the one failure (`QKT200-pulse-fix-03`) appears to be a genuinely hard prompt that even the specialized model can't solve.

---

## Code Quality: The Core Question

The main reason to run this comparison was to check whether the Qiskit model's passes are actually runnable vs granite's false positives. The difference is stark.

### QKT100-opflow-fix-01

**Granite (PASS, 1 attempt):** Completely ignored the opflow task. Generated a generic bell circuit with `transpile(qc, basic_qubit=True)` (not a valid argument) — passes QKT only because it avoids deprecated imports by ignoring the task entirely.

**Qiskit model (PASS, 1 attempt):**
```python
from qiskit.quantum_info import SparsePauliOp
operator = SparsePauliOp.from_list([('ZZ', 1.0), ('XX', 0.5)])
```
Correct. Uses the actual modern replacement for `PauliSumOp`. Cites the migration guide.

### QKT100-execute-fix-01

**Granite (PASS, 1 attempt):** Imports `from qiskit.aero.aer import AerSimulator` — `qiskit.aero` does not exist (misspelling of `qiskit_aer`). Code would fail on import.

**Qiskit model (PASS, 1 attempt):**
```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
simulator = AerSimulator()
isa_circuit = transpile(qc, simulator)
result = simulator.run(isa_circuit, shots=1024).result()
```
Correct. Proper `qiskit_aer` package, correct transpile+run pattern, correct import.

### QKT100-generate-01 (GHZ state)

**Granite (PASS, 9 attempts):** After 9 attempts uses `from qiskit_aer import Simulator` (class doesn't exist — it's `AerSimulator`) and `StatevectorSimulator` (also wrong). Code would fail on import.

**Qiskit model (PASS, 1 attempt):**
```python
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
aer_sim = AerSimulator(method='statevector')
result = aer_sim.run(qc).result()
statevector = result.get_statevector()
```
Correct. Right class, right method, right pattern.

### multi-deprecated-basicaer-01

**Granite (FAIL, 10 attempts):** Could not converge across any attempt.

**Qiskit model (PASS, 2 attempts):**
```python
from qiskit_aer import AerSimulator, QuantumCircuit
backend = AerSimulator()
qc = QuantumCircuit(5, 5)
qc.h(0)
qc.cx(0, range(1, 5))
qc.measure_all()
```
Note: `QuantumCircuit` imported from `qiskit_aer` is unusual (should be `qiskit`) but this is minor — the deprecated patterns are all fixed correctly.

### general-list-fake-backends-01

**Granite (PASS, 1 attempt):** Uses `IBMQ.backends()` — `IBMQ` was removed in Qiskit 1.0. This is a false positive: the validator catches the import path but granite's code uses the removed provider anyway and passes.

**Qiskit model (PASS, 1 attempt):** Uses `GenericBackendV2` from `qiskit.providers.fake_provider` — the correct modern replacement. However, the model also asked a clarifying question before generating (conversational behavior from the chat-style training), which is worth noting for production use.

---

## The Only Failure: QKT200-pulse-fix-03

Both models fail this prompt with 10 attempts. The Qiskit model attempts:
```python
from qiskit.pulse import Constant, Gaussian, Drag
my_pulse = Gaussian(duration=256, amp=0.5, sigma=64).get_waveform()
```
This imports from `qiskit.pulse` which is the deprecated path — the model knows about the pulse API but can't correctly apply the QKT200 migration for this specific case. This is the same systematic issue flagged in the granite analysis: the QKT200 pulse prompts may require migration patterns the models don't know yet, and the validator coverage may also be incomplete.

---

## Key Findings

**1. The Qiskit model solves the false positive problem.** Where granite produces hallucinated APIs that happen to avoid deprecated patterns, the Qiskit model produces correct, runnable code with proper imports and explanations. The 97.8% pass rate is a meaningful number, not an inflated one.

**2. Model knowledge is the bottleneck for granite, not the IVR pattern.** The repair loop can't fix what the model doesn't know. Granite's 9-attempt pass on QKT100-generate-01 that still produces wrong class names shows the repair loop thrashing rather than converging.

**3. Context helps granite but doesn't close the gap.** Granite's best config (both/inline, 93.3%) still trails the Qiskit model running with no context at all (97.8%). The gap is model knowledge, not context provision.

**4. The one shared failure (QKT200-pulse-fix-03) likely indicates a validator gap.** If a model purpose-built for Qiskit migration can't pass this prompt in 10 attempts, either the migration path is genuinely ambiguous or the QKT rule isn't providing actionable enough feedback for repair.

---

## Recommendation

The Qiskit model is the clear quality target. For production use of this example with a small model:

- The IVR pattern + context is a reasonable approximation but users should know they're trading quality for resource cost
- `both/inline` is still the right granite config
- Any validation improvement (execution-based checking) would disproportionately benefit the small model runs since those are where false positives concentrate
- `QKT200-pulse-fix-03` should be investigated as a potential validator gap regardless of model
