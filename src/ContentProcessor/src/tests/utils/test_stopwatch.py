from libs.utils.stopwatch import Stopwatch


def test_stopwatch_initial_state():
    stopwatch = Stopwatch()
    assert stopwatch.elapsed == 0
    assert stopwatch.elapsed_string == "0:00:00"
    assert not stopwatch.is_running


def test_stopwatch_start(mocker):
    mocker.patch("time.perf_counter", return_value=100.0)
    stopwatch = Stopwatch()
    stopwatch.start()
    assert stopwatch.is_running
    assert stopwatch.start_time == 100.0


def test_stopwatch_stop(mocker):
    mocker.patch("time.perf_counter", side_effect=[100.0, 105.0])
    stopwatch = Stopwatch()
    stopwatch.start()
    stopwatch.stop()
    assert not stopwatch.is_running
    assert stopwatch.elapsed == 5.0
    assert stopwatch.elapsed_string == "00:00:05.000"


def test_stopwatch_reset():
    stopwatch = Stopwatch()
    stopwatch.start()
    stopwatch.stop()
    stopwatch.reset()
    assert stopwatch.elapsed == 0
    assert not stopwatch.is_running


def test_stopwatch_context_manager(mocker):
    mocker.patch("time.perf_counter", side_effect=[100.0, 105.0])
    with Stopwatch() as stopwatch:
        assert stopwatch.is_running
    assert not stopwatch.is_running
    assert stopwatch.elapsed == 5.0
    assert stopwatch.elapsed_string == "00:00:05.000"


def test_format_elapsed_time():
    stopwatch = Stopwatch()
    formatted_time = stopwatch._format_elapsed_time(3661.123)
    assert formatted_time == "01:01:01.123"
