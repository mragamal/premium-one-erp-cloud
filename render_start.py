import os
import sys
import traceback
import uvicorn

print("STARTING RENDER DEBUG...", flush=True)

try:
    print("IMPORTING MAIN...", flush=True)
    import main
    print("MAIN IMPORTED OK", flush=True)

    port = int(os.environ.get("PORT", "8000"))
    print(f"RUNNING ON PORT {port}", flush=True)

    uvicorn.run(main.app, host="0.0.0.0", port=port, log_level="debug")

except Exception:
    print("REAL ERROR BELOW:", file=sys.stderr, flush=True)
    traceback.print_exc()
    sys.stderr.flush()
    raise