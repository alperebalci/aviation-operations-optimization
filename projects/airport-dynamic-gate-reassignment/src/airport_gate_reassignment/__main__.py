from __future__ import annotations

from .model import Flight, Gate, GateAssignmentProblem, GateClosure, PassengerConnection
from .optimizer import solve_gate_assignment


def build_initial_problem() -> GateAssignmentProblem:
    return GateAssignmentProblem(
        flights=(
            Flight("F100", 60, 115, preferred_terminal="A"),
            Flight("F200", 125, 185, preferred_terminal="A", international=True),
            Flight("F300", 195, 250, preferred_terminal="B"),
            Flight("F400", 150, 215, preferred_terminal="B"),
        ),
        gates=(
            Gate("A1", "A", max_aircraft_class="widebody", international_capable=True),
            Gate("A2", "A", max_aircraft_class="narrowbody", international_capable=False),
            Gate("B1", "B", max_aircraft_class="widebody", international_capable=True),
            Gate(
                "R1",
                "R",
                max_aircraft_class="widebody",
                international_capable=True,
                remote=True,
            ),
        ),
        connections=(
            PassengerConnection("F100", "F200", 42),
            PassengerConnection("F200", "F300", 30),
        ),
        walking_minutes={
            ("A1", "A2"): 4.0,
            ("A1", "B1"): 14.0,
            ("A2", "B1"): 16.0,
            ("A1", "R1"): 22.0,
            ("A2", "R1"): 24.0,
            ("B1", "R1"): 18.0,
        },
        gate_buffer_minutes=10,
    )


def build_disrupted_problem() -> GateAssignmentProblem:
    initial = build_initial_problem()
    return GateAssignmentProblem(
        flights=(
            Flight("F100", 60, 140, preferred_terminal="A"),
            Flight("F200", 132, 195, preferred_terminal="A", international=True),
            Flight("F300", 205, 260, preferred_terminal="B"),
            Flight("F400", 150, 215, preferred_terminal="B"),
        ),
        gates=initial.gates,
        connections=initial.connections,
        walking_minutes=initial.walking_minutes,
        closures=(GateClosure("A1", 151, 230),),
        gate_buffer_minutes=10,
    )


def main() -> None:
    initial = solve_gate_assignment(build_initial_problem())
    print("Initial plan")
    for flight_id, gate_id in sorted(initial.assignments.items()):
        print(f"  {flight_id}: {gate_id}")

    disrupted = solve_gate_assignment(
        build_disrupted_problem(),
        previous_assignments=initial.assignments,
        now_minute=120,
        freeze_horizon_minutes=35,
    )
    print("\nAfter delay + A1 closure")
    for flight_id, gate_id in sorted(disrupted.assignments.items()):
        marker = " *changed*" if flight_id in disrupted.changed_flights else ""
        print(f"  {flight_id}: {gate_id}{marker}")
    print(f"Changed flights: {disrupted.changed_flights or 'none'}")
    print(
        "Connection walking passenger-minutes: "
        f"{disrupted.connection_walking_passenger_minutes:.1f}"
    )


if __name__ == "__main__":
    main()
