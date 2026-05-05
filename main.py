from src.worker import main_loop
from src.config import logger

def main():
    logger.info("Starting collector...")
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.exception(f"Unhandled exception in main loop: {e}")


if __name__ == "__main__":
    main()
