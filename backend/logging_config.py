# Configuration du systeme de logs structure en JSON.
# Les logs sont formates pour etre compatibles avec Google Cloud Logging.
# Chaque log inclut un trace_id et un tenant_id pour faciliter le suivi
# des requetes et le cloisonnement par cabinet.

import logging
import json
import time
from contextvars import ContextVar
import uuid

# Variables de contexte partagees entre le middleware et les logs.
# Elles permettent d'associer chaque log a une requete (trace_id)
# et a un cabinet (tenant_id) sans avoir a les passer en parametre partout.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="system")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="system")

class StructuredJsonFormatter(logging.Formatter):
    """Formateur qui produit des logs en JSON structure.
    Chaque ligne de log contient : timestamp, niveau, message,
    trace_id et tenant_id pour le suivi et l'audit."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get(),
            "tenant_id": tenant_id_var.get(),
        }
        
        # Si une exception est presente, on l'ajoute au log
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logging():
    """Initialise le systeme de logs pour toute l'application.
    Remplace les handlers par defaut par notre formateur JSON.
    Reduit aussi le bruit des logs internes d'Uvicorn."""

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # On retire tous les handlers existants pour eviter les doublons
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Ajout du handler console avec le formateur JSON
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(console_handler)
    
    # On reduit les logs verbeux d'Uvicorn pour garder la console lisible
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    
    logging.info("Logging JSON initialise.")
