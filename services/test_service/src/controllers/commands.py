import logging

from faststream.redis import RedisRouter
from shared.generated.schemas import CommandReceived

logger = logging.getLogger(__name__)

router = RedisRouter()


@router.subscriber("command_received")
async def handle_command(msg: CommandReceived):
    logger.info(f"Received command: {msg.command} with args: {msg.args} from user: {msg.user_id}")
