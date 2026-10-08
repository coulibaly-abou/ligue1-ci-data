"""Téléchargement des pages web, poli envers le site source."""
import time
from functools import cache
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
import truststore

from config.settings import DELAI_REQUETES, USER_AGENT

# Utilise le magasin de certificats du système (indispensable derrière un
# antivirus ou un proxy qui inspecte le HTTPS, comme Avast).
truststore.inject_into_ssl()

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "fr,en"})


class PageInterdite(Exception):
    """La page est interdite aux robots par le robots.txt du site."""


class PageAbsente(Exception):
    """La page n'existe pas (encore) : 404, par ex. saison pas encore publiée."""


@cache
def _robots(site: str) -> RobotFileParser:
    """Lit le robots.txt d'un site une seule fois par exécution."""
    rp = RobotFileParser()
    try:
        reponse = _session.get(f"{site}/robots.txt", timeout=20)
        rp.parse(reponse.text.splitlines() if reponse.ok else [])
    except requests.RequestException:
        rp.parse([])  # robots.txt inaccessible : tout est autorisé
    return rp


def autorise(url: str) -> bool:
    p = urlparse(url)
    return _robots(f"{p.scheme}://{p.netloc}").can_fetch(USER_AGENT, url)


def telecharger_page(url: str) -> str:
    """Renvoie le HTML d'une page, avec une pause entre deux requêtes."""
    if not autorise(url):
        raise PageInterdite(url)
    time.sleep(DELAI_REQUETES)
    reponse = _session.get(url, timeout=30)
    if reponse.status_code == 404:
        raise PageAbsente(url)
    reponse.raise_for_status()  # lève une erreur si 404, 500...
    reponse.encoding = reponse.encoding or reponse.apparent_encoding
    return reponse.text
