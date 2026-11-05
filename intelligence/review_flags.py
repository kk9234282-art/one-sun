"""Evidence-linked audit flags. These never change source facts or manual review status."""
import json
from functools import lru_cache
from pathlib import Path
@lru_cache(maxsize=1)
def flags():
    data=json.loads((Path(__file__).parent/'data/activity-review-flags.json').read_text())
    return {row['cin']:row for row in data['flags']}
def flag_for(cin):return flags().get(cin)
