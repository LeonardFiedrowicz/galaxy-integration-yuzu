import sys

import subprocess
import struct
import threading
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

from os.path import join, abspath, isdir, dirname, realpath, exists, isfile
from os import listdir, chdir, getcwd, environ
from xml.etree import ElementTree as ET
from shutil import copy
from time import sleep
import re

from dataclasses import dataclass

from urllib.parse import parse_qs, urlparse

from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Game, LicenseInfo, LicenseType, Authentication, LocalGame, NextStep, GameTime
from galaxy.api.consts import Platform, LocalGameState

# Manually override if you dare
roms_path = ""
emulator_path = ""


class AuthenticationHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type='text/html'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def do_GET(self):
        if "setpath" in self.path:
            self._set_headers()
            parse_result = urlparse(self.path)
            params = parse_qs(parse_result.query)
            global roms_path, emulator_path
            if 'path' in params:
                roms_path = params['path'][0]
            else:
                logging.debug("Error: ROM path is missing!")
            if 'emulator_path' in params:
                emulator_path = str(params['emulator_path'][0])
                if emulator_path.endswith(".exe"):
                    emulator_path = re.sub(r'(?:.(?!\\))+$', "", emulator_path)
            else:
                emulator_path = join(environ['LOCALAPPDATA'], "yuzu\\yuzu-windows-msvc\\")
            self.wfile.write("<script>window.location=\"/end\";</script>".encode("utf8"))
            return

        self._set_headers()
        self.wfile.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Yuzu Integration</title>
            <link href="https://fonts.googleapis.com/css?family=Lato:300&display=swap" rel="stylesheet"> 
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.5/css/bulma.min.css" integrity="sha256-vK3UTo/8wHbaUn+dTQD0X6dzidqc5l7gczvH+Bnowwk=" crossorigin="anonymous" />
            <style>
                @charset "UTF-8";
                html, body {
                    padding: 0;
                    margin: 0;
                    border: 0;
                    background: rgb(40, 39, 42) !important;
                }

                html {
                    font-size: 12px;
                    line-height: 1.5;
                    font-family: 'Lato', sans-serif;
                }

                html {
                    overflow: scroll;
                    overflow-x: hidden;
                }
                ::-webkit-scrollbar {
                    width: 0px;  /* Remove scrollbar space */
                    background: transparent;  /* Optional: just make scrollbar invisible */
                }

                .header {
                    background: rgb(46, 45, 48);
                    height: 66px;
                    line-height: 66px;
                    font-weight: 600;
                    text-align: center;
                    vertical-align: middle;
                    padding: 0;
                    margin: 0;
                    border: 0;
                    font-size: 16px;
                    box-sizing: border-box;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
                    color: white !important;
                }

                .sub-container {
                    width: 90%;
                    min-width: 200px;
                }
            </style>
        </head>
        <body>
            <div class="header">
                Yuzu Plugin Configuration
            </div>

            <br />

            <div class="sub-container container">
                <form method="GET" action="/setpath">
                    <div class="field">
                      <label class="label has-text-light">Games Location</label>
                      <div class="control">
                        <input class="input" name="path" type="text" class="has-text-light" placeholder="Enter absolute ROM path">
                      </div>
                    </div>

                    <div class="field">
                      <label class="label has-text-light">Yuzu Location [optional]</label>
                      <div class="control">
                        <input class="input" name="emulator_path" type="text" class="has-text-light" placeholder="Enter absolute Yuzu path [optional]">
                      </div>
                    </div>

                    <div class="field is-grouped">
                      <div class="control">
                        <input type="submit" class="button is-link" value="Enable Plugin" />
                      </div>
                    </div>
                </form>
            </div>
        </body>
        </html>
        """.encode('utf8'))


class AuthenticationServer(threading.Thread):
    def __init__(self, port=0):
        super().__init__()
        self.path = ""
        server_address = ('localhost', port)
        self.httpd = HTTPServer(server_address, AuthenticationHandler)  # partial(AuthenticationHandler, self))
        self.port = self.httpd.server_port

    def run(self):
        self.httpd.serve_forever()


class YuzuPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(
            Platform.NintendoSwitch,  # Choose platform from available list
            "0.2",  # Version
            reader,
            writer,
            token
        )
        self.game_running = False
        self.running_game = None
        self.games = {}
        self.game_times = {}
        #        self.running_games = []
        self.server = AuthenticationServer()
        self.server.start()

    # def tick(self):
    #     if self.game_running and self.running_game is not None:
    #         self.game_times[self.running_game][0] += self.TICK_TIME
    #         self.game_times[self.running_game][1] += self.TICK_TIME
    #         self.update_game_time(GameTime(self.running_game, self.game_times[self.running_game][0] // 60, self.game_times[self.running_game][1]))

    def launch_Yuzu_game(self, game):
        def in_thread(_self, _game):
            chdir(emulator_path)
            proc = subprocess.Popen(["./Yuzu.exe", _game.path])
            _self.game_running = True
            _self.running_game = _game.game_id
            proc.wait()
            _self.game_running = False
            _self.running_game = None
            # _self.update_time(_game)
            logging.debug("GameTime updated, Thread finished")

            return

        thread = threading.Thread(target=in_thread, args=(self, game))
        thread.setDaemon(True)
        thread.start()

        return thread

    # def update_time(self, game):
    #     new_game_times = get_game_times()
    #     game_time = new_game_times[game.game_id]
    #     self.game_times[game.game_id] = game_time
    #     self.update_game_time(GameTime(game.game_id, game_time[0] // 60, game_time[1]))

    def parse_games(self):
        self.games = get_games()
        #self.game_times = get_game_times()

    async def shutdown(self):
        self.server.httpd.shutdown()

    async def launch_game(self, game_id):
        game = self.games[game_id]
        logging.debug("Launching game " + game.game_id)
        self.launch_Yuzu_game(game)

        #       if game_id not in self.running_games:
        #           self.running_games.append(game_id)
        return

    def finish_login(self):
        some_dict = dict()
        some_dict["roms_path"] = roms_path
        some_dict["emulator_path"] = emulator_path
        self.store_credentials(some_dict)

        self.parse_games()
        #        thread = UpdateGameTimeThread(self)
        #        thread.start()
        return Authentication(user_id="a_high_quality_Yuzu_user", user_name=roms_path)

    # implement methods
    async def authenticate(self, stored_credentials=None):
        global roms_path, emulator_path
        # See if we have the path in the cache
        if len(roms_path) == 0 and stored_credentials is not None and "roms_path" in stored_credentials:
            roms_path = stored_credentials["roms_path"]

        if len(emulator_path) == 0 and stored_credentials is not None and "emulator_path" in stored_credentials:
            emulator_path = stored_credentials["emulator_path"]

        if (len(roms_path) == 0) or (len(emulator_path) == 0):
            params = {
                "window_title": "Configure Yuzu Plugin",
                "window_width": 400,
                "window_height": 300,
                "start_uri": "http://localhost:" + str(self.server.port),
                "end_uri_regex": ".*/end.*"
            }
            return NextStep("web_session", params)

        return self.finish_login()

    async def pass_login_credentials(self, step, credentials, cookies):
        return self.finish_login()

    async def get_owned_games(self):
        owned_games = []
        for game in self.games.values():
            license_info = LicenseInfo(LicenseType.OtherUserLicense, None)
            owned_games.append(Game(game_id=game.game_id, game_title=game.game_title, dlcs=None,
                                    license_info=license_info))
        return owned_games

    async def get_local_games(self):
        local_games = []
        for game in self.games.values():
            local_game = LocalGame(game.game_id, LocalGameState.Installed)
            local_games.append(local_game)
        return local_games

    # async def get_game_time(self, game_id, context=None):
    #     if game_id in self.game_times:
    #         game_time = self.game_times[game_id]
    #         return GameTime(game_id, game_time[0] // 60, game_time[1])


@dataclass
class NUSGame:
    game_id: str
    game_title: str
    path: str


def get_games():
    games = {}
    dir_path = dirname(realpath(__file__))
    nxgameinfo_path = join(dir_path, 'nxgameinfo')
    chdir(nxgameinfo_path)

    # get required key files
    if exists(join(emulator_path, "user\\")):
        keys_path = join(emulator_path, "user\\keys\\")
    else:
        keys_path = join(environ['APPDATA'], "yuzu\\keys\\")
    key_files = listdir(keys_path)
    for key_file in key_files:
        full_key_file_name = join(keys_path, key_file)
        if isfile(full_key_file_name) :
            copy(full_key_file_name, nxgameinfo_path)

    nxgameinfo_exe_path = join(dir_path, 'nxgameinfo', 'nxgameinfo_cli.exe')
    game_list_unstructured, stderr = subprocess.Popen([nxgameinfo_exe_path, '-z', roms_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
    game_list_lines = game_list_unstructured.decode('cp437', 'backslashescape').splitlines()

    i = 5               # start in line 5
    #file_count = 1
    while i < len(game_list_lines)-21:
        if "Base" in game_list_lines[i+16] and len(game_list_lines[i+21]) < 10:      # Check if its a base game and if error line is empty
            game_path = game_list_lines[i]
            game_id = game_list_lines[i+2][17:33]
            game_title = game_list_lines[i+3][14:]
            games[game_id] = (NUSGame(game_id=game_id, game_title=game_title, path=game_path))
        i = i + 23
        #file_count = file_count + 1
        #if file_count > 35:
        #    return games

    return games


# def get_game_times():
#     game_times = {}
#     if exists(emulator_path + "./settings.xml"):
#         root = ET.parse(emulator_path + "./settings.xml").getroot()
#     else:
#         return
#     # logging.debug("Extracting play time for games...")
#     for game in root.find("GameCache"):
#         # logging.debug(str(game))
#         title_id = str(hex(int(game.find("title_id").text)).split('x')[-1]).rjust(16, '0').upper()  # convert to hex, remove 0x, add padding
#         time_played = int(game.find("time_played").text)
#         last_time_played = int(game.find("last_played").text)
#         game_times[title_id] = [time_played, last_time_played]
#         # logging.debug("Title ID = {}, Time Played = {}, Last Time Played = {}".format(title_id, time_played, last_time_played))
#     return game_times


def main():
    create_and_run_plugin(YuzuPlugin, sys.argv)


# run plugin event loop
if __name__ == "__main__":
    main()
