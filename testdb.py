import logging
from tgss.internal.db import DB
from tgss.internal.model import Video, WorkerSession, Filter

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    # Create a DB instance
    db = DB('test.db')

    # Insert a video record
    video = Video(file_id=1, message_id=1, dialog_id=1, name='Sample Video', size=1024, height=720, width=1280, bitrate=2500, duration=60.0, status='AVAILABLE')
    db.insert_video(video)
    logging.info('Inserted video: %s', video)

    # Retrieve all videos
    videos = db.get_video(Video(), Filter(limit=5, offset=0))
    logging.info('Retrieved videos: %s', videos)

    # Update a video record
    video.name = 'Updated Video'
    db.update_video(video)
    logging.info('Updated video: %s', video)

    # Delete a video record
    db.delete_video(video.id)
    logging.info('Deleted video with ID: %s', video.id)

    # Insert a worker session record
    session = WorkerSession(user_id=1, dialog_id=1, last_scan_message_id=1001)
    db.insert_worker_session(session)
    logging.info('Inserted worker session: %s', session)

    # Retrieve all worker sessions
    worker_sessions = db.get_worker_session(WorkerSession(), Filter(limit=5, offset=0))
    logging.info('Retrieved worker sessions: %s', worker_sessions)

    # Update a worker session record
    session.last_scan_message_id = 2001
    db.update_worker_session(session)
    logging.info('Updated worker session: %s', session)

    # Delete a worker session record
    db.delete_worker_session(session.id)
    logging.info('Deleted worker session with ID: %s', session.id)

    # Close the database connection
    db.conn.close()

if __name__ == '__main__':
    main()
