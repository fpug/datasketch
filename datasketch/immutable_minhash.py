import random, copy, struct
from hashlib import sha1
import numpy as np

from datasketch import MinHash

class ImmutableMinHash(MinHash):

    __slots__ = ('seed', 'hashvalues', 'hashobj')

    def _initialize_slots(self, seed, hashvalues, hashobj):
        #print('imhere')
        #print(locals())
        self.seed = seed
        self.hashvalues = self._parse_hashvalues(hashvalues)
        self.hashobj = hashobj
        #print(locals())
        #print(self.hash)

    def __init__(self, minhash):
        self._initialize_slots(minhash.seed, minhash.hashvalues, minhash.hashobj)

    def copy(self):
        '''
        Create a copy of this ImmutableMinHash by exporting its state.
        '''
        imh = object.__new__(ImmutableMinHash)
        imh._initialize_slots(*self.__slots__)
        print('copy!')
        return imh

    def update(self, b):
        raise TypeError("Cannot update an ImmutableMinHash")

    def merge(self, other):
        raise TypeError("Cannot merge an ImmutableMinHash")

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
        imh = object.__new__(ImmutableMinHash)
        imh._initialize_slots(seed, hashvalues, 'sha1')
        return imh

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
        self._initialize_slots(seed, hashvalues, 'sha1')


    @classmethod
    def union(cls, *mhs):
        '''
        Return the union MinHash of multiple MinHash
        '''
        if len(mhs) < 2:
            raise ValueError("Cannot union less than 2 MinHash")
        num_perm = len(mhs[0])
        seed = mhs[0].seed
        hashobj = mhs[0].hashobj
        if any((seed, num_perm, hashobj) != (m.seed, len(m), m.hashobj) for m in mhs):
            raise ValueError("The unioning MinHash must have the\
                    same seed, number of permutation functions and hashobj")
        hashvalues = np.minimum.reduce([m.hashvalues for m in mhs])

        imh = object.__new__(ImmutableMinHash)
        imh._initialize_slots(seed, hashvalues, hashobj)
        return imh
    
    # def __init__(self, num_perm=128, seed=1, hashobj=sha1,
    #         hashvalues=None):
    #     if num_perm > _hash_range:
    #         # Because 1) we don't want the size to be too large, and
    #         # 2) we are using 4 bytes to store the size value
    #         raise ValueError("Cannot have more than %d number of\
    #                 permutation functions" % _hash_range)
    #     self.seed = seed
    #     self.hashobj = hashobj
    #     # Initialize hash values
    #     if hashvalues is not None:
    #         self.hashvalues = MinHash._parse_hashvalues(hashvalues)
    #     else:
    #         self.hashvalues = MinHash._init_hashvalues(num_perm)
    #     # Initalize permutation function parameters
    #     if permutations is not None:
    #         self.permutations = permutations
    #     else:
    #         generator = random.Random()
    #         generator.seed(self.seed)
    #         # Create parameters for a random bijective permutation function
    #         # that maps a 32-bit hash value to another 32-bit hash value.
    #         # http://en.wikipedia.org/wiki/Universal_hashing
    #         self.permutations = np.array([(generator.randint(1, _mersenne_prime),
    #                                        generator.randint(0, _mersenne_prime))
    #                                       for _ in range(num_perm)], dtype=np.uint64).T
    #     if len(self) != len(self.permutations[0]):
    #         raise ValueError("Numbers of hash values and permutations mismatch")

    # def __init__(self, minhash):
    #     self.hashvalues = minhash.hashvalues
    #     self.seed = minhash.seed
    #     self.hashobj = minhash.hashobj

    # def update(self, b):
    #     '''
    #     Update the Minhash with a new data value in bytes.
    #     '''
    #     raise ValueError("Cannot update a finalized MinHash!")


    # def copy(self):
    #     '''
    #     Create a copy of this MinHash by exporting its state.
    #     '''
    #     return MinHash(seed=self.seed, hashvalues=self.digest(),
    #             permutations=self.permutations)


    # @classmethod
    # def deserialize(cls, buf):
    #     '''
    #     Reconstruct a MinHash from a byte buffer.
    #     This is more efficient than using the pickle.loads on the pickled
    #     bytes.
    #     '''
    #     try:
    #         seed, num_perm = struct.unpack_from('qi', buf, 0)
    #     except TypeError:
    #         seed, num_perm = struct.unpack_from('qi', buffer(buf), 0)
    #     offset = struct.calcsize('qi')
    #     try:
    #         hashvalues = struct.unpack_from('%dI' % num_perm, buf, offset)
    #     except TypeError:
    #         hashvalues = struct.unpack_from('%dI' % num_perm, buffer(buf), offset)
    #     #return cls(num_perm=num_perm, seed=seed, hashvalues=hashvalues)

    #     print(type(cls))
    #     self = object.__new__(cls)

    #     self.seed = seed
    #     self.num_perm = num_perm
    #     self.hashvalues = MinHash._parse_hashvalues(self, hashvalues)
    #     self.hashobj = sha1 # to remove, after bugfix in the baseclass


    # def __setstate__(self, buf):
    #     '''
    #     This function is called when unpickling the MinHash.
    #     Initialize the object with data in the buffer.
    #     Note that the input buffer is not the same as the input to the
    #     Python pickle.loads function.
    #     '''
    #     try:
    #         seed, num_perm = struct.unpack_from('qi', buf, 0)
    #     except TypeError:
    #         seed, num_perm = struct.unpack_from('qi', buffer(buf), 0)
    #     offset = struct.calcsize('qi')
    #     try:
    #         hashvalues = struct.unpack_from('%dI' % num_perm, buf, offset)
    #     except TypeError:
    #         hashvalues = struct.unpack_from('%dI' % num_perm, buffer(buf), offset)

    #     self.seed = seed
    #     self.num_perm = num_perm
    #     self.hashvalues = MinHash._parse_hashvalues(self, hashvalues)
    #     self.hashobj = sha1 # to remove, after bugfix in the baseclass