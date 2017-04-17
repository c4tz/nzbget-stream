# nzbget-stream

Stream video-files while you are downloading them with nzbget.

## Detailed explanation

This script will sort the files inside your NZB when you add it to the queue, and then (while downloading) scan the destination folder for .rar-Files, look for video files in them and then try to extract the biggest one from the first archive. After that, it will open the video-file with the standard player.

When the next part has finished downloading, it will extract the video-file again and append the difference (the new bytes) to the stream. 

**Warning:** This was only tested with VLC! Other players might choke on incomplete video-files.

## Usage:

Just put the script into your nzbget-scripts folder and activate it in the settings.