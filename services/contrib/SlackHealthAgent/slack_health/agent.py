"""
Agent documentation goes here.
"""

__docformat__ = "reStructuredText"

import logging
import re
from slackclient import SlackClient
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core
import yaml

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "1.0"


def slack_health(config_path, **kwargs):
    """Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.

    :type config_path: str
    :returns: SlackHealth
    :rtype: SlackHealth
    """

    if isinstance(config_path, dict):
        config_dict = config_path
    else:
        config_dict = utils.load_config(config_path)

    utils.update_kwargs_with_config(kwargs, config_dict)
    return SlackHealth(**kwargs)


class SlackHealth(Agent):
    """
    Document agent constructor here.
    """

    def __init__(
        self,
        slack_api_token=None,
        message_template=None,
        agent_channel_config=None,
        **kwargs
    ):
        super(SlackHealth, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self._client = None
        self.slack_api_token = slack_api_token
        self.message_template = message_template
        self.agent_channel_config = agent_channel_config

        self.default_config = {
            "slack_api_token": self.slack_api_token,
            "message_template": self.message_template,
            "agent_channel_config": self.agent_channel_config,
        }

        # Set a default configuration to ensure that self.configure is called
        # immediately to setup the agent.
        self.vip.config.set_default("config", self.default_config)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(
            self.configure, actions=["NEW", "UPDATE"], pattern="config"
        )

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus. If a
        configuration exists at startup this will be called before onstart.

        Is called every time the configuration in the store changes.
        """
        config = self.default_config.copy()
        config.update(contents)

        _log.debug("Configuring Slack Health agent")

        if not isinstance(config["slack_api_token"], str):
            _log.warning("Supplied slack_api_token is not a string, ignored")
            slack_api_token = ""
        else:
            slack_api_token = config["slack_api_token"]

        if not isinstance(config["message_template"], str):
            _log.warning("Supplied message_template is not a string, using default")
            message_template = (
                "Agent {agent_identity} ({agent_class}) health"
                " is {agent_status} ({alert_key}) with {status_context}"
            )
        else:
            message_template = config["message_template"]

        if not isinstance(config["agent_channel_config"], dict):
            _log.warning(
                "Supplied agent_channel_config is not a dict,"
                " nothing will be published to Slack!"
            )
            agent_channel_config = {}
        else:
            agent_channel_config = config["agent_channel_config"]

        if not all([slack_api_token, message_template, agent_channel_config]):
            return

        _log.debug("Setting up Slack client")
        self._client = SlackClient(self.slack_api_token)

        self.slack_api_token = slack_api_token
        self.message_template = message_template
        self.agent_channel_config = agent_channel_config

        try:
            _log.debug("Unsubscribing from all subscriptions")
            self.vip.pubsub.unsubscribe("pubsub", None, None)
        except KeyError:
            pass
        _log.debug("Subscribing to all alerts")
        self.vip.pubsub.subscribe(
            peer="pubsub", prefix="alerts", callback=self._handle_publish
        )

    def _handle_publish(self, peer, sender, bus, topic, headers, message):
        m = re.match(r"alerts/(?P<agent_class>.*)/(?P<agent_identity>.*)", topic)
        if m:
            agent_class = m.group("agent_class")
            agent_identity = m.group("agent_identity")
        else:
            _log.info(
                "Alerts from {sender} do not follow the "
                '"alerts/{agent_class}/{agent_identity}" template.'.format(
                    sender=sender
                )
            )
        alert_key = headers.get("alert_key", None)
        content = yaml.safe_load(message)
        content = content if isinstance(content, dict) else {}
        agent_status = content.get("status", None)
        status_context = content.get("context", None)
        channels = self.agent_channel_config.get(agent_identity, [])
        for channel in channels:
            text = self.message_template.format(
                agent_class=agent_class,
                agent_identity=agent_identity,
                agent_status=agent_status,
                status_context=status_context,
                alert_key=alert_key,
            )
            _log.debug(
                'Sending message "{text}" to Slack channel "{channel}"'.format(
                    text=text, channel=channel
                )
            )
            self._client.api_call("chat.postMessage", channel=channel, text=text)

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to
        the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the
        message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        pass

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before
        it disconnects from the message bus.
        """
        pass


def main():
    """Main method called to start the agent."""
    utils.vip_main(slack_health, identity="slack_health", version=__version__)


if __name__ == "__main__":
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
