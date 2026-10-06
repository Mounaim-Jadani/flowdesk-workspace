# Baseline : WebSocket Typing Indicators

Ce dossier doit contenir 3 captures d'écran servant de référence (baseline) pour garantir le bon fonctionnement des WebSockets concernant l'indicateur de frappe (`typing indicator`).

**Toute sous-tâche future qui casserait un de ces trois comportements sera considérée en échec.**

Veuillez y ajouter manuellement :
1. `outgoing_typing.png` : Trame sortante `{type: "typing", is_typing: true}` (depuis l'onglet Network > WS du navigateur 1).
2. `incoming_typing.png` : Trame entrante équivalente (depuis l'onglet Network > WS du navigateur 2).
3. `ui_typing_indicator.png` : L'indicateur visuel dans l'interface utilisateur ("Alice est en train d'écrire...").
