from datetime import datetime, timedelta, time

from flask import current_app
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from app import db
from app.models import Notification, NotificationHistory, FactNotificationStatus
from app.utils import convert_bst_to_utc


def fetch_notification_status_for_day(process_day, service_id=None):
    start_date = convert_bst_to_utc(datetime.combine(process_day, time.min))
    end_date = convert_bst_to_utc(datetime.combine(process_day + timedelta(days=1), time.min))
    # use notification_history if process day is older than 7 days
    # this is useful if we need to rebuild the ft_billing table for a date older than 7 days ago.
    current_app.logger.info("Fetch ft_notification_status for {} to {}".format(start_date, end_date))
    table = Notification
    if start_date < datetime.utcnow() - timedelta(days=7):
        table = NotificationHistory

    transit_data = db.session.query(
        table.template_id,
        table.service_id,
        func.coalesce(table.job_id, '00000000-0000-0000-0000-000000000000').label('job_id'),
        table.notification_type,
        table.key_type,
        table.status,
        func.count().label('notification_count')
    ).filter(
        table.created_at >= start_date,
        table.created_at < end_date
    ).group_by(
        table.template_id,
        table.service_id,
        'job_id',
        table.notification_type,
        table.key_type,
        table.status
    )

    if service_id:
        transit_data = transit_data.filter(table.service_id == service_id)

    return transit_data.all()


def update_fact_notification_status(data, process_day):
    table = FactNotificationStatus.__table__
    '''
       This uses the Postgres upsert to avoid race conditions when two threads try to insert
       at the same row. The excluded object refers to values that we tried to insert but were
       rejected.
       http://docs.sqlalchemy.org/en/latest/dialects/postgresql.html#insert-on-conflict-upsert
    '''
    for row in data:
        stmt = insert(table).values(
            bst_date=process_day.date(),
            template_id=row.template_id,
            service_id=row.service_id,
            job_id=row.job_id,
            notification_type=row.notification_type,
            key_type=row.key_type,
            notification_status=row.status,
            notification_count=row.notification_count,
        )

        stmt = stmt.on_conflict_do_update(
            constraint="ft_notification_status_pkey",
            set_={"notification_count": stmt.excluded.notification_count,
                  "updated_at": datetime.utcnow()
                  }
        )
        db.session.connection().execute(stmt)
        db.session.commit()
