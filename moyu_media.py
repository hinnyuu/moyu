import datetime as dt
import os
import re
import struct
import tempfile
import zlib
from dataclasses import dataclass, field

DATE_RE = re.compile(
    rb"(\d{4})([-:/])(\d{2})\2(\d{2})([ T])(\d{2}):(\d{2}):(\d{2})"
)
PNG_SIG = b"\x89PNG\r\n\x1a\n"
XMP_PREFIX = b"http://ns.adobe.com/xap/1.0/\x00"
QT_EPOCH_OFFSET = 2082844800
MATROSKA_EPOCH = 978307200
TYPE_SIZES = {
    1: 1,
    2: 1,
    3: 2,
    4: 4,
    5: 8,
    6: 1,
    7: 1,
    8: 2,
    9: 4,
    10: 8,
    11: 4,
    12: 8,
}


class MetadataError(Exception):
    pass


@dataclass
class Patch:
    offset: int
    old: bytes
    new: bytes
    field: str


@dataclass
class MetadataInfo:
    format: str
    patches: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    strict_problems: list = field(default_factory=list)
    requires_materialize: bool = False
    records: list = field(default_factory=list)


@dataclass
class FileReader:
    path: str
    size: int = field(init=False)
    fp: object = field(init=False)

    def __post_init__(self):
        self.fp = open(self.path, "rb")
        self.size = os.fstat(self.fp.fileno()).st_size

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.size:
            raise MetadataError(f"读取越界: offset={offset} size={size}")
        self.fp.seek(offset)
        data = self.fp.read(size)
        if len(data) != size:
            raise MetadataError("读取长度不足")
        return data

    def close(self):
        self.fp.close()


@dataclass
class BytesReader:
    data: bytes
    size: int = field(init=False)

    def __post_init__(self):
        self.size = len(self.data)

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.size:
            raise MetadataError(f"读取越界: offset={offset} size={size}")
        return self.data[offset : offset + size]

    def close(self):
        pass


def target_string(old, target_epoch, tz):
    match = DATE_RE.fullmatch(old)
    if not match:
        return None
    date_sep = match.group(2).decode("ascii")
    dt_sep = match.group(5).decode("ascii")
    value = dt.datetime.fromtimestamp(target_epoch, tz=tz)
    new = (
        f"{value.year:04d}{date_sep}{value.month:02d}{date_sep}{value.day:02d}"
        f"{dt_sep}{value.hour:02d}:{value.minute:02d}:{value.second:02d}"
    ).encode("ascii")
    if len(new) != len(old):
        return None
    return new


def string_patches(offset, blob, target_epoch, tz, label):
    patches = []
    for match in DATE_RE.finditer(blob):
        old = match.group(0)
        new = target_string(old, target_epoch, tz)
        if new is None:
            raise MetadataError(f"{label}: 无法生成等长目标时间 {old!r}")
        patches.append(Patch(offset + match.start(), old, new, label))
    return patches


def apply_patches(data, patches):
    result = bytearray(data)
    last_end = -1
    for patch in sorted(patches, key=lambda item: item.offset):
        if patch.offset < last_end:
            raise MetadataError("补丁区间重叠")
        if len(patch.old) != len(patch.new):
            raise MetadataError(f"{patch.field}: 补丁长度不一致")
        end = patch.offset + len(patch.old)
        if result[patch.offset : end] != patch.old:
            raise MetadataError(f"{patch.field}: 原字节不匹配")
        result[patch.offset : end] = patch.new
        last_end = end
    return bytes(result)


def iter_patched_chunks(path, patches, chunk_size):
    ordered = sorted(patches, key=lambda item: item.offset)
    last_end = -1
    for patch in ordered:
        if patch.offset < last_end:
            raise MetadataError("补丁区间重叠")
        if len(patch.old) != len(patch.new):
            raise MetadataError(f"{patch.field}: 补丁长度不一致")
        last_end = patch.offset + len(patch.old)
    with open(path, "rb") as handle:
        position = 0
        index = 0
        while index < len(ordered):
            patch = ordered[index]
            while position < patch.offset:
                size = min(chunk_size, patch.offset - position)
                data = handle.read(size)
                if len(data) != size:
                    raise MetadataError("源文件读取不完整")
                yield data
                position += size
            old = handle.read(len(patch.old))
            if old != patch.old:
                raise MetadataError(f"{patch.field}: 原字节不匹配")
            yield patch.new
            position += len(patch.old)
            index += 1
        while True:
            data = handle.read(chunk_size)
            if not data:
                break
            yield data


def read_cstring(reader, position, limit):
    data = bytearray()
    while position < limit:
        char = reader.read(position, 1)
        position += 1
        if char == b"\x00":
            return bytes(data), position
        data += char
    raise MetadataError("字符串未终止")


