#! /usr/bin/env python3

# OLD WAY:
#   go to mumble and go trough the cert setup
# NEW WAY: https://stackoverflow.com/questions/21141215/creating-a-p12-file
    # openssl genrsa -out key.pem 2048
    # openssl req -new -sha256 -key key.pem -out csr.csr
    # openssl req -x509 -sha256 -days 365 -key key.pem -in csr.csr -out certificate.pem
    # openssl pkcs12 -export -out client-identity.p12 -inkey key.pem -in certificate.pem
# openssl pkcs12 -in cert.p12 -out cert.crt -nodes
# ./mumble_bot.py --server 192.168.0.101 --name sexbot --certfile certs/cert.crt

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

RADIO_NAME = 'radio jungl'
FOLDER_MUSIC = '/var/tmp/mumble-bot-music'
MESSAGE_MAXLEN = 4500

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

class Queue_item:
    def __init__(s, original_message, audio_file):
        s.audio_file = audio_file
        s.original_message = original_message

        s.sender = mumble.users[original_message.actor]
    
    def send_playing_message(s):
        ans = f'{RADIO_NAME}<br>'
        ans += f'slu6a6 `{s.audio_file}`<br>'
        user = s.sender['name']
        ans += f'specialen pozdrav ot `{user}`'
        send_answer(s.original_message, ans)

def send_answer(source_message, answer):
    if len(answer) > MESSAGE_MAXLEN:
        send_answer(source_message, answer[:MESSAGE_MAXLEN])
        send_answer(source_message, answer[MESSAGE_MAXLEN:])
        return

    for id_ in source_message.channel_id:
        mumble.channels[id_].send_text_message(answer)

def compile_list_of_songs(folder='', pattern=None):
    ans = ''
    for (_,fols,fils) in os.walk(os.path.join(FOLDER_MUSIC, folder)):
        for fil in fils:
            path = os.path.join(folder, fil)
            if pattern != None:
                if re.match(pattern, path) == None:
                    continue
            # ans += f'<br/><br/>{path}'
            ans += f'<br/>{path}'
        for fol in fols:
            ans += compile_list_of_songs(os.path.join(folder, fol))
        break
    return ans

def message_received_handler(message):
    global skip_requested
    global reverse
    global bufsize_mult
    global currently_playing

    msg = message.message
    print(f'{msg=}')

    match msg:

        case 'kakvo slu6am' | 'koi pedal pusna tva':
            currently_playing.send_playing_message()

        case 'ls':
            ans = 'songs found:'
            ans += compile_list_of_songs()
            send_answer(message, ans)

        # case 'show queue':
        #     ans = ''
        #     for item in song_queue: # this can fail if the list gets modified but it doesn't matter if we crash
        #         ...

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
                        'outtmpl': f'{FOLDER_MUSIC}/%(title)s.%(ext)s',
                        'restrictfilenames': True, # just keep this as it is, otherwise mumble might butcher the file name (example: some whitespace)
                        'noplaylist': True,
                        'nocheckcertificate': True,
                        'ignoreerrors': False,
                        'logtostderr': False,
                        'quiet': True,
                        # 'quiet': False,
                        'no_warnings': True,
                        'default_search': 'auto',
                        'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
                    }

                    ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

                    try:
                        resulting_file = ytdl.prepare_filename(ytdl.extract_info(video_link, download=False))
                        resulting_file = resulting_file[len(FOLDER_MUSIC):]
                        if resulting_file.startswith('/'):
                            resulting_file = resulting_file[1:]
                    except:
                        resulting_file = None

                    send_answer(message, f'starting download of `{video_link}` -> `{resulting_file}`')
                    try:
                        ytdl.download(video_link)
                    except:
                        send_answer(message, f'ERROR `{video_link}`')
                        raise
                    else:
                        send_answer(message, f'finished download of `{video_link}` -> `{resulting_file}`')


                case 'play':
                    send_answer(message, f'queued `{arg}`')
                    item = Queue_item(message, arg)
                    play_queue.append(item)

                case 're':
                    pattern = arg

                    ans = 'result:'
                    ans += compile_list_of_songs(pattern=pattern)

                    send_answer(message, ans)

                case _:
                    #send_answer(message, f'unknown command: {cmd}')
                    pass

currently_playing = None

mumble = pymumble_py3.Mumble(server, nick, password=passwd, port=port, certfile=certfile)
mumble.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received_handler)
mumble.start()
mumble.is_ready() # wait for Mumble to get ready to avoid errors after startup

while True:
    
    while not play_queue:
        time.sleep(1)
        
    item = play_queue.pop(0)
    currently_playing = item

    item.send_playing_message()

    file = item.audio_file
    file = os.path.join(FOLDER_MUSIC, file)

    print(f"processing `{file}`")

    command = ["ffmpeg", "-i", file, "-acodec", "pcm_s16le", "-f", "s16le", "-ab", "192k", "-ac", "1", "-ar", "48000",  "-"]
    #command = ['ffplay', file]
    #command = ['ffmpeg', '-i', file, '-f', 's16le']
    sound = sp.Popen(command, stdout=sp.PIPE, stderr=sp.DEVNULL, bufsize=bufsize)

    print("playing")

    skip_requested = False

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
