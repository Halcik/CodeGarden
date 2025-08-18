import logging

def set_logging_format():
  '''Ustawia format logowania informacji i błędów'''
  logger = logging.getLogger("CG-logger")
  logger.setLevel(logging.DEBUG)

  # Handler do pliku
  file_handler = logging.FileHandler("cg.log", encoding="utf-8")
  file_handler.setLevel(logging.DEBUG)

  # Handler do konsoli
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)

  # Format
  formatter = logging.Formatter("[%(asctime)s | %(levelname)8s] %(message)s", datefmt="%d.%m.%Y %H:%M:%S")
  file_handler.setFormatter(formatter)
  console_handler.setFormatter(formatter)

  # Dodanie handlerów (sprawdzenie, żeby nie dodać kilka razy przy imporcie)
  if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
  return logger

def test_logger_levels():
  '''Testuje format i działanie loggera'''
  logger.debug("debug info")
  logger.info("info")
  logger.warning("warning")
  logger.error("error")
  logger.critical("critical")

logger = set_logging_format()

if __name__ == '__main__':
  test_logger_levels()