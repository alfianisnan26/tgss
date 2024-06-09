import sqlite3
import threading
from typing import List
from tgss.internal.model import Video, WorkerSession, Filter
import logging

class DB:
    tab_video = "tab_video"
    tab_preview = "tab_preview"
    tab_worker_session = "tab_worker_session"

    def __init__(self, db_name='local.db'):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db_name = db_name
        self._local = threading.local()
        self.__init_tables()

    def _get_connection(self):
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(self.db_name)
        return self._local.connection

    def execute_query(self, query, *args):
        self.logger.debug(f"execute_query: Execute Query {query} {args}")
        connection = self._get_connection()
        cursor = connection.cursor()
        cursor.execute(query, args)
        connection.commit()
        return cursor.fetchall()

    def __create_table(self, table_name, columns):
        column_definitions = ', '.join([f"{col_name} {col_type}" for col_name, col_type, index_name in columns])
        create_table_query = f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                {column_definitions}
            )
        '''
        self.execute_query(create_table_query)

        # Create indexes if the third tuple value is provided
        for col_name, _, index_name in columns:
            if index_name:
                index_query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({col_name});"
                self.execute_query(index_query)

    def __init_tables(self):
        tab_video_col = [
            ('id', 'INTEGER PRIMARY KEY', None),

            ('message_id', 'INTEGER NOT NULL', 'idx_video_message_id'),
            ('dialog_id', 'INTEGER NOT NULL', 'idx_video_dialog_id'),

            ('name', 'TEXT', None),
            ('size', 'INTEGER', None),
            ('height', 'REAL', None),
            ('width', 'REAL', None),
            ('bitrate', 'INTEGER', None),
            ('duration', 'REAL', None),
            
            ('created_at', 'timestamp NOT NULL', None),
            ('video_date', 'timestamp',  None),
            
            ('status', 'INTEGER NOT NULL', None),
            ('flag_favorited', 'INTEGER NOT NULL', None),
            
            ('ocr', "TEXT", None),
            ('processing_time', "INTEGER", None)
        ]

        tab_worker_session_col = [
            ('id', 'INTEGER PRIMARY KEY', None),

            ('user_id', 'INTEGER NOT NULL', 'idx_user_id'),
            ('dialog_id', 'INTEGER NOT NULL','idx_dialog_id'),

            ('last_scan_message_id', 'INTEGER', None)
        ]

        self.__create_table(DB.tab_video, tab_video_col)
        self.__create_table(DB.tab_worker_session, tab_worker_session_col)

    def __fetch_data(self, table_name: str, ref: object, filter: Filter = Filter()) -> List[object]:
        fields = vars(ref)
        where_conditions = []

        for field, value in fields.items():
            if value is not None and field:
                where_conditions.append(f"{field} = {value}")

        where_clause = " AND ".join(where_conditions)

        sort_clause = ''
        if filter.sort_by:
            sort_clause = f"ORDER BY {filter.sort_by} {filter.sort_direction}"

        query = f"SELECT * FROM {table_name}"
        if where_conditions:
            query += f" WHERE {where_clause}"

        query += f" {sort_clause} LIMIT {filter.limit} OFFSET {filter.offset}"

        return self.execute_query(query)

    def __insert_table(self, table_name: str, obj: object, obtain_data=False):
        columns = ', '.join(vars(obj).keys())
        placeholders = ', '.join(['?' for _ in range(len(vars(obj)))])
        insert_query = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'
        values = tuple(vars(obj).values())
        self.execute_query(insert_query, *values)

    def __update_table(self, table_name: str, obj: object) -> None:
        update_fields = [f"{key} = ?" for key, value in vars(obj).items() if value is not None]
        set_clause = ', '.join(update_fields)
        update_query = f'UPDATE {table_name} SET {set_clause} WHERE id = ?'
        values = tuple(value for value in vars(obj).values() if value is not None) + (obj.id,)
        self.execute_query(update_query, *values)

    def __delete_from_table(self, table_name: str, record_id: int) -> None:
        delete_query = f'DELETE FROM {table_name} WHERE id = ?'
        self.execute_query(delete_query, record_id)

    def get_videos(self, ref: Video, filter:Filter) -> List[Video]:
        rows = self.__fetch_data(DB.tab_video, ref, filter)
        videos = [Video(*row) for row in rows]
        return videos

    def insert_video(self, obj: Video) -> None:
        self.__insert_table(DB.tab_video, obj)

    def update_video(self, new: Video) -> None:
        self.__update_table(DB.tab_video, new)

    def upsert_video(self, video: Video) -> None:
        self.logger.debug(f"upsert_video: Upserting video {video.id}")
        update = False
        try:
            video.flag_favorited = 0
            self.insert_video(video)
            self.logger.debug(f"upsert_video: Complete to insert video {video.id}")
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' in e.__str__():
                self.logger.debug(f"upsert_video: Update instead {video.id}")
                update = True
            else:
                self.logger.error(f"upsert_video: Error integrity error on insert video {video.id} | {e}")
        except Exception as e:
            self.logger.error(f"upsert_video: Error on insert video {video.id} | {e}")
        
        if update:
            self.update_video(video)
            self.logger.debug(f"upsert_video: Complete to update video {video.id}")

    def get_worker_sessions(self, ref: WorkerSession, filter:Filter) -> List[WorkerSession]:
        rows = self.__fetch_data(DB.tab_worker_session, ref, filter)
        worker_sessions = [WorkerSession(*row) for row in rows]
        return worker_sessions

    def insert_worker_session(self, obj: WorkerSession) -> None:
        self.__insert_table(DB.tab_worker_session, obj)

    def update_worker_session(self, new: WorkerSession) -> None:
        self.__update_table(DB.tab_worker_session, new)

    def delete_video(self, video_id: int) -> None:
        self.__delete_from_table(DB.tab_video, video_id)

    def delete_worker_session(self, session_id: int) -> None:
        self.__delete_from_table(DB.tab_worker_session, session_id)

# Example usage
if __name__ == "__main__":
    db = DB()

    # Execute a query
    result = db.execute_query("SELECT * FROM tab_video")
    print(result)
