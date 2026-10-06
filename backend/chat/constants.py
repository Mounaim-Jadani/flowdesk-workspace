# Capacités = identifiants snake_case partagés backend/frontend
CAP_CHECKLIST = "checklist"
CAP_CATCH_ME_UP = "catch_me_up"
CAP_DECISIONS = "decisions"
CAP_DEEP_WORK = "deep_work"
CAP_TRANSLATION = "translation"
CAP_KARMA = "karma"
CAP_NOTIFICATION_ROUTING = "notification_routing"
CAP_PULSE = "pulse_survey"           # groupes uniquement
CAP_ONE_ON_ONE_SYNC = "one_on_one_sync"  # DM uniquement
CAP_STRUCTURED = "structured_fields"
CAP_COMMANDS = "commands"
CAP_WELLBEING = "wellbeing"

GROUP_CAPABILITIES = [CAP_CHECKLIST, CAP_CATCH_ME_UP, CAP_DECISIONS, CAP_DEEP_WORK,
                      CAP_TRANSLATION, CAP_KARMA, CAP_NOTIFICATION_ROUTING, CAP_PULSE,
                      CAP_COMMANDS, CAP_WELLBEING]

DM_CAPABILITIES = [CAP_CHECKLIST, CAP_CATCH_ME_UP, CAP_DECISIONS, CAP_DEEP_WORK,
                   CAP_TRANSLATION, CAP_NOTIFICATION_ROUTING, CAP_ONE_ON_ONE_SYNC,
                   CAP_STRUCTURED, CAP_COMMANDS, CAP_WELLBEING]

MESSAGE_TYPE_TO_CAPABILITY = {
    'checklist_item_create': CAP_CHECKLIST,
    'checklist_toggle': CAP_CHECKLIST,
    'decision_pin': CAP_DECISIONS,
    'pulse_vote': CAP_PULSE,
    # Note : chaque EPIC futur DOIT y ajouter sa ligne
}
