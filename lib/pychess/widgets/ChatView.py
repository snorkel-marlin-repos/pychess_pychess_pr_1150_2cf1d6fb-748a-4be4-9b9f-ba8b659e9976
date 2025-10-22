from __future__ import absolute_import
from time import strftime, gmtime, localtime
import random

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GObject

from pychess.System.idle_add import idle_add
from pychess.System import uistuff
from pychess.widgets import insert_formatted
from pychess.widgets.Background import set_textview_color
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.ic.ICGameModel import ICGameModel
from .BorderBox import BorderBox


class ChatView (Gtk.VPaned):
    __gsignals__ = {
        'messageAdded' : (GObject.SignalFlags.RUN_FIRST, None, (str,str,object)),
        'messageTyped' : (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__ (self, gamemodel=None):
        GObject.GObject.__init__(self)
        self.gamemodel = gamemodel

        # States for the color generator
        self.colors = {}
        self.startpoint = random.random()

        # Inits the read view
        self.readView = Gtk.TextView()
        #self.readView.set_size_request(-1, 30)
        set_textview_color(self.readView)

        sw1 = Gtk.ScrolledWindow()
        sw1.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw1.set_shadow_type(Gtk.ShadowType.NONE)
        #sw1.set_size_request(-1, 300)
        uistuff.keepDown(sw1)

        sw1.add(self.readView)
        self.readView.set_editable(False)
        self.readView.set_cursor_visible(False)
        self.readView.props.wrap_mode = Gtk.WrapMode.WORD
        self.readView.props.pixels_below_lines = 1
        self.readView.props.pixels_above_lines = 2
        self.readView.props.left_margin = 2
        #self.readView.get_buffer().create_tag("log",
        #        foreground = self.readView.get_style().fg[Gtk.StateType.INSENSITIVE])

        if isinstance(self.gamemodel, ICGameModel):
            self.refresh = Gtk.Image()
            self.refresh.set_from_pixbuf(load_icon(16, "view-refresh", "stock-refresh"))

            vp = Gtk.VPaned()

            # Inits the observers view
            self.obsView = Gtk.TextView()
            self.obsView.set_cursor_visible(False)
            #self.obsView.set_size_request(-1, 3)
            set_textview_color(self.obsView)

            sw0 = Gtk.ScrolledWindow()
            sw0.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            sw0.set_shadow_type(Gtk.ShadowType.NONE)
            sw0.set_size_request(-1, 3)
            uistuff.keepDown(sw0)
            sw0.add(self.obsView)
            self.obsView.set_editable(False)
            self.obsView.props.wrap_mode = Gtk.WrapMode.WORD
            self.obsView.props.pixels_below_lines = 1
            self.obsView.props.pixels_above_lines = 2
            self.obsView.props.left_margin = 2

            vp.pack1(BorderBox(sw0, bottom=True), resize=False, shrink=False)
            vp.pack2(BorderBox(sw1, top=True), resize=True, shrink=False)

            self.pack1(BorderBox(vp, bottom=True), resize=True, shrink=True)
        else:
            self.pack1(BorderBox(sw1, bottom=True), resize=True, shrink=True)

        # Create a 'log mark' in the beginning of the text buffer. Because we
        # query the log asynchronously and in chunks, we can use this to insert
        # it correctly after previous log messages, but before the new messages.
        start = self.readView.get_buffer().get_start_iter()
        self.readView.get_buffer().create_mark("logMark", start)

        # Inits the write view
        self.writeView = Gtk.TextView()
        set_textview_color(self.writeView)

        sw2 = Gtk.ScrolledWindow()
        sw2.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw2.set_shadow_type(Gtk.ShadowType.NONE)
        sw2.set_size_request(-1, 3)
        sw2.add(self.writeView)
        self.writeView.props.wrap_mode = Gtk.WrapMode.WORD
        self.writeView.props.pixels_below_lines = 1
        self.writeView.props.pixels_above_lines = 2
        self.writeView.props.left_margin = 2
        self.pack2(BorderBox(sw2, top=True), resize=False, shrink=False)

        # Forces are reasonable position for the panner.
        def callback (widget, ctx):
            widget.disconnect(handle_id)
            allocation = widget.get_allocation()
            self.set_position(int(max(0.70*allocation.height, allocation.height-60)))
        handle_id = self.connect("draw", callback)

        self.writeView.connect("key-press-event", self.onKeyPress)

    def on_obs_btn_clicked(self, other):
        allob = 'allob ' + str(self.gamemodel.ficsgame.gameno)
        self.gamemodel.connection.client.run_command(allob)

    @idle_add
    def update_observers(self, other, observers):
        """
        """

        obs_list = observers.split()
        label = _("Observers")
        self.obsView.get_buffer().props.text = ""
        tb = self.obsView.get_buffer()
        self.obs_btn = Gtk.Button()
        self.obs_btn.set_image(self.refresh)
        self.obs_btn.set_label(label)
        self.obs_btn.connect("clicked", self.on_obs_btn_clicked)
        iter = tb.get_iter_at_offset(0)
        anchor1 = tb.create_child_anchor(iter)
        tb.insert(iter, '\n')
        self.obsView.add_child_at_anchor(self.obs_btn, anchor1)
        for player in obs_list:
            # Colourize only players able to interact with chat View
            if player.endswith("(U)"):
                tb.insert(iter, "%s " % player[:-3])
            elif "(" in player:
                pref,rest = player.split('(',1)
                self._ensureColor(pref)
                tb.insert_with_tags_by_name(iter, "%s " % player, pref+"_bold")
            else:
                tb.insert(iter, "%s " % player)
        self.obsView.show_all()


    def _ensureColor(self, pref):
        """ Ensures that the tags for pref_normal and pref_bold are set in the text buffer """
        tb = self.readView.get_buffer()
        if not pref in self.colors:
            color = uistuff.genColor(len(self.colors) + 1, self.startpoint)
            self.colors[pref] = color
            color = [int(c * 255) for c in color]
            color = "#" + "".join([hex(v)[2:].zfill(2) for v in color])
            tb.create_tag(pref + "_normal", foreground=color)
            tb.create_tag(pref + "_bold", foreground=color, weight=Pango.Weight.BOLD)
            if isinstance(self.gamemodel, ICGameModel):
                otb = self.obsView.get_buffer()
                otb.create_tag(pref + "_normal", foreground=color)
                otb.create_tag(pref + "_bold", foreground=color, weight=Pango.Weight.BOLD)


    def clear (self):
        self.writeView.get_buffer().props.text = ""
        self.readView.get_buffer().props.text = ""
        tagtable = self.readView.get_buffer().get_tag_table()
        for i in range(len(self.colors)):
            tagtable.remove("%d_normal" % i)
            tagtable.remove("%d_bold" % i)
        self.colors.clear()

    def __addMessage (self, iter, time, sender, text):
        pref = sender.lower()
        tb = self.readView.get_buffer()
        # Calculate a color for the sender
        self._ensureColor(pref)
        # Insert time, name and text with different stylesd
        tb.insert_with_tags_by_name(iter, "(%s) "%time, pref+"_normal")
        tb.insert_with_tags_by_name(iter, sender+": ", pref+"_bold")
        insert_formatted(self.readView, iter, text)
        # This is used to buzz the user and add senders to a list of active participants
        self.emit("messageAdded", sender, text, self.colors[pref])

    def insertLogMessage (self, timestamp, sender, text):
        """ Takes a list of (timestamp, sender, text) pairs, and inserts them in
            the beginning of the document.
            All text will be in a gray color """
        tb = self.readView.get_buffer()
        iter = tb.get_iter_at_mark(tb.get_mark("logMark"))
        time = strftime("%H:%M:%S", localtime(timestamp))
        self.__addMessage(iter, time, sender, text)
        tb.insert(iter, "\n")

    def addMessage (self, sender, text):
        tb = self.readView.get_buffer()
        iter = tb.get_end_iter()
        # Messages have linebreak before the text. This is opposite to log
        # messages
        if tb.props.text: tb.insert(iter, "\n")
        self.__addMessage(iter, strftime("%H:%M:%S"), sender, text)

    def disable (self, message):
        """ Sets the write field insensitive, in cases where the channel is
            read only. Use the message to give the user a propriate
            exlpanation """
        self.writeView.set_sensitive(False)
        self.writeView.props.buffer.set_text(message)

    def enable (self):
        self.writeView.props.buffer.set_text("")
        self.writeView.set_sensitive(True)

    def onKeyPress (self, widget, event):
        if event.keyval in list(map(Gdk.keyval_from_name,("Return", "KP_Enter"))):
            if not event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                buffer = self.writeView.get_buffer()
                if buffer.props.text:
                    self.emit("messageTyped", buffer.props.text)
                    buffer.props.text = ""
                return True
