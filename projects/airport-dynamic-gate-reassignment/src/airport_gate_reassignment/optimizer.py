from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import inf

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from .model import (
    Flight,
    Gate,
    GateAssignmentProblem,
    GatePlan,
    OptimizationWeights,
)


class InfeasibleGatePlanError(RuntimeError):
    """Raised when no feasible gate assignment satisfies all hard constraints."""


@dataclass(frozen=True)
class _VariableIndex:
    x: dict[tuple[str, str], int]
    y: dict[tuple[int, str, str], int]
    size: int


def _aircraft_rank(aircraft_class: str) -> int:
    return {"narrowbody": 1, "widebody": 2}[aircraft_class]


def _intervals_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and start_b < end_a


def _gate_compatible(flight: Flight, gate: Gate) -> bool:
    if _aircraft_rank(flight.aircraft_class) > _aircraft_rank(gate.max_aircraft_class):
        return False
    return not (flight.international and not gate.international_capable)


def _closed_for_flight(problem: GateAssignmentProblem, flight: Flight, gate: Gate) -> bool:
    for closure in problem.closures:
        if closure.gate_id != gate.gate_id:
            continue
        if _intervals_overlap(
            flight.arrival_minute,
            flight.departure_minute + problem.gate_buffer_minutes,
            closure.start_minute,
            closure.end_minute,
        ):
            return True
    return False


def _walk_minutes(problem: GateAssignmentProblem, gate_a: Gate, gate_b: Gate) -> float:
    if gate_a.gate_id == gate_b.gate_id:
        return 0.0
    direct = problem.walking_minutes.get((gate_a.gate_id, gate_b.gate_id))
    if direct is not None:
        return float(direct)
    reverse = problem.walking_minutes.get((gate_b.gate_id, gate_a.gate_id))
    if reverse is not None:
        return float(reverse)
    return 7.0 if gate_a.terminal == gate_b.terminal else 18.0


def _build_variable_index(problem: GateAssignmentProblem) -> _VariableIndex:
    x: dict[tuple[str, str], int] = {}
    cursor = 0
    for flight in problem.flights:
        for gate in problem.gates:
            x[(flight.flight_id, gate.gate_id)] = cursor
            cursor += 1

    y: dict[tuple[int, str, str], int] = {}
    for connection_index, _ in enumerate(problem.connections):
        for gate_in in problem.gates:
            for gate_out in problem.gates:
                y[(connection_index, gate_in.gate_id, gate_out.gate_id)] = cursor
                cursor += 1
    return _VariableIndex(x=x, y=y, size=cursor)


def _build_objective(
    problem: GateAssignmentProblem,
    variables: _VariableIndex,
    previous_assignments: Mapping[str, str],
    now_minute: int | None,
    freeze_horizon_minutes: int,
    weights: OptimizationWeights,
) -> np.ndarray:
    c = np.zeros(variables.size, dtype=float)
    gate_by_id = {gate.gate_id: gate for gate in problem.gates}

    for flight in problem.flights:
        previous_gate = previous_assignments.get(flight.flight_id)
        near_term = (
            now_minute is not None
            and flight.arrival_minute >= now_minute
            and flight.arrival_minute <= now_minute + freeze_horizon_minutes
        )
        for gate in problem.gates:
            idx = variables.x[(flight.flight_id, gate.gate_id)]
            cost = 0.0
            if gate.remote:
                cost += weights.remote_gate_penalty
            if flight.preferred_terminal and gate.terminal != flight.preferred_terminal:
                cost += weights.terminal_change_penalty
            if previous_gate and gate.gate_id != previous_gate:
                cost += weights.reassignment_penalty
                if near_term:
                    cost += weights.near_term_reassignment_penalty
            c[idx] = cost

    for connection_index, connection in enumerate(problem.connections):
        for gate_in in problem.gates:
            for gate_out in problem.gates:
                idx = variables.y[(connection_index, gate_in.gate_id, gate_out.gate_id)]
                c[idx] = (
                    connection.passengers
                    * _walk_minutes(problem, gate_in, gate_out)
                    * weights.connection_walk_penalty_per_passenger_minute
                )

    unknown_previous = set(previous_assignments.values()) - set(gate_by_id)
    if unknown_previous:
        raise ValueError(f"Unknown gate(s) in previous_assignments: {sorted(unknown_previous)}")
    return c


def _build_bounds(
    problem: GateAssignmentProblem,
    variables: _VariableIndex,
    previous_assignments: Mapping[str, str],
    now_minute: int | None,
) -> Bounds:
    lower = np.zeros(variables.size, dtype=float)
    upper = np.ones(variables.size, dtype=float)

    for flight in problem.flights:
        for gate in problem.gates:
            idx = variables.x[(flight.flight_id, gate.gate_id)]
            if not _gate_compatible(flight, gate) or _closed_for_flight(problem, flight, gate):
                upper[idx] = 0.0

        if (
            now_minute is not None
            and flight.arrival_minute <= now_minute < flight.departure_minute
            and flight.flight_id in previous_assignments
        ):
            gate_id = previous_assignments[flight.flight_id]
            idx = variables.x[(flight.flight_id, gate_id)]
            if upper[idx] < 0.5:
                raise InfeasibleGatePlanError(
                    "Active flight "
                    f"{flight.flight_id} cannot remain at gate {gate_id} under current constraints"
                )
            lower[idx] = 1.0
            upper[idx] = 1.0

    return Bounds(lower, upper)


