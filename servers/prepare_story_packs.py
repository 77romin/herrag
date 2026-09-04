"""Run once before starting the server; subsequent runs reuse unchanged packs."""
import asyncio
import json
from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor


async def prepare():
    import main
    root = Path(__file__).resolve().parent
    cases = json.loads((root / "story_test_cases.json").read_text(encoding="utf-8"))
    names = sorted({case["file"] for case in cases})
    if len(names) != 5:
        raise ValueError("Expected exactly five built-in story packs")
    async with main.lifespan(main.app):
        main.app.state.get_story_cache()

        def prepare_one(item):
            index, name = item
            print(f"[{index}/5] Preparing {name}", flush=True)
            start = perf_counter()
            path = root.parent / "clients" / "sample_data" / name
            try:
                result = main.app.state.prepare_story_pack(path.read_bytes(), name)
            except Exception as exc:
                print(f"  FAILED: {name}: {exc}", flush=True)
                return False
            print(f"  {'REUSED' if result['cache_hit'] else 'SAVED'}: "
                  f"{name}, {len(result['ids'])} chunks, {perf_counter() - start:.1f}s", flush=True)
            return True

        with ThreadPoolExecutor(max_workers=3) as pool:
            outcomes = list(pool.map(prepare_one, enumerate(names, 1)))
        if not all(outcomes):
            raise RuntimeError("Some story packs could not be prepared; see FAILED entries above")
    print("All five story packs are ready.", flush=True)


if __name__ == "__main__":
    asyncio.run(prepare())
