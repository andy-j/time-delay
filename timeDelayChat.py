#######################################################################
#                                                                     #
#  Mission Communicator                                               #
#                                                                     #
#  2013: Andy Mikula (http://www.andymikula.ca)                       #
#                                                                     #
#                                                                     #
#  Based on sample code from                                          #
#  http://twistedmatrix.com/documents/12.2.0/core/howto/servers.html  #
#                                                                     #
#                                                                     #
#  When run, it will start up a server on port PORT_NUMBER. Clients   #
#  connect and speak to each other based on a 'mission' number.       #
#                                                                     #
#  Type '/admin pleaseandthankyou' to gain access to the '/setdelay', #
#  '/broadcast', and '/warn' commands. Type '/mission 3' to join      #
#  mission 3 after you have logged in. Missions can be integers from  #
#  1 - MISSION_MAX, inclusive.                                        #
#                                                                     #
#######################################################################

import datetime
import urllib2
import smtplib

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

delay = 0.0
MISSION_MAX = 10
PORT_NUMBER = 4000


def is_float(st):
    try:
        float(st)
        return True
    except ValueError:
        return False


def is_int(st):
    try:
        int(st)
        return True
    except ValueError:
        return False


class State:
    GETNAME, GETMISSION, CHAT = range(3)


class Chat(LineReceiver):

    commands = {"/broadcast", "/mission", "/quit", "/setdelay", "/listen",
        "/who", "/admin", "/warn"}
    adminpassword = "pleaseandthankyou"

    def __init__(self, users):

        self.users = users
        self.admin = False    # is the user an admin?
        self.listen = False   # is the user listening in on all communications?
        self.name = ""
        self.mission = None
        self.state = State.GETNAME

    def connectionMade(self):
        self.sendLine("+=============================================================================+")
        self.sendLine("|                                                                             |")
        self.sendLine("|                                                                             |")
        self.sendLine("|                             MARS MISSION COMMUNICATOR                       |")
        self.sendLine("|                                                                             |")
        self.sendLine("|                                                                             |")
        self.sendLine("+=============================================================================+")
        self.sendLine("")
        self.sendLine("PLEASE ENTER YOUR CALLSIGN: ")

    def connectionLost(self, reason):
        self.sendToRoom("%s IS NO LONGER PART OF MISSION %s." % (str.upper(self.name), self.mission, ))
        if self.users.has_key(self.name):
            del self.users[self.name]

    def handle_COMMAND(self, command, args):
        if command == "/quit":
            self.transport.loseConnection()
        elif command == "/admin":
            self.handle_SETADMIN(args)
        elif command == "/mission":
            if is_float(args):
                self.handle_GETMISSION(args)
            else:
                self.sendLine("MISSION MUST BE A NUMBER.")
        elif command == "/broadcast":
            if self.admin:
                self.handle_BROADCAST(args)
            else:
                self.sendLine("ACCESS DENIED")
        elif command == "/setdelay":
            if self.admin:
                self.handle_SETDELAY(args)
            else:
                self.sendLine("ACCESS DENIED")
        elif command == "/warn":
            for mission, protocol in self.users.iteritems():
                if protocol.name == args:
                    protocol.sendLine("PLEASE STOP ABUSING THE SYSTEM. THIS IS A WARNING.")
        elif command == "/listen":
            if self.admin:
                if self.listen:
                    self.listen = False
                    self.sendLine("No longer listening.")
                else:
                    self.listen = True
                    self.sendLine("Listening.")
            else:
                self.sendLine("ACCESS DENIED")
        elif command == "/who":
            try:
                if self.admin:
                    self.sendLine("MISSION PARTICIPANTS:")
                    for mission, protocol in self.users.iteritems():
                        self.sendLine("\x1b[3" + protocol.mission + ";1mMISSION " + protocol.mission + ": " + protocol.name + "\x1b[0m")
                else:
                    self.sendLine("MISSION PARTICIPANTS:")
                    for mission, protocol in self.users.iteritems():
                        if protocol.mission == self.mission:
                            self.sendLine(protocol.name)
            except TypeError:
                self.sendLine("WHO ERROR")
        else:
            return

    def lineReceived(self, line):
        try:
            command = line.split()[0]
            args = ' '.join(line.split()[1:])

            self.sendLine('\33[A\33[2K\33[A')    # move up 1 line and clear it, then move up again
            if self.state == State.GETNAME:
                self.handle_GETNAME(line)
            elif self.state == State.GETMISSION:
                self.handle_GETMISSION(line)
            elif command in self.commands:
                self.handle_COMMAND(command, args)
            else:
                self.handle_CHAT(line)
        except IndexError:
            return

    def handle_KEEPALIVE(self, ping):
        return

    def handle_SETADMIN(self, password):
        if password == self.adminpassword:
            self.admin = True
            self.sendLine("Administrator access granted.")
        else:
            self.sendLine("ACCESS DENIED")

    def handle_BROADCAST(self, message):
        message = "\x1b[31;1m%s: %s\x1b[0m" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message)
        for mission, protocol in self.users.iteritems():
            protocol.sendLine(message)

    def handle_SETDELAY(self, delayIn):
        if is_float(delayIn):
            global delay
            delay = float(delayIn)
            self.sendLine("Delay set to " + delayIn + ".")
        else:
            self.sendLine("Delay must be a number. Try again.")

    def handle_GETNAME(self, name):
        if len(name) > 10:
            self.sendLine("CALLSIGN TOO LONG. CHOOSE ANOTHER:")
            return
        elif name in self.users:
            self.sendLine("CALLSIGN IN USE. CHOOSE ANOTHER:")
            return
        self.name = name
        self.users[name] = self

        self.sendLine("PLEASE ENTER YOUR MISSION NUMBER:")
        self.state = State.GETMISSION

    def handle_GETMISSION(self, mission):
        if is_int(mission) and int(mission) > 0 and int(mission) < MISSION_MAX:
            self.sendLine("WELCOME TO MISSION %s, %s." % (mission, str.upper(self.name)))
            self.mission = mission
            print str.upper(self.name) + " JOINED MISSION " + str.upper(self.mission)
            if not self.admin:
                self.sendToRoom("%s: %s JOINED MISSION %s." % ((datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str.upper(self.name), str.upper(self.mission), )))
            self.state = State.CHAT
        else:
            self.sendLine("MISSION MUST BE A WHOLE NUMBER GREATER THAN 0 AND LESS THAN 8. TRY AGAIN:")

    def handle_CHAT(self, message):
        message = "%s: <%s> %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str.upper(self.name), message)
        self.sendToRoom(message)

    def sendToRoom(self, message):
        for mission, protocol in self.users.iteritems():
            if protocol.listen:
                protocol.sendLine("\x1b[3" + self.mission + ";1mMISSION " + self.mission + ": " + message + "\x1b[0m")
            elif protocol.mission == self.mission:
                if protocol.name == self.name:
                    protocol.sendLine(message)
                else:
                    reactor.callLater(delay, protocol.sendLine, message)


class ChatFactory(Factory):

    def __init__(self):
        self.users = {}

    def buildProtocol(self, addr):
        return Chat(self.users)

myIp = urllib2.urlopen('http://ip.42.pl/raw').read()

reactor.listenTCP(PORT_NUMBER, ChatFactory())

print "MISSION COMMUNICATOR RUNNING ON " + myIp

smtp = smtplib.SMTP('SMTP SERVER', 587)

fromaddr = 'FROM ADDRESS'
toaddrs = {'TO ADDRESS'}
subj = 'Space Communicator running on ' + myIp + ', port 4000!'
msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n"
       % (fromaddr, ", ".join(toaddrs), subj))

try:
    smtp.ehlo()
    if smtp.has_extn('STARTTLS'):
        smtp.starttls()
        smtp.ehlo()
        smtp.login('SMTP LOGIN', 'SMTP PASSWORD')
        smtp.sendmail(fromaddr, toaddrs, msg)
finally:
    smtp.quit()

reactor.run()
