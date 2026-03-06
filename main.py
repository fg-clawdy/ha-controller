"""
Home Assistant Controller - Brain Skill

This ability stores Home Assistant configuration and provides the agent
with instructions on how to control HA devices via REST API.
"""

import json

from src.agent.capability import MatchingCapability
from src.main import AgentWorker
from src.agent.capability_worker import CapabilityWorker


class HomeAssistantController(MatchingCapability):
    """Stores HA config and injects control instructions into agent prompt."""

    worker: AgentWorker = None
    capability_worker: CapabilityWorker = None

    # Configuration - edit these values directly
    ha_url: str = "http://homeassistant.local:8123"
    ha_token: str = "YOUR_HA_TOKEN_HERE"

    # Do not change following tag of register capability
    #{{register capability}}

    @classmethod
    def register_capability(cls) -> "MatchingCapability":
        return cls(
            unique_name="ha-controller",
            matching_hotwords=["hey homey", "hey homie"],
        )

    def call(self, worker: AgentWorker):
        self.worker = worker
        self.capability_worker = CapabilityWorker(self)
        self.worker.session_tasks.create(self.run())

    async def run(self):
        """Inject HA configuration into agent prompt."""
        # Build theHA control instructions
        ha_instructions = self._build_ha_instructions()

        # Inject into agent prompt
        self.capability_worker.update_personality_agent_prompt(ha_instructions)

        # Store credentials in context for other abilities to access
        self.capability_worker.create_key(
            key="home_assistant_config",
            value={
                "ha_url": self.ha_url,
                "ha_token": self.ha_token,
                "configured": self.ha_token != "YOUR_HA_TOKEN_HERE"
            }
        )

        await self.capability_worker.speak(
            "Home Assistant controller configured. "
            "You can now control your smart home devices."
        )
        self.capability_worker.resume_normal_flow()

    def _build_ha_instructions(self) -> str:
        """Build the prompt injection for HA control."""
        return f"""

## Home Assistant Integration

You have access to control Home Assistant devices.

**Configuration:**
- HA URL: {self.ha_url}
- HA Token: {self.ha_token[:10]}... (stored in ability context)

**How to control devices:**

To control any Home Assistant entity, make a REST API call to:
`{{HA_URL}}/api/services/{{domain}}/{{service}}`

With JSON body: {{"entity_id": "entity.id"}}

**Examples:**
- Turn on light: POST to `light/turn_on` with `{{"entity_id": "light.living_room"}}`
- Turn off switch: POST to `switch/turn_off` with `{{"entity_id": "switch.garage"}}`
- Set climate: POST to `climate/set_temperature` with `{{"entity_id": "climate.thermostat", "temperature": 72}}`

**Security:** Do not control locks, garage doors, or alarm panels.

"""