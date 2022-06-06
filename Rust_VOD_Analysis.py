import json, os, re, requests, streamlink, subprocess, time, threading
import speech_recognition as sr

DISCORD_WEB_HOOK = ''
FFMPEG_FILE_PATH = '' # EXAMPLE: 'C:\\Users\\Diego\\Desktop\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe
TWITCH_AUTHORIZATION_KEY = ''
TWITCH_CLIENT_ID = ''
WIT_TOKEN = ''


class vod_downloader():
    
    def __init__(self, tw_api_url, tw_headers, tg_directory):
        self.tw_headers = tw_headers
        self.tw_api_url = tw_api_url
        self.tg_directory = tg_directory
        self.vods = []

    def clear_vod_list(self):
        self.vods = []

    def download_url(self, dl_tuple):
        c_file_name = os.path.join(self.tg_directory, dl_tuple[0])
        url = dl_tuple[1]
        
        try:
            ts_request = requests.get(dl_tuple[1], stream = True)
        except:
            return
        
        if ts_request.status_code == 200:
            with open(c_file_name, 'wb') as f:
                for data in ts_request:
                    f.write(data)
        return

    def get_active_vod_count(self):
        count = 0
        for vod in self.vods:
            if(vod['status'] == 'active'):
                count += 1
        return count

    
    def process_download_queue(self, max_num_sect, n_threads):
        ts_download_list = []
        

        for vod in self.vods:
            if vod['status'] != 'active':
                continue
            num_sections = min([vod['num_sections'], max_num_sect])
            num_processed = vod['num_processed']
                              
            for i in range(num_sections - num_processed):
                ts_download_list.append((vod['vod_id'] + '-' + str(i + num_processed) + '.ts',
                                         vod['m3u8_url'].replace('index-dvr.m3u8', str(i + num_processed) + '.ts')))

        for work_section in ([ts_download_list[i * n_threads:(i + 1) * n_threads]
                      for i in range((len(ts_download_list) + n_threads - 1) // n_threads )]):
            threads = []
            for i in range (0, len(work_section)):
                t = threading.Thread(target = self.download_url, args = (work_section[i], ))
                threads.append(t)
                t.start()
         
            for thrd in threads:
                thrd.join()
        return

    def set_processed_amt(self, vod_id, num_processed):
        for vod in self.vods:
            if(vod['vod_id'] == vod_id):
                vod['num_processed'] = num_processed
    
    def twitch_vod_scan(self):
        try:
            vod_request = requests.get(self.tw_api_url, headers = tw_headers)
        except:
            return

            
        if vod_request.json() is not None:
            for video in vod_request.json().get('data'):
                
                vod_url = video.get('url')
                vod_id = vod_url.split('/')[-1]


                if not any(vod['vod_id'] == vod_id for vod in self.vods):
                    vod_data = {'vod_id' : vod_id, 'vod_url' : vod_url,
                                'm3u8_url' : '', 'status' : 'active',
                                'num_processed' : 0, 'num_sections' : 0}
                    self.vods.append(vod_data)
        for vod in self.vods:
            if(vod['status'] == 'not understandable'):
               continue

            stream_url = vod['vod_url']
            
            try:
                m3u8_url = streamlink.streams(stream_url)['best'].url
            except:
                vod['status'] = 'm3u8 fail'
                continue

            vod['m3u8_url'] = m3u8_url
      
            try:
                m3u8_request = requests.get(vod['m3u8_url'])
            except:
                vod['status'] = 'm3u8 fail'
                continue

            vod['status'] = 'active'
            
    
            if(m3u8_request.status_code == 200):
                num_sections = m3u8_request.text.splitlines()[-2].split('.')[0]
                if('-' in num_sections):
                    num_sections = num_sections.split('-')[1]
                if('muted' == num_sections):
                    continue
                vod['num_sections'] = int(num_sections)


        print(self.vods)



def concatenate_ts_video_files(file_path):
    f_list = os.listdir(file_path)
    f_list.sort()
    crnt_base_name = ''
    concat_map = {}

    
    for f_name in f_list:
        if crnt_base_name != f_name.split('-')[0]:
            crnt_base_name = f_name.split('-')[0]
            concat_map[crnt_base_name] = 1
        else:
            concat_map[crnt_base_name] += 1

    f_list_pos = 0
    for f_name in concat_map:
        with open(os.path.join(file_path, f_name + '.ts'), 'wb') as out_file:
            for i in range (0, concat_map[f_name]):
                crnt_sect_file = os.path.join(file_path, f_list[i + f_list_pos])
                
                with open(crnt_sect_file, 'rb') as in_file:
                    out_file.write(in_file.read())
                os.remove(crnt_sect_file)
            f_list_pos += concat_map[f_name]
    return

def convert_files_ts_to_wav(file_path):
    for f_name in os.listdir(file_path):
        c_name_ts = os.path.join(file_path, f_name)
        c_name_wav = os.path.join(file_path, f_name.replace('.ts', '.wav'))
        subprocess.call(FFEMPG_FILE_PATH + '-i '
                        + c_name_ts + ' -ac 1 -ar 16000 ' + c_name_wav, shell = True)
        os.remove(f_name)
    return

def message_discord(w_hook_url, msg):
    msg_json = {'content' : msg}
    message_request = requests.post(w_hook_url, data = msg_json)
    return

def process_speech_wit(file_path, wit_token, wit_mtx):
    r = sr.Recognizer()
    while True:
        transcript = ''

        wit_mtx.acquire()
        f_list = os.listdir()
        for f_name in f_list:
            if('.wav' not in f_name):
               continue
            base_name = f_name.split('-')[0]
            section_num = int(f_name.split('-')[1].split('.')[0])
            c_f_name = os.path.join(file_path, f_name)

           
            with sr.AudioFile(c_f_name) as source:
                audio = r.record(source)  
            wit_mtx.release()
            try:
                transcript = r.recognize_wit(audio, key = wit_token)
            except sr.UnknownValueError:
                print("Wit could not understand audio")
            except sr.RequestError as e:
                print("Wit error; {0}".format(e))
            print(transcript)

            wit_mtx.acquire()    
            if(re.search('(one|two|three|four|five|six|seven|eight|nine|1|2|3|4|5|6|7|8|9)' +
                 '(one|two|three|four|five|six|seven|eight|nine|1|2|3|4|5|6|7|8|9)', transcript.lower())):

                msg = 'VOD_ID: ' + base_name + '\nTRANSCRIPT: ' + transcript + \
                          '\nAUDIO LENGTH: ' + '\nTIMESTAMP: ' + ''
                message_discord(d_web_hook_url, msg)
    
            os.remove(c_f_name)
        wit_mtx.release()    
        time.sleep(3)
        
    return 

def split_wav_audio_files(time_section):
    for fname in os.listdir():
        base_name = fname.split('.')[0]
        subprocess.call(FFMPEG_FILE_PATH + + ' -i '
                        + fname + ' -f segment -segment_time ' + str(time_section)+ ' '
                        + base_name + '-%01d.wav', shell = True)
        os.remove(fname)


if __name__ == "__main__":
    d_web_hook_url = DISCORD_WEB_HOOK
    prog_path      = os.path.join(os.getenv('APPDATA'), 'Twitch VOD Analysis')
    tw_api_url     =  'https://api.twitch.tv/helix/videos?game_id=263490&sort=time&period=day&first=20'
    tw_headers     = {'Authorization' : TWITCH_AUTHORIZATION,
                          'Client-Id' : TWITCH_CLIENT_ID}
    tw_main_url    = 'https://api.twitch.tv/helix/'
    wav_mtx        = threading.Lock()
    wit_token      = WIT_TOKEN
    wit_prc_thread = threading.Thread()
 


    print('\n\n\nInitializing Rust Bot\n\n')

    downloader = vod_downloader(tw_api_url, tw_headers, '.')
    
    if not os.path.isdir(prog_path):
        print('App Data Folder Created')
        os.mkdir(os.path.join(app_path, 'Twitch VOD Analysis'))
        


    print('Clearing App Data')
    os.chdir(prog_path)

    all_files = os.listdir()
    for f in all_files:
        os.remove(f)



    try:
       response = requests.get(tw_main_url, headers = tw_headers)
    except:
        print('Error Connecting to Twitch API')
        exit(0)


    print('Successfully connected to Twitch API')
    print('Current VOD Queue is:', str(downloader.get_active_vod_count()))

    wit_thread = threading.Thread(target = process_speech_wit, args = ('.',  wit_token, wav_mtx, ))
    wit_thread.start()
                    
    

    while True:
        print('Scanning for Rust VODS')
        downloader.twitch_vod_scan()
        
        print('Downloading video sections.')
        downloader.process_download_queue(30, 15)
        
        print('Concatenating video sections.')
        concatenate_ts_video_files('.')


        print('Converting video files to audio.')
        wav_mtx.acquire()
        convert_files_ts_to_wav('.')
        
        print('Processing Audio Files')
        split_wav_audio_files(20)
        wav_mtx.release()
        
        downloader.clear_vod_list()

            


