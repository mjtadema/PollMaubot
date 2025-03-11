# Poll Maubot
A plugin for [maubot](https://github.com/maubot/maubot) that creates a poll in a riot room and allows users to vote.
Customized to ease bridging between different messaging services (i.e. between signal/whatsapp).


## Usage
'!poll new  "Question" "Choice1" "Choice2" "Choice3"' - Creates a new poll with given (at least 1) choices

The user can now also create polls with line-breaks:
```
!poll new What is my question?
Choice1
Choice2
Choice3
```

'!poll results' - Displays the results from the poll

'!poll close' - Ends the poll and prints results

Users vote by adding the matching emoji to the poll (i.e. if the first choice has a :thumbsup: then in order to pick that choice the user has to react with :thumbsup:)

## Version 3.0.2 (Latest release)
 - Results can now be requested before the poll is closed
 - Result message is simplified to help with bridging to other messaging services
 - Closing the poll also prints results
 - Bridging tested between signal and whatsapp

## Older Releases:

### Version 3.0
 - Made emoji options more accessible
 - Bot now reacts to itself with emoji options
 - The user can now define emoji options
 - User can define answers with line-breaks rather than quotes

### Version 2.0
 - Changed voting format to reactions (instead of '!poll vote')

#### Version 2.0.1
 - Allows every room to have unique poll


## Wish List
- Add user configuration to only allow certain users to create polls
- Add auto-timing ability
- Make emojis configurable
- Add placeholder emojis on each poll (to let users just click one)
