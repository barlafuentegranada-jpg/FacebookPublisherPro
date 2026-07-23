Social Publisher Pro

Telegram Bot API Setup

1. Open Telegram and start a chat with `@BotFather`.
2. Use `/newbot` to create a bot and copy the token BotFather gives you.
3. Add the bot to the channel, group, or supergroup you want to publish to.
4. For channels, make the bot an administrator and grant permission to post messages.
5. In Social Publisher Pro, open Accounts, choose Telegram, and add the bot with a display name and token.
6. The app validates the token with Telegram `getMe` and stores only an encrypted local secret reference in the database.
7. Open Telegram, add a target by `@channel_username`, `@group_username`, or numeric chat id.
8. Use Discover Recent Chats only for chats that have interacted with the bot; the Bot API cannot list every channel or group automatically.
9. Use the Telegram page to send a test message before publishing real posts.

Telegram V1 supports text, links, one image with caption, or one video with caption. Stories, polls, user-account publishing, and album publishing are not enabled in this sprint.
