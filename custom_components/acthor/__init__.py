from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "acthor"


def setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.async_add_job(hass.config_entries.async_forward_entry_setup(config_entry, "sensor"))
