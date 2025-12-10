"""
Voice Agent Main Entry Point

Example usage of the voice agent workflow.

Version: 1.0.0
"""

import asyncio
from typing import Optional

from core.llms import LLMFactory, LLMContext

from app.config import get_settings
from app.workflows import SalonBookingWorkflow, VoiceAgentExecutor


async def create_executor(
    azure_api_key: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
) -> VoiceAgentExecutor:
    """
    Create a configured workflow executor.
    
    Args:
        azure_api_key: Azure OpenAI API key
        azure_endpoint: Azure OpenAI endpoint
        
    Returns:
        Configured VoiceAgentExecutor
    """
    settings = get_settings()
    
    # Create LLM
    connector_config = {
        "api_key": azure_api_key or settings.azure_api_key,
        "azure_endpoint": azure_endpoint or settings.azure_endpoint,
        "api_version": settings.azure_api_version,
    }
    
    llm = LLMFactory.create_llm(
        settings.llm_model,
        connector_config=connector_config,
    )
    
    # Create workflow
    workflow = SalonBookingWorkflow(llm=llm, settings=settings)
    
    # Create executor
    executor = VoiceAgentExecutor(workflow=workflow, settings=settings)
    
    return executor


async def run_demo():
    """
    Run a demo conversation.
    
    This demonstrates the basic flow of the voice agent.
    """
    print("=" * 60)
    print("Voice Agent Demo")
    print("=" * 60)
    
    # Create executor
    # Note: In production, pass actual Azure credentials
    executor = await create_executor()
    
    # Initialize workflow
    print("\n[Initializing workflow...]")
    
    try:
        result = await executor.execute_init(
            caller_id="+18564548056",
            center_id="a2fc1a1b-7146-4078-94e6-b5d2c901ce50",
            org_id="8ff81c76-d55e-4e6c-9024-78f6a7b82a5c",
            agent_id="agent_0401k2j77nj3f96s5xvfe22c3fx3",
            called_number="+15179290774",
        )
        
        print(f"\n[First Message]: {result.get('first_message')}")
        print(f"[Session ID]: {result.get('session_id')}")
        
    except Exception as e:
        print(f"[Error during init]: {e}")
        print("[Note: This demo requires valid API credentials]")
        return
    
    # Simulate conversation
    demo_inputs = [
        "I'd like to book a haircut",
        "Yes, the regular haircut",
        "No add-ons needed",
        "Today at 3 PM",
    ]
    
    for user_input in demo_inputs:
        print(f"\n[User]: {user_input}")
        
        try:
            response = await executor.process_user_input(user_input)
            print(f"[Agent]: {response.get('response')}")
            
            if response.get("detected_intent"):
                print(f"[Intent]: {response.get('detected_intent')}")
                
        except Exception as e:
            print(f"[Error]: {e}")
            break
    
    # Cleanup
    await executor.cancel()
    print("\n[Session ended]")


# Example of how to use the workflow in a real application
class VoiceAgentApp:
    """
    Example application class for voice agent integration.
    
    This shows how to integrate the workflow with a voice platform.
    """
    
    def __init__(self):
        self._executor: Optional[VoiceAgentExecutor] = None
    
    async def start_call(
        self,
        caller_id: str,
        center_id: str,
        org_id: str,
        agent_id: str,
        called_number: str,
        call_sid: str = "",
    ) -> dict:
        """
        Start a new call session.
        
        Called when a new call comes in.
        """
        self._executor = await create_executor()
        
        return await self._executor.execute_init(
            caller_id=caller_id,
            center_id=center_id,
            org_id=org_id,
            agent_id=agent_id,
            called_number=called_number,
            call_sid=call_sid,
        )
    
    async def handle_utterance(self, text: str) -> dict:
        """
        Handle a user utterance.
        
        Called when speech-to-text produces text.
        """
        if not self._executor:
            raise ValueError("Call not started")
        
        return await self._executor.process_user_input(text)
    
    async def handle_interrupt(self, text: str) -> dict:
        """
        Handle user interrupt during agent speech.
        
        Called when user speaks while agent is speaking.
        """
        if not self._executor:
            raise ValueError("Call not started")
        
        # The executor handles interrupts automatically
        # Just process the new input
        return await self._executor.process_user_input(text)
    
    async def end_call(self) -> None:
        """End the call session."""
        if self._executor:
            await self._executor.cancel()
            self._executor = None


if __name__ == "__main__":
    asyncio.run(run_demo())