def patch_to_dict(patch):
    try:
        old = patch.old.decode("ascii")
        new = patch.new.decode("ascii")
        if all(32 <= ord(char) < 127 or char in "\r\n\t" for char in old + new):
            return {"field": patch.field, "old": old, "new": new}
    except UnicodeDecodeError:
        pass
    return {
        "field": patch.field,
        "old": patch.old.hex(),
        "new": patch.new.hex(),
    }


def exr_info(reader, target_epoch, tz):
    if reader.read(0, 4) != b"v/1\x01":
        return None
    position = 8
    patches = []
    while True:
        name, position = read_cstring(reader, position, reader.size)
        if not name:
            break
        attr_type, position = read_cstring(reader, position, reader.size)
        size = struct.unpack("<I", reader.read(position, 4))[0]
        position += 4
        value_offset = position
        if attr_type == b"string" and b"date" in name.lower():
            value = reader.read(value_offset, size)
            patches.extend(
                string_patches(
                    value_offset, value, target_epoch, tz, name.decode("latin1")
                )
            )
        position += size
    return MetadataInfo("exr", patches)


def split_cstring(data, offset=0):
    index = data.find(b"\x00", offset)
    if index < 0:
        return None, None
    return data[offset:index], index + 1


def text_records(label, text, target_epoch, tz):
    records = []
    for match in DATE_RE.finditer(text):
        old = match.group(0)
        new = target_string(old, target_epoch, tz)
        if new is None:
            raise MetadataError(f"{label}: 无法生成等长目标时间")
        records.append(
            {
                "field": label,
                "old": old.decode("ascii", "replace"),
                "new": new.decode("ascii", "replace"),
            }
        )
    return records


def replace_text_dates(text, target_epoch, tz, label):
    records = []
    chunks = []
    last = 0
    for match in DATE_RE.finditer(text):
        old = match.group(0)
        new = target_string(old, target_epoch, tz)
        if new is None:
            raise MetadataError(f"{label}: 无法生成等长目标时间")
        chunks.append(text[last : match.start()])
        chunks.append(new)
        records.append(
            {
                "field": label,
                "old": old.decode("ascii", "replace"),
                "new": new.decode("ascii", "replace"),
            }
        )
        last = match.end()
    if not records:
        return text, []
    chunks.append(text[last:])
    return b"".join(chunks), records


def parse_itxt(data):
    keyword, cursor = split_cstring(data, 0)
    if keyword is None or cursor is None or cursor + 2 > len(data):
        return None
    flag = data[cursor]
    method = data[cursor + 1]
    cursor += 2
    language, cursor = split_cstring(data, cursor)
    if language is None or cursor is None:
        return None
    translated, cursor = split_cstring(data, cursor)
    if translated is None or cursor is None:
        return None
    return keyword, flag, method, language, translated, data[cursor:], cursor


def parse_ztxt(data):
    keyword, cursor = split_cstring(data, 0)
    if keyword is None or cursor is None or cursor >= len(data):
        return None
    return keyword, data[cursor], data[cursor + 1 :]


