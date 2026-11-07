use std::fmt;

use moyu_core::{plan_times, DosTime, SourceTime, TimeError};

mod zip;

pub use zip::{write_zip, ZipEntry};

pub const CRATE_NAME: &str = "moyu-wasm-client";
pub const MAX_ENTRIES: usize = 65_535;
pub const MAX_ENTRY_BYTES: usize = 0xFFFF_FFFF;
pub const DEFAULT_MAX_INPUT_BYTES: usize = 512 * 1024 * 1024;
pub const MAX_TRANSCODE_PIXELS: u64 = 64 * 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PackError {
    Time(TimeError),
    Name(String),
    Limit(String),
    Transcode(String),
}

impl fmt::Display for PackError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Time(error) => write!(formatter, "时间计划失败: {error}"),
            Self::Name(message) => write!(formatter, "条目名非法: {message}"),
            Self::Limit(message) => write!(formatter, "超出客户端限制: {message}"),
            Self::Transcode(message) => write!(formatter, "转码失败: {message}"),
        }
    }
}

impl std::error::Error for PackError {}

impl From<TimeError> for PackError {
    fn from(error: TimeError) -> Self {
        Self::Time(error)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientFile {
    pub name: String,
    pub mtime_ns: i64,
    pub data: Vec<u8>,
}

impl ClientFile {
    pub fn new(name: impl Into<String>, mtime_ns: i64, data: Vec<u8>) -> Self {
        Self {
            name: name.into(),
            mtime_ns,
            data,
        }
    }
}

pub fn pack(
    files: &[ClientFile],
    target_epoch: i64,
    utc_offset_seconds: i32,
) -> Result<Vec<u8>, PackError> {
    if files.len() > MAX_ENTRIES {
        return Err(PackError::Limit(format!(
            "条目数 {} 超过 {MAX_ENTRIES}",
            files.len()
        )));
    }
    let sources: Vec<SourceTime> = files
        .iter()
        .map(|file| SourceTime {
            id: file.name.clone(),
            mtime_ns: file.mtime_ns,
        })
        .collect();
    let plan = plan_times(&sources, target_epoch, utc_offset_seconds)?;
    let mut entries = Vec::with_capacity(files.len());
    for (file, planned) in files.iter().zip(plan.entries.iter()) {
        if file.data.len() > MAX_ENTRY_BYTES {
            return Err(PackError::Limit(format!("{} 超过 4GiB", file.name)));
        }
        entries.push(ZipEntry {
            name: &file.name,
            dos: planned.dos,
            data: &file.data,
        });
    }
    write_zip(&entries)
}

pub fn transcode_image(
    data: &[u8],
    max_width: u32,
    max_height: u32,
    format: &str,
    quality: u8,
) -> Result<Vec<u8>, PackError> {
    if max_width == 0 || max_height == 0 {
        return Err(PackError::Transcode("尺寸必须为正".into()));
    }
    let image = image::load_from_memory(data)
        .map_err(|error| PackError::Transcode(format!("解码失败: {error}")))?;
    if u64::from(image.width()) * u64::from(image.height()) > MAX_TRANSCODE_PIXELS {
        return Err(PackError::Limit(format!(
            "像素数超过 {}",
            MAX_TRANSCODE_PIXELS
        )));
    }
    let resized = image.resize(max_width, max_height, image::imageops::FilterType::Lanczos3);
    let mut output = Vec::new();
    match format.to_ascii_lowercase().as_str() {
        "png" => {
            resized
                .write_to(
                    &mut std::io::Cursor::new(&mut output),
                    image::ImageFormat::Png,
                )
                .map_err(|error| PackError::Transcode(format!("PNG 编码失败: {error}")))?;
        }
        "jpeg" | "jpg" => {
            use image::ImageEncoder;
            let rgb = resized.to_rgb8();
            let encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(
                &mut output,
                quality.clamp(1, 100),
            );
            encoder
                .write_image(
                    rgb.as_raw(),
                    rgb.width(),
                    rgb.height(),
                    image::ExtendedColorType::Rgb8,
                )
                .map_err(|error| PackError::Transcode(format!("JPEG 编码失败: {error}")))?;
        }
        other => return Err(PackError::Transcode(format!("不支持的输出格式: {other}"))),
    }
    Ok(output)
}

pub fn dos_words(dos: DosTime) -> (u16, u16) {
    dos.to_words()
}

#[cfg(target_arch = "wasm32")]
mod bindings {
    use super::*;
    use wasm_bindgen::prelude::*;

    #[wasm_bindgen]
    pub struct PackBuilder {
        files: Vec<ClientFile>,
        max_input_bytes: usize,
        buffered: usize,
    }

    #[wasm_bindgen]
    impl PackBuilder {
        #[wasm_bindgen(constructor)]
        pub fn new() -> Self {
            Self {
                files: Vec::new(),
                max_input_bytes: DEFAULT_MAX_INPUT_BYTES,
                buffered: 0,
            }
        }

        pub fn add_file(&mut self, name: &str, mtime_ns: i64, data: &[u8]) -> Result<(), JsValue> {
            if self.files.len() >= MAX_ENTRIES {
                return Err(JsValue::from_str("条目数超过 65535"));
            }
            if self.buffered + data.len() > self.max_input_bytes {
                return Err(JsValue::from_str("客户端 ZIP 内存上限"));
            }
            self.files
                .push(ClientFile::new(name, mtime_ns, data.to_vec()));
            self.buffered += data.len();
            Ok(())
        }

        pub fn finish(
            &self,
            target_epoch: i64,
            utc_offset_seconds: i32,
        ) -> Result<Vec<u8>, JsValue> {
            pack(&self.files, target_epoch, utc_offset_seconds)
                .map_err(|error| JsValue::from_str(&error.to_string()))
        }
    }

    #[wasm_bindgen]
    pub fn transcode(
        data: &[u8],
        max_width: u32,
        max_height: u32,
        format: &str,
        quality: u8,
    ) -> Result<Vec<u8>, JsValue> {
        transcode_image(data, max_width, max_height, format, quality)
            .map_err(|error| JsValue::from_str(&error.to_string()))
    }

    #[wasm_bindgen]
    pub fn capabilities() -> String {
        format!(
            "{{\"format\":\"zip-store\",\"metadata\":\"dos-only\",\"transcode\":[\"png\",\"jpeg\"],\"maxInputBytes\":{},\"maxEntries\":{}}}",
            DEFAULT_MAX_INPUT_BYTES, MAX_ENTRIES
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn target() -> i64 {
        1_800_000_000
    }

    fn read_u16(data: &[u8], offset: usize) -> u16 {
        u16::from_le_bytes([data[offset], data[offset + 1]])
    }

    fn read_u32(data: &[u8], offset: usize) -> u32 {
        u32::from_le_bytes([
            data[offset],
            data[offset + 1],
            data[offset + 2],
            data[offset + 3],
        ])
    }

    #[test]
    fn writes_store_archive_without_extra_fields() {
        let files = vec![
            ClientFile::new("a.txt", (target() - 100) * 1_000_000_000, b"hello".to_vec()),
            ClientFile::new("dir/b.bin", (target() - 90) * 1_000_000_000, vec![7; 32]),
        ];
        let archive = pack(&files, target(), 0).expect("pack");
        assert_eq!(&archive[..4], &[0x50, 0x4b, 0x03, 0x04]);

        let eocd = archive.len() - 22;
        assert_eq!(read_u32(&archive, eocd), 0x0605_4b50);
        let count = read_u16(&archive, eocd + 10);
        assert_eq!(count, 2);
        let central_offset = read_u32(&archive, eocd + 16) as usize;
        let central_size = read_u32(&archive, eocd + 12) as usize;
        assert_eq!(central_offset + central_size, eocd);

        let mut position = central_offset;
        let mut names = Vec::new();
        for _ in 0..count {
            assert_eq!(read_u32(&archive, position), 0x0201_4b50);
            let flags = read_u16(&archive, position + 8);
            let method = read_u16(&archive, position + 10);
            let extra_len = read_u16(&archive, position + 30);
            let comment_len = read_u16(&archive, position + 32);
            let name_len = read_u16(&archive, position + 28) as usize;
            let size = read_u32(&archive, position + 24);
            let local_offset = read_u32(&archive, position + 42) as usize;
            assert_eq!(flags & 0x0800, 0x0800);
            assert_eq!(method, 0);
            assert_eq!(extra_len, 0);
            assert_eq!(comment_len, 0);
            let name = String::from_utf8(archive[position + 46..position + 46 + name_len].to_vec())
                .expect("name");
            names.push(name.clone());

            assert_eq!(read_u32(&archive, local_offset), 0x0403_4b50);
            let local_extra = read_u16(&archive, local_offset + 28);
            let local_name = read_u16(&archive, local_offset + 26) as usize;
            assert_eq!(local_extra, 0);
            let data_offset = local_offset + 30 + local_name;
            assert_eq!(read_u32(&archive, local_offset + 18), size);
            assert_eq!(
                read_u32(&archive, local_offset + 22),
                size,
                "STORE 的压缩大小应等于原始大小"
            );
            let end = data_offset + size as usize;
            assert!(end <= archive.len());
            position += 46 + name_len;
        }
        assert_eq!(names, vec!["a.txt", "dir/b.bin"]);
    }

    #[test]
    fn applies_same_delta_and_even_seconds() {
        let files = vec![
            ClientFile::new("a.txt", (target() - 100) * 1_000_000_000, b"a".to_vec()),
            ClientFile::new("b.txt", (target() - 90) * 1_000_000_000, b"b".to_vec()),
        ];
        let archive = pack(&files, target(), 0).expect("pack");
        let eocd = archive.len() - 22;
        let central_offset = read_u32(&archive, eocd + 16) as usize;
        let mut position = central_offset;
        let mut epochs = Vec::new();
        for _ in 0..2 {
            let name_len = read_u16(&archive, position + 28) as usize;
            let time = read_u16(&archive, position + 12);
            let date = read_u16(&archive, position + 14);
            epochs.push(decode_dos(date, time));
            position += 46 + name_len;
        }
        assert_eq!(epochs[1], target());
        assert_eq!(epochs[0], target() - 10);
        assert_eq!(epochs[0] % 2, 0);
    }

    fn decode_dos(date: u16, time: u16) -> i64 {
        let year = ((date >> 9) & 0x7F) as i64 + 1980;
        let month = ((date >> 5) & 0x0F) as i64;
        let day = (date & 0x1F) as i64;
        let hour = ((time >> 11) & 0x1F) as i64;
        let minute = ((time >> 5) & 0x3F) as i64;
        let second = ((time & 0x1F) * 2) as i64;
        let days = days_from_civil(year, month, day);
        days * 86_400 + hour * 3_600 + minute * 60 + second
    }

    fn days_from_civil(year: i64, month: i64, day: i64) -> i64 {
        let year = if month <= 2 { year - 1 } else { year };
        let era = if year >= 0 { year } else { year - 399 } / 400;
        let yoe = year - era * 400;
        let month_prime = if month > 2 { month - 3 } else { month + 9 };
        let doy = (153 * month_prime + 2) / 5 + day - 1;
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        era * 146_097 + doe - 719_468
    }

    fn sample_png(width: u32, height: u32) -> Vec<u8> {
        use image::{DynamicImage, ImageFormat, Rgba, RgbaImage};
        let image = RgbaImage::from_pixel(width, height, Rgba([30, 80, 150, 255]));
        let mut output = Vec::new();
        DynamicImage::ImageRgba8(image)
            .write_to(&mut std::io::Cursor::new(&mut output), ImageFormat::Png)
            .expect("png");
        output
    }

    #[test]
    fn transcodes_png_to_jpeg_and_png() {
        let source = sample_png(80, 40);
        let jpeg = transcode_image(&source, 20, 20, "jpeg", 80).expect("jpeg");
        assert_eq!(&jpeg[..2], &[0xFF, 0xD8]);
        let decoded = image::load_from_memory(&jpeg).expect("decode jpeg");
        assert!(decoded.width() <= 20 && decoded.height() <= 20);

        let png = transcode_image(&source, 16, 16, "png", 80).expect("png");
        assert_eq!(&png[..8], b"\x89PNG\r\n\x1a\n");
    }

    #[test]
    fn transcode_rejects_bad_input_and_format() {
        assert!(matches!(
            transcode_image(b"not an image", 10, 10, "jpeg", 80),
            Err(PackError::Transcode(_))
        ));
        let source = sample_png(4, 4);
        assert!(matches!(
            transcode_image(&source, 10, 10, "webp", 80),
            Err(PackError::Transcode(_))
        ));
    }

    #[test]
    fn rejects_unsafe_names() {
        for name in [
            "",
            "/abs.txt",
            "../up.txt",
            "a/../b.txt",
            "a\\b.txt",
            "a//b.txt",
        ] {
            let file = ClientFile::new(name, (target() - 10) * 1_000_000_000, b"x".to_vec());
            assert!(matches!(
                pack(&[file], target(), 0),
                Err(PackError::Name(_))
            ));
        }
    }

    #[test]
    fn rejects_late_target_and_empty_input() {
        assert!(matches!(
            pack(&[], target(), 0),
            Err(PackError::Time(TimeError::Empty))
        ));
        let file = ClientFile::new("a.txt", target() * 1_000_000_000, b"x".to_vec());
        assert!(matches!(
            pack(&[file], target(), 0),
            Err(PackError::Time(TimeError::TargetNotLater))
        ));
    }
}
