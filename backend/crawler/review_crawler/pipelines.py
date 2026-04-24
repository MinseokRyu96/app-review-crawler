import sys
import os

# pipelines.py → review_crawler/ → crawler/ → backend/
_BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from models.database import SessionLocal, Review


class PostgresPipeline:
    def open_spider(self, spider):
        self.db = SessionLocal()
        self.buffer = []

    def close_spider(self, spider):
        self._flush()
        self.db.close()

    def process_item(self, item, spider):
        self.buffer.append(
            Review(
                job_id=item.get("job_id", ""),
                store=item.get("store", ""),
                author=item.get("author", ""),
                rating=int(item.get("rating", 0)),
                title=item.get("title", ""),
                content=item.get("content", ""),
                review_date=item.get("date", ""),
                version=item.get("version", ""),
            )
        )
        if len(self.buffer) >= 50:
            self._flush()
        return item

    def _flush(self):
        if not self.buffer:
            return
        try:
            self.db.bulk_save_objects(self.buffer)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        finally:
            self.buffer = []
