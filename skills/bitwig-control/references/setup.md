# One-time setup (per machine)

Needed only when `bw.py ping` fails on a machine that never had the link.

1. Install the DrivenByMoss extension: download from
   <https://www.mossgrabers.de/Software/Bitwig/Bitwig.html> (Bitwig 5.3+),
   copy `DrivenByMoss.bwextension` into `~/Documents/Bitwig Studio/Extensions/`.
2. Human step — there is no API for it: in Bitwig, **Dashboard → Settings →
   Controllers → + Add Controller → Utilities → Open Sound Control**, activate.
3. Ports `bw.py` expects (the controller's defaults): receive **8000**, send
   host **127.0.0.1**, send port **9000**, value resolution **128**. If the
   user changed them in the controller settings, mirror via env vars
   `BITWIG_OSC_HOST` / `BITWIG_OSC_SEND_PORT` / `BITWIG_OSC_FEEDBACK_PORT` /
   `BITWIG_OSC_RESOLUTION`. Symptom of a resolution mismatch: `param` moves
   knobs to wrong values. Raising the resolution preference (e.g. 1024)
   buys finer moves than the default ~0.3 dB steps — keep the env var in sync.
4. Python side: `pip install python-osc` (any Python ≥3.9; the track-analysis
   venv already has it).

Done when `bw.py ping` prints `OK` with the project name.
