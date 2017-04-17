#!/usr/bin/python

##############################################################################
### NZBGET SCAN/QUEUE/POST-PROCESSING SCRIPT                                ###
### QUEUE EVENTS: FILE_DOWNLOADED                                           ###

# Stream video while downloading.
#
# This script partially extracts video from 
# .rar files after sorting the nzb so that 
# you can stream it while downloading.
#
# NOTE: This script requires Python and lxml
# to be installed on your system.

### NZBGET SCAN/QUEUE/POST-PROCESSING SCRIPT                                ###
##############################################################################

import base64, copy, os, re, shlex, shutil, subprocess, sys, tempfile, time
from lxml import etree as ET
try:
    from xmlrpclib import ServerProxy # python 2
except ImportError:
    from xmlrpc.client import ServerProxy # python 3

class Strip:
    def __init__(self):
        self.namespaces = {'nzb': 'http://www.newzbin.com/DTD/2003/nzb'}

    def writeFile(self, path, data):
        with open(path, 'w') as f:
                f.write(data)

    def sort(self, nzbTree):
        files = nzbTree.xpath('nzb:file', namespaces=self.namespaces)
        files = sorted(files, key=lambda file: file.get('subject'))

        parFiles, rarFiles = [], []
        for file in files:
            if '.rar' in file.get('subject'):
                rarFiles.append(file)
            elif '.par2' in file.get('subject'):
                parFiles.append(file)
        files = list(set(files) - set(rarFiles))
        files = list(set(files) - set(parFiles))
        firstPar = [parFiles.pop(0)] if len(parFiles) > 0 else []
        files = firstPar + rarFiles + files + parFiles

        for file in files:
            nzbTree.getroot().remove(file)
            nzbTree.getroot().append(file)
        
        return nzbTree

    def scan(self):
        nzbFile = os.environ['NZBNP_FILENAME']
        if '[SORTED].nzb' in nzbFile:
            quit()

        nzb = ET.parse(nzbFile)

        rarFiles = nzb.xpath('nzb:file[contains(@subject, ".rar")]', namespaces=self.namespaces)
        if len(rarFiles) == 0: # obfuscated NZB
            tmpNZB = copy.deepcopy(nzb)
            segments = tmpNZB.xpath('nzb:file/nzb:segments/nzb:segment[@number!="1"]', namespaces=self.namespaces)
            [element.getparent().remove(element) for element in segments]
            
            tmpFile = tempfile.mkstemp()[1]
            self.writeFile(tmpFile, ET.tostring(nzb, encoding=nzb.docinfo.encoding).decode(nzb.docinfo.encoding))

            # set params for PostProcessor
            print('[NZB] NZBPR_*Unpack:=no')
            print('[NZB] NZBPR_*naming=nzb')
            print('[NZB] NZBPR_nzbtmp='+tmpFile)

            self.writeFile(nzbFile, ET.tostring(tmpNZB, encoding=tmpNZB.docinfo.encoding).decode(tmpNZB.docinfo.encoding))
        else:
            nzb = self.sort(nzb)
            self.writeFile(nzbFile, ET.tostring(nzb, encoding=nzb.docinfo.encoding).decode(nzb.docinfo.encoding))

    def process(self):
        if not 'NZBPR_nzbtmp' in os.environ:
            sys.exit(95) # Post-process skipped

        host = 'localhost' #script will be called from nzbget => same host
        port = os.environ['NZBOP_CONTROLPORT']
        if ('NZBOP_CONTROLUSERNAME' and 'NZBOP_CONTROLPASSWORD') in os.environ:
            username = os.environ['NZBOP_CONTROLUSERNAME'];
            password = os.environ['NZBOP_CONTROLPASSWORD'];
            rpcUrl = 'http://%s:%s@%s:%s/xmlrpc' % (username, password, host, port);
        else:
            rpcUrl = 'http://%s:%s/xmlrpc' % (host, port)        
        server = ServerProxy(rpcUrl)

        nzbName = os.environ['NZBPP_NZBNAME'] + ' [SORTED].nzb'
        nzbID = int(os.environ['NZBPP_NZBID'])
        nzb = ET.parse(os.environ['NZBPR_nzbtmp'])

        log = server.loadlog(nzbID, 0, 999999)
        for entry in log:
            match = re.match(r'Renaming (.*) to (.*)', entry['Text'])
            if match:
                file = nzb.xpath('nzb:file[contains(@subject, "' + match.group(1) + '")]', namespaces=self.namespaces)[0]
                file.set("subject", file.get('subject').replace(match.group(1), match.group(2)))
        nzb = self.sort(nzb)
        
        ppParams = [('*naming', 'nzb')]
        if 'NZBPR__UNPACK_PASSWORD' in os.environ:
                ppParams += [os.environ['NZBPR__UNPACK_PASSWORD']]

        # cleanup
        shutil.rmtree(os.environ['NZBPP_DIRECTORY'])
        os.remove(os.environ['NZBPR_nzbtmp'])
        server.editqueue('HistoryDelete', '', [nzbID])

        server.append(nzbName,
            base64.b64encode(ET.tostring(nzb, encoding=nzb.docinfo.encoding)).decode('utf-8'),
            '', 0, True, False, '', 0, 'SCORE', ppParams)

        sys.exit(93) # Post-process successful

