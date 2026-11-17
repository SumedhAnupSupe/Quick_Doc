"""Imports every model module so Base.metadata (and Alembic autogenerate) sees all tables."""
import app.modules.academics.models  # noqa: F401
import app.modules.audit.models  # noqa: F401
import app.modules.auth.models  # noqa: F401
import app.modules.documents.models  # noqa: F401
import app.modules.duplicates.models  # noqa: F401
import app.modules.enrolments.models  # noqa: F401
import app.modules.imports.models  # noqa: F401
import app.modules.institutions.models  # noqa: F401
import app.modules.persons.models  # noqa: F401
import app.modules.users.models  # noqa: F401
import app.modules.verification.models  # noqa: F401
