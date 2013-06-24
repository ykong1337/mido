# -*- coding: utf-8 -*-

"""
msg.py - MIDI messages

http://www.midi.org/techspecs/midimessages.php

New messages are created with mido.new() or mido.Message(),
which both return a message object.
"""

from __future__ import print_function
from collections import namedtuple


# Pitchwheel is a 14 bit signed integer
pitchwheel_min = -8192
pitchwheel_max = 8191

Spec = namedtuple('Spec', 'opcode type args size')

msg_specs = [
    #
    # MIDI message specifications
    #
    # This is the authorative definition of message types.
    #
    
    #
    # Channel messages
    # 
    # pitchwheel value is a signed integer in the range -8192 - 8191
    #
    Spec(0x80, 'note_off',        ('channel', 'note',    'velocity'), 3),
    Spec(0x90, 'note_on',         ('channel', 'note',    'velocity'), 3),
    Spec(0xa0, 'polytouch',       ('channel', 'note',    'value'),    3),
    Spec(0xb0, 'control_change',  ('channel', 'control', 'value'),    3),
    Spec(0xc0, 'program_change',  ('channel', 'program',),   3),
    Spec(0xd0, 'aftertouch',      ('channel', 'value',),    3),
    Spec(0xe0, 'pitchwheel',      ('channel', 'value',),    3),

    #
    # System common messages
    #
    # songpos.pos is 14 bit unsigned int,
    # seralized as lsb msb
    #
    # Todo: rename song to song_select?
    #
    # Sysex messages have a potentially infinite size.
    #
    Spec(0xf0, 'sysex',         ('data',),          float('inf')),
    Spec(0xf1, 'undefined_f1',  (),                 1), 
    Spec(0xf2, 'songpos',       ('pos',),           3),  
    Spec(0xf3, 'song',          ('song',),          2),
    Spec(0xf4, 'undefined_f4',  (), 1),
    Spec(0xf5, 'undefined_f5',  (), 1),
    Spec(0xf6, 'tune_request',  (), 1),
    Spec(0xf7, 'sysex_end',     (), 1),

    #
    # System realtime messages These can interleave other messages but
    # they have no data bytes, so that's OK
    #
    Spec(0xf8, 'clock',          (), 1),
    Spec(0xf9, 'undefined_f9',   (), 1),
    Spec(0xfa, 'start',          (), 1),
    # Note: 'continue' is a keyword in python, so is
    # is bound to protomidi.msg.continue_
    Spec(0xfb, 'continue',       (), 1),
    Spec(0xfc, 'stop',           (), 1),
    Spec(0xfd, 'undefined_fd',   (), 1),
    Spec(0xfe, 'active_sensing', (), 1),
    Spec(0xff, 'reset',          (), 1),
    ]

#
# Lookup tables for quick access
# You can look up by opcode or type.
#
spec_lookup = dict()
for spec in msg_specs:
    if spec.opcode < 0xf0:
        # Channel message. Add one lookup for all channels.
        for i in range(16):
            spec_lookup[spec.opcode + i] = spec
    else:
        spec_lookup[spec.opcode] = spec

    spec_lookup[spec.type] = spec

del spec, i

#                                                                                  
# Assert that data values as of correct type and size                              
#                                                                                  
def isint(val):
    """Check if a value is an integer"""
    # Todo: is there a better way to check this?                                   
    return isinstance(val, int)

def isnum(val):
    """Check if a value is a number"""
    # Todo: is there a better way to check this?                                   
    return isinstance(val, int) \
        or isinstance(val, float) \
        or isinstance(val, long)

def assert_time(time):
    if not (time == None or isnum(time)):
        raise ValueError('time must be a number or None')

def assert_channel(val):
    if not isint(val) or not (0 <= val < 16):
        raise ValueError('channel must be integer in range(0, 16)')

# Todo: fix range (should be 14 bit unsigned)                                      
def assert_songpos(val):
    if not isint(val) or not (0 <= val < 32768):
        raise ValueError('song position must be integer in range(0, 32768)')

def assert_pitchwheel(val):
    if not isint(val) or not (pitchwheel_min <= val <= pitchwheel_max):
        fmt = 'pitchwheel value must be number in range({}, {})'
        raise ValueError(fmt.format(
                pitchwheel_min,
                pitchwheel_max))

def assert_databyte(val):
    if not isint(val) or not (0 <= val < 128):
        raise ValueError('data byte must by in range(0, 128)')


