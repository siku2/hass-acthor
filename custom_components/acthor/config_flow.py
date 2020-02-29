import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_NAME

from .acthor import test_connection
from .const import DEVICE_NAME, DOMAIN


class ACThorConfigFlow(ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input: dict = None) -> dict:
        errors = {}
        if user_input is not None:
            ok = await test_connection(user_input[CONF_HOST], timeout=5)
            if ok:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )
            else:
                errors["base"] = "connection_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=DEVICE_NAME): str,
                vol.Required(CONF_HOST): str,
            }),
            errors=errors,
        )
