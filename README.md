# nzbget-stream

Stream video-files while you are downloading them with nzbget.

## Requirements

You will need:

* [nzbget](https://github.com/nzbget/nzbget) >= 19.0-testing-r1956
* [python](https://www.python.org/downloads/)

## Detailed explanation

This script is called when a file from a nzb is finished. The script will then scan the nzb-folder for .rar-Files, look for video files in them and then try to extract the biggest one from the first archive. After that, it will start the video-file with the standard player.

When the next part has finished downloading, it will extract the video-file again and append the difference (the new bytes) to the stream.

**Warning:** This was only tested with VLC! Other players might choke on incomplete video-files.

## Usage:

**You'll need to activate the options `DirectRename` and `ReorderFiles` (tip: use the searchbox on the settings page)**

Afterwards, just put the script into your nzbget-scripts folder and activate it in the settings.