"""
Backup manager for Neo4j graph database.
Creates backups using neo4j-admin dump and stores them.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import subprocess
import os
import structlog

from ..config import config
from ..exceptions import BackupError

logger = structlog.get_logger(__name__)


class BackupManager:
    """
    Manager for creating and managing Neo4j database backups.
    """

    def __init__(self):
        """Initialize backup manager."""
        self.backup_dir = os.getenv("NEO4J_BACKUP_DIR", "/backups/neo4j")
        self.retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

    def create_backup(
        self,
        backup_name: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a backup of the Neo4j database using neo4j-admin dump.
        
        Args:
            backup_name: Optional backup name (default: timestamp-based)
            trace_id: Trace ID for correlation
            
        Returns:
            Backup metadata
            
        Raises:
            BackupError: If backup creation fails
        """
        try:
            # Generate backup name if not provided
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"neo4j_backup_{timestamp}"
            
            # Ensure backup directory exists
            os.makedirs(self.backup_dir, exist_ok=True)
            
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.dump")
            
            logger.info(
                "backup_creation_started",
                backup_name=backup_name,
                backup_path=backup_path,
                trace_id=trace_id,
            )
            
            # Build neo4j-admin dump command
            # Note: This assumes neo4j-admin is in PATH or NEO4J_HOME is set
            neo4j_home = os.getenv("NEO4J_HOME", "/var/lib/neo4j")
            neo4j_admin = os.path.join(neo4j_home, "bin", "neo4j-admin")
            
            if not os.path.exists(neo4j_admin):
                # Try system PATH
                neo4j_admin = "neo4j-admin"
            
            command = [
                neo4j_admin,
                "dump",
                f"--database={config.neo4j_database}",
                f"--to={backup_path}",
            ]
            
            # Execute backup command
            start_time = datetime.now()
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result.returncode != 0:
                raise BackupError(
                    message=f"neo4j-admin dump failed: {result.stderr}",
                    details={
                        "command": " ".join(command),
                        "return_code": result.returncode,
                        "stderr": result.stderr,
                    },
                )
            
            # Get backup file size
            backup_size = os.path.getsize(backup_path)
            
            backup_metadata = {
                "backup_name": backup_name,
                "backup_path": backup_path,
                "backup_size_bytes": backup_size,
                "backup_size_mb": round(backup_size / (1024 * 1024), 2),
                "created_at": start_time.isoformat(),
                "duration_seconds": duration,
                "database": config.neo4j_database,
            }
            
            logger.info(
                "backup_created",
                backup_name=backup_name,
                backup_size_mb=backup_metadata["backup_size_mb"],
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return backup_metadata
            
        except subprocess.TimeoutExpired as e:
            logger.error(
                "backup_timeout",
                backup_name=backup_name,
                error=str(e),
                trace_id=trace_id,
            )
            raise BackupError(
                message=f"Backup creation timed out: {str(e)}",
                details={"backup_name": backup_name, "error": str(e)},
            ) from e
            
        except Exception as e:
            logger.error(
                "backup_creation_failed",
                backup_name=backup_name,
                error=str(e),
                trace_id=trace_id,
            )
            raise BackupError(
                message=f"Failed to create backup: {str(e)}",
                details={"backup_name": backup_name, "error": str(e)},
            ) from e

    def restore_backup(
        self,
        backup_path: str,
        force: bool = False,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Restore a backup using neo4j-admin load.
        
        WARNING: This will replace the current database!
        
        Args:
            backup_path: Path to backup file
            force: Force restore even if database exists
            trace_id: Trace ID for correlation
            
        Returns:
            Restore metadata
            
        Raises:
            BackupError: If restore fails
        """
        try:
            if not os.path.exists(backup_path):
                raise BackupError(
                    message=f"Backup file not found: {backup_path}",
                    details={"backup_path": backup_path},
                )
            
            logger.warning(
                "backup_restore_started",
                backup_path=backup_path,
                force=force,
                trace_id=trace_id,
            )
            
            # Build neo4j-admin load command
            neo4j_home = os.getenv("NEO4J_HOME", "/var/lib/neo4j")
            neo4j_admin = os.path.join(neo4j_home, "bin", "neo4j-admin")
            
            if not os.path.exists(neo4j_admin):
                neo4j_admin = "neo4j-admin"
            
            command = [
                neo4j_admin,
                "load",
                f"--database={config.neo4j_database}",
                f"--from={backup_path}",
            ]
            
            if force:
                command.append("--force")
            
            # Execute restore command
            start_time = datetime.now()
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result.returncode != 0:
                raise BackupError(
                    message=f"neo4j-admin load failed: {result.stderr}",
                    details={
                        "command": " ".join(command),
                        "return_code": result.returncode,
                        "stderr": result.stderr,
                    },
                )
            
            restore_metadata = {
                "backup_path": backup_path,
                "restored_at": start_time.isoformat(),
                "duration_seconds": duration,
                "database": config.neo4j_database,
                "force": force,
            }
            
            logger.warning(
                "backup_restored",
                backup_path=backup_path,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return restore_metadata
            
        except subprocess.TimeoutExpired as e:
            logger.error(
                "restore_timeout",
                backup_path=backup_path,
                error=str(e),
                trace_id=trace_id,
            )
            raise BackupError(
                message=f"Backup restore timed out: {str(e)}",
                details={"backup_path": backup_path, "error": str(e)},
            ) from e
            
        except Exception as e:
            logger.error(
                "backup_restore_failed",
                backup_path=backup_path,
                error=str(e),
                trace_id=trace_id,
            )
            raise BackupError(
                message=f"Failed to restore backup: {str(e)}",
                details={"backup_path": backup_path, "error": str(e)},
            ) from e

    def list_backups(
        self,
        trace_id: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """
        List all available backups.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            List of backup metadata
        """
        try:
            if not os.path.exists(self.backup_dir):
                logger.info("backup_directory_not_found", trace_id=trace_id)
                return []
            
            backups = []
            
            for filename in os.listdir(self.backup_dir):
                if filename.endswith(".dump"):
                    backup_path = os.path.join(self.backup_dir, filename)
                    
                    stat = os.stat(backup_path)
                    
                    backups.append({
                        "backup_name": filename.replace(".dump", ""),
                        "backup_path": backup_path,
                        "backup_size_bytes": stat.st_size,
                        "backup_size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            logger.debug(
                "backups_listed",
                backup_count=len(backups),
                trace_id=trace_id,
            )
            
            return backups
            
        except Exception as e:
            logger.error(
                "backup_listing_failed",
                error=str(e),
                trace_id=trace_id,
            )
            return []

    def delete_old_backups(
        self,
        retention_days: Optional[int] = None,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Delete backups older than retention period.
        
        Args:
            retention_days: Number of days to retain backups (default: from config)
            trace_id: Trace ID for correlation
            
        Returns:
            Number of backups deleted
        """
        if retention_days is None:
            retention_days = self.retention_days
        
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            backups = self.list_backups(trace_id)
            deleted_count = 0
            
            for backup in backups:
                created_at = datetime.fromisoformat(backup["created_at"])
                
                if created_at < cutoff_date:
                    try:
                        os.remove(backup["backup_path"])
                        deleted_count += 1
                        
                        logger.info(
                            "old_backup_deleted",
                            backup_name=backup["backup_name"],
                            created_at=backup["created_at"],
                            trace_id=trace_id,
                        )
                        
                    except Exception as e:
                        logger.error(
                            "backup_deletion_failed",
                            backup_name=backup["backup_name"],
                            error=str(e),
                            trace_id=trace_id,
                        )
            
            logger.info(
                "old_backups_deleted",
                retention_days=retention_days,
                deleted_count=deleted_count,
                trace_id=trace_id,
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "backup_cleanup_failed",
                retention_days=retention_days,
                error=str(e),
                trace_id=trace_id,
            )
            return 0


# Global backup manager instance
backup_manager = BackupManager()