def png_info(reader, target_epoch, tz):
    if reader.read(0, 8) != PNG_SIG:
        return None
    position = 8
    patches = []
    notes = []
    strict_problems = []
    requires_materialize = False
    compressed_records = []
    date_keywords = {
        b"date",
        b"creation time",
        b"date:create",
        b"date:modify",
        b"creation_time",
    }
    while position + 12 <= reader.size:
        length = struct.unpack(">I", reader.read(position, 4))[0]
        chunk_type = reader.read(position + 4, 4)
        data_offset = position + 8
        crc_offset = data_offset + length
        if crc_offset + 4 > reader.size:
            break
        if chunk_type in (b"tEXt", b"iTXt", b"zTXt", b"eXIf"):
            data = reader.read(data_offset, length)
            relative = []
            if chunk_type == b"tEXt":
                if b"\x00" in data:
                    keyword, text = data.split(b"\x00", 1)
                    text_offset = len(keyword) + 1
                    if keyword.lower() in date_keywords or DATE_RE.search(text):
                        for match in DATE_RE.finditer(text):
                            old = match.group(0)
                            new = target_string(old, target_epoch, tz)
                            if new is None:
                                raise MetadataError(
                                    f"tEXt {keyword!r}: 无法生成等长目标时间"
                                )
                            relative.append(
                                (
                                    text_offset + match.start(),
                                    old,
                                    new,
                                    f"tEXt {keyword.decode('latin1')}",
                                )
                            )
            elif chunk_type == b"eXIf":
                tiff = tiff_info(BytesReader(data), target_epoch, tz, "eXIf")
                relative.extend(
                    (patch.offset, patch.old, patch.new, patch.field)
                    for patch in tiff
                )
            elif chunk_type == b"iTXt":
                parsed = parse_itxt(data)
                if parsed is None:
                    notes.append("iTXt 结构无法解析")
                    strict_problems.append("iTXt 结构无法解析")
                else:
                    keyword, flag, method, language, translated, text, text_offset = parsed
                    label = f"iTXt {keyword.decode('latin1')}"
                    if flag == 0:
                        for match in DATE_RE.finditer(text):
                            old = match.group(0)
                            new = target_string(old, target_epoch, tz)
                            if new is None:
                                raise MetadataError(f"{label}: 无法生成等长目标时间")
                            relative.append(
                                (
                                    text_offset + match.start(),
                                    old,
                                    new,
                                    label,
                                )
                            )
                    else:
                        if method != 0:
                            notes.append(f"{label} 压缩方法 {method} 不支持")
                            strict_problems.append(f"{label} 压缩方法不支持")
                        else:
                            try:
                                raw = zlib.decompress(text)
                            except zlib.error as exc:
                                notes.append(f"{label} 解压失败: {exc}")
                                strict_problems.append(f"{label} 解压失败")
                            else:
                                _, records = replace_text_dates(
                                    raw, target_epoch, tz, label
                                )
                                if records:
                                    requires_materialize = True
                                    compressed_records.extend(records)
                                    notes.append(f"{label} 已压缩，将重建 chunk")
            elif chunk_type == b"zTXt":
                parsed = parse_ztxt(data)
                if parsed is None:
                    notes.append("zTXt 结构无法解析")
                    strict_problems.append("zTXt 结构无法解析")
                else:
                    keyword, method, compressed = parsed
                    label = f"zTXt {keyword.decode('latin1')}"
                    if method != 0:
                        notes.append(f"{label} 压缩方法 {method} 不支持")
                        strict_problems.append(f"{label} 压缩方法不支持")
                    else:
                        try:
                            raw = zlib.decompress(compressed)
                        except zlib.error as exc:
                            notes.append(f"{label} 解压失败: {exc}")
                            strict_problems.append(f"{label} 解压失败")
                        else:
                            _, records = replace_text_dates(
                                raw, target_epoch, tz, label
                            )
                            if records:
                                requires_materialize = True
                                compressed_records.extend(records)
                                notes.append(f"{label} 已压缩，将重建 chunk")
            if relative:
                for offset, old, new, label in relative:
                    patches.append(Patch(data_offset + offset, old, new, label))
                new_data = apply_patches(
                    data,
                    [
                        Patch(offset, old, new, label)
                        for offset, old, new, label in relative
                    ],
                )
                old_crc = reader.read(crc_offset, 4)
                new_crc = struct.pack(
                    ">I", zlib.crc32(chunk_type + new_data) & 0xFFFFFFFF
                )
                patches.append(
                    Patch(crc_offset, old_crc, new_crc, f"{chunk_type.decode()} CRC")
                )
        position = crc_offset + 4
    records = []
    if requires_materialize:
        records = [
            patch_to_dict(patch)
            for patch in patches
            if not patch.field.endswith("CRC")
        ]
        records.extend(compressed_records)
    return MetadataInfo(
        "png",
        patches,
        notes,
        strict_problems,
        requires_materialize,
        records,
    )


def rewrite_png_chunk(chunk_type, data, target_epoch, tz):
    if chunk_type == b"tEXt":
        keyword, text = split_cstring(data, 0)
        if keyword is None:
            return None
        new_text, _ = replace_text_dates(
            text, target_epoch, tz, f"tEXt {keyword.decode('latin1')}"
        )
        if new_text == text:
            return None
        return keyword + b"\x00" + new_text
    if chunk_type == b"zTXt":
        parsed = parse_ztxt(data)
        if parsed is None:
            return None
        keyword, method, compressed = parsed
        if method != 0:
            raise MetadataError(f"zTXt {keyword!r}: 不支持的压缩方法 {method}")
        raw = zlib.decompress(compressed)
        new_text, _ = replace_text_dates(
            raw, target_epoch, tz, f"zTXt {keyword.decode('latin1')}"
        )
        if new_text == raw:
            return None
        return keyword + b"\x00" + bytes([method]) + zlib.compress(new_text, 6)
    if chunk_type == b"iTXt":
        parsed = parse_itxt(data)
        if parsed is None:
            return None
        keyword, flag, method, language, translated, text, _ = parsed
        if flag == 0:
            new_text, _ = replace_text_dates(
                text, target_epoch, tz, f"iTXt {keyword.decode('latin1')}"
            )
            if new_text == text:
                return None
            return (
                keyword
                + b"\x00"
                + bytes([flag, method])
                + language
                + b"\x00"
                + translated
                + b"\x00"
                + new_text
            )
        if method != 0:
            raise MetadataError(f"iTXt {keyword!r}: 不支持的压缩方法 {method}")
        raw = zlib.decompress(text)
        new_text, _ = replace_text_dates(
            raw, target_epoch, tz, f"iTXt {keyword.decode('latin1')}"
        )
        if new_text == raw:
            return None
        return (
            keyword
            + b"\x00"
            + bytes([flag, method])
            + language
            + b"\x00"
            + translated
            + b"\x00"
            + zlib.compress(new_text, 6)
        )
    if chunk_type == b"eXIf":
        tiff = tiff_info(BytesReader(data), target_epoch, tz, "eXIf")
        if not tiff:
            return None
        return apply_patches(data, tiff)
    return None


