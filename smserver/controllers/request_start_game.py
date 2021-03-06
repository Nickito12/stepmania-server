#!/usr/bin/env python3
# -*- coding: utf8 -*-

from smserver.smutils import smpacket
from smserver.stepmania_controller import StepmaniaController
from smserver.chathelper import with_color
from smserver import models, ability

class RequestStartGameController(StepmaniaController):
    command = smpacket.SMClientCommand.NSCRSG
    require_login = True

    def handle(self):
        if not self.room:
            return

        song = models.Song.find_or_create(
            self.packet["song_title"],
            self.packet["song_subtitle"],
            self.packet["song_artist"],
            self.session)
        if self.packet["usage"] == 2:
            self.start_game_request(song)
            return

        have_song = self.check_song_presence(song)
        for user in self.active_users:
            user.has_song = have_song
        if not have_song:
            self.send_message("%s does %s have the song (%s)!" % (
                self.colored_user_repr(self.room.id),
                with_color("not", "ff0000"),
                with_color(song.fullname)
                ))

    def start_game_request(self, song):
        with self.conn.mutex:
            self.conn.songs[song.id] = True

        if self.conn.song == song.id:
            self.request_launch_song(song)
            return

        self.send_message("%s selected %s which has been played %s times.%s" % (
            self.colored_user_repr(self.room.id),
            with_color(song.fullname),
            song.time_played,
            " Best scores:" if song.time_played > 0 and self.room.show_bests else ""
            ))

        self.room.active_song = song
        self.room.active_song_hash = self.packet["song_hash"]

        if song.time_played > 0 and self.room.show_bests:
            for song_stat in song.best_scores:
                self.send_message(song_stat.pretty_result(room_id=self.room.id, color=True, toasty=True, points=self.room.show_points))

        self.conn.song = song.id
        self.conn.songs[song.id] = True

        hashpacket = smpacket.SMPacketServerNSCRSG(
                usage=1,
                song_title=song.title,
                song_subtitle=song.subtitle,
                song_artist=song.artist,
                song_hash=self.packet["song_hash"]
                )
        nonhashpacket = smpacket.SMPacketServerNSCRSG(
                usage=1,
                song_title=song.title,
                song_subtitle=song.subtitle,
                song_artist=song.artist
                )
        for conn in self.server.player_connections(self.room.id):
            if conn.stepmania_version < 4:
                conn.send(nonhashpacket)
            else:
                conn.send(hashpacket)

    def check_song_presence(self, song):
        with self.conn.mutex:
            self.conn.songs[song.id] = {0: True, 1: False}[self.packet["usage"]]

            return self.conn.songs[song.id]

    def request_launch_song(self, song):
        if not self.room.free and self.cannot(ability.Permissions.start_game, self.room.id):
            self.send_message("You don't have the permission to start a game", to="me")
            return

        canstart = True
        isplaying = False
        busy = []
        nosong = []
        for user in self.room.online_users:
            if user.status == 2 and self.room.active_song_id and self.room.ingame and self.room.status != 1:
                canstart = False
                isplaying = True
            if user.status == 3 or user.status == 4:
                busy.append(user)
                canstart = False
            if self.room.reqsong:
                if user.has_song == False:
                    canstart = False
                    nosong.append(user)

        if not canstart:
            for user in busy:
                self.send_message("User %s is busy." % with_color(user.name),to="me")
            for user in nosong:
                    self.send_message("User %s does not have the song." % with_color(user.name),to="me")
            if isplaying:
                self.send_message(
                    "Room %s is already playing %s." % (
                        with_color(self.room.name),
                        with_color(self.room.active_song.fullname)
                        ),
                    to="me"
                )
            return

        game = models.Game(room_id=self.room.id, song_id=song.id)

        self.session.add(game)
        self.session.commit()

        self.send_message("%s started the song %s" % (self.colored_user_repr(self.room.id), with_color(song.fullname)) )

        self.room.status = 2
        self.room.active_song = song
        self.room.active_song_hash = self.packet["song_hash"]

        hashpacket = smpacket.SMPacketServerNSCRSG(
                usage=2,
                song_title=song.title,
                song_subtitle=song.subtitle,
                song_artist=song.artist,
                song_hash=self.packet["song_hash"]
                )
        nonhashpacket = smpacket.SMPacketServerNSCRSG(
                usage=2,
                song_title=song.title,
                song_subtitle=song.subtitle,
                song_artist=song.artist
                )
        for conn in self.server.player_connections(self.room.id):
            if conn.stepmania_version < 4:
                conn.send(nonhashpacket)
            else:
                conn.send(hashpacket)
        
        roomspacket = models.Room.smo_list(self.session, self.active_users)
        for conn in self.server.connections:
            if conn.room == None:
                conn.send(roomspacket)
                self.server.send_user_list_lobby(conn, self.session)
