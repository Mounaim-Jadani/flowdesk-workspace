def serialize_item(item):
    """
    Serializes an ActionItem instance into a dictionary.
    """
    # Gestion robuste de la date (string en mémoire vs datetime object)
    due_at_str = None
    if item.due_at:
        due_at_str = item.due_at if isinstance(item.due_at, str) else item.due_at.isoformat()

    return {
        'id': str(item.id),
        'room_id': str(item.room_id),
        'description': item.description,
        'assignee': {
            'id': item.assignee.id,
            'username': item.assignee.username,
        } if item.assignee else None,
        'created_by': {
            'id': item.created_by.id,
            'username': item.created_by.username,
        } if item.created_by else None,
        'due_at': due_at_str,
        'status': item.status,
        'source_message_id': str(item.source_message_id) if item.source_message_id else None,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'completed_at': item.completed_at.isoformat() if item.completed_at else None,
    }
