import os
import re
import json
import time
import requests
import threading
import subprocess
from tqdm import tqdm
from bs4 import BeautifulSoup


def set_request_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36",
        "referer": "https://www.bilibili.com",
    }


def get_playinfo(video_id, cookies):
    headers = set_request_headers()
    url = f"https://www.bilibili.com/video/{video_id}"
    try:
        resp = requests.get(url, headers=headers, cookies=cookies)
        resp.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        playinfo_matches = re.findall(r'<script>window.__playinfo__=(.*?)</script>', resp.text)
        if playinfo_matches:
            playinfo = playinfo_matches[0]
            playinfo_data = json.loads(playinfo)
            return resp, playinfo_data
        else:
            print("未找到播放信息。")
            return resp, None
    except requests.RequestException as e:
        print(f"网络请求失败: {e}")
        return None, None


def download_file(file_url, file_type, title, cookies, max_retries=3):
    headers = set_request_headers()

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url=file_url, headers=headers, cookies=cookies, stream=True)
            resp.raise_for_status()

            if resp.status_code == 200:
                print(f'文件名称：{title}.{file_type}')
                chunk_size = 1024
                file_size = int(resp.headers['content-length'])
                start_time = time.time()
                with open(f"{title}.{file_type}", mode='wb') as f, tqdm(
                        desc="下载中",
                        total=file_size,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                ) as pbar:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        f.write(chunk)
                        pbar.update(len(chunk))
                end_time = time.time()
                cost_time = end_time - start_time
                # print(f'\n累计耗时：{cost_time:0.2f} 秒')
                # print(f'下载速度：{file_size / cost_time:0.2f} B/s')
                break  # Exit the loop if download is successful
            else:
                print(f"文件下载失败。状态码: {resp.status_code}")
        except requests.RequestException as e:
            print(f"文件下载失败: {e}")
            if attempt < max_retries:
                print(f"重试下载，尝试次数: {attempt + 1}")
                time.sleep(2)  # Add a short delay before retrying
            else:
                print(f"达到最大重试次数 ({max_retries})，放弃下载。")


def organize_videos_by_quality(videos, accept_qualities, accept_description):
    quality_dict = {}
    for i, video in enumerate(videos, start=1):
        quality = accept_description[accept_qualities.index(video['id'])]
        if quality not in quality_dict:
            quality_dict[quality] = []

        quality_dict[quality].append({
            'index': i,
            'resolution': f"{video['width']}x{video['height']}",
            'frame_rate': video.get('frame_rate', 'Unknown Frame Rate'),
            'codecs': video.get('codecs', 'Unknown Codecs'),
            'video_url': video['base_url']
        })

    return quality_dict


def display_videos_by_quality(quality_dict):
    print("可选的视频：")
    for index, (quality, videos_info) in enumerate(quality_dict.items(), start=1):
        print(f"{index}. 视频清晰度: {quality}")
        """
        for video_info in videos_info:
            print(
                f"  --{video_info['index']}). 视频 {video_info['index']} - 分辨率: {video_info['resolution']}, "
                f"帧率: {video_info['frame_rate']}, Codecs: {video_info['codecs']}")
        """


def input_with_timeout(prompt, timeout, default_choice):
    print(prompt, end="", flush=True)
    result = None

    def input_thread():
        nonlocal result
        result = input()

    thread = threading.Thread(target=input_thread)
    thread.start()
    thread.join(timeout)

    if result is None:
        print(f"\n！--无用户输入，将默认选择第{default_choice}个视频清晰度")
        return default_choice
    else:
        return result


def choose_quality(playinfo_data):
    videos = playinfo_data['data']['dash']['video']
    accept_qualities = playinfo_data['data']['accept_quality']
    accept_description = playinfo_data['data']['accept_description']

    quality_dict = organize_videos_by_quality(videos, accept_qualities, accept_description)
    display_videos_by_quality(quality_dict)

    choice = input_with_timeout("请输入所需视频清晰度的序号（默认为1）：", 3, '1')

    try:
        choice = int(choice)
        if 1 <= choice <= len(quality_dict):
            selected_quality = quality_dict[list(quality_dict.keys())[choice - 1]]
            for video_info in selected_quality:
                print(
                    f"  {video_info['index']}). - 分辨率: {video_info['resolution']}, "
                    f"帧率: {video_info['frame_rate']}, Codecs: {video_info['codecs']}")
            return choice - 1, selected_quality
        else:
            print("无效的选择，将默认选择第 1 个视频清晰度")
            # 默认选择第一个清晰度
            selected_quality = quality_dict[list(quality_dict.keys())[0]]
            for video_info in selected_quality:
                print(
                    f"  {video_info['index']}). - 分辨率: {video_info['resolution']}, "
                    f"帧率: {video_info['frame_rate']}, Codecs: {video_info['codecs']}")
            return 0, selected_quality
    except ValueError:
        print("无效的输入，将默认选择第 1 个视频清晰度")
        # 默认选择第一个清晰度
        selected_quality = quality_dict[list(quality_dict.keys())[0]]
        for video_info in selected_quality:
            print(
                f"  {video_info['index']}). - 分辨率: {video_info['resolution']}, "
                f"帧率: {video_info['frame_rate']}, Codecs: {video_info['codecs']}")
        return 0, selected_quality


