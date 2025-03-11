import re
import random
from typing import List, Tuple
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from mautrix.types import (EventType, ReactionEvent, RedactionEvent)
from maubot import Plugin, MessageEvent
from maubot.handlers import command, event
import emoji as _emoji


QUOTES_REGEX = r"\"?\s*?\""  # Regex to split string between quotes
# [Octopus, Ghost, Robot, Okay Hand, Clapping Hands, Hundred, Pizza Slice, Taco, Bomb, Checquered Flag]
REACTIONS = ["\U0001F44D", "\U0001F622", "\U0001F62E", "\U0001F602"]
EMOJI_REGEX = r"^[\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF]"


class Poll:
    def __init__(self, question, choices, emojis=None):
        self.question = question
        self.choices = choices
        self.votes = [0] * len(choices)  # initialize all votes to zero
        self.voters = {}
        self.active = True  # Begins the poll
        self.total = 0

        self.emojis = REACTIONS[:len(choices)]
        self.emoji_strings = [_emoji.demojize(emoji) for emoji in self.emojis]

    def vote(self, choice, user_id, event_id):
        self.votes[choice] += 1
        # Adds user to list of users who have already voted
        if user_id in self.voters:
            self.redact_vote(user_id)
        self.voters[user_id] = (choice, event_id)
        self.total += 1

    def redact_vote(self, user_id):
        if user_id in self.voters:
            choice, event_id = self.voters[user_id]
            # Remove the vote
            del self.voters[user_id]
            self.votes[choice] -= 1
            self.total -= 1


    def isAvailable(self, choice):
        # Checks if given choice is an option
        return choice <= len(self.choices)

    def hasVoted(self, user):
        # Checks if user has already voted
        return user in self.voters

    def isActive(self):
        # Checks if the poll is currently active
        return self.active

    def get_results(self):
        # Formats the results with percentages
        results = f"{self.question}<br />" + "<br />".join(
            [
                f"{self.emojis[i]} - {choice}: {self.votes[i]}"
                for i, choice in sorted(enumerate(self.choices),
                                        key=lambda x: self.votes[x[0]], reverse=True)
            ]
        )
        return results

    def close_poll(self):
        self.active = False


class PollPlugin(Plugin):
    currentPolls = {}

    def hasActivePoll(self, room_id):
        poll = self.getPoll(room_id)
        return poll is not None and poll.isActive()

    def getPoll(self, room_id):
        return self.currentPolls.get(room_id, None)

    @command.new("poll", help="Make a poll")
    async def poll(self) -> None:
        pass

    @poll.subcommand("new", help='Creates a new poll with "Question" "choice" "choice" "choice" ...')
    @command.argument(
        "poll_setup",
        pass_raw=True,
        required=True
    )
    async def handler(self, evt: MessageEvent, poll_setup: str) -> None:
        await evt.mark_read()

        if self.hasActivePoll(evt.room_id):
            await evt.reply("A poll is active, please close the poll before creating a new one.", allow_html=False)
            return

        if poll_setup[0] == '"':
            r = re.compile(QUOTES_REGEX)  # Compiles regex for quotes
            setup = [
                s for s in r.split(poll_setup) if s != ""
            ]  # Split string between quotes
        else:
            setup = re.findall(r"^.*$", poll_setup, re.MULTILINE)
        question = setup[0]
        choices = setup[1:]
        if len(choices) <= 1:
            response = "You need to enter at least 2 choices."
            await evt.reply(response, allow_html=True)
            return
        elif len(choices) > len(REACTIONS):
            response = f"You can only enter up to {len(REACTIONS)} choices."
            await evt.reply(response, allow_html=True)
            return
        else:
            emojis = []
            r = re.compile(EMOJI_REGEX)
            for i, choice in enumerate(choices):
                choice_tmp = choice.strip()
                x = r.search(choice_tmp[0])
                if x:
                    emoji = choice_tmp[0]
                    choice_tmp = choice_tmp[1:].strip()
                else:
                    emoji = None
                choices[i] = choice_tmp
                emojis.append(emoji)

            self.currentPolls[evt.room_id] = Poll(question, choices, emojis)
            # Show users active poll
            choice_list = "<br />".join(
                [f"{self.currentPolls[evt.room_id].emojis[i]} - {choice}" for i,
                    choice in enumerate(choices)]
            )
            response = f"{question}<br />{choice_list}"
        self.currentPolls[evt.room_id].event_id = await evt.reply(response, allow_html=True)
        for emoji in self.currentPolls[evt.room_id].emojis:
            await evt.client.react(evt.room_id, self.currentPolls[evt.room_id].event_id, emoji)

    @poll.subcommand("results", help="Prints out the current results of the poll")
    async def handler(self, evt: MessageEvent) -> None:
        await evt.mark_read()
        poll = self.getPoll(evt.room_id)
        if poll is not None:
            await evt.reply(poll.get_results(), allow_html=True)
        else:
            await evt.reply("There is no active poll in this room", allow_html=True)

    @poll.subcommand("close", help="Ends the poll and prints out results")
    async def handler(self, evt: MessageEvent) -> None:
        await evt.mark_read()
        if self.hasActivePoll(evt.room_id):
            poll = self.getPoll(evt.room_id)
            self.currentPolls[evt.room_id].close_poll()
            await evt.reply("This poll is now over. <br />" + poll.get_results(), allow_html=True)
        else:
            await evt.reply("There is no active poll in this room")

    @command.passive(regex=EMOJI_REGEX,
                     field=lambda evt: evt.content.relates_to.key,
                     event_type=EventType.REACTION, msgtypes=None)
    async def get_react_vote(self, evt: ReactionEvent, _: Tuple[str]) -> None:
        self.log.debug(f"received reaction: {evt}")
        # Is this on the correct message?
        if (evt.content.relates_to.event_id == self.currentPolls[evt.room_id].event_id):
            self.log.debug(f"received vote: {evt.content.relates_to.key} ({evt.content.relates_to.key.encode('utf-8')})")
            # Is this a possible choice?
            # Turn emojis into emoji shortcodes to avoid issues with emoji variants
            emoji_shortcode = _emoji.demojize(evt.content.relates_to.key)
            self.log.debug(f"short: {emoji_shortcode}")
            if (emoji_shortcode in self.currentPolls[evt.room_id].emoji_strings):
                self.log.debug(f"accepting emoji {evt.content.relates_to.key}")
                self.currentPolls[evt.room_id].vote(self.currentPolls[evt.room_id].emoji_strings.index(
                    emoji_shortcode), evt.sender, evt.event_id)  # Add vote/sender to poll
            else:
                self.log.debug(f"{emoji_shortcode} not in {self.currentPolls[evt.room_id].emoji_strings}")


    @event.on(EventType.ROOM_REDACTION)
    async def get_redact_vote(self, evt: RedactionEvent) -> None:
        self.log.info("Redaction event data: %s", evt)
        self.currentPolls[evt.room_id].redact_vote(evt.sender)


