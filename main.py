"""
Home Assistant Controller for OpenHome

Voice control for Home Assistant entities (lights, switches, climate, etc.)
via natural language commands. Uses LLM to parse intent, then calls HA REST API.
"""

import json
import os
import requests

from src.agent.capability import MatchingCapability
from src.main import AgentWorker
from src.agent.capability_worker import CapabilityWorker


class HomeAssistantController(MatchingCapability):
    """Voice-controlled Home Assistant entity management."""

    worker: AgentWorker = None
    capability_worker: CapabilityWorker = None

    # Config values loaded from config.json
    ha_url: str = ""
    ha_token: str = ""

    # Security blocklist — these entity domains are not allowed
    BLOCKED_DOMAINS = {
        "lock", "garage", "alarm", "binary_sensor", "sensor"
    }

    # Do not change following tag of register capability
    #{{register capability}}

    @classmethod
    def register_capability(cls) -> "MatchingCapability":
        with open(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        ) as file:
            data = json.load(file)
        return cls(
            unique_name=data["unique_name"],
            matching_hotwords=data["matching_hotwords"],
            ha_url=data.get("ha_url", ""),
            ha_token=data.get("ha_token", ""),
        )

    def call(self, worker: AgentWorker):
        self.worker = worker
        self.capability_worker = CapabilityWorker(self.worker)
        self.worker.session_tasks.create(self.run())

    async def run(self):
        """Main ability entry point."""
        try:
            # Validate config on startup
            if not self.ha_url or not self.ha_token:
                await self.capability_worker.speak(
                    "Home Assistant is not configured. "
                    "Please add your HA URL and token in the ability settings."
                )
                return

            await self._handle_command()
        except Exception as e:
            self.worker.editor_logging_handler.error(f"HA Controller error: {e}")
            await self.capability_worker.speak(
                "I had trouble connecting to Home Assistant. Let me hand you back."
            )
        finally:
            self.capability_worker.resume_normal_flow()

    async def _handle_command(self):
        """Listen for user command and execute via HA API."""
        await self.capability_worker.speak(
            "I'm listening. Tell me what you'd like to control in your home."
        )

        # Wait for user to speak their command
        user_command = await self.capability_worker.user_response()
        self.worker.editor_logging_handler.info(f"User command: {user_command}")

        if not user_command or user_command.strip() == "":
            await self.capability_worker.speak("I didn't catch that. Goodbye!")
            return

        # Use LLM to parse intent into HA action
        intent = self._parse_intent(user_command)

        if not intent:
            await self.capability_worker.speak(
                "I couldn't understand that command. Try something like "
                "'turn on the living room lights'."
            )
            return

        # Check for security-related commands
        if self._is_blocked(intent):
            await self.capability_worker.speak(
                "I can't control security devices like locks or alarms. "
                "Is there something else I can help with?"
            )
            return

        # Execute the HA API call
        result = self._execute_ha_action(intent)

        if result["success"]:
            await self.capability_worker.speak(result["message"])
        else:
            await self.capability_worker.speak(
                f"Something went wrong: {result.get('error', 'Unknown error')}"
            )

    def _parse_intent(self, user_command: str) -> dict:
        """
        Use LLM to parse natural language into HA action.
        Returns dict with: entity_id, domain, service, data (optional)
        """
        prompt = f"""You are a Home Assistant intent parser.
Given a user's voice command, extract the action they want to perform.

Rules:
- Only respond with valid Home Assistant service calls
- Reject security commands (locks, alarms, garage doors, sensors)
- Map to standard services: turn_on, turn_off, toggle, set_temperature, set_speed, volume_set
- Extract entity_id (e.g., light.living_room, switch.garage, climate.thermostat)
- For dimming/brightness, extract brightness_pct (0-100)
- For volume, extract volume_level (0.0-1.0)
- For temperature, extract temperature (number)

User said: "{user_command}"

Respond ONLY with a JSON object like this (or "null" if invalid):
{{
  "entity_id": "light.living_room_lights",
  "domain": "light",
  "service": "turn_on",
  "data": {{"brightness_pct": 50}}
}}

If the command is invalid, rejected, or unclear, respond with exactly: null"""

        response = self.capability_worker.text_to_text_response(prompt)
        self.worker.editor_logging_handler.info(f"LLM intent response: {response}")

        # Try to parse JSON from response
        try:
            # Handle potential markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            intent = json.loads(response.strip())
            return intent
        except (json.JSONDecodeError, AttributeError) as e:
            self.worker.editor_logging_handler.error(f"Intent parse error: {e}")
            return None

    def _is_blocked(self, intent: dict) -> bool:
        """Check if the target domain is blocked for security."""
        if not intent or "domain" not in intent:
            return True

        domain = intent.get("domain", "").lower()
        return domain in self.BLOCKED_DOMAINS

    def _execute_ha_action(self, intent: dict) -> dict:
        """
        Execute a Home Assistant service call via REST API.
        Returns success/error dict.
        """
        entity_id = intent.get("entity_id", "")
        domain = intent.get("domain", "homeassistant")
        service = intent.get("service", "turn_on")
        data = intent.get("data", {})

        # Build HA API URL
        ha_url = self.ha_url.rstrip("/")
        url = f"{ha_url}/api/services/{domain}/{service}"

        # Prepare request payload
        payload = {"entity_id": entity_id}
        payload.update(data)

        headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)

            if resp.status_code == 200:
                # Generate friendly response message
                action = "turned on" if service == "turn_on" else \
                         "turned off" if service == "turn_off" else \
                         "set" if service == "set_temperature" else \
                         "controlled"

                # Extract friendly name from entity_id
                friendly_name = entity_id.split(".")[-1].replace("_", " ")

                return {
                    "success": True,
                    "message": f"Done. I've {action} the {friendly_name}."
                }
            else:
                return {
                    "success": False,
                    "error": f"HA returned status {resp.status_code}"
                }

        except requests.exceptions.RequestException as e:
            self.worker.editor_logging_handler.error(f"HA API error: {e}")
            return {
                "success": False,
                "error": f"Could not connect to Home Assistant: {str(e)}"
            }