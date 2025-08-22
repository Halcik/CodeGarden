import logging
from pathlib import Path
from datetime import datetime
import inspect

def set_logging_format():
  '''Ustawia format logowania informacji i błędów'''
  logger = logging.getLogger("CG-logger")
  logger.setLevel(logging.DEBUG)

  # Miejsce i nazwa przechowywania plików logów
  logs_dir = Path(__file__).resolve().parent.parent / "logs"
  logs_dir.mkdir(exist_ok=True)
  log_filename = logs_dir / f"cg_{datetime.now().strftime('%Y-%m-%d')}.log"

  # Handler do pliku
  file_handler = logging.FileHandler(log_filename, encoding="utf-8")
  file_handler.setLevel(logging.DEBUG)

  # Handler do konsoli
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)

  # Format
  formatter = logging.Formatter("[%(asctime)s | %(levelname)8s | %(message)s", datefmt="%d.%m.%Y %H:%M:%S")
  file_handler.setFormatter(formatter)
  console_handler.setFormatter(formatter)

  # Dodanie handlerów (sprawdzenie, żeby nie dodać kilka razy przy imporcie)
  if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
  return logger


def log_mess(level: str, message: str):
    """Loguje komunikat w formacie | plik | funkcja] treść"""
    frame = inspect.currentframe().f_back
    file = Path(frame.f_code.co_filename).name
    func = frame.f_code.co_name

    prefix = f"{file} | {func}()]"
    full_message = f"{prefix} {message}"

    match level.lower():
        case "debug":
            logger.debug(full_message)
        case "info":
            logger.info(full_message)
        case "warning":
            logger.warning(full_message)
        case "error":
            logger.error(full_message)
        case "critical":
            logger.critical(full_message)
        case _:  # fallback
            logger.info(full_message)


def test_logger_levels():
  '''Testuje format i działanie loggera'''
  log_mess("debug", "debug info")
  log_mess("info", "info")
  log_mess("warning", "warning")
  log_mess("error", "error")
  log_mess("critical", "critical")


logger = set_logging_format()

if __name__ == '__main__':
  test_logger_levels()