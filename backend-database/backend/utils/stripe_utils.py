from typing import Literal, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta

def get_end_coupon_timestamp(start_timestamp:int, duration:Literal['once', 'repeating', 'forever'], months:Optional[int]=None) -> Optional[float]:
    # when duration is forever
    if duration not in ['once', 'repeating']:
        return None
    
    start_time = datetime.fromtimestamp(start_timestamp)
    if duration == 'once':
        end_time = start_time + relativedelta(months=1)
    elif duration == 'repeating':
        end_time = start_time + relativedelta(months=months)

    return end_time.timestamp()
