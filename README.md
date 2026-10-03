# Aviation Operations Optimization

<!-- portfolio-umbrella:start -->
## Portfolio role

This repository is the primary umbrella repository for this Jors Academy research area. Related projects have been consolidated under `projects/` so the methods, implementations, experiments, and case studies can be maintained and explored from one place.

### Native flagship

The repository root contains the actively maintained **airline disruption-recovery optimization model** described below. Most entries under `projects/` are consolidated companion projects; new research modules may also be developed directly in this umbrella repository.

### Included projects

- [`aircraft-allocation-under-uncertain-demand`](projects/aircraft-allocation-under-uncertain-demand/)
- [`aircraft-maintenance-scheduling-gurobi`](projects/aircraft-maintenance-scheduling-gurobi/)
- [`airline-crew-scheduling-column-generation`](projects/airline-crew-scheduling-column-generation/)
- [`airline-crew-workforce-optimization-ga`](projects/airline-crew-workforce-optimization-ga/)
- [`airline-operations-under-uncertainty-stochastic-optimization`](projects/airline-operations-under-uncertainty-stochastic-optimization/)
- [`airport-checkin-counter-optimization-erlang-c`](projects/airport-checkin-counter-optimization-erlang-c/)
- [`airport-checkin-simulation-optimization`](projects/airport-checkin-simulation-optimization/)
- [`airport-dynamic-gate-reassignment`](projects/airport-dynamic-gate-reassignment/)
- [`aviation-crew-scheduling-milp`](projects/aviation-crew-scheduling-milp/)
- [`metroglobal-airport-counter-optimization`](projects/metroglobal-airport-counter-optimization/)

Consolidated projects keep their own files and a `SOURCE_REPOSITORY.md` provenance record. Their snapshots preserve the source repository's default-branch files at consolidation time; repository-level history and metadata remain separate from the snapshot.
<!-- portfolio-umbrella:end -->

A mixed-integer optimization model for airline disruption recovery using aircraft-flow networks and airport-capacity degradation scenarios.

The model assigns flights to aircraft, enforces feasible aircraft rotations, handles overnight flights, permits aircraft to remain idle, and evaluates disruption levels through an airport-capacity factor `alpha` in `[0, 1]`.

## Model highlights

- Binary flight-operation decisions with at-most-one-aircraft assignment.
- Aircraft-specific source/sink flow networks.
- Location and turnaround-time-compatible flight connections.
- Explicit idle arcs so aircraft are not forced to operate.
- Minute-based time normalization, including next-day arrivals.
- Revenue-loss minimization without double-counting cancelled-flight revenue.
- Airport departure and arrival capacity constraints controlled by `alpha`.

## Installation

```bash
python -m pip install -e .
```

A working Gurobi installation and license are required to solve optimization instances. The structural unit tests do not require an active solver license.

## Run

```bash
python -m airline_disruption.cli
```

## Tests

```bash
pytest
```

To run the solver integration test when a Gurobi license is available:

```bash
RUN_GUROBI_INTEGRATION=1 pytest -m integration
```

## License

This repository is source-available for noncommercial purposes only under the PolyForm Noncommercial License 1.0.0. Commercial use is prohibited. See `LICENSE` for the full terms.
