from typing import Any
from backend.core.plugins.generic import GenericPlugin
from backend.plugins.AutomatedPipeline.automated_pipe import automated_pipe
from backend.core.notifications import notification_manager
from backend.core.database.models import NotificationMessage, NotificationType, Plugin
from backend.core.database.database import engine
from backend.plugin_manager import plugin_manager
from sqlmodel import Session, select


async def run_automated_pipeline():
    print("Running automated pipeline...")
    try:
        initial_data = {}
        result = await automated_pipe.execute(initial_data)
        
        # Extract results from pipeline execution
        indexer_results = result.get("indexer_results", [])
        parsed_results = result.get("parsed_results", {})
        sent_items = result.get("sent_items", [])
        
        # Log results
        print(f"Indexer found {len(indexer_results)} results")
        print(f"Parser matched {len(parsed_results)} items")
        print(f"Sent {len(sent_items)} items to download client")
        
        # Send notification based on results
        if sent_items:
            await notification_manager.broadcast(
                NotificationMessage(
                    type=NotificationType.INFO,
                    message=f"Automated pipeline completed: {len(sent_items)} item(s) sent to download client.",
                )
            )
        elif indexer_results:
            await notification_manager.broadcast(
                NotificationMessage(
                    type=NotificationType.INFO,
                    message=f"Automated pipeline completed: {len(indexer_results)} result(s) found, but none matched monitored series.",
                )
            )
        else:
            print("No new releases found in indexer feeds")
            
    except Exception as e:
        print(f"Error running automated pipeline: {e}")
        await notification_manager.broadcast(
            NotificationMessage(
                type=NotificationType.ERROR,
                message=f"Automated pipeline failed: {str(e)}",
            )
        )

class AutomatedPipe(GenericPlugin):
    """Automated pipeline plugin for RSS feed processing and download automation."""
    
    name = "AutomatedPipeline"
    version = "0.1.0"
    description = "Automated pipeline for RSS feed processing and download automation"
    
    def start(self) -> None:
        """Plugin start - scheduled jobs are registered separately."""
        print(f"AutomatedPipe plugin started")
    
    def stop(self) -> None:
        """Plugin stop."""
        print(f"AutomatedPipe plugin stopped")
    
    def get_scheduler_jobs(self) -> list[dict[str, Any]]:
        """Return the scheduled job configuration for the automated pipeline.
        
        Only schedules the job if both an Indexer plugin and Download Client plugin are available.
        This allows the plugin to decide its own scheduling requirements without the core
        system needing to know about plugin-specific logic.
        """
        # Check if required plugin capabilities are available
        with Session(engine) as session:
            plugins = session.exec(select(Plugin).where(Plugin.enabled == True)).all()
            
            has_indexer_plugin = False
            has_parser_plugin = False
            has_download_client_plugin = False
            
            for plugin in plugins:
                try:
                    plugin_instance = plugin_manager.get_plugin(plugin.name)
                    if plugin_instance:
                        # Check if plugin has indexer capability
                        try:
                            indexers = plugin_instance.get_available_indexers()
                            if indexers:
                                has_indexer_plugin = True
                        except (NotImplementedError, AttributeError):
                            pass
                        
                        # Check if plugin has parser capability
                        try:
                            parsers = plugin_instance.get_available_parsers()
                            if parsers:
                                has_parser_plugin = True
                        except (NotImplementedError, AttributeError):
                            pass
                        
                        # Check if plugin has download client capability
                        try:
                            clients = plugin_instance.get_available_clients()
                            if clients:
                                has_download_client_plugin = True
                        except (NotImplementedError, AttributeError):
                            pass
                except Exception:
                    pass
            
            if not (has_indexer_plugin and has_parser_plugin and has_download_client_plugin):
                missing = []
                if not has_indexer_plugin:
                    missing.append("Indexer capability")
                if not has_parser_plugin:
                    missing.append("Parser capability")
                if not has_download_client_plugin:
                    missing.append("Download Client capability")
                print(
                    f"AutomatedPipeline: Not scheduling automated_pipeline job - "
                    f"missing plugin capabilities: {', '.join(missing)}"
                )
                return []  # Don't schedule any jobs
        
        print("AutomatedPipeline: Scheduling automated_pipeline job (requirements met)")
        return [
            {
                "func": run_automated_pipeline,
                "trigger": "interval",
                "minutes": 15,
                "id": "automated_pipeline",
                "replace_existing": True,
            }
        ] 