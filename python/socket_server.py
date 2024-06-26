#!/usr/bin/python

# MIT License
#
# Copyright (c) [2016] [Okan Ulas Gezeroglu]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# This multi thread socket server receive commands from php and executes them on the pathfinder.
from ev3dev.ev3 import *
import time
t1 = time.time()
Sound.speak('Starting Server')

import socket
import xml.sax

from threading import *
from ev3dev.auto import OUTPUT_A, OUTPUT_B, OUTPUT_C, OUTPUT_D

from get_info import BrickInfo
from maze import make_maze
from maze import parse_maze
from printer import LegoPrinter
from svg_parser import SvgParser

lego_printer = LegoPrinter()
brick_info = BrickInfo()

timea = 0
timeb = 0
tap_dash = ""
switch = 0
in_mode = 0

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = 'localhost'
port = int(3000)
socket.bind((host, port))

clients = set()
clients_lock = Lock()

class Client(Thread):
    def __init__(self, client_socket, client_address):
        Thread.__init__(self)
        print ("New Connection", client_address)
        self.socket = client_socket
        self.address = client_address
        self.start()

    def run(self):
        self.is_receiver = False
        tit = 0
        n = 0
        tapping_keys = {
            "01": "A",
            "1000": "B",
            "1010": "C",
            "100": "D",
            "0": "E",
            "0010": "F",
            "110": "G",
            "0000": "H",
            "00": "I",
            "0111": "J",
            "101": "K",
            "0100": "L",
            "11": "M",
            "10": "N",
            "111": "O",
            "0110": "P",
            "1101": "Q",
            "010": "R",
            "000": "S",
            "1": "T",
            "001": "U",
            "0001": "V",
            "011": "W",
            "1001": "X",
            "1011": "Y",
            "1100": "Z",
            "01111": "1",
            "00111": "2",
            "00011": "3",
            "00001": "4",
            "00000": "5",
            "10000": "6",
            "11000": "7",
            "11100": "8",
            "11110": "9",
            "11111": "0",
            "001100": "?",
            "101011": "!",
            "010101": ".",
            "110011": ",",
            "101010": ";",
            "111000": ":",
            "01010": "+",
            "100001": "-",
            "10010": "/",
            "10001": "="
        }
        try:
            while 1:
                data = self.socket.recv(1024)
                data = data.decode("utf-8")

                if not data:
                    break
                else:
                    if data == "receive":
                        with clients_lock:
                            self.is_receiver = True
                            clients.add(self.socket)

                    global in_mode
                    
                    global tap_dash

                    reply = "received:"
                    reply += data
                    print (data)
                    if data == "feed_paper_in":
                        reply += "feeding paper in"
                        lego_printer.manual_paper_feed(1)
                    elif data == "feed_paper_out":
                        reply += "feeding paper out"
                        lego_printer.manual_paper_feed(-1)
                    elif data == "stop_feed":
                        reply += "stop feeding paper"
                        lego_printer.stop_paper_feed()
                    elif data == "start_tipping":
                        in_mode = 1
                        tap_dash = ""
                    elif data == "end_tipping":
                        in_mode = 0
                        tap_dash = ""
                    elif data == "start_time" and in_mode == 1:
                        global timea
                        timea = time.time()
                    elif data == "end_time" and in_mode == 1:
                        global timeb
                        n = timeb
                        timeb = time.time()
                        #reply += str(n - timeb)
                        tit = timeb - timea    
                        reply += tap_dash
                        if (timeb - n) > 1.5:
                            if tap_dash in tapping_keys:
                                reply += tapping_keys[tap_dash]
                                tap_dash = ""
                        if tit < 0.14:
                            tap_dash += "0"
                        else:
                            tap_dash += "1"
                        reply += "hello"        
                    elif data == "feed_paper_in_inc":
                        lego_printer.manual_paper_feed_inc(1)
                    elif data == "feed_paper_out_inc":
                        lego_printer.manual_paper_feed_inc(-1)
                    elif data == "feed_paper_stop_inc":
                        lego_printer.manual_paper_feed_inc_stop()
                    elif data == "move_right":
                        lego_printer.manual_move_x(1)
                    elif data == "move_left":
                        lego_printer.manual_move_x(-1)
                    elif data == "move_stop":
                        reply += "bye"
                        lego_printer.manual_stop_x()
                    elif data == "switch_pen_pos":
                        lego_printer.switch_pen_pos()
                    elif data == "move_pen_up":
                        lego_printer.pen_up()
                    elif data == "move_pen_down":
                        lego_printer.pen_down()
                    elif data == "set_pen_position":
                        lego_printer.set_pen_position()
                    elif data == "switch_pen_state":
                        lego_printer.switch_pen_state()
                        print("pen state is", lego_printer.pen_is_adjustable)
                    elif data == "get_info":
                        reply += brick_info.get_info()
                    elif data == "calibrate":
                        lego_printer.calibrate()
                    elif data == "force_stop":
                        lego_printer.force_stop()
                    elif data.startswith("draw_maze") and lego_printer.is_busy is False:
                        Sound.speak('drawing maze')
                        lego_printer.stop_paper_feed()

                        maze_data = data.split('|')
                        rows = int(maze_data[1])
                        cols = int(maze_data[2])
                        grid_size = int(maze_data[3])

                        s, h, v = make_maze(rows, cols)
                        reply += s
                        draw_list = parse_maze(rows, cols, grid_size, s, h, v)
                        lego_printer.draw(list(draw_list))
                    elif data.startswith("draw_svg") and lego_printer.is_busy is False:
                        Sound.speak('drawing svg').wait()
                        svg_data = data.split('|')

                        Sound.speak('split svg').wait()

                        if os.path.isfile(svg_data[1]):
                            svg_path = svg_data[1]
                        else:
                            svg_path = "../" + svg_data[1]
                        
                        Sound.speak('checked file').wait()

                        reply += svg_path

                        svg_parser = SvgParser()
                        Sound.speak('check1').wait()
                        parser = xml.sax.make_parser()
                        Sound.speak('check2').wait()
                        parser.setFeature(xml.sax.handler.feature_namespaces, 0)
                        Sound.speak('check3').wait()
                        parser.setContentHandler(svg_parser)
                        Sound.speak('check4').wait()
                        parser.parse(svg_path)

                        Sound.speak('svg parsed').wait()

                        lego_printer.draw(list(svg_parser.draw_list))

                        Sound.speak('draw complete').wait()

                    with clients_lock:
                        if self.is_receiver is False:
                            self.socket.sendall(bytes(reply, 'UTF-8'))
                        for c in clients:
                            c.sendall(bytes(reply, 'UTF-8'))
        finally:
            with clients_lock:
                if self.is_receiver is True:
                    clients.remove(self.socket)
                self.socket.close()


socket.listen(5)
t2 = time.time()
t_sec = round(t2 - t1)
Sound.speak('Server Started in ' + str(t_sec) + ' seconds.').wait()

isActive = True
while isActive:
    clientsocket, address = socket.accept()
    Client(clientsocket, address)
