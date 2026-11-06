use std::fmt;

pub const CRATE_NAME: &str = "moyu-core";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceTime {
    pub id: String,
    pub mtime_ns: i64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DosTime {
    pub year: u16,
    pub month: u8,
    pub day: u8,
    pub hour: u8,
    pub minute: u8,
    pub second: u8,
}

impl DosTime {
    pub fn new(
        year: i32,
        month: u32,
        day: u32,
        hour: u32,
        minute: u32,
        second: u32,
    ) -> Result<Self, TimeError> {
        if !(1980..=2107).contains(&year) {
            return Err(TimeError::DosOutOfRange);
        }
        if !(1..=12).contains(&month) {
            return Err(TimeError::DosOutOfRange);
        }
        if !(1..=31).contains(&day) {
            return Err(TimeError::DosOutOfRange);
        }
        if hour > 23 || minute > 59 || second > 58 || !second.is_multiple_of(2) {
            return Err(TimeError::DosOutOfRange);
        }
        Ok(Self {
            year: year as u16,
            month: month as u8,
            day: day as u8,
            hour: hour as u8,
            minute: minute as u8,
            second: second as u8,
        })
    }

    pub fn to_words(self) -> (u16, u16) {
        let date = ((self.year - 1980) << 9) | (u16::from(self.month) << 5) | u16::from(self.day);
        let time = (u16::from(self.hour) << 11)
            | (u16::from(self.minute) << 5)
            | (u16::from(self.second) / 2);
        (date, time)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlanEntry {
    pub id: String,
    pub source_mtime_ns: i64,
    pub target_epoch: i64,
    pub dos: DosTime,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TimePlan {
    pub target_epoch: i64,
    pub delta_ns: i64,
    pub utc_offset_seconds: i32,
    pub entries: Vec<PlanEntry>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TimeError {
    Empty,
    TargetNotLater,
    DosOutOfRange,
    Overflow,
}

impl fmt::Display for TimeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => write!(formatter, "没有源文件"),
            Self::TargetNotLater => write!(formatter, "目标时间不晚于最新源时间"),
            Self::DosOutOfRange => write!(formatter, "DOS 时间越界"),
            Self::Overflow => write!(formatter, "时间计算溢出"),
        }
    }
}

impl std::error::Error for TimeError {}

pub fn floor_dos_second(second: u8) -> u8 {
    second & !1
}

pub fn dos_from_unix(epoch_seconds: i64, utc_offset_seconds: i32) -> Result<DosTime, TimeError> {
    let local = i128::from(epoch_seconds) + i128::from(utc_offset_seconds);
    let days = local.div_euclid(86_400);
    let seconds_of_day = local.rem_euclid(86_400) as u32;
    let days = i64::try_from(days).map_err(|_| TimeError::Overflow)?;
    let (year, month, day) = civil_from_days(days);
    let hour = seconds_of_day / 3_600;
    let minute = (seconds_of_day % 3_600) / 60;
    let second = seconds_of_day % 60;
    DosTime::new(
        year,
        month,
        day,
        hour,
        minute,
        u32::from(floor_dos_second(second as u8)),
    )
}

pub fn plan_times(
    sources: &[SourceTime],
    target_epoch: i64,
    utc_offset_seconds: i32,
) -> Result<TimePlan, TimeError> {
    let max_mtime_ns = sources
        .iter()
        .map(|source| source.mtime_ns)
        .max()
        .ok_or(TimeError::Empty)?;
    let target_ns = i128::from(target_epoch) * 1_000_000_000;
    let delta_ns = target_ns - i128::from(max_mtime_ns);
    if delta_ns <= 0 {
        return Err(TimeError::TargetNotLater);
    }
    let delta_ns = i64::try_from(delta_ns).map_err(|_| TimeError::Overflow)?;
    let mut entries = Vec::with_capacity(sources.len());
    for source in sources {
        let shifted_ns = i128::from(source.mtime_ns) + i128::from(delta_ns);
        let target_epoch =
            i64::try_from(shifted_ns.div_euclid(1_000_000_000)).map_err(|_| TimeError::Overflow)?;
        let dos = dos_from_unix(target_epoch, utc_offset_seconds)?;
        entries.push(PlanEntry {
            id: source.id.clone(),
            source_mtime_ns: source.mtime_ns,
            target_epoch,
            dos,
        });
    }
    Ok(TimePlan {
        target_epoch,
        delta_ns,
        utc_offset_seconds,
        entries,
    })
}

fn civil_from_days(days: i64) -> (i32, u32, u32) {
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let year = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = if month <= 2 { year + 1 } else { year };
    (year as i32, month as u32, day as u32)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn floors_odd_seconds() {
        assert_eq!(floor_dos_second(0), 0);
        assert_eq!(floor_dos_second(5), 4);
        assert_eq!(floor_dos_second(58), 58);
    }

    #[test]
    fn converts_epoch_to_dos() {
        let dos = dos_from_unix(315_532_800, 0).expect("1980 epoch");
        assert_eq!(
            dos,
            DosTime {
                year: 1980,
                month: 1,
                day: 1,
                hour: 0,
                minute: 0,
                second: 0
            }
        );
        let dos = dos_from_unix(315_532_800 + 86_400 + 45_296, 0).expect("1980+1 day");
        assert_eq!(dos.day, 2);
        assert_eq!(dos.hour, 12);
        assert_eq!(dos.minute, 34);
        assert_eq!(dos.second, 56);
        let (date, time) = dos.to_words();
        assert_eq!(date, 34);
        assert_eq!(time, (12 << 11) | (34 << 5) | 28);
    }

    #[test]
    fn plans_relative_times() {
        let target = 1_800_000_000;
        let sources = vec![
            SourceTime {
                id: "a".to_string(),
                mtime_ns: (target - 100) * 1_000_000_000,
            },
            SourceTime {
                id: "b".to_string(),
                mtime_ns: (target - 90) * 1_000_000_000,
            },
            SourceTime {
                id: "c".to_string(),
                mtime_ns: (target - 80) * 1_000_000_000,
            },
        ];
        let plan = plan_times(&sources, target, 8 * 3_600).expect("plan");
        assert_eq!(plan.delta_ns, 80_000_000_000);
        assert_eq!(plan.entries[0].target_epoch, target - 20);
        assert_eq!(plan.entries[1].target_epoch, target - 10);
        assert_eq!(plan.entries[2].target_epoch, target);
        assert_eq!(plan.entries[0].dos.year, 2027);
    }

    #[test]
    fn rejects_empty_and_late_target() {
        assert_eq!(plan_times(&[], 0, 0), Err(TimeError::Empty));
        let source = SourceTime {
            id: "a".to_string(),
            mtime_ns: 1_800_000_000_000_000_000,
        };
        assert_eq!(
            plan_times(&[source], 1_800_000_000, 0),
            Err(TimeError::TargetNotLater)
        );
    }

    #[test]
    fn rejects_dos_out_of_range() {
        assert_eq!(dos_from_unix(0, 0), Err(TimeError::DosOutOfRange));
        assert_eq!(
            DosTime::new(1979, 12, 31, 23, 59, 58),
            Err(TimeError::DosOutOfRange)
        );
        assert_eq!(
            DosTime::new(2108, 1, 1, 0, 0, 0),
            Err(TimeError::DosOutOfRange)
        );
    }
}
