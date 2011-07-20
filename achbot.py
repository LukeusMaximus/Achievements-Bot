import socket
import threading
import sys
import re

def sendIRCLine(string):
    print("Sending \"" + string + "\"")
    irc.send(bytes(string, "ascii") + b"\r\n" )

class ircOutputBuffer:
    def __init__(self):
        self.waiting = False
        self.queue = []
    def startPopTimer(self):
        self.timer = threading.Timer(1, self.pop)
        self.timer.start()
    def push(self, string):
        if self.waiting:
            self.queue.append(string)
        else:
            self.waiting = True
            sendIRCLine(string)
            self.startPopTimer()
    def pop(self):
        if len(self.queue) == 0:
            self.waiting = False
        else:
            sendIRCLine(self.queue[0])
            self.queue = self.queue[1:]
            self.startPopTimer()

class identification:
    def __init__(self, out):
        self.identifiedNicks = []
        self.ircOutput = out
    def identifyNick(self, nick):
        self.ircOutput.push("WHOIS " + nick)
    def confirmIdentifyNick(self, nick):
        self.identifiedNicks.append(nick)
    def isIdentified(self, nick):
        if nick in self.identifiedNicks:
            return True
        else:
            return False
        
class regexes:
    def __init__(self):
        self.regexList = []
    def loadRegexes(self, fileName):
        self.regexList = []
        f = open(fileName, 'r')
        line = f.readline()
        while line != '':
            regex = re.compile(line.strip())
            regexList.append(regex)
    def matchToRegexes(self, string):
        matchedIDs = []
        for i in range(len(self.regexList)):
            match = self.regexList[i].match()
            if match != None:
                matchedIDs.append(i)
        return matchedIDs



def processPRIVMSG(whoFrom, remSect, message):
    sectStr = ' '.join(remSect)
    print("Message from " + whoFrom + ": " + sectStr + ' ' + message)

    if message.startswith("AchBot "):
        message = message[7:]
        if whoFrom == "Lukeus_Maximus":
            if message.startswith("identify"):
                ident.identifyNick("Lukeus_Maximus")
            if ident.isIdentified("Lukeus_Maximus") == True:
                if message.startswith("confirm identity"):
                    outBuf.push("PRIVMSG #maximustestchannel :Identity Confirmed")
                if message.startswith("send "):
                    outBuf.push(message[5:])
    return True

def processUserMessage(whoFrom, msgType, remSect, message):
    sectStr = ' '.join(remSect)
    if msgType == "PRIVMSG":
        return processPRIVMSG(whoFrom, remSect, message)
    elif msgType == "NOTICE":
        print("Notice from " + whoFrom + ": " + sectStr + '  ' + message)
    elif msgType == "MODE":
        print("Mode from " + whoFrom + ": " + sectStr + ' ' + message)
    elif msgType == "JOIN":
        print("Join from " + whoFrom + ": " + sectStr + ' ' + message)
    else:
        print("Unrecognised Message type " + msgType)

    return True

def processServerMessage(msgType, remSect, message):
    sectStr = " ".join(remSect)
    print("[Server Message]: " + msgType + ' ' + sectStr + ' ' + message)
    
    if msgType == "307" and len(remSect) == 2 and remSect[0] == "AchBot":
        ident.confirmIdentifyNick(remSect[1])
    
    return True

# Returning the function with "True" will let the bot wait for the next IRC message
# Returning "False" will stop the bot entirely
def doActions(data):
    # sanitise the data to something we can work with more easily
    if len(data) == 0:
        return True
    data = str(data, "UTF-8")
    
    # split by colon
    splitCol = data.split(":")
    splitCol = splitCol[1:]
    if len(splitCol) != 2:
        return True
        
    # split first section by spaces
    sections = splitCol[0].strip().split(" ")
    message = splitCol[1]
    if len(sections) < 2:
        return True
    
    # process first two values (who the message is from and the message type)
    cutoff = sections[0].find("!")
    if cutoff != -1:
        sections[0] = sections[0][0:cutoff]
    whoFrom = sections[0]
    msgType = sections[1]
    if len(sections) >= 3:
        remSect = sections[2:]
    else:
        remSect = []
 
    if sections[0].find(".") != -1:
        #It"s the server talking
        return processServerMessage(msgType, remSect, message);
    else:
        #It"s a user talking
        return processUserMessage(whoFrom, msgType, remSect, message);
        
# Main program begins here
if len(sys.argv) == 2:
    chanName = "#" + sys.argv[1]
else:
    chanName = "#maximustestchannel"

network = "irc.synirc.net"
port = 6667
irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
irc.connect((network, port))

# Out buffer exists to prevent IRC flooding and potentially
# missing messages sent to the server
outBuf = ircOutputBuffer()
outBuf.push("NICK AchBot")
outBuf.push("USER AchBot AchBot AchBot :Achievements Bot")
outBuf.push("JOIN " + chanName)
outBuf.push("PRIVMSG " + chanName + " :Hello.")
outBuf.push("PRIVMSG nickserv :identify i84Vt7yiICq33iRy")

# In buffer exists to prevent lines that are cut off at the
# end of the socket read from being partially discarded
inBuf = b""

ident = identification(outBuf)

keepGoing = True
while keepGoing:
    data = irc.recv (4096)
    inBuf = inBuf + data
    dataLines = inBuf.split(b"\r\n")
    if dataLines[len(dataLines) - 1].find(b"PING") != -1:
        dataLines.append(b"")
    inBuf = dataLines[len(dataLines) - 1]
    for i in range(len(dataLines) - 1): 
        if dataLines[i].find(b"PING") != -1:
            irc.send(b"PONG " + dataLines[i].split()[1] + b"\r\n")
        else:
            carryOn = doActions(dataLines[i])
            if carryOn == False:
                keepGoing = False

