use crate::{PackError, MAX_ENTRIES};

const LOCAL_HEADER: u32 = 0x0403_4b50;
const CENTRAL_HEADER: u32 = 0x0201_4b50;
const EOCD: u32 = 0x0605_4b50;
const FLAG_UTF8: u16 = 0x0800;
const VERSION: u16 = 20;

pub struct ZipEntry<'a> {
    pub name: &'a str,
    pub dos: moyu_core::DosTime,
    pub data: &'a [u8],
}

pub fn write_zip(entries: &[ZipEntry<'_>]) -> Result<Vec<u8>, PackError> {
    if entries.len() > MAX_ENTRIES {
        return Err(PackError::Limit(format!(
            "条目数 {} 超过 {MAX_ENTRIES}",
            entries.len()
        )));
    }
    let mut output = Vec::new();
    let mut central = Vec::new();

    for entry in entries {
        validate_name(entry.name)?;
        let name = entry.name.as_bytes();
        if name.len() > u16::MAX as usize {
            return Err(PackError::Name(format!("文件名过长: {}", entry.name)));
        }
        if entry.data.len() > 0xFFFF_FFFF {
            return Err(PackError::Limit(format!("{} 超过 4GiB", entry.name)));
        }
        if output.len() > 0xFFFF_FFFF {
            return Err(PackError::Limit("归档超过 4GiB".into()));
        }
        let (date, time) = entry.dos.to_words();
        let crc = crc32(entry.data);
        let size = entry.data.len() as u32;
        let offset = output.len() as u32;

        push_u32(&mut output, LOCAL_HEADER);
        push_u16(&mut output, VERSION);
        push_u16(&mut output, FLAG_UTF8);
        push_u16(&mut output, 0);
        push_u16(&mut output, time);
        push_u16(&mut output, date);
        push_u32(&mut output, crc);
        push_u32(&mut output, size);
        push_u32(&mut output, size);
        push_u16(&mut output, name.len() as u16);
        push_u16(&mut output, 0);
        output.extend_from_slice(name);
        output.extend_from_slice(entry.data);

        push_u32(&mut central, CENTRAL_HEADER);
        push_u16(&mut central, VERSION);
        push_u16(&mut central, VERSION);
        push_u16(&mut central, FLAG_UTF8);
        push_u16(&mut central, 0);
        push_u16(&mut central, time);
        push_u16(&mut central, date);
        push_u32(&mut central, crc);
        push_u32(&mut central, size);
        push_u32(&mut central, size);
        push_u16(&mut central, name.len() as u16);
        push_u16(&mut central, 0);
        push_u16(&mut central, 0);
        push_u16(&mut central, 0);
        push_u16(&mut central, 0);
        push_u32(&mut central, 0);
        push_u32(&mut central, offset);
        central.extend_from_slice(name);
    }

    if central.len() > 0xFFFF_FFFF {
        return Err(PackError::Limit("中央目录超过 4GiB".into()));
    }
    let central_offset = output.len() as u32;
    let central_size = central.len() as u32;
    output.extend_from_slice(&central);
    let count = entries.len() as u16;

    push_u32(&mut output, EOCD);
    push_u16(&mut output, 0);
    push_u16(&mut output, 0);
    push_u16(&mut output, count);
    push_u16(&mut output, count);
    push_u32(&mut output, central_size);
    push_u32(&mut output, central_offset);
    push_u16(&mut output, 0);
    Ok(output)
}

fn validate_name(name: &str) -> Result<(), PackError> {
    if name.is_empty() {
        return Err(PackError::Name("空文件名".into()));
    }
    if name.starts_with('/') || name.starts_with('\\') || name.contains('\\') {
        return Err(PackError::Name(format!("绝对路径或反斜杠: {name}")));
    }
    for part in name.split('/') {
        if part.is_empty() || part == "." || part == ".." {
            return Err(PackError::Name(format!("非法路径段: {name}")));
        }
    }
    Ok(())
}

fn push_u16(target: &mut Vec<u8>, value: u16) {
    target.extend_from_slice(&value.to_le_bytes());
}

fn push_u32(target: &mut Vec<u8>, value: u32) {
    target.extend_from_slice(&value.to_le_bytes());
}

pub fn crc32(data: &[u8]) -> u32 {
    let mut table = [0u32; 256];
    for (index, slot) in table.iter_mut().enumerate() {
        let mut value = index as u32;
        for _ in 0..8 {
            value = if value & 1 == 1 {
                0xEDB8_8320 ^ (value >> 1)
            } else {
                value >> 1
            };
        }
        *slot = value;
    }
    let mut crc = 0xFFFF_FFFFu32;
    for byte in data {
        crc = table[((crc ^ u32::from(*byte)) & 0xFF) as usize] ^ (crc >> 8);
    }
    crc ^ 0xFFFF_FFFF
}

#[cfg(test)]
mod tests {
    use super::*;
    use moyu_core::DosTime;

    #[test]
    fn crc32_known_vector() {
        assert_eq!(crc32(b"123456789"), 0xCBF4_3926);
    }

    #[test]
    fn rejects_unsafe_names() {
        let dos = DosTime::new(2026, 1, 2, 3, 4, 4).expect("dos");
        for name in ["", "/a", "a/../b", "a\\b", "a//b", "./a"] {
            let entry = ZipEntry {
                name,
                dos,
                data: b"x",
            };
            assert!(write_zip(&[entry]).is_err());
        }
    }
}