class Message():
    """
    MIDI message class.

    New messages are created with mido.new() or mido.Message().
    Valid arguments are:

    mido.new('note_off', channel=0, note=0, velocity=0, time=0)
    mido.new('note_on', channel=0, note=0, velocity=0, time=0)
    mido.new('polytouch', channel=0, note=0, value=0, time=0)
    mido.new('control_change', channel=0, control=0, value=0, time=0)
    mido.new('program_change', channel=0, program=0, time=0)
    mido.new('aftertouch', channel=0, value=0, time=0)
    mido.new('pitchwheel', channel=0, value=0, time=0)
    mido.new('sysex', data=(), time=0)
    mido.new('undefined_f1', time=0)
    mido.new('songpos', pos=0, time=0)
    mido.new('song', song=0, time=0)
    mido.new('undefined_f4', time=0)
    mido.new('undefined_f5', time=0)
    mido.new('tune_request', time=0)
    mido.new('sysex_end', time=0)
    mido.new('clock', time=0)
    mido.new('undefined_f9', time=0)
    mido.new('start', time=0)
    mido.new('continue', time=0)
    mido.new('stop', time=0)
    mido.new('undefined_fd', time=0)
    mido.new('active_sensing', time=0)
    mido.new('reset', time=0)
    """
    
    def __init__(self, type_or_opcode, **kw):

        try:
            spec = spec_lookup[type_or_opcode]
        except KeyError:
            try:
                value = hex(type_or_opcode)
            except TypeError:
                value = type_or_opcode
            raise ValueError('Invalid type name or opcode (status byte): %r' % value)

        opcode = spec.opcode

        # Get channel. Can be overrided with keyword argument.
        if opcode < 0xf0:
            # Channel message. Split out channel from opcode.
            default_channel = opcode & 0x0f
            opcode &= 0xf0
        else:
            channel = 0

        self._set('spec', spec)
        self._set('opcode', opcode)
        self._set('type', self.spec.type)

        # Set default values
        for name in self.spec.args:
            if name == 'data':
                self._set('data', ())
            elif name == 'channel':
                self._set('channel', default_channel)
            else:
                self._set(name, 0)
        self._set('time', 0)

        # Override
        for name, value in kw.items():
            setattr(self, name, value)

        # self._set('is_chanmsg', (self.opcode < 0xf0))

    def copy(self, **override):
        """
        Return a copy of the message. Attributes can
        be overriden by passing keyword arguments.

        msg = Message('note_on', note=20, velocity=64)  # Create a note_on
        msg2 = msg.copy(velocity=32)  # New note_on with softer velocity
        """

        # Get values from this object
        kw = {'time' : self.time}
        for name in self.spec.args:
            kw[name] = getattr(self, name)

        # Override
        kw.update(override)

        return Message(self.type, **kw)

    def _set(self, name, value):
        """
        Set an attribute, bypassing all name and type checks.
        """
        self.__dict__[name] = value

    def __setattr__(self, name, value):
        # Todo: validation

        if name in self.spec.args or name == 'time':
            if name == 'time':
                assert_time(value)
            elif name == 'channel':
                assert_channel(value)
            elif name == 'pos':
                assert_songpos(value)
            elif name == 'pitchwheel':
                assert_pichwheel(value)
            elif name == 'data':
                value = tuple(value)  # Make the data bytes immutable
                for byte in value:
                    assert_databyte(byte)

            self.__dict__[name] = value
        else:
            raise ValueError('Invalid argument for MIDI message: %r (must be one of: %s)' % (
                    name, ' '.join(self.spec.args)))
                    
    def __delattr__(self, name):
        raise ValueError('MIDI message attributes can\'t be deleted')

    def bytes(self):
        """
        Encode message and return as a list of bytes.
        """

        if hasattr(self, 'channel'):
            b = [self.opcode | self.channel]
        else:
            b = [self.opcode]

        for name in self.spec.args:
            if name == 'channel':
                continue  # We already have this

            elif name == 'data':
                b.extend(self.data)

            elif self.type == 'pitchwheel' and name == 'value':
                value = self.value + (2**13)
                lsb = value & 0x7f
                msb = value >> 7
                b.append(lsb)
                b.append(msb)

            elif self.type == 'songpos' and name == 'pos':
                # Convert 14 bit value to two 7-bit values
                # Todo: check if this is correct
                lsb = msg.pos & 0x7f
                b.append(lsb)

                msb = msg.pos >> 7
                b.append(msb)
            else:
                # Ordinary data byte
                b.append(getattr(self, name))

        if self.type == 'sysex':
            # Append a sysex_end
            b.append(0xf7)

        return b

    def bin(self):
        """
        Encode message and return as a bytearray().
        """
        
        # Todo: bytearray() or bytes()
        return bytearray(self.bytes())

    def hex(self, sep=' '):
        """
        Encode message and return as a string of hex numbers,
        separated by the string sep. The default separator is
        a single space.
        """

        return sep.join(['%02X' % byte for byte in self.bytes()])

    def __repr__(self):
        args = [repr(self.type)] 
        args += ['%s=%r' % (name, getattr(self, name)) for name in list(self.spec.args) + ['time']]
        args = ', '.join(args)
        return 'mido.Message(%s)' % args

    def __eq__(self, other):
        # The time attribute is not compared.
        def key(msg):
            k = tuple([msg.type] + [getattr(msg, a) for a in msg.spec.args])
            return k
            
        return key(self) == key(other)

def build_signature(spec, include_type=True):
    """
    Builds a contructor signature for a message.

    This is used to create documentation.
    """

    if include_type:
        parts = [repr(spec.type)]
    else:
        parts = []

    for name in spec.args + ('time',):
        if name == 'data':
            parts.append('data=()')
        else:
            parts.append(name + '=0')

    sig = '(' + ', '.join(parts) + ')'

    return sig

def _print_signatures():
    """
    Print arguments for mido.new() for all supported message types.

    This will be used to generate documentation.
    """
    
    for spec in msg_specs:
        sig = build_signature(spec)
        print('mido.new' + sig)