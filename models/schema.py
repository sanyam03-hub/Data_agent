from operator import add

from pydantic import BaseModel, Field
from typing import Annotated

class AgentSchema(BaseModel):
    messages: Annotated[list, add] = Field(..., description="List of messages from the agent.")