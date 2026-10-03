import pytest

from airport_gate_reassignment import (
    Flight,
    Gate,
    GateAssignmentProblem,
    GateClosure,
    InfeasibleGatePlanError,
    OptimizationWeights,
    PassengerConnection,
    solve_gate_assignment,
)


def test_overlapping_flights_use_distinct_gates():
    problem = GateAssignmentProblem(
        flights=(
            Flight("F1", 100, 160),
            Flight("F2", 120, 180),
        ),
        gates=(Gate("A1", "A"), Gate("A2", "A")),
        gate_buffer_minutes=10,
    )
    plan = solve_gate_assignment(problem)
    assert plan.assignments["F1"] != plan.assignments["F2"]


def test_widebody_international_flight_uses_compatible_gate():
    problem = GateAssignmentProblem(
        flights=(Flight("F1", 100, 160, aircraft_class="widebody", international=True),),
        gates=(
            Gate("A1", "A", max_aircraft_class="narrowbody", international_capable=True),
            Gate("B1", "B", max_aircraft_class="widebody", international_capable=True),
            Gate("B2", "B", max_aircraft_class="widebody", international_capable=False),
        ),
    )
    plan = solve_gate_assignment(problem)
    assert plan.assignments == {"F1": "B1"}


def test_reassignment_penalty_keeps_previous_gate_when_feasible():
    problem = GateAssignmentProblem(
        flights=(Flight("F1", 100, 160),),
        gates=(Gate("A1", "A"), Gate("R1", "R", remote=True)),
    )
    weights = OptimizationWeights(remote_gate_penalty=5.0, reassignment_penalty=20.0)
    plan = solve_gate_assignment(
        problem,
        previous_assignments={"F1": "R1"},
        weights=weights,
    )
    assert plan.assignments["F1"] == "R1"
    assert plan.changed_flights == ()


def test_gate_closure_forces_reassignment():
    problem = GateAssignmentProblem(
        flights=(Flight("F1", 100, 160),),
        gates=(Gate("A1", "A"), Gate("A2", "A")),
        closures=(GateClosure("A1", 90, 170),),
    )
    plan = solve_gate_assignment(problem, previous_assignments={"F1": "A1"})
    assert plan.assignments["F1"] == "A2"
    assert plan.changed_flights == ("F1",)


def test_connection_walking_cost_prefers_same_gate_when_capacity_allows():
    problem = GateAssignmentProblem(
        flights=(
            Flight("IN", 100, 130),
            Flight("OUT", 150, 210),
        ),
        gates=(Gate("A1", "A"), Gate("B1", "B")),
        connections=(PassengerConnection("IN", "OUT", passengers=80),),
        walking_minutes={("A1", "B1"): 25.0},
        gate_buffer_minutes=10,
    )
    plan = solve_gate_assignment(problem)
    assert plan.assignments["IN"] == plan.assignments["OUT"]
    assert plan.connection_walking_passenger_minutes == 0.0


def test_active_flight_is_frozen_to_current_gate():
    problem = GateAssignmentProblem(
        flights=(Flight("F1", 100, 180, preferred_terminal="A"),),
        gates=(Gate("A1", "A"), Gate("B1", "B")),
    )
    plan = solve_gate_assignment(
        problem,
        previous_assignments={"F1": "B1"},
        now_minute=120,
    )
    assert plan.assignments["F1"] == "B1"


def test_infeasible_when_no_compatible_gate_exists():
    problem = GateAssignmentProblem(
        flights=(Flight("F1", 100, 160, aircraft_class="widebody"),),
        gates=(Gate("A1", "A", max_aircraft_class="narrowbody"),),
    )
    with pytest.raises(InfeasibleGatePlanError):
        solve_gate_assignment(problem)
