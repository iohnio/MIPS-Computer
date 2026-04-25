# cache.py

from dataclasses import dataclass
from typing import Optional
from memory import Memory

WORD_SIZE = 4
BLOCK_WORDS = 4
BLOCK_SIZE = WORD_SIZE * BLOCK_WORDS

# One cache block: tag, valid/dirty bits, data words, and LRU state
@dataclass
class CacheBlock:
    valid: bool = False
    dirty: bool = False
    tag: Optional[int] = None
    words: Optional[list] = None
    last_used: int = 0

# Base class for both instruction and data caches
class BaseCache:
    def __init__(self, memory: Memory):
        self.memory = memory
        self.accesses = 0
        self.hits = 0

    def stats(self):
        return {"accesses": self.accesses, "hits": self.hits}


# Direct-mapped I-cache: 4 blocks, 4 words each
class InstructionCache(BaseCache):
    def __init__(self, memory: Memory):
        super().__init__(memory)
        self.num_blocks = 4
        self.blocks = [
            CacheBlock(valid=False, dirty=False, tag=None, words=[0] * BLOCK_WORDS)
            for _ in range(self.num_blocks)
        ]
    
    def _index_and_tag(self, address: int):
        block_addr = address // BLOCK_SIZE
        index = block_addr % self.num_blocks
        tag = block_addr // self.num_blocks
        word_offset = (address % BLOCK_SIZE) // WORD_SIZE
        return index, tag, word_offset
    
    # Instruction fetch (read-only)
    def access_read(self, address: int) -> int:
        self.accesses += 1
        index, tag, word_offset = self._index_and_tag(address)
        block = self.blocks[index]

        if block.valid and block.tag == tag:
            self.hits += 1
            return block.words[word_offset]

        # Miss: load block from memory
        block_base_addr = (address // BLOCK_SIZE) * BLOCK_SIZE
        words = [self.memory.load_word(block_base_addr + i * WORD_SIZE)
                 for i in range(BLOCK_WORDS)]

        block.valid = True
        block.dirty = False
        block.tag = tag
        block.words = words
        return block.words[word_offset]


# 2-way set-associative D-cache: 2 sets x 2 ways
class DataCache(BaseCache):
    def __init__(self, memory: Memory):
        super().__init__(memory)
        self.num_sets = 2
        self.ways = 2
        self.sets = [
            [CacheBlock(valid=False, dirty=False, tag=None, words=[0] * BLOCK_WORDS)
             for _ in range(self.ways)]
            for _ in range(self.num_sets)
        ]
        self.use_counter = 0

    def _index_and_tag(self, address: int):
        block_addr = address // BLOCK_SIZE
        set_index = block_addr % self.num_sets
        tag = block_addr // self.num_sets
        word_offset = (address % BLOCK_SIZE) // WORD_SIZE
        return set_index, tag, word_offset

    def _choose_victim_block(self, set_index: int):
        for blk in self.sets[set_index]:
            if not blk.valid:
                return blk
        return min(self.sets[set_index], key=lambda b: b.last_used)

    def _load_block_from_memory(self, address: int, set_index: int, tag: int):
        victim = self._choose_victim_block(set_index)

        if victim.valid and victim.dirty and victim.tag is not None:
            block_number = victim.tag * self.num_sets + set_index
            block_base_addr = block_number * BLOCK_SIZE
            for i in range(BLOCK_WORDS):
                self.memory.store_word(block_base_addr + i * WORD_SIZE,
                                       victim.words[i])

        block_base_addr = (address // BLOCK_SIZE) * BLOCK_SIZE
        words = [self.memory.load_word(block_base_addr + i * WORD_SIZE)
                 for i in range(BLOCK_WORDS)]

        victim.valid = True
        victim.dirty = False
        victim.tag = tag
        victim.words = words
        victim.last_used = self.use_counter
        return victim
    
    # Data read (LW) with write-back, write-allocate policy
    def access_read(self, address: int) -> int:
        self.accesses += 1
        self.use_counter += 1

        set_index, tag, word_offset = self._index_and_tag(address)

        for blk in self.sets[set_index]:
            if blk.valid and blk.tag == tag:
                self.hits += 1
                blk.last_used = self.use_counter
                return blk.words[word_offset]

        blk = self._load_block_from_memory(address, set_index, tag)
        return blk.words[word_offset]
    
    # Data write (SW) with write-back, write-allocate policy
    def access_write(self, address: int, value: int) -> None:
        self.accesses += 1
        self.use_counter += 1

        set_index, tag, word_offset = self._index_and_tag(address)

        for blk in self.sets[set_index]:
            if blk.valid and blk.tag == tag:
                self.hits += 1
                blk.words[word_offset] = value
                blk.dirty = True
                blk.last_used = self.use_counter
                return

        blk = self._load_block_from_memory(address, set_index, tag)
        blk.words[word_offset] = value
        blk.dirty = True
        blk.last_used = self.use_counter