def _build_constraints(
    problem: GateAssignmentProblem,
    variables: _VariableIndex,
) -> LinearConstraint:
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    row = 0

    def add_constraint(coefficients: list[tuple[int, float]], lb: float, ub: float) -> None:
        nonlocal row
        for col, coefficient in coefficients:
            rows.append(row)
            cols.append(col)
            data.append(coefficient)
        lower.append(lb)
        upper.append(ub)
        row += 1

    for flight in problem.flights:
        add_constraint(
            [(variables.x[(flight.flight_id, gate.gate_id)], 1.0) for gate in problem.gates],
            1.0,
            1.0,
        )

    for i, flight_a in enumerate(problem.flights):
        for flight_b in problem.flights[i + 1 :]:
            if not _intervals_overlap(
                flight_a.arrival_minute,
                flight_a.departure_minute + problem.gate_buffer_minutes,
                flight_b.arrival_minute,
                flight_b.departure_minute + problem.gate_buffer_minutes,
            ):
                continue
            for gate in problem.gates:
                add_constraint(
                    [
                        (variables.x[(flight_a.flight_id, gate.gate_id)], 1.0),
                        (variables.x[(flight_b.flight_id, gate.gate_id)], 1.0),
                    ],
                    -inf,
                    1.0,
                )

    for connection_index, connection in enumerate(problem.connections):
        for gate_in in problem.gates:
            x_in = variables.x[(connection.inbound_flight_id, gate_in.gate_id)]
            for gate_out in problem.gates:
                x_out = variables.x[(connection.outbound_flight_id, gate_out.gate_id)]
                y = variables.y[(connection_index, gate_in.gate_id, gate_out.gate_id)]
                add_constraint([(y, 1.0), (x_in, -1.0)], -inf, 0.0)
                add_constraint([(y, 1.0), (x_out, -1.0)], -inf, 0.0)
                add_constraint([(y, 1.0), (x_in, -1.0), (x_out, -1.0)], -1.0, inf)

    matrix = coo_matrix((data, (rows, cols)), shape=(row, variables.size)).tocsr()
    return LinearConstraint(matrix, np.asarray(lower), np.asarray(upper))


def solve_gate_assignment(
    problem: GateAssignmentProblem,
    *,
    previous_assignments: Mapping[str, str] | None = None,
    now_minute: int | None = None,
    freeze_horizon_minutes: int = 30,
    weights: OptimizationWeights | None = None,
) -> GatePlan:
    """Solve static or rolling-horizon gate assignment as a binary MILP.

    Previous assignments are soft-stable: moving a planned flight incurs a penalty.
    Flights already occupying a gate at now_minute are hard-frozen at their current gate.
    Upcoming flights inside the freeze horizon receive an additional change penalty rather
    than a hard lock, preserving feasibility when disruptions force a reassignment.
    """

    if freeze_horizon_minutes < 0:
        raise ValueError("freeze_horizon_minutes cannot be negative")

    previous_assignments = dict(previous_assignments or {})
    flight_ids = {flight.flight_id for flight in problem.flights}
    unknown_flights = set(previous_assignments) - flight_ids
    if unknown_flights:
        raise ValueError(f"Unknown flight(s) in previous_assignments: {sorted(unknown_flights)}")

    weights = weights or OptimizationWeights()
    variables = _build_variable_index(problem)
    objective = _build_objective(
        problem,
        variables,
        previous_assignments,
        now_minute,
        freeze_horizon_minutes,
        weights,
    )
    bounds = _build_bounds(problem, variables, previous_assignments, now_minute)
    constraints = _build_constraints(problem, variables)
    result = milp(
        c=objective,
        integrality=np.ones(variables.size, dtype=np.int8),
        bounds=bounds,
        constraints=constraints,
        options={"presolve": True},
    )

    if not result.success or result.x is None:
        raise InfeasibleGatePlanError(
            f"No feasible gate plan found (status={result.status}, message={result.message})"
        )

    assignments: dict[str, str] = {}
    for flight in problem.flights:
        selected = [
            gate.gate_id
            for gate in problem.gates
            if result.x[variables.x[(flight.flight_id, gate.gate_id)]] > 0.5
        ]
        if len(selected) != 1:
            raise RuntimeError(
                f"Solver returned an invalid assignment for {flight.flight_id}: {selected}"
            )
        assignments[flight.flight_id] = selected[0]

    changed = tuple(
        sorted(
            flight_id
            for flight_id, previous_gate in previous_assignments.items()
            if assignments[flight_id] != previous_gate
        )
    )

    gate_by_id = {gate.gate_id: gate for gate in problem.gates}
    passenger_minutes = 0.0
    for connection in problem.connections:
        gate_in = gate_by_id[assignments[connection.inbound_flight_id]]
        gate_out = gate_by_id[assignments[connection.outbound_flight_id]]
        passenger_minutes += connection.passengers * _walk_minutes(problem, gate_in, gate_out)

    mip_gap = getattr(result, "mip_gap", None)
    return GatePlan(
        assignments=assignments,
        objective_value=float(result.fun),
        changed_flights=changed,
        connection_walking_passenger_minutes=float(passenger_minutes),
        mip_gap=None if mip_gap is None else float(mip_gap),
    )
