"""Progress tracking for transcription."""
from __future__ import annotations

from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ProgressInfo:
    """Progress information."""
    current: float
    total: float
    message: str
    start_time: Optional[datetime] = None
    
    @property
    def percentage(self) -> float:
        """Get progress percentage."""
        if self.total == 0:
            return 0.0
        return min(self.current / self.total, 1.0) * 100.0
    
    @property
    def estimated_time_remaining(self) -> Optional[timedelta]:
        """Estimate time remaining."""
        if not self.start_time or self.current == 0:
            return None
        
        elapsed = datetime.now() - self.start_time
        if self.current > 0:
            rate = self.current / elapsed.total_seconds()
            remaining = (self.total - self.current) / rate
            return timedelta(seconds=int(remaining))
        return None

