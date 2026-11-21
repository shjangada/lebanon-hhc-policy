"""python -m beqaa.ingest [all|cadasters_population|facilities|conflict|vulnerability|funding_flows|hdx_access|...]

Runs the converters in dependency order. Each converter is idempotent and writes to data/processed/ (see scripts/ingest/<dataset>.py for single-dataset entry points)."""
import importlib
import sys

ORDER = ["cadasters_population", "facilities", "conflict", "vulnerability", "funding_flows", "hdx_access"]
OPTIONAL = ["lhf_allocations", "facility_status", "soil_sites", "official_severity", "interventions", "crop_transfer", "cascade_baseline", "vasyr_msna",
            "governance", "mobile_units", "acled", "checks", "report"]


def main(names=None):
    want = names or ["all"]
    todo = ORDER + OPTIONAL if "all" in want else want
    for n in todo:
        try:
            mod = importlib.import_module(f"beqaa.ingest.{n}")
        except ModuleNotFoundError as e:
            if n in OPTIONAL and e.name == f"beqaa.ingest.{n}":
                print(f"{n}: not implemented yet (skipped)")
                continue
            raise
        try:
            print(f"{n}:", mod.run())
        except FileNotFoundError as e:                       # raw input missing: say so, keep going
            print(f"{n}: SKIPPED, missing input: {e}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