class Stream:

    def __init__(self):
        self.firstFile = True
        self.dlPath = os.environ['NZBNA_DIRECTORY']
        self.streamDir = os.path.join(self.dlPath, 'stream')
        self.streamFile = os.path.join(self.streamDir, 'stream');

        # https://en.wikipedia.org/wiki/Video_file_format
        self.videoExtensions = ["*.webm", "*.mkv", "*.flv", "*.vob", "*.ogv", "*.ogg",
                            "*.drc", "*.mng", "*.avi", "*.mov", "*.qt", "*.wmv",
                            "*.yuv", "*.rm", "*.rmvb", "*.asf", "*.mp4", "*.m4p",
                            "*.m4v", "*.mpg", "*.mp2", "*.mpeg", "*.mpe", "*.mpv",
                            "*.m2v", "*.svi", "*.3pg", "*.3g2", "*.mxf", "*.roq", "*.nsv"]

    # unrar() function from "FakeDetector" extension script
    def getUnrarExecutable(self):
        exe_name = 'unrar.exe' if os.name == 'nt' else 'unrar'
        UnrarCmd = os.environ['NZBOP_UNRARCMD']
        if os.path.isfile(UnrarCmd) and UnrarCmd.lower().endswith(exe_name):
            return UnrarCmd
        args = shlex.split(UnrarCmd)
        for arg in args:
            if arg.lower().endswith(exe_name):
                return arg
        return exe_name

    def unrarFile(self, rarFile, fileName, destinationDir):
        try:
            command = [self.getUnrarExecutable(), "e", "-o+", "-kb"]
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

    def findVideoFile(self, rarFile):
        try:
            command = [self.getUnrarExecutable(), "vt"]
            if 'NZBPR__UNPACK_PASSWORD' in os.environ:
                command += ['-p'+str(os.environ['NZBPR__UNPACK_PASSWORD'])]
            else:
                command += ['-p-']
            command += [rarFile]
            command += self.videoExtensions
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

    def findMainArchive(self, dir):
        files = os.listdir(dir)
        files = sorted(files)
        for file in files:
            # All files of a multipart-rar have to have the same filename,
            # so the first .rar is most likely the one we want.
            if '.rar' in file:
                if not dir in file:
                    file = os.path.join(dir,file)
                return file

    def appendFile(self, source, destination):
        with open(source, "rb") as s, open(destination, "a+b") as d:
            s.seek(os.path.getsize(destination))
            chunk_length = 4096
            while True:
                chunk = s.read(chunk_length)
                d.write(chunk)
                if len(chunk) < chunk_length:
                    break

    def openMediaFile(self, filePath):
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filePath))
        elif os.name == 'nt':
            os.startfile(filePath)
        elif os.name == 'posix':
            subprocess.call(('xdg-open', filePath))

    def show(self):
        rarFile = self.findMainArchive(self.dlPath)
        if rarFile:
            inRarPath = self.findVideoFile(rarFile)
            dummy, videoFile = os.path.split(inRarPath)
            if videoFile:
                videoPath = os.path.join(self.streamDir, videoFile)
                self.streamFile += os.path.splitext(videoPath)[1]
                self.firstFile = not os.path.exists(self.streamFile)

                if not os.path.exists(self.streamDir):
                    os.makedirs(self.streamDir)

                self.unrarFile(rarFile, inRarPath, self.streamDir)

                if self.firstFile:
                    os.rename(videoPath, self.streamFile)
                    self.openMediaFile(self.streamFile)
                else:
                    self.appendFile(videoPath, self.streamFile)
                    os.remove(videoPath)


def main():
    if 'NZBNP_FILENAME' in os.environ: # scan-script
        strip = Strip()
        strip.scan()
    if 'NZBNA_EVENT' in os.environ: # queue-script
        stream = Stream()
        stream.show()
    if 'NZBPP_DIRECTORY' in os.environ: # pp-script
        strip = Strip()
        strip.process()
    
main()