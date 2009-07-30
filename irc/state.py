#!/usr/bin/env python

import time
import p10.parser

# IRC masks are very similar to UNIX filename pattern matching, so we can cheat and use the same algorithm
import fnmatch

class state:
    """ Holds the state for the current connection """
    
    _config = None
    users = dict()
    channels = dict()
    _servers = dict()
    maxClientNumerics = dict()
    _glines = dict()
    
    def __init__(self, config):
        self.users = dict()
        self.channels = dict()
        self._config = config
        self._servers = dict()
        self._servers[self.getServerID()] = server(None, self.getServerID(), self.getServerName(), 262143, self.ts(), self.ts(), "P10", 0, [], "WISH on " + self.getServerName())
        self.maxClientNumerics = dict({self.getServerID(): 262143})
        self._glines = dict()
    
    def sendLine(self, client, command, args):
        """ Send a line """
        #
        # TODO: This needs to be completely rewritten to deal with the better connection design that will be introduced later
        #
        self._config.sendLine(client, command, args)
    
    def getServerID(self):
        return self._config.numericID
    
    def getServerName(self):
        return self._config.serverName
    
    def getAdminName(self):
        return self._config.adminNick
    
    def getContactEmail(self):
        return self._config.contactEmail
    
    def ts(self):
        """ Returns our current timestamp """
        return int(time.time())
    
    def userExists(self, numeric):
        """ Check if the user is known to us """
        return numeric in self.users
    
    def nick2numeric(self, nick):
        for user in self.users:
            if nick == self.users[user].nickname:
                return user
    
    def newUser(self, origin, numeric, nickname, username, hostname, modes, ip, hops, ts, fullname):
        """ Change state to include a new user """
        # TODO: Do we have a name clash?
        if self.serverExists(origin[0]):
            if origin[1] == None:
                if self.userExists(numeric):
                    raise StateError("Numeric collision - attempting to create second user with numeric we already know")
                else:
                    self.users[numeric] = user(numeric, nickname, username, hostname, modes, ip, hops, ts, fullname)
            else:
                raise p10.parser.ProtocolError("Only servers can create users")
        else:
            raise StateError("A non-existant server tried to create a user")
    
    def serverExists(self, numeric):
        return numeric in self._servers
    
    def newServer(self, origin, numeric, name, maxclient, boot_ts, link_ts, protocol, hops, flags, description):
        """ Add a new server """
        # TODO: More stringent checks - do we have a name clash?
        # We disregard most of the arguments, because, tbh, we don't care about them
        if self.serverExists(numeric):
            raise StateError("Attempted to add a duplicate server")
        elif origin[1] != None:
            raise p10.parser.ProtocolError("User attempted to add a server")
        else:
            uplink = origin[0]
            self._servers[numeric] = server(uplink, numeric, name, maxclient, boot_ts, link_ts, protocol, hops, flags, description)
            self.maxClientNumerics[numeric] = maxclient
            if self.serverExists(uplink):
                self._servers[uplink].addChild(numeric)
            else:
                raise StateError("Unknown server introduced a new server")
    
    def changeNick(self, origin, numeric, newnick, newts):
        """ Change the nickname of a user on the network """
        # TODO: More stringent checks on new nickname, i.e., is it valid/already in use?
        if self.userExists(numeric):
            self.users[numeric].nickname = newnick
            self.users[numeric].ts = newts
        else:
            raise StateError('Nick change attempted for unknown user')
    
    def authenticate(self, origin, numeric, acname):
        """ Authenticate a user """
        if origin[1] == None:
            if self.serverExists(origin[0]):
                if self.userExists(numeric):
                    self.users[numeric].auth(acname)
                else:
                    raise StateError("Authentication state change received for unknown user")
            else:
                raise StateError("Authentication from unknown server")
        else:
            raise p10.parser.ProtocolError("Only servers can change state")
    
    def getAccountName(self, numeric):
        """ Get the account name for a user. Blank if not authenticated. """
        return self.users[numeric].account
    
    def setAway(self, numeric, reason):
        if reason == "":
            raise StateError("Attempted to set an empty away reason")
        if self.userExists(numeric):
            self.users[numeric].away_reason = reason
        else:
            raise StateError("Attempted to mark a user as away who does not exist")
    
    def setBack(self, numeric):
        if self.userExists(numeric):
            self.users[numeric].away_reason = None
        else:
            raise StateError("Attempted to mark a user as not away who does not exist")
    
    def createChannel(self, origin, name, ts):
        """ Create a channel. Returns false if the new channel is invalid (i.e., is newer than one already known about) """
        # TODO: More stringent checks on whether or not this channel can be created (i.e., is badchan'd or juped)
        if self.userExists(origin):
            # Channel already exists
            if name in self.channels:
                # Our channel is older. Disregard.
                if self.channels[name].ts < ts:
                    return False
                # They're both the same, add new user as op
                elif self.channels[name].ts == ts:
                    self.channels[name].join(origin, ["o"])
                    self.users[origin].join(name)
                    return True
                # Their channel is older, overrides ours and merge users
                else:
                    # Get old users
                    oldusers = dict.keys(self.channels[name].users)
                    self.channels[name] = channel(name, ts)
                    for user in oldusers:
                        self.joinChannel(None, user, name, [])
                    return True
            else:
                self.channels[name] = channel(name, ts)
                self.channels[name].join(origin, ["o"])
                self.users[origin].join(name)
                return True
        else:
            raise StateError("Unknown entity attempted to create a channel")
    
    def channelExists(self, name):
        """ Returns if a channel exists or not """
        return name in self.channels
    
    def joinChannel(self, origin, numeric, name, modes, ts=1270080000):
        """ A user joins a channel, with optional modes already set. If the channel does not exist, it is created. """
        # TODO: More stringent checks on whether or not this user is allowed to join this channel
        if self.userExists(numeric):
            if self.channelExists(name):
                self.channels[name].join(numeric, modes)
                self.users[numeric].join(name)
            else:
                self.createChannel(numeric, name, ts)
        else:
            raise StateError("Unknown user attempted to join a channel")
    
    def _cleanupChannel(self, name):
        if len(self.channels[name].users) == 0:
            del self.channels[name]
            for user in self.users:
                if self.users[user].isInvited(name):
                    self.users[user].invites.remove(name)
    
    def partChannel(self, numeric, name):
        """ A user parts a channel """
        if self.userExists(numeric):
            if self.channelExists(name):
                # Note: No ison protection in order to support zombies
                self.channels[name].part(numeric)
                self.users[numeric].part(name)
                self._cleanupChannel(name)
            else:
                raise StateError("User tried to leave a channel that does not exist")
        else:
            raise StateError("Unknown user attempted to leave a channel")
    
    def partAllChannels(self, numeric):
        """ A user parts all channels """
        # Shallow copy to allow us to modify during loop
        for channel in self.users[numeric].channels.copy():
            self.channels[channel].part(numeric)
            self.users[numeric].part(channel)
            self._cleanupChannel(channel)
    
    def changeChannelMode(self, origin, name, mode):
        """ Change the modes on a channel. Modes are tuples of the desired change (single modes only) and an optional argument, or None """
        # TODO: More stringent checks on whether or not this user is allowed to make this mode change
        if self.userExists(origin) or (self.serverExists(origin[0]) and origin[1] == None):
            if self.channelExists(name):
                self.channels[name].changeMode(mode)
            else:
                raise StateError("Attempted to change the modes on a channel that does not exist")
        else:
            raise StateError("An invalid entity attempted to change a channel mode")
    
    def addChannelBan(self, origin, name, mask):
        """ Adds a ban to the channel. """
        # TODO: More stringent checks on whether or not this user is allowed to make this mode change
        if self.userExists(origin) or (self.serverExists(origin[0]) and origin[1] == None):
            if self.channelExists(name):
                self.channels[name].addBan(mask)
            else:
                raise StateError("Attempted to add a ban to a channel that does not exist")
        else:
            raise StateError("An invalid entity attempted to add a channel ban")
    
    def removeChannelBan(self, origin, name, ban):
        """ Removes a ban from the channel. """
        # TODO: More stringent checks on whether or not this user is allowed to make this mode change
        if self.userExists(origin) or (self.serverExists(origin[0]) and origin[1] == None):
            if self.channelExists(name):
                self.channels[name].removeBan(ban)
            else:
                raise StateError("Attempted to remove a ban from a channel that does not exist")
        else:
            raise StateError("An invalid entity attempted to remove a channel ban")
    
    def clearChannelBans(self, origin, name):
        """ Clears all bans from the channel. """
        # TODO: More stringent checks on whether or not this user is allowed to make this mode change
        if self.userExists(origin) or (self.serverExists(origin[0]) and origin[1] == None):
            if self.channelExists(name):
                for ban in self.channels[name].bans:
                    self.removeChannelBan(origin, name, ban)
            else:
                raise StateError("Attempted to clear bans from a channel that does not exist")
        else:
            raise StateError("An invalid entity attempted to clear channel bans")
    
    def deop(self, origin, channel, user):
        """ Deops a user from the channel. """
        # TODO: More stringent checks on whether or not this user is allowed to make this mode change
        if self.userExists(origin) or (self.serverExists(origin[0]) and origin[1] == None):
            if self.channelExists(channel):
                if self.channels[channel].isop(user):
                    self.channels[channel].deop(user)
                else:
                    raise StateError('Attempted to deop a user that was not op on the channel')
            else:
                raise StateError('Attempted to deop from a channel that does not exist')
        else:
            raise StateError("An invalid entity attempted to deop a user")
    
    def clearChannelOps(self, origin, name):
        """ Clears all ops from the channel. """
        # TODO: More stringent checks on whether or not this user is allowed to make this mode change
        if self.userExists(origin) or (self.serverExists(origin[0]) and origin[1] == None):
            if self.channelExists(name):
                for op in self.channels[name].ops():
                    self.deop(origin, name, op)
            else:
                raise StateError("Attempted to clear ops from a channel that does not exist")
        else:
            raise StateError("An invalid entity attempted to clear channel ops")
    
    def devoice(self, origin, channel, user):
        """ Devoices a user from the channel. """
        # TODO: More stringent checks on whether or not this user is allowed to make this mode change
        if self.userExists(origin) or (self.serverExists(origin[0]) and origin[1] == None):
            if self.channelExists(channel):
                if self.channels[channel].isvoice(user):
                    self.channels[channel].devoice(user)
                else:
                    raise StateError('Attempted to devoice a user that was not op on the channel')
            else:
                raise StateError('Attempted to devoice from a channel that does not exist')
        else:
            raise StateError("An invalid entity attempted to devoice a user")
    
    def clearChannelVoices(self, origin, name):
        """ Clears all voices from the channel. """
        # TODO: More stringent checks on whether or not this user is allowed to make this mode change
        if self.userExists(origin) or (self.serverExists(origin[0]) and origin[1] == None):
            if self.channelExists(name):
                for voice in self.channels[name].voices():
                    self.devoice(origin, name, voice)
            else:
                raise StateError("Attempted to clear voices from a channel that does not exist")
        else:
            raise StateError("An invalid entity attempted to clear channel voices")
    
    def _cleanupGlines(self):
        """ Remove expired g-lines """
        # Make shallow copy of dictionary so we can modify it during iteration
        for gline in self._glines.copy():
            # Remove expired g-lines
            if self._glines[gline][1] < self.ts():
                del self._glines[gline]
    
    def addGline(self, origin, mask, target, expires, description):
        """ Add a g-line """
        if target == None or target == self.getServerID():
            self._glines[mask] = (description, expires)
    
    def isGlined(self, host):
        """ Check if someone is g-lined """
        self._cleanupGlines()
        for mask in self._glines:
            if fnmatch.fnmatch(host, mask):
                return self._glines[mask]
            else:
                return None
    
    def removeGline(self, origin, mask, target):
        """ Remove a gline """
        if target == None or target == self.getServerID():
            # Make shallow copy of dictionary so we can modify it during iteration
            for gline in self._glines.copy():
                # Remove any g-lines that match that mask
                if fnmatch.fnmatch(gline, mask):
                    del self._glines[gline]
    
    def invite(self, origin, target, channel):
        """ Origin invites Target to Channel """
        # TODO: Check origin can actually send invites
        if self.userExists(target):
            if self.channelExists(channel):
                self.users[target].invite(channel)
            else:
                raise StateError("Attempted to invite a user into a non-existant channel")
        else:
            raise StateError("Attempted to invite a non-existant user to a channel")

