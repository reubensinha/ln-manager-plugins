"""This Pipeline is intended to execute regularly on a scheduled basis. (Scheduled execution and logic is handled elsewhere.)

The Pipeline has 3 default stages:
1. Check Indexer Feed from Indexer plugins
2. Parse Results and match to series/books
3. Send Results to Download Client plugin
"""

from backend.core.services.pipeline.pipe import Pipe
from backend.core.services.pipeline.stage import Stage
from backend.core.services.indexer_service import get_all_feeds
from backend.core.services.download_client_service import send_to_download_client
from backend.core.services.parser import parse_titles
from backend.plugin_manager import plugin_manager
from backend.api.v1.core import read_series_list


# Default stage implementations
async def check_indexer_feed(data: dict) -> dict:
    """Check indexer feed of all plugins."""
    feeds = get_all_feeds()
    data["indexer_results"] = feeds
    return data


async def parse_results(data: dict) -> dict:
    """Parse results and match to series/books."""
    indexer_results = data.get("indexer_results", [])
    if indexer_results:
        result_titles = [result.get("title", "") for result in indexer_results]
        parsed_data = parse_titles(result_titles)
        data["parsed_results"] = parsed_data
    else:
        data["parsed_results"] = {}
    return data


async def send_to_client(data: dict) -> dict:
    """Send matched results to download client plugins."""
    parsed_results = data.get("parsed_results", {})
    indexer_results = data.get("indexer_results", [])

    # TODO: Check if this is necessary
    sent_items = []
    for result in indexer_results:
        # Send items that were successfully parsed/matched
        if result.get("title") in parsed_results:
            send_to_download_client(result)
            sent_items.append(result)

    data["sent_items"] = sent_items
    return data


check_indexer_stage = Stage("check_indexer_feed", check_indexer_feed)
parse_results_stage = Stage("parse_results", parse_results)
send_to_download_client_stage = Stage("send_to_download_client", send_to_client)


class AutomatedPipe(Pipe):
    """Automated pipeline with pre-configured stages for RSS feed processing.

    Provides convenience methods to insert custom stages at specific points
    in the default pipeline workflow.
    """

    INDEXER_STAGE_NAME = "check_indexer_feed"
    PARSE_STAGE_NAME = "parse_results"
    DOWNLOAD_STAGE_NAME = "send_to_download_client"

    def __init__(self):
        """Initialize pipeline with default stages."""
        super().__init__()
        self._setup_default_stages()

    def _setup_default_stages(self):
        """Reset pipeline to default stages."""
        self.stages = [
            check_indexer_stage,
            parse_results_stage,
            send_to_download_client_stage,
        ]
        
    def _find_stage_index(self, stage_name: str) -> int:
        """Find the index of a stage by name.

        Args:
            stage_name: Name of the stage to find

        Returns:
            int: Index of the stage, or -1 if not found
        """
        for i, stage in enumerate(self.stages):
            if stage.name == stage_name:
                return i
        return -1

    def before_indexer_feed(self, stage: Stage):
        """Add stage before checking indexer feed."""
        index = self._find_stage_index(self.INDEXER_STAGE_NAME)
        if index != -1:
            self.insert_stage(index, stage)
        else:
            # If indexer stage doesn't exist, add to beginning
            self.insert_stage(0, stage)

    def on_indexer_feed(self, stage: Stage):
        """Add stage after checking indexer feed."""
        index = self._find_stage_index(self.INDEXER_STAGE_NAME)
        if index != -1:
            self.insert_stage(index + 1, stage)
        else:
            self.add_stage(stage)

    def before_parsed_results(self, stage: Stage):
        """Add stage before parsing results."""
        index = self._find_stage_index(self.PARSE_STAGE_NAME)
        if index != -1:
            self.insert_stage(index, stage)
        else:
            self.add_stage(stage)

    def on_parsed_results(self, stage: Stage):
        """Add stage after parsing results."""
        index = self._find_stage_index(self.PARSE_STAGE_NAME)
        if index != -1:
            self.insert_stage(index + 1, stage)
        else:
            self.add_stage(stage)

    def before_send_to_download_client(self, stage: Stage):
        """Add stage before sending to download client."""
        index = self._find_stage_index(self.DOWNLOAD_STAGE_NAME)
        if index != -1:
            self.insert_stage(index, stage)
        else:
            self.add_stage(stage)

    def on_send_to_download_client(self, stage: Stage):
        """Add stage after sending to download client."""
        index = self._find_stage_index(self.DOWNLOAD_STAGE_NAME)
        if index != -1:
            self.insert_stage(index + 1, stage)
        else:
            self.add_stage(stage)


automated_pipe = AutomatedPipe()
