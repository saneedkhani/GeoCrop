from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.db.models import Base

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Only manage GeoCrop's own tables; ignore PostGIS tiger/topology tables in the image."""
    if type_ == "table" and reflected and compare_to is None:
        return False
    return alembic_helpers.include_object(obj, name, type_, reflected, compare_to)


def run_migrations_online() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
        context.configure(connection=conn, target_metadata=target_metadata,
                          include_object=include_object,
                          process_revision_directives=alembic_helpers.writer,
                          render_item=alembic_helpers.render_item, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