class user:
    """ Represents a user internally """
    
    numeric = None
    nickname = ""
    username = ""
    hostname = ""
    _modes = dict()
    channels = set()
    ip = 0
    fullname = ""
    account = ""
    hops = 0
    ts = 0
    away_reason = None
    invites = set()
    
    def __init__(self, numeric, nickname, username, hostname, modes, ip, hops, ts, fullname):
        self.numeric = numeric
        self.nickname = nickname
        self.username = username
        self.hostname = hostname
        self._modes = dict()
        for mode in modes:
            self.changeMode(mode)
        self.ip = ip
        self.hops = hops
        self.ts = ts
        self.fullname = fullname
        self.away_reason = None
        self.channels = set()
        self.invites = set()
    
    def auth(self, account):
        """ Mark this user as authenticated """
        if self.account == "":
            self.account = account
        else:
            raise StateError("Authentication state change received for someone who is already authenticated")
    
    def changeMode(self, mode):
        """ Change a single mode associated with this user """
        if mode[0][0] == "+" and mode[1] == None:
            self._modes[mode[0][1]] = True
        elif mode[0][0] == "+" and mode[1] != None:
            self._modes[mode[0][1]] = mode[1]
            # If this mode is an authentication mode (i.e., in a burst)
            if mode[0][1] == "r":
                self.auth(mode[1])
        else:
            self._modes[mode[0][1]] = False
    
    def hasGlobalMode(self, mode):
        """ Return whether a user has a mode """
        if mode in self._modes:
            return self._modes[mode]
        else:
            return False
    
    def isAway(self):
        """ Return whether a user is away or not """
        if self.away_reason == None:
            return False
        else:
            return True
    
    def join(self, channel):
        self.channels.add(channel)
        if self.isInvited(channel):
            self.invites.remove(channel)
    
    def part(self, channel):
        self.channels.remove(channel)
    
    def invite(self, channel):
        self.invites.add(channel)
    
    def isInvited(self, channel):
        return channel in self.invites

