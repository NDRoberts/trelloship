"""This module contains the class and methods that parse a java file."""
import struct

# Disables pylint errors for too many instance methods, too few public methods.
# pylint: disable=R0902, R0903


class ClassFile:
    """This class reads in a Java .class file and parses its values."""

    def __init__(self, name):
        """Instantiate a ClassFile and read its constants,
        fields, methods, & attributes
        """
        print(name)
        with open(name, "rb") as binary_file:
            self.data = bytes(binary_file.read())
            self.offset = 0
            self.i_am_code = 0
            self.run_code = bytearray(0x00)
            self.magic = get_u4(self)
            self.minor = int.from_bytes(get_u2(self), byteorder="big")
            self.major = int.from_bytes(get_u2(self), byteorder="big")
            # print('About to parse the CONSTANT POOL...')
            self.pool_count = int.from_bytes(get_u2(self), byteorder="big")

            self.cp_begin = self.offset
            self.constant_pool = get_constant_pool(self)

            self.access_flags = get_u2(self)
            self.this_class = get_u2(self)
            self.super_class = get_u2(self)

            # print('About to parse the INTERFACES...')
            self.interfaces_count = int.from_bytes(get_u2(self), byteorder="big")
            self.interfaces_begin = self.offset
            if self.interfaces_count:
                self.interfaces = get_info(self, self.interfaces_count)

            # print('About to parse the FIELDS...')
            self.fields_count = int.from_bytes(get_u2(self), byteorder="big")
            self.fields_begin = self.offset
            if self.fields_count:
                self.fields = get_info(self, self.fields_count)

            # print('About to parse the METHODS...')
            self.methods_count = int.from_bytes(get_u2(self), byteorder="big")
            self.methods_begin = self.offset
            if self.methods_count:
                self.methods = get_info(self, self.methods_count)

            # print('About to parse the CLASS ATTRIBUTES...')
            self.class_attributes_count = int.from_bytes(get_u2(self), byteorder="big")
            if self.class_attributes_count:
                self.class_attributes = get_attributes(
                    self, self.class_attributes_count
                )


def get_constant_pool(self):
    """Collect the Constant Pool from a .class file as a list.
    Each constant is in a Python-readable format
    """
    tag_table = {
        1: {
            "type": "utf-8",
            "value": lambda: get_extended(self).decode("utf-8"),
        },
        3: {
            "type": "Integer",
            "value": lambda: int.from_bytes(get_u4(self), byteorder="big"),
        },
        4: {
            "type": "Float",
            "value": lambda: struct.unpack("f", (get_u4(self))),
        },
        5: {
            "type": "Long",
            "value": lambda: int.from_bytes(get_u8(self), byteorder="big"),
        },
        6: {
            "type": "Double",
            "value": lambda: struct.unpack("d", get_u8(self)),
        },
        7: {
            "type": "Class",
            "name_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
        },
        8: {
            "type": "String",
            "string_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
        },
        9: {
            "type": "Fieldref",
            "class_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
            "name_and_type_index": lambda: int.from_bytes(
                get_u2(self), byteorder="big"
            ),
        },
        10: {
            "type": "Methodref",
            "class_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
            "name_and_type_index": lambda: int.from_bytes(
                get_u2(self), byteorder="big"
            ),
        },
        11: {
            "type": "InterfaceMethodref",
            "class_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
            "name_and_type_index": lambda: int.from_bytes(
                get_u2(self), byteorder="big"
            ),
        },
        12: {
            "type": "NameAndType",
            "name_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
            "descriptor_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
        },
        15: {
            "type": "MethodHandle",
            "reference_kind": lambda: get_u1(self),
            "reference_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
        },
        16: {
            "type": "MethodType",
            "descriptor_index": lambda: int.from_bytes(get_u2(self), byteorder="big"),
        },
        18: {
            "type": "InvokeDynamic",
            "bootstrap_method_attr_index": lambda: int.from_bytes(
                get_u2(self), byteorder="big"
            ),
            "name_and_type_index": lambda: int.from_bytes(
                get_u2(self), byteorder="big"
            ),
        },
    }
    pool = {0: []}
    pool[0] = self.pool_count
    for index in range(1, self.pool_count):
        tag = get_u1(self)
        constant = tag_table.get(tag, None).copy()
        for aspect in constant:
            if aspect != "type":
                constant[aspect] = constant[aspect]()
        pool[index] = constant
        if tag == 1 and constant["value"] == "Code":
            self.i_am_code = index
        if tag in [5, 6]:
            index += 1
    return pool


def get_info(self, count):
    """Get the contents of a Field or Method section"""
    info = {0: {"values_count": count}}
    for val in range(1, count + 1):
        info[val] = {}
        info[val]["access_flags"] = get_u2(self)
        info[val]["name_index"] = int.from_bytes(get_u2(self), byteorder="big")
        info[val]["descriptor_index"] = int.from_bytes(get_u2(self), byteorder="big")
        info[val]["attributes_count"] = int.from_bytes(get_u2(self), byteorder="big")
        info[val]["attributes"] = get_attributes(self, info[val]["attributes_count"])
    return info


def get_attributes(self, count):
    """Get the attributes of a Field, Method, or Class"""
    attributes = []
    attributes.append(0)
    num_attributes = 0
    if count:
        while num_attributes < count:
            attr = get_an_attribute(self)
            attributes.append(attr)
            attributes[0] += 6 + attr["length"]
            num_attributes += 1
    return attributes


def get_an_attribute(self):
    """Return the index, length, and info of a
    single attribute as a dictionary
    """
    attribute = {}
    attribute["name_index"] = int.from_bytes(get_u2(self), byteorder="big")
    attribute["length"] = int.from_bytes(get_u4(self), byteorder="big")
    # print(attribute['length'])
    attribute["info"] = get_extended(self, length=attribute["length"])
    # # WANGLE OUT CODE ATTRIBUTES
    if attribute["name_index"] == self.i_am_code:
        self.run_code.extend(attribute["info"])
    return attribute


def get_u1(self):
    """Fetch a single-byte value from the class data"""
    value = self.data[self.offset]
    self.offset += 1
    # print('Fetched',value)
    return value


def get_u2(self):
    """Fetch a two-byte value from the class data"""
    value = self.data[self.offset : self.offset + 2]
    self.offset += 2
    # print('Fetched',value)
    return value


def get_u4(self):
    """Fetch a four-byte value from the class data"""
    value = self.data[self.offset : self.offset + 4]
    self.offset += 4
    # print('Fetched',value)
    return value


def get_u8(self):
    """Fetch an eight-byte value from the class data"""
    value = self.data[self.offset : self.offset + 8]
    self.offset += 8
    # print('Fetched',value)
    return value


def get_extended(self, length=0):
    """Fetch a variable-length value from the class data.
    If no length value is supplied, assume the first two bytes
    of the target value represent its length.
    """
    if not length:
        length = int.from_bytes(get_u2(self), byteorder="big")
    value = self.data[self.offset : self.offset + length]
    self.offset += length
    # print('Fetched',value)
    return value
