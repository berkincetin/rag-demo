from src.rag.resources import ResourceMonitor, ResourceSnapshot, read_gpu_vram_mb


class _FakeHttp:
    def __init__(self, payload=None, fail=False):
        self.payload = payload or {}
        self.fail = fail

    def get_json(self, url, timeout):
        if self.fail:
            raise ConnectionError("yok")
        return self.payload


def test_a_snapshot_reports_cpu_and_ram():
    monitor = ResourceMonitor()

    snapshot = monitor.sample()

    assert isinstance(snapshot, ResourceSnapshot)
    assert snapshot.cpu_percent is not None
    assert snapshot.ram_used_mb > 0


def test_gpu_is_none_when_ollama_is_unreachable():
    # "Ölçemedim" ile "GPU yok" farklı şeyler; ikisi de 0 değildir.
    assert read_gpu_vram_mb(http=_FakeHttp(fail=True)) is None


def test_a_model_loaded_on_cpu_reports_zero_vram():
    # size_vram == 0 gerçek bir ölçüm: model yüklü ama GPU kullanmıyor.
    payload = {"models": [{"name": "qwen", "size_vram": 0}]}

    assert read_gpu_vram_mb(http=_FakeHttp(payload)) == 0


def test_vram_is_converted_to_megabytes():
    payload = {"models": [{"name": "qwen", "size_vram": 2_147_483_648}]}

    assert read_gpu_vram_mb(http=_FakeHttp(payload)) == 2048


def test_no_loaded_model_means_nothing_to_measure():
    assert read_gpu_vram_mb(http=_FakeHttp({"models": []})) is None


def test_monitor_records_the_peak_not_the_average():
    monitor = ResourceMonitor()
    monitor._record(ResourceSnapshot(cpu_percent=10.0, ram_used_mb=1000, ram_total_mb=8000))
    monitor._record(ResourceSnapshot(cpu_percent=90.0, ram_used_mb=4000, ram_total_mb=8000))
    monitor._record(ResourceSnapshot(cpu_percent=20.0, ram_used_mb=1200, ram_total_mb=8000))

    assert monitor.peak_cpu_percent == 90.0
    assert monitor.peak_ram_mb == 4000


def test_monitor_stops_its_thread():
    # A monitor left running would leak a thread per question.
    monitor = ResourceMonitor(interval=0.01)
    monitor.start()
    monitor.stop()

    assert not monitor.is_running()


def test_peaks_are_none_before_any_sample():
    monitor = ResourceMonitor()

    assert monitor.peak_cpu_percent is None
    assert monitor.peak_ram_mb is None
