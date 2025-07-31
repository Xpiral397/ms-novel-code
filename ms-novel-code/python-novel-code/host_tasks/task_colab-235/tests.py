# tests

import unittest
import threading
import gc
import weakref
import time

from main import WeatherData, _ObserverEntry

class TestWeatherDataObserverPattern(unittest.TestCase):
    def test_subscribe_non_callable(self):
        wd = WeatherData()
        with self.assertRaises(TypeError):
            wd.subscribe(123)

    def test_priority_ordering_and_ties(self):
        wd = WeatherData()
        calls = []
        # priority lower = earlier
        wd.subscribe(lambda t,h,p: calls.append('low'), priority=10)
        wd.subscribe(lambda t,h,p: calls.append('mid1'), priority=50)
        wd.subscribe(lambda t,h,p: calls.append('mid2'), priority=50)
        wd.subscribe(lambda t,h,p: calls.append('high'), priority=100)
        wd.set_measurements(1,1,1)
        self.assertEqual(calls, ['low','mid1','mid2','high'])

    def test_once_semantics_and_log(self):
        wd = WeatherData()
        calls = []
        token = wd.subscribe(lambda t,h,p: calls.append((t,h,p)), once=True)
        wd.set_measurements(2,2,2)
        wd.set_measurements(3,3,3)
        self.assertEqual(calls, [(2,2,2)])
        logs = wd.get_log()
        self.assertIn(f"unsubscribe:{token}", "".join(logs))

    def test_ttl_semantics_and_log(self):
        wd = WeatherData()
        calls = []
        token = wd.subscribe(lambda t,h,p: calls.append((t,h,p)), ttl=2)
        wd.set_measurements(10,10,10)
        wd.set_measurements(20,20,20)
        wd.set_measurements(30,30,30)
        self.assertEqual(calls, [(10,10,10),(20,20,20)])
        logs = wd.get_log()
        self.assertIn(f"unsubscribe:{token}", "".join(logs))

    def test_filter_fn(self):
        wd = WeatherData()
        calls = []
        wd.subscribe(lambda t,h,p: calls.append(p), filter_fn=lambda d: d[2]>50)
        wd.set_measurements(0,0,10)
        wd.set_measurements(0,0,60)
        self.assertEqual(calls, [60])

    def test_pause_resume(self):
        wd = WeatherData()
        calls = []
        wd.subscribe(lambda t,h,p: calls.append(p))
        wd.pause()
        wd.set_measurements(5,5,5)
        self.assertEqual(calls, [])
        wd.resume()
        # resume should NOT auto-notify per P/R
        self.assertEqual(calls, [])
        wd.set_measurements(6,6,6)
        self.assertEqual(calls, [6])

    def test_dead_observer_cleanup(self):
        wd = WeatherData()
        class Obs:
            def __init__(self):
                self.called = False
            def update(self, t,h,p):
                self.called = True
        obs = Obs()
        token = wd.subscribe(obs)
        ref = weakref.ref(obs)
        del obs
        gc.collect()
        wd.set_measurements(1,1,1)
        logs = wd.get_log()
        self.assertIn(f"dead:{token}", "".join(logs))
        # no exception

    def test_exception_isolation(self):
        wd = WeatherData()
        called = []
        wd.subscribe(lambda t,h,p: (_ for _ in ()).throw(ValueError("err")))
        wd.subscribe(lambda t,h,p: called.append(True))
        wd.set_measurements(1,1,1)
        self.assertEqual(called,[True])
        logs = wd.get_log()
        self.assertTrue(any("error:" in e for e in logs))

    def test_get_metrics(self):
        wd = WeatherData()
        wd.subscribe(lambda t,h,p: None)
        wd.set_measurements(1,1,1)
        m = wd.get_metrics()
        self.assertTrue(isinstance(m, dict))
        # average > 0
        self.assertTrue(all(v>=0 for v in m.values()))

    def test_unsubscribe_no_error(self):
        wd = WeatherData()
        wd.unsubscribe(999)
        # no exception, no log for unknown token
        logs = wd.get_log()
        self.assertNotIn("unsubscribe:999", "".join(logs))

    def test_concurrent_operations(self):
        wd = WeatherData()
        stop = threading.Event()
        errors = []
        def spam():
            while not stop.is_set():
                try:
                    wd.set_measurements(1,2,3)
                    wd.subscribe(lambda t,h,p: None)
                except Exception as e:
                    errors.append(e)
        t = threading.Thread(target=spam)
        t.start()
        time.sleep(0.1)
        stop.set()
        t.join()
        self.assertFalse(errors)

if __name__ == '__main__':
    unittest.main()
