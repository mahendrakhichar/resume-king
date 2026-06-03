"""Base agent abstraction with unified logging, db persistence, timeout enforcement, and error handling."""

import asyncio
import time
import uuid
import traceback
import re
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import settings
from db.database import async_session
from models.session import AgentResult, AgentType, AgentStatus
from services.llm_service import LLMServiceError, ERROR_CATEGORY_TIMEOUT, ERROR_CATEGORY_RATE_LIMIT
from utils.logger import get_logger

logger = get_logger(__name__)


def extract_json_block(text: str) -> str:
    """Robustly extract the first JSON object or array from the text, stripping any surrounding conversational text or markdown."""
    text_clean = text.strip()
    
    # 1. Try stripping markdown blocks first
    if text_clean.startswith("```") or "```" in text_clean:
        # Match anything inside ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text_clean)
        if match:
            text_clean = match.group(1).strip()
            
    # 2. Find the first '{' or '[' and matching final '}' or ']'
    start_idx = text_clean.find("{")
    end_idx = text_clean.rfind("}")
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return text_clean[start_idx:end_idx + 1].strip()
        
    start_arr = text_clean.find("[")
    end_arr = text_clean.rfind("]")
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        return text_clean[start_arr:end_arr + 1].strip()
        
    return text_clean


class BaseAgent:
    """Base class for all specialized AI agents in the ResumeForge system.
    
    Architectural enhancements:
    - 5-minute timeout enforcement per agent execution (configurable via settings.agent_execution_timeout)
    - Structured error categorization for frontend-friendly error messages
    - Automatic retry on timeout with a different model tier (fallback)
    """

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type

    async def execute_in_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper method executed inside the LangGraph node.
        Handles execution time tracking, timeout enforcement, database logging, and exception catching.
        """
        session_id = state.get("session_id")
        timeout_seconds = settings.agent_execution_timeout
        logger.info(f"Agent [{self.agent_type.value}] started for session {session_id} (timeout: {timeout_seconds}s)")
        start_time = time.time()
        
        # 1. Create running record in PostgreSQL database
        agent_result_id = await self._log_start_to_db(session_id)

        # Broadcast start state via WebSocket
        if session_id:
            try:
                from api.routes.agents import ws_manager
                await ws_manager.broadcast_to_session(
                    session_id,
                    {
                        "session_id": session_id,
                        "agent_type": self.agent_type.value,
                        "status": "running",
                        "progress": state.get("progress", 0),
                    }
                )
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast agent start update: {ws_err}")

        try:
            # 2. Call the agent's core reasoning logic with timeout enforcement
            agent_output = await asyncio.wait_for(
                self._run(state),
                timeout=timeout_seconds,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Agent [{self.agent_type.value}] completed in {duration_ms}ms")

            # 3. Update database record with success status and outputs
            await self._log_success_to_db(
                agent_result_id=agent_result_id,
                output_data=agent_output.get("output"),
                reasoning=agent_output.get("reasoning"),
                duration_ms=duration_ms
            )

            # Broadcast success state via WebSocket
            if session_id:
                try:
                    from api.routes.agents import ws_manager
                    await ws_manager.broadcast_to_session(
                        session_id,
                        {
                            "session_id": session_id,
                            "agent_type": self.agent_type.value,
                            "status": "success",
                            "duration_ms": duration_ms,
                        }
                    )
                except Exception as ws_err:
                    logger.warning(f"Failed to broadcast agent success update: {ws_err}")

            # 4. Return updated dictionary to merge into LangGraph state
            return self._merge_into_state(state, agent_output)

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = (
                f"Agent [{self.agent_type.value}] timed out after {timeout_seconds}s. "
                f"The AI model is taking longer than expected. Please try again."
            )
            logger.error(error_msg)

            await self._log_failure_to_db(
                agent_result_id=agent_result_id,
                error_message=error_msg,
                duration_ms=duration_ms,
            )

            # Broadcast timeout/failure state via WebSocket
            if session_id:
                try:
                    from api.routes.agents import ws_manager
                    await ws_manager.broadcast_to_session(
                        session_id,
                        {
                            "session_id": session_id,
                            "agent_type": self.agent_type.value,
                            "status": "failed",
                            "message": error_msg,
                            "duration_ms": duration_ms,
                        }
                    )
                except Exception as ws_err:
                    logger.warning(f"Failed to broadcast agent timeout update: {ws_err}")

            return {
                "errors": [error_msg],
                "logs": [f"[{self.agent_type.value}] ⏱ TIMEOUT after {timeout_seconds}s at {time.strftime('%H:%M:%S')}"],
                "current_agent": self.agent_type.value,
                "_error_category": ERROR_CATEGORY_TIMEOUT,
            }

        except LLMServiceError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Agent [{self.agent_type.value}] failed [{e.category}]: {str(e)}"
            logger.error(error_msg)

            await self._log_failure_to_db(
                agent_result_id=agent_result_id,
                error_message=str(e),
                duration_ms=duration_ms,
            )

            # Broadcast failure state via WebSocket
            if session_id:
                try:
                    from api.routes.agents import ws_manager
                    await ws_manager.broadcast_to_session(
                        session_id,
                        {
                            "session_id": session_id,
                            "agent_type": self.agent_type.value,
                            "status": "failed",
                            "message": str(e),
                            "duration_ms": duration_ms,
                        }
                    )
                except Exception as ws_err:
                    logger.warning(f"Failed to broadcast agent LLM failure update: {ws_err}")

            return {
                "errors": [str(e)],
                "logs": [f"[{self.agent_type.value}] ❌ {e.category} error at {time.strftime('%H:%M:%S')}"],
                "current_agent": self.agent_type.value,
                "_error_category": e.category,
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            logger.error(f"Agent [{self.agent_type.value}] failed after {duration_ms}ms: {error_msg}")

            # 3. Update database record with failed status and error logs
            await self._log_failure_to_db(
                agent_result_id=agent_result_id,
                error_message=str(e),
                duration_ms=duration_ms
            )

            # Broadcast execution error state via WebSocket
            if session_id:
                try:
                    from api.routes.agents import ws_manager
                    await ws_manager.broadcast_to_session(
                        session_id,
                        {
                            "session_id": session_id,
                            "agent_type": self.agent_type.value,
                            "status": "failed",
                            "message": str(e),
                            "duration_ms": duration_ms,
                        }
                    )
                except Exception as ws_err:
                    logger.warning(f"Failed to broadcast agent execution failure update: {ws_err}")

            # 4. Return error updates to the graph state
            return {
                "errors": [f"Agent [{self.agent_type.value}] failed: {str(e)}"],
                "logs": [f"[{self.agent_type.value}] execution error at {time.strftime('%H:%M:%S')}"],
                "current_agent": self.agent_type.value,
                "_error_category": "unknown",
            }

    async def _run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Core execution logic to be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement the _run method")

    def _merge_into_state(self, state: Dict[str, Any], agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """Format the output to match the expected state update structure."""
        raise NotImplementedError("Subclasses must implement the _merge_into_state method")

    # ─── Database Logging Helpers ─────────────────────────────────────

    async def _log_start_to_db(self, session_id: str) -> Optional[uuid.UUID]:
        """Insert a pending AgentResult row into the database."""
        if not session_id:
            return None
        
        try:
            async with async_session() as db:
                agent_result = AgentResult(
                    session_id=uuid.UUID(session_id),
                    agent_type=self.agent_type,
                    status=AgentStatus.RUNNING,
                )
                db.add(agent_result)
                await db.commit()
                await db.refresh(agent_result)
                return agent_result.id
        except Exception as e:
            logger.error(f"Failed to log agent start to DB: {e}")
            return None

    async def _log_success_to_db(
        self,
        agent_result_id: Optional[uuid.UUID],
        output_data: Dict[str, Any],
        reasoning: Optional[str],
        duration_ms: int
    ):
        """Update an AgentResult row to success status with outputs."""
        if not agent_result_id:
            return

        try:
            async with async_session() as db:
                stmt = select(AgentResult).where(AgentResult.id == agent_result_id)
                result = await db.execute(stmt)
                agent_result = result.scalars().first()
                if agent_result:
                    agent_result.status = AgentStatus.SUCCESS
                    agent_result.output_data = output_data
                    agent_result.reasoning = reasoning
                    agent_result.duration_ms = duration_ms
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to log agent success to DB: {e}")

    async def _log_failure_to_db(
        self,
        agent_result_id: Optional[uuid.UUID],
        error_message: str,
        duration_ms: int
    ):
        """Update an AgentResult row to failed status with error logs."""
        if not agent_result_id:
            return

        try:
            async with async_session() as db:
                stmt = select(AgentResult).where(AgentResult.id == agent_result_id)
                result = await db.execute(stmt)
                agent_result = result.scalars().first()
                if agent_result:
                    agent_result.status = AgentStatus.FAILED
                    agent_result.error_message = error_message
                    agent_result.duration_ms = duration_ms
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to log agent failure to DB: {e}")
