"""Taken from CPython functools.py lru_cache decorator implementation
https://github.com/python/cpython/blob/3.8/Lib/functools.py
"""

from threading import RLock

PREV, NEXT, KEY, RESULT = 0, 1, 2, 3   # names for the link fields


class LRUCache(object):
    # Constants shared by all lru cache instances:
    sentinel = object()          # unique object used to signal cache misses
    lock = RLock()           # because linkedlist updates aren't threadsafe

    def __init__(self, maxsize=128):
        # cache instance variables
        self.maxsize = maxsize
        self.cache = {}
        self.root = []                # root of the circular doubly linked list
        self.root[:] = [self.root, self.root, None, None]     # initialize by pointing to self
        self.full = False

    def _move_link(self, link):
        # Move the link to the front of the circular queue
        link_prev, link_next, _key, result = link
        link_prev[NEXT] = link_next
        link_next[PREV] = link_prev
        last = self.root[PREV]
        last[NEXT] = self.root[PREV] = link
        link[PREV] = last
        link[NEXT] = self.root
        return result

    def get(self, key):
        link = self.cache.get(key)
        if link is not None:
            result = self._move_link(link)
            return result
        return -1

    def put(self, key, value):
        # Size limited caching that tracks accesses by recency
        with self.lock:
            link = self.cache.get(key)
            if link is not None:
                self._move_link(link)
                self.cache[key][RESULT] = value
                return
        with self.lock:
            if self.full:
                # Use the old root to store the new key and result.
                oldroot = self.root
                oldroot[KEY] = key
                oldroot[RESULT] = value
                # Empty the oldest link and make it the new root.
                # Keep a reference to the old key and old result to
                # prevent their ref counts from going to zero during the
                # update. That will prevent potentially arbitrary object
                # clean-up code (i.e. __del__) from running while we're
                # still adjusting the links.
                self.root = oldroot[NEXT]
                oldkey = self.root[KEY]
                oldresult = self.root[RESULT]
                self.root[KEY] = self.root[RESULT] = None
                # Now update the cache dictionary.
                del self.cache[oldkey]
                # Save the potentially reentrant cache[key] assignment
                # for last, after the root and links have been put in
                # a consistent state.
                self.cache[key] = oldroot
            else:
                # Put result in a new link at the front of the queue.
                last = self.root[PREV]
                link = [last, self.root, key, value]
                last[NEXT] = self.root[PREV] = self.cache[key] = link
                # Use the cache_len bound method instead of the len() function
                # which could potentially be wrapped in an lru_cache itself.
                self.full = (len(self.cache) >= self.maxsize)

    def has_key(self, key):
        return key in self.cache

    def clear(self):
        self.cache.clear()
        self.root[:] = [self.root, self.root, None, None]
