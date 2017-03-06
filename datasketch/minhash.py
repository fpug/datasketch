'''
This module implements MinHash - a probabilistic data structure for computing
Jaccard similarity between datasets.

The original MinHash paper:
http://cs.brown.edu/courses/cs253/papers/nearduplicate.pdf
'''

import random, copy, struct
from hashlib import sha1
import numpy as np

# The size of a hash value in number of bytes
hashvalue_byte_size = len(bytes(np.int64(42).data))

# http://en.wikipedia.org/wiki/Mersenne_prime
_mersenne_prime = (1 << 61) - 1
_max_hash = (1 << 32) - 1
_hash_range = (1 << 32)

class MinHash(object):
    '''
    Create a MinHash with `num_perm` number of random permutation
    functions.
    The `seed` parameter controls the set of random permutation functions
    generated for this MinHash.
    Different seed will generate different sets of permutaiton functions.
    The `hashobj` parameter specifies a hash used for generating
    hash value. It must implements the `digest` interface similar to
    hashlib hashes.
    `hashvalues` and `permutations` can be specified for faster
    initialization using existing state from another MinHash.
    '''

    __slots__ = ('permutations', 'hashvalues', 'seed', 'hashobj', 'finalized')

    def __init__(self, num_perm=128, seed=1, hashobj=sha1, 
            hashvalues=None, permutations=None, finalized=False):
        if num_perm > _hash_range:
            # Because 1) we don't want the size to be too large, and
            # 2) we are using 4 bytes to store the size value
            raise ValueError("Cannot have more than %d number of\
                    permutation functions" % _hash_range)
        self.seed = seed
        self.hashobj = hashobj
        self.finalized = finalized
        # Initialize hash values
        if hashvalues is not None:
            self.hashvalues = self._parse_hashvalues(hashvalues)
        else:
            self.hashvalues = self._init_hashvalues(num_perm)
        # Initialize permutations
        if finalized:
        # NB: a MinHash only needs permutations to update; if the MinHash is already in 
        # its finalized state, not storing permutations will make it more space efficient.
            if permutations is not None:
                raise ValueError("Cannot have permutations != None\
                    and finalized == True at the same time")
            self.permutations = None
        elif permutations is not None:
            self.load_permutations(permutations)
        else:
            permutations = generate_permutations(seed, num_perm)
            self.load_permutations(permutations)

    def _init_hashvalues(self, num_perm):
        return np.ones(num_perm, dtype=np.uint64)*_max_hash

    def _parse_hashvalues(self, hashvalues):
        return np.array(hashvalues, dtype=np.uint64)

    def generate_permutations(self, seed, num_perm):
        '''
        Generates the permutations given the seed; the method is called by the init,
        but can also be called to unfinalize a MinHash
        '''
        generator = random.Random()
        generator.seed(self.seed)
        # Create parameters for a random bijective permutation function
        # that maps a 32-bit hash value to another 32-bit hash value.
        # http://en.wikipedia.org/wiki/Universal_hashing
        permutations = np.array([(generator.randint(1, _mersenne_prime),
                                  generator.randint(0, _mersenne_prime))
                                  for _ in range(num_perm)], dtype=np.uint64).T
        return permutations

    def load_permutations(self, permutations):
        '''
        Loads the permutations into the MinHash; the method is called by the init,
        but can also be called to unfinalize a MinHash
        NB: providing permutations not matching the seeds will result in inconsistency
        '''
        if len(self) != len(self.permutations[0]):
            raise ValueError("Numbers of hash values and permutations mismatch")
        self.permutations = permutations
        self.finalized=False

    def __len__(self):
        '''
        Return the size of the MinHash
        '''
        return len(self.hashvalues)

    def __eq__(self, other):
        '''
        Check equivalence between MinHash
        '''
        return self.seed == other.seed and \
                np.array_equal(self.hashvalues, other.hashvalues)

    def is_empty(self):
        '''
        Check if the current MinHash is empty - at the state of just
        initialized.
        '''
        if np.any(self.hashvalues != _max_hash):
            return False
        return True

    def clear(self):
        '''
        Clear the current state of the Minhash.
        '''
        self.hashvalues = self._init_hashvalues(len(self))

    def copy(self):
        '''
        Create a copy of this MinHash by exporting its state.
        '''
        return MinHash(seed=self.seed, hashvalues=self.digest(),
                permutations=self.permutations)

    def update(self, b):
        '''
        Update the Minhash with a new data value in bytes.
        '''
        if self.permutations is None:
            raise ValueError("the MinHash doesn't store permutations,\
                    so it can't be updated")
        hv = struct.unpack('<I', self.hashobj(b).digest()[:4])[0]
        a, b = self.permutations
        phv = np.bitwise_and((a * hv + b) % _mersenne_prime, np.uint64(_max_hash))
        self.hashvalues = np.minimum(phv, self.hashvalues)

    def finalize(self):
        '''
        Finalizes the MinHash, forbidding further updates but greatly speeding up the deserialization
        performance.  It can be undone by calling generate_permutations or load_permutations.
        '''
        self.permutations=None
        self.finalized=True

    def digest(self):
        '''
        Returns the hash values.
        '''
        return copy.copy(self.hashvalues)

    def merge(self, other):
        '''
        Merge the other MinHash with this one, making this the union
        of both.
        '''
        if other.seed != self.seed:
            raise ValueError("Cannot merge MinHash with\
                    different seeds")
        if len(self) != len(other):
            raise ValueError("Cannot merge MinHash with\
                    different numbers of permutation functions")
        self.hashvalues = np.minimum(other.hashvalues, self.hashvalues)

    def count(self):
        '''
        Estimate the cardinality count.
        See: http://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=365694
        '''
        k = len(self)
        return np.float(k) / np.sum(self.hashvalues / np.float(_max_hash)) - 1.0

    def jaccard(self, other):
        '''
        Estimate the Jaccard similarity (resemblance) between this Minhash
        and the other.
        '''
        if other.seed != self.seed:
            raise ValueError("Cannot compute Jaccard given MinHash with\
                    different seeds")
        if len(self) != len(other):
            raise ValueError("Cannot compute Jaccard given MinHash with\
                    different numbers of permutation functions")
        return np.float(np.count_nonzero(self.hashvalues==other.hashvalues)) /\
                np.float(len(self))

    def bytesize(self):
        '''
        Returns the size of this MinHash in bytes.
        To be used in serialization.
        '''
        # Use 8 bytes to store the seed integer
        seed_size = struct.calcsize('q')
        # Use 4 bytes to store the number of hash values
        length_size = struct.calcsize('i')
        # Use 4 bytes to store each hash value as we are using the lower 32 bit
        hashvalue_size = struct.calcsize('I')
        finalized_size = struct.calcsize('?')
        return seed_size + length_size + len(self) * hashvalue_size + finalized_size

    def serialize(self, buf):
        '''
        Serializes this MinHash into bytes, store in `buf`.
        This is more efficient than using pickle.dumps on the object.
        '''
        if len(buf) < self.bytesize():
            raise ValueError("The buffer does not have enough space\
                    for holding this MinHash.")
        fmt = "qi%dI?" % len(self)
        struct.pack_into(fmt, buf, 0,
                self.seed, len(self), *self.hashvalues, self.finalized)

    @classmethod
    def deserialize(cls, buf):
        '''
        Reconstruct a MinHash from a byte buffer.
        This is more efficient than using the pickle.loads on the pickled
        bytes.
        '''
        try:
            seed, num_perm = struct.unpack_from('qi', buf, 0)
        except TypeError:
            seed, num_perm = struct.unpack_from('qi', buffer(buf), 0)
        offset = struct.calcsize('qi')
        try:
            hashvalues = struct.unpack_from('%dI' % num_perm, buf, offset)
        except TypeError:
            hashvalues = struct.unpack_from('%dI' % num_perm, buffer(buf), offset)
        # the code below is clumsy but was added for backwards-compatibility reasons
        offset2 = offset + struct.calcsize('%dI' % num_perm)
        try:
            finalized = struct.unpack_from('?', buf, offset2)[0]
        except TypeError:
            try:
                finalized = struct.unpack_from('?', buffer(buf), offset2)[0]
            except struct.error:
                finalized = False
        except struct.error:
            finalized = False
        return cls(num_perm=num_perm, seed=seed, hashvalues=hashvalues, finalized=finalized)


    def __getstate__(self):
        '''
        This function is called when pickling the MinHash.
        Returns a bytearray which will then be pickled.
        Note that the bytes returned by the Python pickle.dumps is not
        the same as the buffer returned by this function.
        '''
        buf = bytearray(self.bytesize())
        fmt = "qi%dI?" % len(self)
        struct.pack_into(fmt, buf, 0,
                self.seed, len(self), *self.hashvalues, self.finalized)
        return buf

    def __setstate__(self, buf):
        '''
        This function is called when unpickling the MinHash.
        Initialize the object with data in the buffer.
        Note that the input buffer is not the same as the input to the
        Python pickle.loads function.
        '''
        try:
            seed, num_perm = struct.unpack_from('qi', buf, 0)
        except TypeError:
            seed, num_perm = struct.unpack_from('qi', buffer(buf), 0)
        offset = struct.calcsize('qi')
        try:
            hashvalues = struct.unpack_from('%dI' % num_perm, buf, offset)
        except TypeError:
            hashvalues = struct.unpack_from('%dI' % num_perm, buffer(buf), offset)
        # the code below is clumsy but was added for backwards-compatibility reasons
        offset2 = offset + struct.calcsize('%dI' % num_perm)
        try:
            finalized = struct.unpack_from('?', buf, offset2)[0]
        except TypeError:
            try:
                finalized = struct.unpack_from('?', buffer(buf), offset2)[0]
            except struct.error:
                finalized = False
        except struct.error:
            finalized = False
        self.__init__(num_perm=num_perm, seed=seed, hashvalues=hashvalues, finalized=finalized)


    @classmethod
    def union(cls, *mhs):
        '''
        Return the union MinHash of multiple MinHash
        '''
        if len(mhs) < 2:
            raise ValueError("Cannot union less than 2 MinHash")
        num_perm = len(mhs[0])
        seed = mhs[0].seed
        if any(seed != m.seed for m in mhs) or \
                any(num_perm != len(m) for m in mhs):
            raise ValueError("The unioning MinHash must have the\
                    same seed and number of permutation functions")
        hashvalues = np.minimum.reduce([m.hashvalues for m in mhs])
        return cls(num_perm=num_perm, seed=seed, hashvalues=hashvalues)
