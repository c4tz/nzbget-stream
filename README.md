# nzbget-stream

Stream video-files while you are downloading them with nzbget.

## Detailed explanation

This script is called when a file from a nzb is finished. The script will then scan the nzb-folder for .rar-Files, look for video files in them and then try to extract the biggest one from the first archive. After that, it will start the video-file with the standard player.

When the next file has finished downloading, it will extract the video-file again and append the difference (the new bytes) to the stream. 

**Warning:** This was only tested with VLC! Other players might choke on incomplete video-files.

Also, the nzb should be sorted so that the first archive will be the first file downloaded. Else you have to wait before the stream begins! But I might aswell write another script to do that in the future ;)

## Usage:

Just put the script into your nzbget-scripts folder and activate it in the settings.