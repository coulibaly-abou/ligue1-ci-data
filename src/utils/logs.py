"""Journal des exécutions : affiché dans le terminal et enregistré dans logs/."""
import logging

from config.settings import DOSSIER_LOGS


def get_logger(nom: str) -> logging.Logger:
    logger = logging.getLogger(nom)
    if logger.handlers:  # évite les doublons si appelé plusieurs fois
        return logger

    DOSSIER_LOGS.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    fichier = logging.FileHandler(DOSSIER_LOGS / "pipeline.log", encoding="utf-8")
    fichier.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(fichier)
    logger.setLevel(logging.INFO)
    return logger
