import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
from minio.commonconfig import ENABLED, Filter

from app.storage.minio_client import MinioClientFactory

# Configuration Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StorageManager")

class BucketName(str, Enum):
    """Enums pour garantir la cohérence des noms de buckets dans tout le projet."""
    USER_IDENTITY_ASSETS = "user-identity-assets"
    POSTS_RAW_UPLOADS = "posts-raw-uploads"
    POSTS_PERMANENT_CONTENT = "posts-permanent-content"
    STORIES_EPHEMERAL_CONTENT = "stories-ephemeral-content"
    STORIES_RAW_UPLOADS = "stories-raw-uploads"

@dataclass
class BucketSpec:
    """Définition technique d'un bucket."""
    name: BucketName
    is_public: bool
    retention_days: Optional[int] = None
    quota_gb: Optional[int] = None

class StorageManager:
    def __init__(self):
        self.client = MinioClientFactory.get_backend_client()

    def get_buckets_definition(self) -> List[BucketSpec]:
        return [
            BucketSpec(BucketName.USER_IDENTITY_ASSETS, is_public=True, quota_gb=1),
            BucketSpec(BucketName.POSTS_RAW_UPLOADS, is_public=False, retention_days=1, quota_gb=2),
            BucketSpec(BucketName.POSTS_PERMANENT_CONTENT, is_public=False, quota_gb=5),
            BucketSpec(BucketName.STORIES_EPHEMERAL_CONTENT, is_public=False, retention_days=2, quota_gb=1),
            BucketSpec(BucketName.STORIES_RAW_UPLOADS, is_public=False, retention_days=1, quota_gb=1),
        ]

    def setup_infrastructure(self):
        """Initialise toute l'infrastructure de stockage"""
        # logger.info(f"Les buckets actuels : {self.client.list_buckets()}")
        try:
            for spec in self.get_buckets_definition():
                self._ensure_bucket(spec)
            logger.info("🚀 Infrastructure de stockage synchronisée avec succès.")
        except Exception as e:
            logger.error(f"Erreur lors de la configuration de l'infrastructure de stockage : {e}")
            exit(1)
    def _ensure_bucket(self, bucket: BucketSpec):
        if not self.client.bucket_exists(bucket.name.value):
            self.client.make_bucket(bucket.name.value)
            logger.info(f"📁 Bucket créé : {bucket.name.value}")
            self._configure_lifecycle(bucket)
            self._apply_policy(bucket)
            logger.info(f"✅ Bucket configuré entierement avec succès : {bucket.name.value} (Public: {bucket.is_public}, Retention: {bucket.retention_days} jours)")
        else:
            logger.info(f"✅ Bucket déjà existant : {bucket.name.value}")


    def _configure_lifecycle(self, spec: BucketSpec):
        """Gère la suppression automatique (Stories et Raw)."""
        if spec.retention_days:
            rule = Rule(
                ENABLED,
                rule_filter=Filter(prefix=""),
                rule_id=f"delete_after_{spec.retention_days}_days",
                expiration=Expiration(days=spec.retention_days),
            )
            self.client.set_bucket_lifecycle(spec.name.value, LifecycleConfig([rule]))
            logger.info(f"⏳ Rétention de {spec.retention_days} jours activée pour {spec.name.value}")

    def _apply_policy(self, spec: BucketSpec):
        """Définit si le bucket est accessible via URL directe ou via Presigned URL uniquement."""
        if spec.is_public:
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket", "s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{spec.name.value}", f"arn:aws:s3:::{spec.name.value}/*"]
                }]
            }
            self.client.set_bucket_policy(spec.name.value, json.dumps(policy))

# Exemple d'usage
if __name__ == "__main__":
    # Remplacer par tes variables d'environnement
    manager = StorageManager()
    manager.setup_infrastructure()