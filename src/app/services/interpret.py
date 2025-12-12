import yaml
import logging
from pathlib import Path
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)


class InterpretService:
    def __init__(self, mapping_path: str = "configs/mappings.yaml"):
        self.mapping_path = Path(mapping_path)
        self._mappings = self._load_mappings()

    def _load_mappings(self) -> Dict[str, Any]:
        if not self.mapping_path.exists():
            return {}
        with self.mapping_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    async def execute(self, label: str) -> Dict[str, Any]:
        """Execute action mapped to the label. Returns info dict."""
        mapping = self._mappings.get(label)
        if not mapping:
            logger.info("No mapping for label: %s", label)
            return {"status": "no_mapping"}

        typ = mapping.get("type")
        if typ == "log":
            msg = mapping.get("message", f"Action for {label}")
            logger.info("Interpret action: %s", msg)
            return {"status": "logged", "message": msg}

        if typ == "callback":
            url = mapping.get("url")
            if not url:
                return {"status": "bad_mapping"}
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.post(url, json={"label": label})
                    return {"status": "callback", "code": resp.status_code}
                except Exception as e:
                    logger.exception("Callback failed: %s", e)
                    return {"status": "callback_error", "error": str(e)}

        logger.info("Unknown mapping type %s for label %s", typ, label)
        return {"status": "unknown_type"}
