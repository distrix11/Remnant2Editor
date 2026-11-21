"""game_running(): tasklist output parsing (tasklist cuts image names to 25 characters)."""
import os, sys, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from r2save import storage

RUNNING = (
    "Remnant2-Win64-Shipping.e    12345 Console                    1  4,512,000 K\r\n"
)
NOT_RUNNING = "INFO: No tasks are running which match the specified criteria.\r\n"
NOT_RUNNING_RU = "ИНФОРМАЦИЯ: задачи, соответствующие заданным критериям, не найдены.\r\n"

assert storage._is_in_tasklist(RUNNING)
assert not storage._is_in_tasklist(NOT_RUNNING)
assert not storage._is_in_tasklist(NOT_RUNNING_RU)
assert not storage._is_in_tasklist("")
assert storage._is_in_tasklist(RUNNING.lower())

# end to end with a fake tasklist (pretend we are on Windows)
class R:  # noqa
    def __init__(self, out): self.stdout = out
real_run, real_platform = subprocess.run, sys.platform
try:
    sys.platform = "win32"
    subprocess.run = lambda *a, **k: R(RUNNING)
    assert storage.game_running() is True
    subprocess.run = lambda *a, **k: R(NOT_RUNNING)
    assert storage.game_running() is False
    def boom(*a, **k): raise OSError("no tasklist")
    subprocess.run = boom
    assert storage.game_running() is False
finally:
    subprocess.run, sys.platform = real_run, real_platform
print("game_running OK")
