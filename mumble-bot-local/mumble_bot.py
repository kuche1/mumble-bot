#! /usr/bin/env python3

# go to mumble and go trough the cert setup, then convert it
# openssl pkcs12 -in cert.p12 -out cert.crt -nodes
# ./mumble_bot.py --server 212.5.153.130 --name niggerbot2  --certfile cert/cert.crt EPIC\ FLUTE\ DROP\ ft.\ KFC\ AND\ WATERMELONS\ \[dbe1e6624979e0053c6b4c273c3fdb374f84c7d6\].mp4

# put the music in the folder called `music`

import pymumble_py3
import subprocess as sp
import audioop, time
import argparse
from pymumble_py3.callbacks import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED
import os

HERE = os.path.realpath(os.path.dirname(__file__))
FOLDER_MUSIC = os.path.join(HERE, 'music')

parser = argparse.ArgumentParser(description='get parameters.')

parser.add_argument('--server', '-s', required=True)
parser.add_argument('--port', '-P', type=int, default=64738)
parser.add_argument('--name', '-n', required=True)
parser.add_argument('--passwd', '-p', default="")
parser.add_argument('--certfile', '-c', required=True)
parser.add_argument('file')
args = parser.parse_args()

file = args.file
server = args.server
nick = args.name
passwd = args.passwd
port = args.port
certfile = args.certfile

play_queue = []
# skip_requested = False

def send_answer(source_message, answer):
    for id_ in source_message.channel_id:
        mumble.channels[id_].send_text_message(answer)

def compile_list_of_songs(folder=''):
    ans = ''
    for (_,fols,fils) in os.walk(os.path.join(FOLDER_MUSIC, folder)):
        for fil in fils:
            ans += f'<br/><br/>{os.path.join(folder, fil)}'
        for fol in fols:
            ans += compile_list_of_songs(os.path.join(folder, fol))
        break
    return ans

def message_received_handler(message):
    # global skip_requested

    msg = message.message
    print(f'msg:{msg}')

    match msg:
        case 'ls':
            ans = 'songs found:'
            ans += compile_list_of_songs()
            send_answer(message, ans)
        # case 'skip':
        #     skip_requested = True
        case _:
            idx = msg.find(' ')
            if idx == -1:
                return
            cmd = msg[:idx]
            arg = msg[idx+1:]
            match cmd:
                case 'play':
                    send_answer(message, f'trying to queue: {arg}')
                    play_queue.append(arg)
                case _:
                    #send_answer(message, f'unknown command: {cmd}')
                    pass

mumble = pymumble_py3.Mumble(server, nick, password=passwd, port=port, certfile=certfile)
mumble.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received_handler)
mumble.start()
mumble.is_ready()   #wait for Mumble to get ready to avoid errors after startup

while True:
    
    while not play_queue:
        time.sleep(1)
        
    file = play_queue.pop(0)
    file = os.path.join(FOLDER_MUSIC, file)

    print("start Processing")
    command = ["ffmpeg", "-i", file, "-acodec", "pcm_s16le", "-f", "s16le", "-ab", "192k", "-ac", "1", "-ar", "48000",  "-"]
    sound = sp.Popen(command, stdout=sp.PIPE, stderr=sp.DEVNULL, bufsize=1024)

    print("playing")
    while True:
        raw_music = sound.stdout.read(1024)
        if not raw_music:
            break

        # print('skipping')
        # if skip_requested:
        #     skip_requested = False
        #     break

        #vol = 0.1
        #mumble.sound_output.add_sound(audioop.mul(raw_music, 2, vol))   #adjusting volume
        mumble.sound_output.add_sound(raw_music)

    print("finished")
    while mumble.sound_output.get_buffer_size() > 0.5:  #
        time.sleep(0.01)

    print("sleep")
    time.sleep(2)
