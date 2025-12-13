"""
Dynamic Variables Models

Models for dynamic variables returned from workflow initialization
and customer preferences.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CustomerPreferences(BaseModel):
    """Customer preference templates for first message."""
    
    outside_business_new_user_message_template: str = Field(
        default="Hey you have reached outside business hours. I still can help you"
    )
    inside_business_new_user_message_template: str = Field(
        default="Hey, how can I help you today"
    )
    outside_business_existing_user_message_template: str = Field(
        default="Hey {guest_name}, you have reached outside business hours. I still can help you"
    )
    inside_business_existing_user_message_template: str = Field(
        default="Hey {guest_name}, how can I help you today"
    )
    
    def get_first_message(
        self,
        is_outside_business_hours: bool,
        is_new_user: bool,
        guest_name: Optional[str] = None,
    ) -> str:
        """Get the appropriate first message based on context."""
        if is_outside_business_hours:
            if is_new_user:
                return self.outside_business_new_user_message_template
            else:
                return self.outside_business_existing_user_message_template.format(
                    guest_name=guest_name or "there"
                )
        else:
            if is_new_user:
                return self.inside_business_new_user_message_template
            else:
                return self.inside_business_existing_user_message_template.format(
                    guest_name=guest_name or "there"
                )


class DynamicVariables(BaseModel):
    """
    Dynamic variables from workflow initialization.
    
    These are populated from the WorkflowInit API call and used
    throughout the workflow execution.
    """
    
    # Center information
    center_name: str = Field(default="")
    center_id: str = Field(default="")
    org_name: str = Field(default="")
    org_id: str = Field(default="")
    
    # Business hours
    is_outside_business_hours: bool = Field(default=False)
    center_current_time: str = Field(default="")
    system_time: str = Field(default="")
    
    # Handover configuration
    is_handover_enabled: bool = Field(default=True)
    is_handover_enabled_outside_business_hours: bool = Field(default=True)
    is_handover_allowed: bool = Field(default=True)
    hand_over_number: str = Field(default="")
    transfer_other_number: str = Field(default="")
    
    # Guest information
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    guest_name: str = Field(default="")
    guest_id: str = Field(default="")
    caller_id: str = Field(default="")
    phone_code: str = Field(default="")
    is_new_user: bool = Field(default=True)
    guest_identification: str = Field(default="new_guest")
    guest_codes: str = Field(default="[]")
    guest_code_map: str = Field(default="{}")
    was_new_guest: bool = Field(default=True)
    
    # Appointment history
    has_previous_appointment: bool = Field(default=False)
    past_appointments_count: int = Field(default=0)
    future_appointments_count: int = Field(default=0)
    future_appointments_info: str = Field(default="")
    last_appointment_service_name: str = Field(default="")
    last_appointment_service_code: str = Field(default="")
    last_appointment_therapist_name: str = Field(default="")
    last_appointment_therapist_code: str = Field(default="")
    last_appointment_service_date_time: str = Field(default="")
    last_appointment_center_id: str = Field(default="")
    last_appointment_center_name: str = Field(default="")
    last_appointment_center_code: str = Field(default="")
    
    # Services
    categories: str = Field(default="[]")
    total_services_count: int = Field(default=0)
    
    # Agent configuration
    agent_name: str = Field(default="Atlas")
    agent_id: str = Field(default="")
    api_key: str = Field(default="")
    
    # Prompts and context
    caller_info: str = Field(default="")
    action_item: str = Field(default="")
    addressing_prompt: str = Field(default="")
    agent_context: str = Field(default="")
    booking_flow: str = Field(default="")
    rescheduling_flow: str = Field(default="")
    tools_section: str = Field(default="")
    current_intent: str = Field(default="BOOK")
    
    # Guest details configuration
    mandatory_fields_str: str = Field(default="first_name, last_name")
    guest_details_collection_mode: int = Field(default=1)
    form_submission_type: int = Field(default=1)
    
    # Deposit and payment
    is_deposit_enabled_for_center: bool = Field(default=False)
    credit_card_required_for_center: bool = Field(default=False)
    is_deposit_enabled_for_guest: bool = Field(default=True)
    
    # Call center
    is_callcenter: bool = Field(default=False)
    call_center_centers: str = Field(default="[]")
    hc_sid: Optional[str] = Field(default=None)
    
    # Booking configuration
    center_allows_multiple_service_booking: bool = Field(default=True)
    ask_for_more_services: str = Field(default="ask_initially")
    center_allows_multiple_therapist_booking: bool = Field(default=False)
    
    # Additional dynamic fields (catch-all)
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable value with fallback to extra."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a variable value."""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.extra[key] = value
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update variables from a dictionary."""
        for key, value in data.items():
            self.set(key, value)
    
    def to_context_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template substitution."""
        result = self.model_dump(exclude={"extra"})
        result.update(self.extra)
        return result
    
    def get_guest_display_name(self) -> str:
        """Get the best display name for the guest."""
        if self.guest_name and self.guest_name.strip():
            return self.guest_name.strip()
        
        parts = []
        if self.first_name and self.first_name.strip():
            parts.append(self.first_name.strip())
        if self.last_name and self.last_name.strip():
            parts.append(self.last_name.strip())
        
        if parts:
            return " ".join(parts)
        
        return "there"
    
    def should_ask_for_more_services(self) -> bool:
        """Check if we should ask for more services."""
        if not self.center_allows_multiple_service_booking:
            return False
        return self.ask_for_more_services == "ask_initially"
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> "DynamicVariables":
        """Create from API response."""
        dynamic_vars = response.get("dynamic_variables", response)
        
        # Extract known fields
        known_fields = {}
        extra = {}
        
        for key, value in dynamic_vars.items():
            if key in cls.model_fields:
                known_fields[key] = value
            else:
                extra[key] = value
        
        return cls(**known_fields, extra=extra)

