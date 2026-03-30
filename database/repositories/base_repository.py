class BaseRepository:
    ID_FIELD = None

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.session_factory = self.db_manager._get_sqlalchemy_session_factory()
        self.model = self._map_model()
        self.column_names = list(self.model.__table__.columns.keys())

    def _map_model(self):
        raise NotImplementedError()

    def _resolve_id_field(self, id_field=None):
        resolved_id_field = id_field or self.ID_FIELD
        if not resolved_id_field:
            raise ValueError("ID field non configurato per questo repository.")
        return resolved_id_field

    def _build_filtered_query(self, session, filters=None, order_by=None):
        query = session.query(self.model)
        for field_name, field_value in (filters or {}).items():
            query = query.filter(getattr(self.model, field_name) == field_value)
        if order_by:
            query = query.order_by(getattr(self.model, order_by))
        return query

    def get_all(self, filters=None, order_by=None):
        with self.session_factory() as session:
            return self._build_filtered_query(session, filters=filters, order_by=order_by).all()

    def get_by_id(self, entity_id, id_field=None):
        resolved_id_field = self._resolve_id_field(id_field)
        with self.session_factory() as session:
            return self._build_filtered_query(session, filters={resolved_id_field: entity_id}).one_or_none()

    def get_first_by_filters(self, filters=None, order_by=None):
        with self.session_factory() as session:
            return self._build_filtered_query(session, filters=filters, order_by=order_by).first()

    def add(self, values):
        with self.session_factory.begin() as session:
            entity = self.model()
            for field_name, field_value in values.items():
                setattr(entity, field_name, field_value)
            session.add(entity)
            session.flush()
            return entity

    def update_by_id(self, entity_id, values, id_field=None):
        resolved_id_field = self._resolve_id_field(id_field)
        return self.update_by_filters({resolved_id_field: entity_id}, values)

    def update_by_filters(self, filters, values):
        with self.session_factory.begin() as session:
            entity = self._build_filtered_query(session, filters=filters).one_or_none()
            if entity is None:
                return None
            for field_name, field_value in values.items():
                setattr(entity, field_name, field_value)
            session.flush()
            return entity

    def delete_by_id(self, entity_id, id_field=None):
        resolved_id_field = self._resolve_id_field(id_field)
        return self.delete_by_filters({resolved_id_field: entity_id})

    def delete_by_filters(self, filters):
        with self.session_factory.begin() as session:
            entity = self._build_filtered_query(session, filters=filters).one_or_none()
            if entity is None:
                return False
            session.delete(entity)
            return True
