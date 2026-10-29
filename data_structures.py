"""Small, testable data structures used by the game engine.

The Stack is backed by the custom DoublyLinkedList. Tableau sequence moves can
therefore detach and splice a suffix without maintaining duplicate pile data.
"""
from __future__ import annotations

from typing import Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")


class Node(Generic[T]):
    __slots__ = ("data", "next", "prev")

    def __init__(self, data: T) -> None:
        self.data = data
        self.next: Node[T] | None = None
        self.prev: Node[T] | None = None


class DoublyLinkedList(Generic[T]):
    def __init__(self, values: Iterable[T] = ()) -> None:
        self.head: Node[T] | None = None
        self.tail: Node[T] | None = None
        self._size = 0
        for value in values:
            self.append(value)

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def __iter__(self) -> Iterator[T]:
        node = self.head
        while node is not None:
            yield node.data
            node = node.next

    def append(self, value: T) -> None:
        node = Node(value)
        if self.tail is None:
            self.head = self.tail = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node
        self._size += 1

    def appendleft(self, value: T) -> None:
        node = Node(value)
        if self.head is None:
            self.head = self.tail = node
        else:
            node.next = self.head
            self.head.prev = node
            self.head = node
        self._size += 1

    def node_at(self, index: int) -> Node[T]:
        if index < 0 or index >= self._size:
            raise IndexError("linked-list index out of range")
        if index <= self._size // 2:
            node = self.head
            for _ in range(index):
                assert node is not None
                node = node.next
        else:
            node = self.tail
            for _ in range(self._size - index - 1):
                assert node is not None
                node = node.prev
        assert node is not None
        return node

    def get(self, index: int) -> T:
        return self.node_at(index).data

    def pop(self) -> T:
        if self.tail is None:
            raise IndexError("pop from empty linked list")
        node = self.tail
        self.tail = node.prev
        if self.tail is None:
            self.head = None
        else:
            self.tail.next = None
        self._size -= 1
        node.prev = None
        node.next = None
        return node.data

    def popleft(self) -> T:
        if self.head is None:
            raise IndexError("pop from empty linked list")
        node = self.head
        self.head = node.next
        if self.head is None:
            self.tail = None
        else:
            self.head.prev = None
        self._size -= 1
        node.prev = None
        node.next = None
        return node.data

    def remove_at(self, index: int) -> T:
        node = self.node_at(index)
        if node.prev is None:
            return self.popleft()
        if node.next is None:
            return self.pop()
        node.prev.next = node.next
        node.next.prev = node.prev
        self._size -= 1
        node.prev = node.next = None
        return node.data

    def split_off(self, index: int) -> "DoublyLinkedList[T]":
        """Detach and return the suffix starting at index."""
        if index < 0 or index > self._size:
            raise IndexError("split index out of range")
        suffix: DoublyLinkedList[T] = DoublyLinkedList()
        if index == self._size:
            return suffix
        if index == 0:
            suffix.head, suffix.tail, suffix._size = self.head, self.tail, self._size
            self.head = self.tail = None
            self._size = 0
            return suffix
        first = self.node_at(index)
        before = first.prev
        assert before is not None
        suffix.head, suffix.tail = first, self.tail
        suffix._size = self._size - index
        before.next = None
        first.prev = None
        self.tail = before
        self._size = index
        return suffix

    def extend(self, other: "DoublyLinkedList[T]") -> None:
        """Splice other onto this list and leave other empty."""
        if not other:
            return
        if not self:
            self.head, self.tail, self._size = other.head, other.tail, other._size
        else:
            assert self.tail is not None and other.head is not None
            self.tail.next = other.head
            other.head.prev = self.tail
            self.tail = other.tail
            self._size += other._size
        other.head = other.tail = None
        other._size = 0

    def to_list(self) -> list[T]:
        return list(iter(self))

    def clear(self) -> None:
        self.head = self.tail = None
        self._size = 0


class Stack(Generic[T]):
    """LIFO stack. Iteration and to_list return bottom-to-top order."""

    def __init__(self, values: Iterable[T] = ()) -> None:
        self._items: DoublyLinkedList[T] = DoublyLinkedList(values)

    @classmethod
    def from_list(cls, values: Iterable[T]) -> "Stack[T]":
        return cls(values)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def is_empty(self) -> bool:
        return not self._items

    def push(self, value: T) -> None:
        self._items.append(value)

    def pop(self) -> T:
        return self._items.pop()

    def peek(self) -> T | None:
        return self._items.tail.data if self._items.tail is not None else None

    def clear(self) -> None:
        self._items.clear()

    def to_list(self) -> list[T]:
        return self._items.to_list()

    def split_off(self, index: int) -> "Stack[T]":
        result: Stack[T] = Stack()
        result._items = self._items.split_off(index)
        return result

    def extend_stack(self, other: "Stack[T]") -> None:
        self._items.extend(other._items)

    def replace(self, values: Iterable[T]) -> None:
        self._items = DoublyLinkedList(values)


class Queue(Generic[T]):
    """FIFO queue implemented with linked nodes."""

    def __init__(self, values: Iterable[T] = ()) -> None:
        self.front: Node[T] | None = None
        self.rear: Node[T] | None = None
        self._size = 0
        for value in values:
            self.enqueue(value)

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def __iter__(self) -> Iterator[T]:
        node = self.front
        while node is not None:
            yield node.data
            node = node.next

    def is_empty(self) -> bool:
        return self._size == 0

    def enqueue(self, value: T) -> None:
        node: Node[T] = Node(value)
        if self.rear is None:
            self.front = self.rear = node
        else:
            self.rear.next = node
            node.prev = self.rear
            self.rear = node
        self._size += 1

    def dequeue(self) -> T:
        if self.front is None:
            raise IndexError("dequeue from empty queue")
        node = self.front
        self.front = node.next
        if self.front is None:
            self.rear = None
        else:
            self.front.prev = None
        self._size -= 1
        node.next = node.prev = None
        return node.data

    def peek(self) -> T | None:
        return self.front.data if self.front is not None else None

    def to_list(self) -> list[T]:
        return list(iter(self))

    def clear(self) -> None:
        self.front = self.rear = None
        self._size = 0
