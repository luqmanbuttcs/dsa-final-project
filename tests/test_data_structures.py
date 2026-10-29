import unittest

from data_structures import DoublyLinkedList, Queue, Stack


class StackTests(unittest.TestCase):
    def test_lifo_order(self):
        stack = Stack([1, 2])
        stack.push(3)
        self.assertEqual(stack.peek(), 3)
        self.assertEqual(stack.pop(), 3)
        self.assertEqual(stack.pop(), 2)
        self.assertEqual(stack.to_list(), [1])

    def test_split_suffix_and_splice(self):
        original = Stack(["A", "B", "C", "D"])
        suffix = original.split_off(2)
        self.assertEqual(original.to_list(), ["A", "B"])
        self.assertEqual(suffix.to_list(), ["C", "D"])
        original.extend_stack(suffix)
        self.assertEqual(original.to_list(), ["A", "B", "C", "D"])
        self.assertTrue(suffix.is_empty())

    def test_empty_stack_pop_raises(self):
        with self.assertRaises(IndexError):
            Stack().pop()


class QueueTests(unittest.TestCase):
    def test_fifo_order(self):
        queue = Queue([1, 2])
        queue.enqueue(3)
        self.assertEqual(queue.dequeue(), 1)
        self.assertEqual(queue.dequeue(), 2)
        self.assertEqual(queue.dequeue(), 3)
        self.assertTrue(queue.is_empty())

    def test_empty_queue_dequeue_raises(self):
        with self.assertRaises(IndexError):
            Queue().dequeue()


class DoublyLinkedListTests(unittest.TestCase):
    def test_remove_from_both_ends(self):
        linked = DoublyLinkedList([2, 3])
        linked.appendleft(1)
        linked.append(4)
        self.assertEqual(linked.popleft(), 1)
        self.assertEqual(linked.pop(), 4)
        self.assertEqual(linked.to_list(), [2, 3])

    def test_split_at_zero_and_end(self):
        linked = DoublyLinkedList([1, 2, 3])
        empty = linked.split_off(len(linked))
        self.assertEqual(empty.to_list(), [])
        suffix = linked.split_off(0)
        self.assertEqual(linked.to_list(), [])
        self.assertEqual(suffix.to_list(), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
