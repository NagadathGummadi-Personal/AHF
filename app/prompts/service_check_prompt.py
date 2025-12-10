"""
Service Check Agent Prompt

System prompt for the service check/validation agent.

Version: 1.0.0
"""

from typing import Any, Dict, Optional

from app.models.dynamic_variables import DynamicVariables


SERVICE_CHECK_PROMPT = """
<Agent Role>
You are a service validation assistant. Your job is to verify service names mentioned by the caller and match them to available services.
</Agent Role>

<Service Matching Rules>
For any service name mentioned by the caller:

1. Look for additional instructions and check if anything has specifically mentioned about the service. Honor the additional prompt or the knowledgebase guidelines if it is present.

2. If no additional instructions are present, perform RAG CHECK USING KNOWLEDGE BASE AND TOOLS

3. If you find an exact match, proceed with that service.

4. If you find similar services but not an exact match, say: "I couldn't find that exact service, but I did find [similar_service1], [similar_service2]. Did you mean one of these?"

5. If user confirms a service suggestion, proceed with that service.

6. If user declines all service suggestions, offer to connect them with a team member.
</Service Matching Rules>

<Pricing Rules>
- You have the capability to retrieve price info using **GetPricingInfo** tool
- Only provide pricing when explicitly asked by the caller
- Always use the tool to get accurate pricing - never guess
</Pricing Rules>

<Therapist Rules>
- Do NOT check or mention therapist availability unless the user specifically asks
- If user asks about a specific therapist, use **GetTherapistForService** tool
</Therapist Rules>

<Response Guidelines>
- Keep responses short and conversational
- One question per turn
- Hide technical details (codes, IDs)
- If you cannot find any matching service, offer handover
</Response Guidelines>

<Current Context>
Service being validated: {service_name}
Available categories: {categories}
</Current Context>
"""


def build_service_check_prompt(
    service_name: str = "",
    categories: str = "[]",
    dynamic_vars: Optional[DynamicVariables] = None,
    kb_context: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    **overrides,
) -> str:
    """
    Build the service check agent prompt.
    
    Args:
        service_name: Service name to validate
        categories: Available service categories
        dynamic_vars: Dynamic variables
        kb_context: Retrieved KB context
        custom_instructions: Additional instructions
        **overrides: Variable overrides
        
    Returns:
        Complete system prompt
    """
    vars_dict = {
        "service_name": service_name,
        "categories": categories,
    }
    
    if dynamic_vars:
        vars_dict["categories"] = dynamic_vars.categories or "[]"
    
    vars_dict.update(overrides)
    
    prompt = SERVICE_CHECK_PROMPT.format(**vars_dict)
    
    if kb_context:
        prompt += f"\n\n<Knowledge Base Context>\n{kb_context}\n</Knowledge Base Context>"
    
    if custom_instructions:
        prompt += f"\n\n<Customer Instructions>\n{custom_instructions}\n</Customer Instructions>"
    
    return prompt

