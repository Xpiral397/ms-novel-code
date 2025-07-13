# tests
import unittest
import threading
import gc
import weakref
from main import Publisher, SubscriberError


class TestPublisherCore(unittest.TestCase):
    def test_subscribe_non_callable(self):
        pub = Publisher()
        with self.assertRaises(TypeError):
            pub.subscribe(123)

    def test_broadcast_no_subscribers(self):
        pub = Publisher()
        self.assertEqual(pub.broadcast("x"), [])

    def test_priority_ordering_and_ties(self):
        pub = Publisher()
        results = []
        pub.subscribe(lambda m: results.append(("low", m)), priority=50)
        pub.subscribe(lambda m: results.append(("mid1", m)), priority=100)
        pub.subscribe(lambda m: results.append(("mid2", m)), priority=100)
        pub.subscribe(lambda m: results.append(("high", m)), priority=150)
        out = pub.broadcast("msg")
        self.assertEqual([r[0] for r in results], ["low", "mid1", "mid2", "high"])
        self.assertEqual(out, [None, None, None, None])

    def test_once_semantics_and_log(self):
        pub = Publisher()
        calls = []
        token = pub.subscribe(lambda m: calls.append(m), once=True)
        pub.broadcast(1)
        pub.broadcast(2)
        # only first call
        self.assertEqual(calls, [1])
        # automatic unsubscribe must be logged
        ops = [e.split(":", 1)[1] for e in pub.audit_log]
        self.assertIn(f"unsubscribe:{token}", ops)

    def test_ttl_semantics_and_log(self):
        pub = Publisher()
        calls = []
        token = pub.subscribe(lambda m: calls.append(m), ttl=2)
        pub.broadcast("a")
        pub.broadcast("b")
        pub.broadcast("c")
        # only first two calls
        self.assertEqual(calls, ["a", "b"])
        # automatic unsubscribe must be logged
        ops = [e.split(":", 1)[1] for e in pub.audit_log]
        self.assertIn(f"unsubscribe:{token}", ops)

    def test_filter_predicate(self):
        pub = Publisher()
        calls = []
        pub.subscribe(lambda m: calls.append(m), filter=lambda x: x % 2 == 0)
        pub.broadcast(1)
        pub.broadcast(2)
        pub.broadcast(3)
        pub.broadcast(4)
        self.assertEqual(calls, [2, 4])

    def test_return_value_propagation(self):
        pub = Publisher()
        pub.subscribe(lambda m: m * 2, priority=20)
        pub.subscribe(lambda m: str(m), priority=10)
        # lower priority value first
        out = pub.broadcast(3)
        self.assertEqual(out, ["3", 6])

    def test_unsubscribe_unknown_no_error(self):
        pub = Publisher()
        pub.unsubscribe(999)  # no-op
        self.assertEqual(pub.audit_log, [])

    def test_reset_idempotent_and_log(self):
        pub = Publisher()
        pub.subscribe(lambda m: None)
        pub.reset()
        ops = [e.split(":", 1)[1] for e in pub.audit_log]
        self.assertIn("reset", ops)
        before = len(pub.audit_log)
        pub.reset()
        self.assertEqual(len(pub.audit_log), before)

    def test_overflow_max_size(self):
        pub = Publisher(max_size=1)
        pub.subscribe(lambda m: None)
        with self.assertRaises(OverflowError):
            pub.subscribe(lambda m: None)

    def test_temporary_context_manager(self):
        pub = Publisher()
        calls = []
        def fn(m): calls.append(m)
        with pub.temporary(fn, once=True):
            pub.broadcast("x")
        pub.broadcast("y")
        self.assertEqual(calls, ["x"])

    def test_weakref_cleanup_for_callable_object(self):
        class A:
            def __call__(self, m): return True
        obj = A()
        pub = Publisher()
        token = pub.subscribe(obj)
        ref = weakref.ref(obj)
        del obj
        gc.collect()
        out = pub.broadcast("z")
        self.assertEqual(out, [])
        self.assertIsNone(ref())

    def test_weakref_cleanup_for_bound_method(self):
        class B:
            def method(self, m): return m
        b = B()
        pub = Publisher()
        token = pub.subscribe(b.method)
        ref = weakref.ref(b)
        del b
        gc.collect()
        out = pub.broadcast("hello")
        self.assertEqual(out, [])
        self.assertIsNone(ref())

    def test_exception_aggregation(self):
        pub = Publisher()
        pub.subscribe(lambda m: (_ for _ in ()).throw(ValueError("err1")))
        called = []
        pub.subscribe(lambda m: called.append("ok"))
        with self.assertRaises(SubscriberError) as cm:
            pub.broadcast("x")
        # second subscriber was still called
        self.assertEqual(called, ["ok"])
        exc = cm.exception
        self.assertEqual(len(exc.exc_info), 1)

    def test_audit_log_sequence(self):
        pub = Publisher()
        t1 = pub.subscribe(lambda m: None)
        t2 = pub.subscribe(lambda m: None)
        pub.unsubscribe(t1)
        pub.reset()
        ops = [e.split(":", 1)[1] for e in pub.audit_log]
        expected = [f"subscribe:{t1}", f"subscribe:{t2}",
                    f"unsubscribe:{t1}", "reset"]
        self.assertEqual(ops, expected)


class TestPublisherConcurrency(unittest.TestCase):
    def test_concurrent_broadcast_and_reset(self):
        pub = Publisher()
        pub.subscribe(lambda m: None)
        errors = []
        stop = threading.Event()

        def spam_broadcast():
            while not stop.is_set():
                try:
                    pub.broadcast("h")
                except Exception as e:
                    errors.append(e)

        t = threading.Thread(target=spam_broadcast)
        t.start()
        threading.Timer(0.05, pub.reset).start()
        threading.Timer(0.1, stop.set).start()
        t.join(1)
        self.assertFalse(errors)
        self.assertEqual(pub.broadcast("x"), [])


if __name__ == "__main__":
    unittest.main(argv=[""], exit=False)
