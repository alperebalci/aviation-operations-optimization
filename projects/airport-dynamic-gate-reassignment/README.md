# Dynamic Airport Gate Reassignment

A rolling-horizon mixed-integer optimization baseline for airport gate assignment under delays, gate closures, aircraft/gate compatibility rules, passenger connections, and plan-stability costs.

The implementation is intentionally an exact, inspectable MILP baseline rather than a deep-RL policy. That makes hard operational constraints explicit and gives future learning-based methods a benchmark/oracle for small and medium scenarios.

## Why this project exists

Static gate plans degrade when arrival/departure times move or a gate becomes unavailable. A useful operational model must therefore balance two goals:

1. restore feasibility under the new state of the airport, and
2. avoid unnecessary last-minute gate changes that propagate passenger and handling disruption.

This project supports both pre-assignment and repeated real-time reoptimization from an updated snapshot.

## Implemented decision logic

For every flight, the MILP selects exactly one gate while enforcing:

- aircraft-size compatibility,
- international-gate eligibility,
- temporary gate closures,
- non-overlapping gate occupation windows with configurable safety buffer,
- hard freezing of flights already occupying a gate,
- soft reassignment penalties for previously planned flights,
- stronger near-term reassignment penalties inside a freeze horizon,
- terminal-preference penalties,
- remote/apron-gate penalties,
- passenger-connection walking cost using a linearized pairwise gate assignment term.

The objective is a weighted sum of disruption, terminal mismatch, remote-gate use, and connection walking passenger-minutes.

## Rolling-horizon interpretation

Call `solve_gate_assignment(...)` again whenever the operational state changes. Pass the previous plan via `previous_assignments`, the current clock via `now_minute`, and a `freeze_horizon_minutes` value.

Flights already on stand are hard-frozen. Upcoming flights remain movable, but a move is penalized; flights close to arrival receive an additional stability penalty. This avoids the brittle behavior of hard-freezing the entire near-term plan when a disruption makes it infeasible.

## Install

```bash
python -m pip install -e '.[dev]'
```

## Run the disruption demo

```bash
python -m airport_gate_reassignment
```

The demo first creates a pre-assignment, then delays flights and closes a gate before reoptimizing from the previous plan.

## Test

```bash
pytest
ruff check .
```

Tests cover overlap conflicts, aircraft/gate compatibility, international eligibility, gate closures, connection walking cost, active-flight freezing, stability penalties, and infeasibility detection.

## Minimal API example

```python
from airport_gate_reassignment import Flight, Gate, GateAssignmentProblem, solve_gate_assignment

problem = GateAssignmentProblem(
    flights=(Flight("F1", 100, 160), Flight("F2", 170, 230)),
    gates=(Gate("A1", "A"), Gate("A2", "A")),
)

plan = solve_gate_assignment(problem)
print(plan.assignments)
```

## Research connection

Recent work frames real-time gate assignment as a dynamic sequential decision problem and uses deep reinforcement learning to react to schedule changes while considering gate availability and passenger walking time:

- H. Li, X. Wu, M. Ribeiro, B. Santos, P. Zheng, *Deep reinforcement learning approach for real-time airport gate assignment*, Operations Research Perspectives 14 (2025), 100338. https://doi.org/10.1016/j.orp.2025.100338

This implementation targets a complementary role: an exact optimization baseline with transparent feasibility constraints and change penalties. It is suitable for benchmarking heuristics or DRL policies and for generating supervised/imitative training targets on smaller instances.

## Deliberate scope limits

This is not yet a full Airport Collaborative Decision Making system. It does not model towing, pushback queues, taxiway conflicts, stochastic delay distributions, gate-service crews, baggage transfer capacity, or learned policies. Those should be added only with data and validation appropriate to the operating airport.
