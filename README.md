These commands can only be used in the #mods channel.

+announce {role you want to ping} message
=========================================

The most basic command the reason that the bot was created initially. The bot will make the announcement for you and ping any role that you want which helps keep you anonymous or just ping the group of people easily. Keep in mind that there MUST be a SPACE after the role name. A return will cause an error. Thanks Disco.

Roles that can be pinged using announceBot

android - Android Alpha

bug - Bug Hunter

canary - Canary

ios - iOS TestFlight

linux - Linux

mac - Mac

windows - Windows

+update {channel ID} {message ID} new message
=============================================

The bot can edit any of it's previous messages with this command. By nature of how the API works, you need to tell it what channel to look in, and what message to change via IDs. So the command is +update channelID messageID new message. Here are list of the IDs for the announcement channels, for reference.

Global Announcements: 197038477953597440

Bug Hunter: 421790860057903104

Android:  411645018105970699

Desktop: 411645098946985984

iOS: 411645199866003471


+evilping
==========

Standard ping command

+multiping -r {<name of any of the roles to ping}" -a "{announcement}"
======================================================================

Can only be used with the desktop roles: Linux, Mac, Canary and Windows. Will only post to #desktop-announcements. Allows for pinging any number of desktop roles and make the same announcement. Due to a bug within disco.py, you cannot use single or double quotes when using this command. Sorry.

The bot will automatically post in the correct channel based on the role you want to ping.

+Lockdown
=========

The lockdown command can be used by any mod+ in any channel. It is ONLY to be used during an emergency. It will lock any combination of reporting channels + approval queue, or all of them. This is the command for it:
+lockdown -c "channel_names_as_defined_below" -r "reason_that_this_command_is_being_used"

Note that you cannot use ' or " in the quoted sections due to how disco.py works.

The short name for all of the channels are:

bug

ios

android

desktop

linux

in addition, instead of each channel you can say all instead. For example: +lockdown -c "all" -r "Trello is down" and that will lock all of the above channels.

The "reason" category will be the EXACT message that appears in all of the channels that are locked down

+Unlock
=======

The "undo" command for Lockdown. Same idea just use it backwards.

+slowmode
============

In case there is a lot of people sending messages after an update has released or there is ongoing outages.
You can set slowmode between 1-120 seconds.
Command usage:
`+slowmode CHNANEL_ID_OR_MENTION AMOUNT_OF_SECONDS`

An example on how you disable slowmode:

`+slowmode #android-client-chat 0`


+Verification
=============

In the event of a raid ONLY, any mod+ can use +verification LEVEL_NAME CHANGE_REASON.

Note that the level names are:

None

Low

Medium

High

Extreme

The CHANGE_REASON is optional for speed.

+ping
=====

Unlike a standard ping command, this one makes any role in the server mentionable if you're an employee. It's useful for when you want to make an announcement without using the announce feature the bot has. You can use this same command to make a role unmentionable as well. As a QOL improvement to this feature, when the bot detects that a role has been pinged it'll automatically set it to be unmentionable automatically.

+addtag {tag_key} {tag_content}
=======

The tag_key is the name of the tag as you'll be calling it later. Make it something easy to remember like "hypesquad" or "common_questions" or anything you want. Just one single word. The tag_content is the text that you want displayed to other users. For example:

+addtag Dabbit He is the best :dabHeart:

Would add the tag "Dabbit" to the .txt. When you use the follow up command +tag {tag_key}, in this case +tag Dabbit, the bot will respond with the text: "He is the best :dabHeart:".

The bot will take links and markdown just fine. It does NOT take new lines as returns. You have to keep everything on a single line and use \n instead of a return when adding the tag_content.

+taglist
=======

Shows the tag_key for all available tags.

+removetag {Tag_Key}
==========

Iterates through the tags.txt file to find the specified key:value pair and remove it.


+addfaq -f "{phrase_to_respond_to}" -c "{content}"
=======

The bot has an auto response feature for commonly asked questions which are referred to as "FAQs". It reads each message and looks for the specific phrase added in the faqs.txt file and then responds with the corresponding value. For example, if someone shows up and says "How do I report a bug in this server?" the bot will respond with a preset message for the phrase `how do i report a bug`. This command will add another phrase to the faqs.txt file. Example usage:

+faqadd -f "how do i report a bug" -c "Just read the write up in #report-a-bug for information on how to report a bug!"

Note that due to a bug in the disco.py library you CANNOT use single or double quotes at any point in this or it will fail. Use `\n` for a new line. It will only respond to people lower on the role heirarchy than Bug Hunter.

+faq {phrase_to_respond_to}
==========================

This command is mainly to check the formatting of an already existing FAQ by manually triggering the response. Example usage:

+faq how do i report a bug

+faqlist
========

Generates a list of all FAQs phrases currently in the faqs.txt file. Does not show the content of the FAQs. This currently does not support pagination and when the message it returns gets over 2000 character limit it'll just fail.

+removefaq {phrase_to_respond_to}
=================================

As a management feature you can dynamically remove an FAQ from the list. This permanently deletes it with no recovery. Example usage:

+removefaq how do i report a bug

+editfaq -f "{phrase_to_respond_do}" -c "{new_content}"
===================

A quality of life feature, allows you to rewrite the content of an FAQ without first removing it. You cannot edit the `phrase_to_respond_to`. Example usage:

+editfaq -f "how do i respond to a bug" -c "Just checkout out #report-a-bug!"
