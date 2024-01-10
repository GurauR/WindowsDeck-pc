from cx_Freeze import setup, Executable

base = None

executables = [Executable("main.py", base=base)]

packages = ["socket", "subprocess", "pyaudio", "re", "sounddevice", "ctypes", "comtypes", "pycaw", "screen_brightness_control", "win32api", "win32con"]
options = {
    'build_exe': {
        'packages':packages,
    },
}

setup(
    name = "WindowsDeck",
    options = options,
    version = "1.0",
    description = 'Control windows using android',
    executables = executables
)