class channel:
    """ Represents a channel internally """
    
    name = ""
    ts = 0
    users = dict()
    _modes = dict()
    bans = []
    
    def __init__(self, name, ts):
        self.name = name
        self.ts = ts
        self.users = dict()
        self._modes = dict()
        self.bans = []
    
    def join(self, numeric, modes):
        """ Add a user to a channel """
        self.users[numeric] = modes
    
    def part(self, numeric):
        """ A user is parting this channel """
        del self.users[numeric]
    
    def changeMode(self, mode):
        """ Change a single mode associated with this channel """
        if mode[0][0] == "+" and mode[1] == None:
            self._modes[mode[0][1]] = True
        elif mode[0][0] == "+" and mode[1] != None:
            self._modes[mode[0][1]] = mode[1]
        else:
            self._modes[mode[0][1]] = False
    
    def hasMode(self, mode):
        """ Return whether a channel has a mode (and if it's something with an option, what it is) """
        if mode in self._modes:
            return self._modes[mode]
        else:
            return False
    
    def addBan(self, mask):
        """ Adds a ban to the channel """
        self.bans.append(mask)
    
    def removeBan(self, mask):
        """ Removes a ban from the channel """
        self.bans.remove(mask)
    
    def ison(self, numeric):
        """ Returns whether a not a user is on a channel """
        return numeric in self.users
    
    def isop(self, numeric):
        """ Check if a user is op on a channel """
        if self.ison(numeric):
            return "o" in self.users[numeric]
        else:
            return False
    
    def ops(self):
        ret = list()
        for user in self.users:
            if self.isop(user):
                ret.append(user)
        return ret
    
    def deop(self, numeric):
        self.users[numeric].remove("o")
    
    def isvoice(self, numeric):
        """ Check if a user is voice on a channel """
        if self.ison(numeric):
            return "v" in self.users[numeric]
        else:
            return False
    
    def voices(self):
        ret = list()
        for user in self.users:
            if self.isvoice(user):
                ret.append(user)
        return ret
    
    def devoice(self, numeric):
        self.users[numeric].remove("v")

class server:
    """ Internally represent a server """
    numeric = 0
    origin = None
    name = ""
    maxclient = 0
    boot_ts = 0
    link_ts = 0
    protocol = ""
    hops = 0
    flags = set()
    description = ""
    children = set()
    
    def __init__(self, origin, numeric, name, maxclient, boot_ts, link_ts, protocol, hops, flags, description):
        self.numeric = numeric
        self.origin = origin
        self.name = name
        self.maxclient = maxclient
        self.boot_ts = boot_ts
        self.link_ts = link_ts
        self.protocol = protocol
        self.hops = hops
        self.flags = set(flags)
        self.description = description
        self.children = set()
    
    def addChild(self, child):
        self.children.add(child)

class StateError(Exception):
    """ An exception raised if a state change would be impossible, generally suggesting we've gone out of sync """
    pass