"""Worker Entry Point - Run with: python -m worker.main"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worker.consumer import run_worker


async def design_task_handler(task_id: str, payload: dict, worker) -> dict:
    """
    Real task handler for design generation.

    For now, this delegates to the default mock handler.
    In Phase Q3, this will integrate with Hunyuan3D-2 + trimesh pipelines.
    """
    return await worker._default_handler(task_id, payload)


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 60)
    print("ClayWords Worker Starting...")
    print("=" * 60)

    try:
        asyncio.run(run_worker(handler=design_task_handler))
    except KeyboardInterrupt:
        print("\nWorker stopped by user")


if __name__ == "__main__":
    main()
