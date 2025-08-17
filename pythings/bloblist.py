import struct

class BlobList:
    """A list-like wrapper storing uint32 values as a binary blob."""

    def __init__(self, blob: bytes = b''):
        """Initialize the BlobList from a bytes object."""
        self.blob = bytearray(blob)

    def _offset(self, i):
        """Calculate byte offset for index i."""
        return i * 4
    def _validate_i(self, i):
        if i is None: return None
        if not isinstance(i, int):
            try:
                i = int(i)
            except:
                raise TypeError(f"Value must be int, got {type(i).__name__}")
        if not (0 <= i < len(self.blob) // 4):
            raise IndexError(f"Index {i} out of range")
        return i
    def _validate_v(self, v):
        if v is None: return None
        if not isinstance(v, int):
            try:
                v = int(v)
            except:
                raise TypeError(f"Value must be int, got {type(v).__name__}")
        if not (0 <= v <= 0xFFFFFFFF):
            raise ValueError(f"Value {v} out of uint32 range")
        return v
    @classmethod
    def from_bytes(cls, *args):
        return cls(*args)
    def get(self, i):
        """[i]: Get the integer value at index i."""
        i = self._validate_i(i)
        o = self._offset(i)
        return struct.unpack_from('<I', self.blob, o)[0]

    def set(self, i, v):
        """[i, v]: Set the integer value at index i."""
        v = self._validate_v(v)
        i = self._validate_i(i)
        o = self._offset(i)
        struct.pack_into('<I', self.blob, o, v)

    def add(self, v):
        """[v]: Append an integer value to the end of the blob."""
        v = self._validate_v(v)
        i = self.find(v)
        if i == -1:
            self.blob += struct.pack('<I', v)
            return True
        else:
            return False

    def find(self, v):
        """[v]: Return index of value v, or -1 if not found."""
        v = self._validate_v(v)
        for i in range(len(self.blob) // 4):
            if self.get(i) == v:
                return i
        return -1

    def rem(self, v=None, i=None):
        """[v, i]: Remove the value v or the element at index i."""
        v = self._validate_v(v)
        i = self._validate_i(i)
        if i is None and v is not None:
            i = self.find(v)
        if i is None or i == -1:
            raise IndexError(f"Index {i} out of range or value {v} not found")
        del self.blob[self._offset(i):self._offset(i+1)]

    def to_bytes(self):
        """[]: Return the blob as bytes."""
        return bytes(self.blob)

    def to_list(self):
        """[]: Return the blob as a list of integers."""
        return [self.get(i) for i in range(len(self.blob) // 4)]

    def __repr__(self):
        """Return a string representation of the BlobList."""
        return f"BlobList({self.to_list()})"

if __name__=="__main__":
    t = BlobList.from_bytes(b'1')
    print(t)