def write_png_chunk(output, chunk_type, data):
    output.write(struct.pack(">I", len(data)))
    output.write(chunk_type)
    output.write(data)
    output.write(
        struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def copy_exact(source, output, size, chunk_size=1024 * 1024):
    remaining = size
    while remaining:
        data = source.read(min(chunk_size, remaining))
        if not data:
            raise MetadataError("PNG chunk 数据不完整")
        output.write(data)
        remaining -= len(data)


def materialize_png(path, target_epoch, tz, dest_dir):
    file_descriptor, temp_path = tempfile.mkstemp(
        prefix=".moyu-meta-", suffix=".png", dir=dest_dir
    )
    os.close(file_descriptor)
    try:
        os.chmod(temp_path, 0o644)
    except OSError:
        pass
    try:
        with open(path, "rb") as source, open(temp_path, "wb") as output:
            signature = source.read(8)
            if signature != PNG_SIG:
                raise MetadataError("PNG 签名不正确")
            output.write(signature)
            while True:
                header = source.read(8)
                if len(header) != 8:
                    raise MetadataError("PNG chunk 头部不完整")
                length, chunk_type = struct.unpack(">I4s", header)
                if chunk_type in (b"tEXt", b"iTXt", b"zTXt", b"eXIf"):
                    data = source.read(length)
                    if len(data) != length:
                        raise MetadataError("PNG chunk 数据不完整")
                    crc = source.read(4)
                    if len(crc) != 4:
                        raise MetadataError("PNG chunk CRC 不完整")
                    new_data = rewrite_png_chunk(
                        chunk_type, data, target_epoch, tz
                    )
                    if new_data is None:
                        output.write(header)
                        output.write(data)
                        output.write(crc)
                    else:
                        write_png_chunk(output, chunk_type, new_data)
                else:
                    output.write(header)
                    copy_exact(source, output, length)
                    crc = source.read(4)
                    if len(crc) != 4:
                        raise MetadataError("PNG chunk CRC 不完整")
                    output.write(crc)
                if chunk_type == b"IEND":
                    break
        return temp_path
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def materialize_metadata(path, info, target_epoch, tz, dest_dir):
    if info.format == "png" and info.requires_materialize:
        return materialize_png(path, target_epoch, tz, dest_dir)
    return None


def tiff_info(reader, target_epoch, tz, label):
    header = reader.read(0, 8)
    if header[:2] == b"II":
        endian = "<"
    elif header[:2] == b"MM":
        endian = ">"
    else:
        raise MetadataError(f"{label}: 不是 TIFF 头")
    if struct.unpack(endian + "H", header[2:4])[0] != 42:
        raise MetadataError(f"{label}: TIFF magic 不正确")
    first_ifd = struct.unpack(endian + "I", header[4:8])[0]
    patches = []
    date_tags = {306, 36867, 36868, 700, 34377, 270}
    visited = set()

    def read_value(entry_offset, tag, typ, count, value_field):
        size = TYPE_SIZES.get(typ, 0) * count
        if size <= 0:
            return None, None
        if size <= 4:
            value_offset = entry_offset + 8
            value = value_field[:size]
        else:
            value_offset = struct.unpack(endian + "I", value_field)[0]
            value = reader.read(value_offset, size)
        return value_offset, value

    def walk(offset, depth):
        if not offset or depth > 4 or offset in visited:
            return
        visited.add(offset)
        count = struct.unpack(endian + "H", reader.read(offset, 2))[0]
        for index in range(count):
            entry_offset = offset + 2 + index * 12
            entry = reader.read(entry_offset, 12)
            tag, typ, item_count = struct.unpack(endian + "HHI", entry[:8])
            value_field = entry[8:12]
            if tag == 0x8769:
                sub = struct.unpack(endian + "I", value_field)[0]
                walk(sub, depth + 1)
                continue
            if tag not in date_tags:
                continue
            value_offset, value = read_value(
                entry_offset, tag, typ, item_count, value_field
            )
            if value is None:
                continue
            for match in DATE_RE.finditer(value):
                old = match.group(0)
                new = target_string(old, target_epoch, tz)
                if new is None:
                    raise MetadataError(f"{label} tag {tag}: 无法生成等长目标时间")
                patches.append(
                    Patch(
                        value_offset + match.start(),
                        old,
                        new,
                        f"{label} tag {tag}",
                    )
                )
        next_offset = struct.unpack(
            endian + "I", reader.read(offset + 2 + count * 12, 4)
        )[0]
        if next_offset:
            walk(next_offset, depth + 1)

    walk(first_ifd, 0)
    return patches


def jpeg_info(reader, target_epoch, tz):
    if reader.read(0, 2) != b"\xff\xd8":
        return None
    position = 2
    patches = []
    notes = []
    while position + 2 <= reader.size:
        if reader.read(position, 1) != b"\xff":
            break
        marker = reader.read(position + 1, 1)[0]
        if marker == 0xDA:
            break
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            position += 2
            continue
        if position + 4 > reader.size:
            break
        length = struct.unpack(">H", reader.read(position + 2, 2))[0]
        if length < 2:
            break
        body_offset = position + 4
        body_length = length - 2
        body = reader.read(body_offset, body_length)
        if marker == 0xFE:
            patches.extend(
                string_patches(body_offset, body, target_epoch, tz, "JPEG COM")
            )
        elif marker == 0xE1:
            if body.startswith(b"Exif\x00\x00"):
                tiff = tiff_info(
                    BytesReader(body[6:]), target_epoch, tz, "JPEG Exif"
                )
                patches.extend(
                    Patch(
                        body_offset + 6 + patch.offset,
                        patch.old,
                        patch.new,
                        patch.field,
                    )
                    for patch in tiff
                )
            elif body.startswith(XMP_PREFIX):
                text_offset = body_offset + len(XMP_PREFIX)
                patches.extend(
                    string_patches(
                        text_offset,
                        body[len(XMP_PREFIX) :],
                        target_epoch,
                        tz,
                        "JPEG XMP",
                    )
                )
        elif marker == 0xED:
            patches.extend(
                string_patches(body_offset, body, target_epoch, tz, "JPEG APP13")
            )
        position = body_offset + body_length
    return MetadataInfo("jpeg", patches, notes)


def detect_bmff(path):
    with open(path, "rb") as handle:
        header = handle.read(16)
    if len(header) < 12 or header[4:8] != b"ftyp":
        return None
    brand = header[8:12]
    if brand in (b"qt  ", b"qt\x20\x20"):
        return "mov"
    if brand in (b"avif", b"avis"):
        return "avif"
    return "mp4"


def mp4_info(reader, target_epoch, tz, format_name):
    patches = []
    notes = []

    def patch_time(atom_type, body, atom_end):
        if body + 4 > atom_end:
            return
        version = reader.read(body, 1)[0]
        if version == 0:
            creation_offset = body + 4
            modification_offset = body + 8
            width = 4
            fmt = ">I"
        elif version == 1:
            creation_offset = body + 4
            modification_offset = body + 12
            width = 8
            fmt = ">Q"
        else:
            return
        target = target_epoch + QT_EPOCH_OFFSET
        if target > (0xFFFFFFFF if width == 4 else 0xFFFFFFFFFFFFFFFF):
            raise MetadataError("目标时间超出 MP4 时间范围")
        for name, offset in (
            ("creation", creation_offset),
            ("modification", modification_offset),
        ):
            old = reader.read(offset, width)
            old_value = struct.unpack(fmt, old)[0]
            if old_value == 0:
                continue
            new = struct.pack(fmt, target)
            patches.append(
                Patch(offset, old, new, f"{atom_type.decode()} {name}")
            )

    def walk(start, end, depth):
        if depth > 10:
            return
        position = start
        while position + 8 <= end:
            size = struct.unpack(">I", reader.read(position, 4))[0]
            atom_type = reader.read(position + 4, 4)
            header = 8
            if size == 1:
                if position + 16 > end:
                    break
                size = struct.unpack(">Q", reader.read(position + 8, 8))[0]
                header = 16
            elif size == 0:
                size = end - position
            if size < header or position + size > end:
                break
            body = position + header
            atom_end = position + size
            if atom_type in (b"mvhd", b"tkhd", b"mdhd"):
                patch_time(atom_type, body, atom_end)
            elif atom_type in (b"\xa9day", b"date", b"creation_time"):
                value = reader.read(body, atom_end - body)
                patches.extend(
                    string_patches(
                        body,
                        value,
                        target_epoch,
                        tz,
                        f"{format_name} {atom_type.decode('latin1')}",
                    )
                )
            if atom_type in (
                b"moov",
                b"trak",
                b"mdia",
                b"minf",
                b"stbl",
                b"udta",
                b"ilst",
                b"edts",
                b"dinf",
                b"mvex",
                b"wave",
            ):
                walk(body, atom_end, depth + 1)
            elif atom_type == b"meta":
                walk(body + 4, atom_end, depth + 1)
            position = atom_end

    walk(0, reader.size, 0)
    return MetadataInfo(format_name, patches, notes)


def read_ebml_id(reader, position):
    first = reader.read(position, 1)[0]
    mask = 0x80
    length = 1
    while length <= 4 and not (first & mask):
        mask >>= 1
        length += 1
    if length > 4:
        raise MetadataError("EBML ID 长度非法")
    return length, int.from_bytes(reader.read(position, length), "big")


def read_ebml_size(reader, position):
    first = reader.read(position, 1)[0]
    mask = 0x80
    length = 1
    while length <= 8 and not (first & mask):
        mask >>= 1
        length += 1
    if length > 8:
        raise MetadataError("EBML size 长度非法")
    value = first & (mask - 1)
    if length > 1:
        value = (value << (8 * (length - 1))) | int.from_bytes(
            reader.read(position + 1, length - 1), "big"
        )
    return length, value, length + 1


def mkv_info(reader, target_epoch, tz):
    patches = []
    notes = []
    containers = {
        0x18538067,
        0x1549A966,
        0x1654AE6B,
        0xAE,
        0xE0,
        0xE1,
        0x1254C367,
        0x7373,
        0x63C0,
    }
    date_tag_names = {
        b"DATE",
        b"DATE_RELEASED",
        b"DATE_ENCODED",
        b"DATE_DIGITIZED",
        b"DATE_TAGGED",
        b"DATE_PURCHASED",
    }

    def parse_simple_tag(start, end):
        position = start
        tag_name = None
        tag_value = None
        tag_value_offset = None
        while position < end:
            id_length, element_id = read_ebml_id(reader, position)
            size_length, size, header_size = read_ebml_size(
                reader, position + id_length
            )
            body = position + id_length + size_length
            if body + size > end:
                break
            if element_id == 0x45A3:
                tag_name = reader.read(body, size)
            elif element_id == 0x4487:
                tag_value = reader.read(body, size)
                tag_value_offset = body
            position = body + size
        if tag_name and tag_value and tag_value_offset is not None:
            name = tag_name.decode("latin1", "replace")
            if name.encode("ascii", "ignore").upper() in date_tag_names or b"DATE" in tag_name.upper():
                patches.extend(
                    string_patches(
                        tag_value_offset,
                        tag_value,
                        target_epoch,
                        tz,
                        f"MKV {name}",
                    )
                )

    def walk(start, end, depth):
        if depth > 20:
            return
        position = start
        while position < end:
            id_length, element_id = read_ebml_id(reader, position)
            size_length, size, header_size = read_ebml_size(
                reader, position + id_length
            )
            body = position + id_length + size_length
            if size == 0xFFFFFFFFFFFFFFFF or body + size > end:
                break
            atom_end = body + size
            if element_id in containers:
                walk(body, atom_end, depth + 1)
            elif element_id == 0x4461 and size == 8:
                old = reader.read(body, 8)
                target_ns = (target_epoch - MATROSKA_EPOCH) * 1_000_000_000
                new = struct.pack(">q", target_ns)
                patches.append(Patch(body, old, new, "MKV DateUTC"))
            elif element_id == 0x67C8:
                parse_simple_tag(body, atom_end)
            position = atom_end

    walk(0, reader.size, 0)
    return MetadataInfo("mkv", patches, notes)


def webp_info(reader, target_epoch, tz):
    header = reader.read(0, 12)
    if header[:4] != b"RIFF" or header[8:12] != b"WEBP":
        return None
    position = 12
    patches = []
    notes = []
    while position + 8 <= reader.size:
        chunk_type = reader.read(position, 4)
        size = struct.unpack("<I", reader.read(position + 4, 4))[0]
        data_offset = position + 8
        if data_offset + size > reader.size:
            break
        if chunk_type == b"EXIF":
            data = reader.read(data_offset, size)
            tiff_data = data[6:] if data.startswith(b"Exif\x00\x00") else data
            tiff = tiff_info(BytesReader(tiff_data), target_epoch, tz, "WebP Exif")
            base = data_offset + (6 if data.startswith(b"Exif\x00\x00") else 0)
            patches.extend(
                Patch(base + patch.offset, patch.old, patch.new, patch.field)
                for patch in tiff
            )
        elif chunk_type == b"XMP ":
            data = reader.read(data_offset, size)
            patches.extend(
                string_patches(data_offset, data, target_epoch, tz, "WebP XMP")
            )
        position = data_offset + size + (size & 1)
    return MetadataInfo("webp", patches, notes)


def find_bytes(reader, needle, chunk_size=1024 * 1024):
    if not needle:
        return -1
    overlap = len(needle) - 1
    position = 0
    tail = b""
    while position < reader.size:
        data = reader.read(position, min(chunk_size, reader.size - position))
        buffer = tail + data
        index = buffer.find(needle)
        if index >= 0:
            return position - len(tail) + index
        tail = buffer[-overlap:] if overlap else b""
        position += len(data)
    return -1


def read_box(reader, position, limit):
    if position + 8 > limit:
        raise MetadataError("BMFF box 头部不完整")
    size = struct.unpack(">I", reader.read(position, 4))[0]
    box_type = reader.read(position + 4, 4)
    header = 8
    if size == 1:
        size = struct.unpack(">Q", reader.read(position + 8, 8))[0]
        header = 16
    elif size == 0:
        size = limit - position
    if size < header or position + size > limit:
        raise MetadataError("BMFF box 尺寸非法")
    return box_type, position + header, position + size


def iter_boxes(reader, start, end):
    position = start
    while position + 8 <= end:
        box_type, body, box_end = read_box(reader, position, end)
        yield box_type, body, box_end
        position = box_end


def read_box_cstring(reader, position, limit):
    data = bytearray()
    while position < limit:
        char = reader.read(position, 1)
        position += 1
        if char == b"\x00":
            return bytes(data), position
        data += char
    raise MetadataError("BMFF 字符串未终止")


def read_uint(reader, position, size):
    if size == 0:
        return 0, position
    return int.from_bytes(reader.read(position, size), "big"), position + size


def avif_items(reader):
    meta = None
    for box_type, body, box_end in iter_boxes(reader, 0, reader.size):
        if box_type == b"meta":
            meta = (body + 4, box_end)
            break
    if meta is None:
        raise MetadataError("AVIF 缺少 meta box")
    iinf = None
    iloc = None
    for box_type, body, box_end in iter_boxes(reader, meta[0], meta[1]):
        if box_type == b"iinf":
            iinf = (body, box_end)
        elif box_type == b"iloc":
            iloc = (body, box_end)
    if iinf is None or iloc is None:
        raise MetadataError("AVIF 缺少 iinf/iloc")

    version = reader.read(iinf[0], 1)[0]
    position = iinf[0] + 4
    if version == 0:
        item_count = struct.unpack(">H", reader.read(position, 2))[0]
        position += 2
    else:
        item_count = struct.unpack(">I", reader.read(position, 4))[0]
        position += 4
    items = {}
    for box_type, body, box_end in iter_boxes(reader, position, iinf[1]):
        if box_type != b"infe":
            continue
        infe_version = reader.read(body, 1)[0]
        cursor = body + 4
        if infe_version in (0, 1):
            item_id = struct.unpack(">H", reader.read(cursor, 2))[0]
            cursor += 4
            item_type = None
        else:
            if infe_version == 3:
                item_id = struct.unpack(">I", reader.read(cursor, 4))[0]
                cursor += 4
            else:
                item_id = struct.unpack(">H", reader.read(cursor, 2))[0]
                cursor += 2
            cursor += 2
            item_type = reader.read(cursor, 4)
            cursor += 4
        _, cursor = read_box_cstring(reader, cursor, box_end)
        content_type = b""
        if item_type == b"mime" or (item_type is None and cursor < box_end):
            content_type, cursor = read_box_cstring(reader, cursor, box_end)
            if cursor < box_end:
                read_box_cstring(reader, cursor, box_end)
        items[item_id] = {
            "type": item_type,
            "content_type": content_type,
            "construction": 0,
            "base": 0,
            "extents": [],
        }

    version = reader.read(iloc[0], 1)[0]
    position = iloc[0] + 4
    first = reader.read(position, 1)[0]
    position += 1
    offset_size = first >> 4
    length_size = first & 0x0F
    second = reader.read(position, 1)[0]
    position += 1
    base_size = second >> 4
    index_size = second & 0x0F
    if version < 2:
        iloc_count = struct.unpack(">H", reader.read(position, 2))[0]
        position += 2
    else:
        iloc_count = struct.unpack(">I", reader.read(position, 4))[0]
        position += 4
    for _ in range(iloc_count):
        if version < 2:
            item_id = struct.unpack(">H", reader.read(position, 2))[0]
            position += 2
        else:
            item_id = struct.unpack(">I", reader.read(position, 4))[0]
            position += 4
        construction = 0
        if version in (1, 2):
            construction = struct.unpack(">H", reader.read(position, 2))[0] & 0x0F
            position += 2
        position += 2
        base_offset, position = read_uint(reader, position, base_size)
        extent_count = struct.unpack(">H", reader.read(position, 2))[0]
        position += 2
        extents = []
        for _ in range(extent_count):
            if version >= 1 and index_size:
                _, position = read_uint(reader, position, index_size)
            extent_offset, position = read_uint(reader, position, offset_size)
            extent_length, position = read_uint(reader, position, length_size)
            extents.append((extent_offset, extent_length))
        item = items.setdefault(item_id, {})
        item["construction"] = construction
        item["base"] = base_offset
        item["extents"] = extents
    return items


def avif_info(reader, target_epoch, tz, path):
    patches = []
    notes = []
    strict_problems = []
    try:
        items = avif_items(reader)
    except Exception as exc:
        items = None
        notes.append(f"AVIF iinf/iloc 解析失败: {exc}")
        strict_problems.append("AVIF 元数据结构无法解析")
    if items is not None:
        for item in items.values():
            item_type = item.get("type")
            content_type = item.get("content_type") or b""
            if item.get("construction", 0) != 0:
                notes.append("AVIF idat construction_method 暂不支持")
                strict_problems.append("AVIF idat 元数据无法改写")
                continue
            extents = item.get("extents") or []
            if len(extents) != 1:
                notes.append("AVIF 元数据 extent 数量不为 1，跳过")
                strict_problems.append("AVIF 多 extent 元数据无法改写")
                continue
            extent_offset, extent_length = extents[0]
            data_offset = item.get("base", 0) + extent_offset
            if item_type == b"Exif":
                data = reader.read(data_offset, extent_length)
                if data[:6] == b"Exif\x00\x00":
                    tiff_data = data[6:]
                    tiff_base = data_offset + 6
                elif len(data) >= 10 and data[4:10] == b"Exif\x00\x00":
                    tiff_offset = int.from_bytes(data[:4], "big")
                    tiff_base = data_offset + 4 + tiff_offset
                    tiff_data = data[4 + tiff_offset :]
                else:
                    tiff_data = data
                    tiff_base = data_offset
                tiff = tiff_info(BytesReader(tiff_data), target_epoch, tz, "AVIF Exif")
                patches.extend(
                    Patch(tiff_base + patch.offset, patch.old, patch.new, patch.field)
                    for patch in tiff
                )
            elif item_type == b"mime" and (
                b"rdf+xml" in content_type or b"XMP" in content_type
            ):
                data = reader.read(data_offset, extent_length)
                patches.extend(
                    string_patches(data_offset, data, target_epoch, tz, "AVIF XMP")
                )
        return MetadataInfo("avif", patches, notes, strict_problems)

    try:
        from PIL import Image
    except ImportError:
        notes.append("未安装 Pillow，AVIF 回退扫描不可用")
        strict_problems.append("AVIF Exif 无法确认")
        return MetadataInfo("avif", [], notes, strict_problems)
    try:
        with Image.open(path) as image:
            exif = image.info.get("exif")
    except Exception as exc:
        notes.append(f"无法读取 AVIF Exif: {exc}")
        strict_problems.append("AVIF Exif 无法读取")
        return MetadataInfo("avif", [], notes, strict_problems)
    if not exif:
        return MetadataInfo("avif", [], notes, strict_problems)
    index = find_bytes(reader, exif)
    if index < 0:
        notes.append("AVIF Exif 未在文件中找到，跳过")
        strict_problems.append("AVIF Exif 未定位")
        return MetadataInfo("avif", [], notes, strict_problems)
    tiff_data = exif[6:] if exif.startswith(b"Exif\x00\x00") else exif
    tiff = tiff_info(BytesReader(tiff_data), target_epoch, tz, "AVIF Exif")
    patches = [
        Patch(
            index + (6 if exif.startswith(b"Exif\x00\x00") else 0) + patch.offset,
            patch.old,
            patch.new,
            patch.field,
        )
        for patch in tiff
    ]
    return MetadataInfo("avif", patches, notes, strict_problems)


def detect_format(path):
    with open(path, "rb") as handle:
        header = handle.read(16)
    if header[:4] == b"v/1\x01":
        return "exr"
    if header.startswith(PNG_SIG):
        return "png"
    if header[:2] == b"\xff\xd8":
        return "jpeg"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    if header[:4] == b"\x1a\x45\xdf\xa3":
        return "mkv"
    bmff = detect_bmff(path)
    if bmff:
        return bmff
    if header[:2] in (b"II", b"MM"):
        return "tiff"
    return None


def build_metadata_patches(path, target_epoch, tz):
    format_name = detect_format(path)
    if not format_name:
        return MetadataInfo(
            "unknown",
            [],
            ["未识别的文件格式"],
            ["未识别的文件格式"],
        )
    reader = FileReader(path)
    try:
        if format_name == "exr":
            info = exr_info(reader, target_epoch, tz)
        elif format_name == "png":
            info = png_info(reader, target_epoch, tz)
        elif format_name == "jpeg":
            info = jpeg_info(reader, target_epoch, tz)
        elif format_name == "tiff":
            info = MetadataInfo(
                "tiff", tiff_info(reader, target_epoch, tz, "TIFF")
            )
        elif format_name in ("mp4", "mov"):
            info = mp4_info(reader, target_epoch, tz, format_name)
        elif format_name == "mkv":
            info = mkv_info(reader, target_epoch, tz)
        elif format_name == "webp":
            info = webp_info(reader, target_epoch, tz)
        elif format_name == "avif":
            info = avif_info(reader, target_epoch, tz, path)
        else:
            info = MetadataInfo(format_name, [], ["未支持该格式"])
    finally:
        reader.close()
    if info is None:
        return MetadataInfo(
            "unknown", [], ["格式识别失败"], ["格式识别失败"]
        )
    patches = sorted(info.patches, key=lambda patch: patch.offset)
    last_end = -1
    for patch in patches:
        if patch.offset < last_end:
            raise MetadataError(f"{path}: 补丁区间重叠")
        if len(patch.old) != len(patch.new):
            raise MetadataError(f"{path}: {patch.field} 补丁长度不一致")
        last_end = patch.offset + len(patch.old)
    info.patches = patches
    return info