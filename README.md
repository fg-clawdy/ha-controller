# Home Assistant Controller

Voice control your Home Assistant smart home directly through OpenHome. Control lights, switches, climate, media players, and more using natural language commands.

## Suggested Trigger Words

- hey homey
- hey homie

## Setup

### Prerequisites

1. **Home Assistant Instance**
   - Running Home Assistant (Hass.io / Home Assistant Core)
   - Accessible via HTTP (local IP or cloud)

2. **Long-Lived Access Token**
   - In Home Assistant: Profile → Security → Create Token
   - Copy the token (you'll need it for configuration)

### Configuration

After uploading this ability, you'll need to add your Home Assistant details:

1. Go to your OpenHome dashboard → Abilities → HA Controller
2. Add these configuration values:
   - `ha_url`: Your Home Assistant URL (e.g., `http://192.168.1.100:8123`)
   - `ha_token`: Your Long-Lived Access Token

## Usage

1. Say **"hey homey"** or **"hey homie"** to activate
2. Tell it what you want to do, for example:
   - "Turn on the living room lights"
   - "Turn off the kitchen light"
   - "Set the thermostat to 72"
   - "Dim the bedroom to 50 percent"
   - "Turn on the fan"
3. The ability will confirm when complete

## Supported Commands

| Command Type | Examples |
|--------------|----------|
| Lights | turn on/off, dim, brightness |
| Switches | turn on/off, toggle |
| Climate | set temperature, mode |
| Fans | turn on/off, set speed |
| Media | volume up/down, play/pause |

## Security

This ability is configured to **block** control of:
- Locks
- Garage doors
- Alarm panels
- Sensors

Voice commands for these devices will be politely declined.

## Troubleshooting

**"Home Assistant is not configured"**
- Make sure you added ha_url and ha_token in the ability settings

**"Could not connect to Home Assistant"**
- Check your HA URL is correct and accessible
- Ensure Home Assistant is running
- Verify your access token is valid

**"Something went wrong"**
- Check the entity name exists in Home Assistant
- Verify the service is valid for that entity

## Author

Built with OpenHome Ability SDK