def extract_title(resp_text, playinfo_data, video_quality_index):
    soup = BeautifulSoup(resp_text, 'html.parser')
    up_name_tag = soup.find('a', class_='up-name')
    up_name = up_name_tag.text.strip() if up_name_tag else '未知上传者'

    title_matches = re.findall(r'title="(.*?)" class="video-title"', resp_text)
    title = title_matches[0].strip() if title_matches else 'video'

    quality = playinfo_data['data']['accept_description'][video_quality_index]
    return f"{up_name}_{title}_{quality}"


def extract_video_id(url):
    # 从URL中提取视频ID
    video_id_match = re.search(r'/video/([a-zA-Z0-9]+)', url)
    if video_id_match:
        return video_id_match.group(1)
    else:
        print("无效的 Bilibili 视频 URL.")
        exit()


def download_videos(selected_quality, resp, playinfo_data, video_quality_index, cookies):
    global downloaded_file_names
    downloaded_file_names = []

    def download_single_video(index, video_info):
        global downloaded_file_names
        video_url = video_info['video_url']
        v_title_index = extract_title(resp.text, playinfo_data, video_quality_index) + f"_{index}"
        downloaded_file_names.append(f"{v_title_index}.mp4")
        download_file(video_url, 'mp4', v_title_index, cookies)

    choice = input_with_timeout("请输入要下载的视频序号（输入回车跳过，默认为2）：", 3, '2')

    if choice.lower() == 'all':
        for index, video_info in enumerate(selected_quality, start=1):
            download_single_video(index, video_info)
    else:
        try:
            choice = int(choice)
            if 1 <= choice <= len(selected_quality):
                download_single_video(choice, selected_quality[choice - 1])
            else:
                print("无效的选择，将默认选择第 2 个视频编码")
                download_single_video(2, selected_quality[1])
        except ValueError:
            print("无效的输入，将默认选择第 2 个视频编码")
            download_single_video(2, selected_quality[1])


def choose_best_video(v_title):
    global downloaded_file_names
    current_directory = os.getcwd()
    largest_file = max(downloaded_file_names, key=os.path.getsize)
    for filename in downloaded_file_names:
        if filename == largest_file:
            new_file_path = os.path.join(current_directory, f"{v_title}.mp4")
            os.rename(filename, new_file_path)
        else:
            os.remove(os.path.join(current_directory, filename))


def combine_video_and_audio(video_path, audio_path, output_path):
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c", "copy",
        "-map", "0",
        "-map", "1",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd)


def main():
    url = input("Enter the Bilibili video URL: ")
    cookies = {
        "SESSDATA": "cf22fb7d%2C1723636963%2Ce5744*21",
    }

    video_id = extract_video_id(url)
    resp, playinfo_data = get_playinfo(video_id, cookies)

    if playinfo_data:
        video_quality_index, selected_quality = choose_quality(playinfo_data)
        v_title = extract_title(resp.text, playinfo_data, video_quality_index)

        download_videos(selected_quality, resp, playinfo_data, video_quality_index, cookies)

        a_title = extract_title(resp.text, playinfo_data, video_quality_index)
        audio_url = playinfo_data['data']['dash']['audio'][0]['base_url']
        download_file(audio_url, 'mp3', a_title, cookies)

        choose_best_video(v_title)
        combine_video_and_audio(f"{v_title}.mp4", f"{a_title}.mp3", f"{v_title}——合成.mp4")
        os.remove(f"{v_title}.mp4")
        os.remove(f"{a_title}.mp3")
        os.rename(os.path.join(os.getcwd(), f"{v_title}——合成.mp4"), os.path.join(os.getcwd(), f"{v_title}.mp4"))

        print("Done  !")


if __name__ == "__main__":
    main()
