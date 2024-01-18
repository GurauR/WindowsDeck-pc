import socket
import subprocess
import pyaudio
import re

import sounddevice as sd
import ctypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

import screen_brightness_control as sbc
import win32api
from win32con import VK_MEDIA_PLAY_PAUSE, VK_MEDIA_PREV_TRACK, VK_MEDIA_NEXT_TRACK, KEYEVENTF_EXTENDEDKEY

# get the brightness

brightness = sbc.get_brightness()

input_string = "< 3 Speakers (Realtek(R) Audio), MME (0 in, 2 out)"

# Define a regular expression pattern to match the desired text
pattern = re.compile(r'\d+\s*([^()]+)')

currentDevice = ""

device = str(sd.query_devices())
ll = device.split("\n")
for j in ll:
    if "<" in j:
        matches = pattern.findall(j)

        # Output the result
        if matches:
            currentDevice = matches[0]
        else:
            print("No match found")

audio = pyaudio.PyAudio()

info = audio.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
devices = []
for i in range(0, numdevices):
    device_info = audio.get_device_info_by_host_api_device_index(0, i)

    if device_info.get('maxOutputChannels') > 0:
        device_name = device_info.get('name')

        if "Microsoft Sound Mapper" not in device_name:
            # Use re.sub to replace the matched pattern with an empty string
            cleaned_device_name = re.sub(" \(.*", "", device_name)
            devices.append(cleaned_device_name.strip())

print(devices)
HOST = '0.0.0.0'
PORT = 8080

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"Server listening on {HOST}:{PORT}")


def switch_to_next_device():
    global devices, currentDevice

    if not devices:
        print("No audio output devices available.")
        return

    current_index = devices.index(currentDevice.strip())
    next_index = (current_index + 1) % len(devices)
    currentDevice = devices[next_index]
    sd.default.device = [2, 3]

    print(f"Switching to the next output device: {currentDevice}")


def get_master_volume():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    # Get the current volume level (0.0 to 1.0)
    current_volume = volume.GetMasterVolumeLevelScalar()

    return current_volume


def get_ip():
    ipconfig = subprocess.run(
        'ipconfig',
        capture_output=True, text=True)

    return ipconfig


def get_hostname():
    hostname = subprocess.run(
        'hostname',
        capture_output=True, text=True).stdout.replace("\n", "")

    return hostname


def is_audio_muted():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    # Check if the audio is muted
    muted = volume.GetMute()

    return muted


if __name__ == "__main__":
    master_volume = get_master_volume()
    muted = is_audio_muted()
    ipconfig = get_ip()
    hostname = get_hostname()

    print(f"Master Volume: {master_volume}")
    print(f"Is Muted: {muted}")
    ipv4_addresses = re.findall(r'IPv4 Address\. .+? : (\d+\.\d+\.\d+\.\d+)', ipconfig.stdout)
    print(f"IpConfig: {ipv4_addresses}")
    print(f"HostName: {hostname}")

while True:
    client_socket, addr = server_socket.accept()
    print(f"Connection from {addr}")

    data = client_socket.recv(1024).decode('utf-8')

    if not data:
        break

    try:
        output = ""
        # Execute the received nircmd command
        if 'mutesysvolume' in data:
            result = subprocess.run(
                '.\\utility\\nircmd-x64\\nircmd.exe' + data.replace("nircmd", "").replace("\n", ""),
                capture_output=True, text=True)
            output = str(is_audio_muted())

        elif 'setdefaultsounddevice' in data:

            current_index = devices.index(currentDevice.strip())

            next_index = (current_index + 1) % len(devices)

            next_device = devices[next_index]

            # Use nircmd to set the default sound device to the next device

            result = subprocess.run(
                '.\\utility\\nircmd-x64\\nircmd.exe' + f' setdefaultsounddevice "{next_device}"',
                capture_output=True, text=True)

            # Update the current device
            currentDevice = next_device

            output = currentDevice.strip()

        elif 'setsysvolume' in data:

            result = subprocess.run('.\\utility\\nircmd-x64\\nircmd.exe' + data.replace("nircmd", ""),
                                    capture_output=True, text=True)
            output = ""

        elif 'isMuted' in data:

            muted = is_audio_muted()
            output = str(muted)

        elif 'deviceVolume' in data:

            volume = get_master_volume()
            output = str(volume)

        elif 'currentDevice' in data:

            output = currentDevice

        elif 'currentBrightness' in data:

            brightness = sbc.get_brightness()
            output = str(brightness[0] / 100)

        elif 'playMedia' in data:
            win32api.keybd_event(VK_MEDIA_PLAY_PAUSE, 0)

        elif 'pauseMedia' in data:
            win32api.keybd_event(VK_MEDIA_PLAY_PAUSE, 0)

        elif 'nextTrack' in data:

            win32api.keybd_event(VK_MEDIA_NEXT_TRACK, 0, KEYEVENTF_EXTENDEDKEY, 0)

        elif 'prevTrack' in data:

            win32api.keybd_event(VK_MEDIA_PREV_TRACK, 0, KEYEVENTF_EXTENDEDKEY, 0)

        elif 'hostname' in data:

            output = get_hostname()

        elif '/SetValue' in data:

            result = subprocess.run(
                '.\\utility\\controlmymonitor\\ControlMyMonitor.exe' + data.replace(
                    "ControlMyMonitor.exe", "").replace("\n", ""), capture_output=True, text=True)
            output = ""

        else:
            result = subprocess.run(data)
            output = ""
        # Send the result back to the client
        client_socket.send(output.encode('utf-8'))
    except Exception as e:
        print(f"Error executing command: {e}")
        client_socket.send(f"Error: {e}".encode('utf-8'))

    client_socket.close()

server_socket.close()
