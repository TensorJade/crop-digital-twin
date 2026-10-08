"""Run the local SQL simulation worker; credentials come from configuration, never flags."""

import argparse
import logging
import time
from pathlib import Path

from crop_twin.core.settings import Settings
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.workers.simulation import process_one
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Process one task or poll until Ctrl+C; no implicit migrations or default data."""
    parser = argparse.ArgumentParser(description="处理 PCSE 潜在生长任务")
    parser.add_argument("--once", action="store_true", help="最多处理一条可领取任务后退出")
    arguments = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    settings = Settings()
    if settings.environment == "production":
        raise SystemExit("Production release requires the M7 gate.")
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")
    engine = build_engine(settings.database_url.get_secret_value())
    try:
        if arguments.once:
            print("Processed one task." if process_one(engine) else "No claimable task.")
            return
        print("Simulation worker running. Stop with Ctrl+C.")
        while True:
            if not process_one(engine):
                time.sleep(2)
    except KeyboardInterrupt:
        print("Simulation worker stopped.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
