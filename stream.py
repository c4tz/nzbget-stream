##############################################################################
### NZBGET QUEUE SCRIPT 												   ###

### QUEUE EVENTS: FILE_DOWNLOADED

# Stream video while downloading.
#
# This script partially extracts video from .rar files
# so that you can view them while downloading.
#
# NOTE: This script requires Python to be installed on your system.

### NZBGET QUEUE SCRIPT 												   ###
##############################################################################

import sys, os, subprocess, shlex

FIRST_FILE = True
DL_PATH = os.environ['NZBNA_DIRECTORY']
STREAM_DIR = os.path.join(DL_PATH, 'stream')
STREAM_FILE = os.path.join(STREAM_DIR, 'stream');

# https://en.wikipedia.org/wiki/Video_file_format
VIDEO_EXTENSIONS = ["*.webm", "*.mkv", "*.flv", "*.vob", "*.ogv", "*.ogg",
					"*.drc", "*.mng", "*.avi", "*.mov", "*.qt", "*.wmv",
					"*.yuv", "*.rm", "*.rmvb", "*.asf", "*.mp4", "*.m4p",
					"*.m4v", "*.mpg", "*.mp2", "*.mpeg", "*.mpe", "*.mpv",
					"*.m2v", "*.svi", "*.3pg", "*.3g2", "*.mxf", "*.roq", "*.nsv"]

# unrar() function from "FakeDetector" extension script
def getUnrarExecutable():
	exe_name = 'unrar.exe' if os.name == 'nt' else 'unrar'
	UnrarCmd = os.environ['NZBOP_UNRARCMD']
	if os.path.isfile(UnrarCmd) and UnrarCmd.lower().endswith(exe_name):
		return UnrarCmd
	args = shlex.split(UnrarCmd)
	for arg in args:
		if arg.lower().endswith(exe_name):
			return arg
	return exe_name

def unrarFile(rarFile, fileName, destinationDir):
	try:
		command = [getUnrarExecutable(), "x", "-o+", "-kb"]
		if 'NZBPR__UNPACK_PASSWORD' in os.environ:
			command += ['-p'+os.environ['NZBPR__UNPACK_PASSWORD']]
		else:
			#to avoid hanging on password request
			command += ['-p-']
		command += [rarFile, fileName, destinationDir]
		#discard output
		with open(os.devnull, "w") as f:
			subprocess.check_call(command, stdout=f, stderr=f)
	except Exception as e:
		#exit code 3 means "corrupt file" which will always fire here
		if not e.returncode == 3:
			print('[ERROR] unrar %s: %s' % (rarFile, e))

def findVideoFile(rarFile):
	try:
		command = [getUnrarExecutable(), "vt"]
		if 'NZBPR__UNPACK_PASSWORD' in os.environ:
			command += ['-p'+str(os.environ['NZBPR__UNPACK_PASSWORD'])]
		else:
			command += ['-p-']
		command += [rarFile]
		command += VIDEO_EXTENSIONS
		out = subprocess.check_output(command)
		lines = out.splitlines()
		files = {}
		currentName = ''
		for line in lines:
			#if pyhon 3, decode bytes to string
			if sys.version_info >= (3, 0):
				line = line.decode('utf-8')
			arr = line.strip().split(': ')
			if arr[0] == 'Name':
				currentName = arr[1]
			if arr[0] == 'Size':
				files[currentName] = int(arr[1])
		# assuming biggest video file is the one we want
		files = sorted(files, key=files.get, reverse=True)
		if files:
			return files[0]
		else: 
			print('[ERROR] No video file found in rar-archive!')
	except Exception as e:
		print('[ERROR] find %s: %s' % (rarFile, e))

def findMainArchive(dir):
	files = os.listdir(dir)
	for file in files:
		# All files of a multipart-rar have to have the same filename,
		# so the first .rar is most likely the one we want.
		if '.rar' in file:
			if not dir in file:
				file = os.path.join(dir,file)
			return file

def appendFile(source, destination):
	with open(source, "rb") as s, open(destination, "a+b") as d:
		s.seek(os.path.getsize(destination))
		chunk_length = 4096
		while True:
			chunk = s.read(chunk_length)
			d.write(chunk)
			if len(chunk) < chunk_length:
				break

def openMediaFile(filePath):
	if sys.platform.startswith('darwin'):
		subprocess.call(('open', filePath))
	elif os.name == 'nt':
		os.startfile(filePath)
	elif os.name == 'posix':
		subprocess.call(('xdg-open', filePath))

def main():
	global FIRST_FILE
	global STREAM_FILE

	rarFile = findMainArchive(DL_PATH)
	if rarFile:
		videoFile = findVideoFile(rarFile)
		if videoFile:
			videoPath = os.path.join(STREAM_DIR, videoFile)
			STREAM_FILE += os.path.splitext(videoPath)[1]
			FIRST_FILE = not os.path.exists(STREAM_FILE)

			if not os.path.exists(STREAM_DIR):
				os.makedirs(STREAM_DIR)

			unrarFile(rarFile, videoFile, STREAM_DIR)

			if FIRST_FILE:
				os.rename(videoPath, STREAM_FILE)
				openMediaFile(STREAM_FILE)
			else:
				appendFile(videoPath, STREAM_FILE)
				os.remove(videoPath)

main()