These commands can only be used in the #mods channel.

+announce {role you want to ping} message
=========================================

The most basic command the reason that the bot was created initially. The bot will make the announcement for you and ping any role that you want which helps keep you anonymous or just ping the group of people easily. Keep in mind that there MUST be a SPACE after the role name. A return will cause an error. Thanks Disco.

+update {channel ID} {message ID} new message
=============================================

The bot can edit any of it's previous messages with this command. By nature of how the API works, you need to tell it what channel to look in, and what message to change via IDs. So the command is +update <channel ID> <message ID> new message. Here are list of the IDs for the announcement channels, for reference.

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

Roles that can be pinged using announceBot

android - Android Alpha

bug - Bug Hunter

canary - Canary

ios - iOS TestFlight

linux - Linux

mac - Mac

windows - Windows

The bot will automatically post in the correct channel based on the role you want to ping.

+tag TOPIC_NAME
===============

The topics I currently have are:

suggestions

raids

abuse

install

bug

badge

hypesquad

support

lazy

hunter

Example: +tag badge

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
