from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class Flight:
    flight_id: str
    arrival_minute: int
    departure_minute: int
    aircraft_class: str = "narrowbody"
    international: bool = False
    preferred_terminal: str | None = None

    def __post_init__(self) -> None:
        if not self.flight_id:
            raise ValueError("flight_id must be non-empty")
        if self.arrival_minute >= self.departure_minute:
            raise ValueError("arrival_minute must be earlier than departure_minute")
        if self.aircraft_class not in {"narrowbody", "widebody"}:
            raise ValueError("aircraft_class must be 'narrowbody' or 'widebody'")


@dataclass(frozen=True)
class Gate:
    gate_id: str
    terminal: str
    max_aircraft_class: str = "narrowbody"
    international_capable: bool = True
    remote: bool = False

    def __post_init__(self) -> None:
        if not self.gate_id:
            raise ValueError("gate_id must be non-empty")
        if not self.terminal:
            raise ValueError("terminal must be non-empty")
        if self.max_aircraft_class not in {"narrowbody", "widebody"}:
            raise ValueError("max_aircraft_class must be 'narrowbody' or 'widebody'")


@dataclass(frozen=True)
class GateClosure:
    gate_id: str
    start_minute: int
    end_minute: int

    def __post_init__(self) -> None:
        if self.start_minute >= self.end_minute:
            raise ValueError("closure start_minute must be earlier than end_minute")


@dataclass(frozen=True)
class PassengerConnection:
    inbound_flight_id: str
    outbound_flight_id: str
    passengers: int

    def __post_init__(self) -> None:
        if self.passengers <= 0:
            raise ValueError("passengers must be positive")
        if self.inbound_flight_id == self.outbound_flight_id:
            raise ValueError("connection flights must be distinct")


@dataclass(frozen=True)
class GateAssignmentProblem:
    flights: tuple[Flight, ...]
    gates: tuple[Gate, ...]
    connections: tuple[PassengerConnection, ...] = ()
    closures: tuple[GateClosure, ...] = ()
    walking_minutes: Mapping[tuple[str, str], float] = field(default_factory=dict)
    gate_buffer_minutes: int = 15

    def __post_init__(self) -> None:
        if not self.flights:
            raise ValueError("At least one flight is required")
        if not self.gates:
            raise ValueError("At least one gate is required")
        if self.gate_buffer_minutes < 0:
            raise ValueError("gate_buffer_minutes cannot be negative")

        flight_ids = [flight.flight_id for flight in self.flights]
        if len(flight_ids) != len(set(flight_ids)):
            raise ValueError("flight_id values must be unique")

        gate_ids = [gate.gate_id for gate in self.gates]
        if len(gate_ids) != len(set(gate_ids)):
            raise ValueError("gate_id values must be unique")

        flight_id_set = set(flight_ids)
        gate_id_set = set(gate_ids)
        for connection in self.connections:
            if connection.inbound_flight_id not in flight_id_set:
                raise ValueError(f"Unknown inbound flight: {connection.inbound_flight_id}")
            if connection.outbound_flight_id not in flight_id_set:
                raise ValueError(f"Unknown outbound flight: {connection.outbound_flight_id}")
        for closure in self.closures:
            if closure.gate_id not in gate_id_set:
                raise ValueError(f"Unknown gate in closure: {closure.gate_id}")
        for (gate_a, gate_b), minutes in self.walking_minutes.items():
            if gate_a not in gate_id_set or gate_b not in gate_id_set:
                raise ValueError("walking_minutes contains an unknown gate")
            if minutes < 0:
                raise ValueError("walking time cannot be negative")


@dataclass(frozen=True)
class OptimizationWeights:
    remote_gate_penalty: float = 30.0
    terminal_change_penalty: float = 12.0
    reassignment_penalty: float = 25.0
    near_term_reassignment_penalty: float = 60.0
    connection_walk_penalty_per_passenger_minute: float = 0.08

    def __post_init__(self) -> None:
        values = (
            self.remote_gate_penalty,
            self.terminal_change_penalty,
            self.reassignment_penalty,
            self.near_term_reassignment_penalty,
            self.connection_walk_penalty_per_passenger_minute,
        )
        if any(value < 0 for value in values):
            raise ValueError("Optimization weights cannot be negative")


@dataclass(frozen=True)
class GatePlan:
    assignments: Mapping[str, str]
    objective_value: float
    changed_flights: tuple[str, ...]
    connection_walking_passenger_minutes: float
    mip_gap: float | None
