"""SESSION 267 §5.2 — Poll the setup Composition once and report.

READ-ONLY. Prints status + minimal state each invocation so the
outer shell loop can wait until COMPLETED or FAILED.
"""
from apps.compositions.models import Composition, CompositionStep

COMP_ID = "b0b0e932-4e54-4b1b-b393-3c441aae93b7"

comp = Composition.objects.get(pk=COMP_ID)
steps = list(CompositionStep.objects.filter(composition=comp).order_by("position"))

print(f"status={comp.status} verification={comp.verification_status!r}")
print(f"attempts={comp.synthesis_attempt_count} "
      f"predicted={comp.synthesis_predicted_seconds}")
print(f"error_message={comp.error_message[:200]!r}")
for s in steps:
    print(f"  step {s.position:2d} {s.primitive:28s} {s.status:10s} "
          f"cost={s.cost_actual_micros}")
