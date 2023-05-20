#! /usr/bin/env python3

# go to mumble and go trough the cert setup, then convert it
# openssl pkcs12 -in cert.p12 -out cert.crt -nodes
# ./mumble_bot.py --server 192.168.0.101 --name sexbot --certfile mumble-cert/cert.crt

# put the music in the folder called `music`

import pymumble_py3 # pip3 install pymumble
import subprocess as sp
import audioop, time
import argparse
from pymumble_py3.callbacks import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED
import os
import yt_dlp #
import re
import random

HERE = os.path.realpath(os.path.dirname(__file__))
FOLDER_MUSIC = os.path.join(HERE, 'music')

parser = argparse.ArgumentParser(description='mumble bot')

parser.add_argument('--server', '-s', required=True)
parser.add_argument('--port', '-P', type=int, default=64738)
parser.add_argument('--name', '-n', required=True)
parser.add_argument('--passwd', '-p', default="")
parser.add_argument('--certfile', '-c', required=True)
args = parser.parse_args()

server = args.server
nick = args.name
passwd = args.passwd
port = args.port
certfile = args.certfile

play_queue = []
skip_requested = False
volume = 1.0
bufsize = 1024
bufsize_mult = 1
reverse = False

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
    global skip_requested
    global reverse
    global bufsize_mult

    msg = message.message
    print(f'{msg=}')

    match msg:

        case 'ls':
            ans = 'songs found:'
            ans += compile_list_of_songs()
            send_answer(message, ans)

        case 'reverse':
            reverse = not reverse

        case 'skip':
            send_answer(message, 'skip requested')
            skip_requested = True

        case _:

            idx = msg.find(' ')
            if idx == -1:
                return
            cmd = msg[:idx]
            arg = msg[idx+1:]

            match cmd:

                case 'bufsize_mult':
                    mult = int(arg)
                    assert mult >= 1
                    bufsize_mult = mult

                # case 'download':
                #     video_link = arg
                    
                #     pattern = re.compile('<.*?>')
                #     video_link = re.sub(pattern, '', video_link)
                #     print(f'{video_link=}')

                #     ytdl_format_options = {
                #         'format': 'bestaudio/best',
                #         'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                #         'restrictfilenames': True,
                #         'noplaylist': True,
                #         'nocheckcertificate': True,
                #         'ignoreerrors': False,
                #         'logtostderr': False,
                #         'quiet': True,
                #         'no_warnings': True,
                #         'default_search': 'auto',
                #         'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
                #     }
                #     ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
                #     video_data = ytdl.extract_info(video_link, download=False)

                #     # ffmpeg_options = {
                #     #     'options': '-vn'
                #     # }
                #     # url = video_data['url']
                #     # print(f'now playing music from URL: {url}')
                #     # #source = discord.FFmpegPCMAudio(url, **ffmpeg_options)

                #     url = video_data['url']

                #     play_queue.append(url)

                case 'download':
                    video_link = arg
                    pattern = re.compile('<.*?>')
                    video_link = re.sub(pattern, '', video_link)
                    
                    ytdl_format_options = {
                        'format': 'bestaudio/best',
                        #'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                        'outtmpl': 'music/%(title)s.%(ext)s',
                        'restrictfilenames': True,
                        'noplaylist': True,
                        'nocheckcertificate': True,
                        'ignoreerrors': False,
                        'logtostderr': False,
                        'quiet': True,
                        'no_warnings': True,
                        'default_search': 'auto',
                        'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
                    }

                    ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
                    send_answer(message, f'starting download of `{video_link}`')
                    ytdl.download(video_link)
                    send_answer(message, f'finished download of `{video_link}`')

                case 'play':
                    send_answer(message, f'queued `{arg}`')
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

    print("processing")

    command = ["ffmpeg", "-i", file, "-acodec", "pcm_s16le", "-f", "s16le", "-ab", "192k", "-ac", "1", "-ar", "48000",  "-"]
    #command = ['ffplay', file]
    #command = ['ffmpeg', '-i', file, '-f', 's16le']
    sound = sp.Popen(command, stdout=sp.PIPE, stderr=sp.DEVNULL, bufsize=bufsize)

    print("playing")

    while True:
        raw_music = sound.stdout.read(bufsize * bufsize_mult)
        if not raw_music:
            break

        if skip_requested:
            break

        if reverse:
            raw_music = audioop.reverse(raw_music, 2)
        
        # volume += random.uniform(-0.18, 0.18)
        raw_music = audioop.mul(raw_music, 2, volume)

        mumble.sound_output.add_sound(raw_music)

        target_buffer = 0.8
        current_buffer = mumble.sound_output.get_buffer_size()
        diff = current_buffer - target_buffer
        if diff > 0:
            time.sleep(diff)

    print('killing pipe')

    sound.terminate()
    sound.kill()

    print("finished")

    skip_requested = False
