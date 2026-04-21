"""A Python library for interacting with the Discord widget."""

import requests
import aiohttp
import logging
import re
from typing import List, Optional
from .member import Member
from .channel import Channel


class WidgetException(Exception):
    """Exception raised for errors related to the Discord widget.

    Attributes:
        None
    """

    pass


class Widget:
    """Represents a Discord widget for a specific guild.

    Attributes:
        id (int): The ID of the widget.
        members (List[Member]): The list of members in the guild.
        channels (List[Channel]): The list of channels in the guild.
        presence_count (int): The number of members currently online.
        name (str): The name of the guild.
        instant_invite (str): The instant invite URL for the guild.
    """

    def __init__(self, guild_id: int, timeout: float = 10.0) -> None:
        """Initializes a new instance of the DiscordWidget class.

        Args:
            guild_id (int): The ID of the guild.
            timeout (float): Timeout in seconds for widget API requests.
        """
        self._guild_id = guild_id
        self._url = f"https://discord.com/api/guilds/{guild_id}/widget.json"
        self._widget_url = f"https://discord.com/widget?id={guild_id}"
        self._timeout = timeout

        self._members: List[Member] = []
        self._channels: List[Channel] = []

        self.id: int = 0
        self.presence_count: int = 0
        self.name: str = ""
        self.instant_invite: str = ""

    def __repr__(self) -> str:  # noqa: D105
        return f"<DiscordWidget {self._guild_id}>"

    def __eq__(self, other) -> bool:  # noqa: D105
        if not isinstance(other, Widget):
            return False
        return self._guild_id == other._guild_id

    def __str__(self) -> str:  # noqa: D105
        if self.id == 0:
            return f"Uninitialized DiscordWidget ({self._guild_id}) object"

        return f"DiscordWidget ({self.id}) object with {self.presence_count} members online in {self.name} ({self.instant_invite})"

    ### PRIVATE METHODS ###
    async def _async_request_json(
        self, session: Optional[aiohttp.ClientSession] = None
    ) -> dict:
        if session:
            async with session.get(
                self._url, timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as response:
                if response.status != 200:
                    raise WidgetException(f"HTTP error: {response.status}")
                return await response.json()
        else:
            async with aiohttp.ClientSession() as new_session:
                async with new_session.get(
                    self._url, timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as response:
                    if response.status != 200:
                        raise WidgetException(f"HTTP error: {response.status}")
                    return await response.json()

    def _sync_request_json(self) -> dict:
        try:
            r = requests.get(self._url, timeout=self._timeout)
            r.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
            return r.json()
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
            raise WidgetException(f"HTTP error: {http_err}")
        except requests.exceptions.RequestException as err:
            logging.error(f"Error fetching data: {err}")
            raise WidgetException(f"Network error: {err}")

    def _parse_members(self, members) -> None:
        if not isinstance(members, list):
            raise WidgetException("Invalid members data format")
        self._members = []
        for member in members:
            m_id = int(member["id"])
            m_username = member["username"]
            m_discriminator = member["discriminator"]
            m_avatar_url = member["avatar_url"]
            m_status = member["status"]
            m_avatar = member["avatar"]

            m = Member(
                m_id, m_username, m_discriminator, m_avatar_url, m_status, m_avatar
            )

            # Optional
            if "deaf" in member:
                m.deaf = member["deaf"]
            if "mute" in member:
                m.mute = member["mute"]
            if "self_deaf" in member:
                m.self_deaf = member["self_deaf"]
            if "self_mute" in member:
                m.self_mute = member["self_mute"]
            if "suppress" in member:
                m.suppress = member["suppress"]
            if "channel_id" in member:
                m.channel_id = int(member["channel_id"])
            if "game" in member:
                m.game = member["game"]["name"]

            self.members.append(m)

    def _parse_channels(self, channels) -> None:
        if not isinstance(channels, list):
            raise WidgetException("Invalid channels data format")
        self._channels = []
        for channel in channels:
            c = Channel(int(channel["id"]), channel["name"], int(channel["position"]))
            self.channels.append(c)

        self.channels.sort()

    def _parse_json(self, json) -> None:
        if json is None:
            raise WidgetException("Failed to get widget json.")

        if not isinstance(json, dict):
            raise WidgetException("Invalid JSON format")

        if "message" in json:
            raise WidgetException(f"Failed to get widget json: {json['message']}")
        try:
            self.id = int(json["id"])
            self.presence_count = json["presence_count"]
            self.name = json["name"]
            self.instant_invite = json["instant_invite"]

            self._parse_members(json["members"])
            self._parse_channels(json["channels"])
        except Exception:
            raise WidgetException("Failed to parse widget json")

    ### PUBLIC METHODS ###

    def get(self) -> None:
        """Retrieves data from the Discord API and parses the JSON response.

        Returns:
            None
        """
        json = self._sync_request_json()
        self._parse_json(json)

    async def get_async(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        """Asynchronously retrieves data from the server and parses the JSON response.

        Args:
            session (Optional[aiohttp.ClientSession]): An optional `aiohttp.ClientSession` object to use for the request.

        Returns:
            None
        """
        json = await self._async_request_json(session)
        self._parse_json(json)

    @property
    def channels(self) -> List[Channel]:
        """Returns the list of channels in the guild."""
        return self._channels

    @property
    def members(self) -> List[Member]:
        """Returns the list of members in the guild."""
        return self._members

    @classmethod
    def from_url(cls, url: str) -> "Widget":
        """Creates a new DiscordWidget object from a widget URL."""
        if not re.match(r"https://discord.com/api/guilds/(\d+)/widget.json", url):
            raise WidgetException("Invalid url")
        guild_id = int(url.split("/")[-1])
        return cls(guild_id)
