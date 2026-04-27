import os
import traceback
import uvicorn

try:
    import main
    print("MAIN IMPORTED OK")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="debug")
except Exception:
    print("REAL STARTUP ERROR:")
    traceback.print_exc()
    raise